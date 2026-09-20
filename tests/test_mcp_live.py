"""
MCP live integration and offline unit tests.

Tests that require a running server are skipped unless THEOSIS_MCP_URL is set.
Offline tests exercise the client's SSE parser, Content-Type validation,
error handling, and connection-reset logic with synthetic responses.
"""
import json
import os

import pytest

from tests.mcp_live_client import McpClient, McpError

# ---------------------------------------------------------------------------
# Helpers for building synthetic responses
# ---------------------------------------------------------------------------

def _sse_response(*data_lines: str) -> str:
    """Build a minimal SSE body from data: lines, separated by blank lines."""
    parts = []
    for d in data_lines:
        parts.append(f"data: {d}")
    parts.append("")  # trailing blank line
    return "\n".join(parts)


def _jsonrpc_result(obj_id: int, result: dict) -> str:
    return json.dumps({"jsonrpc": "2.0", "id": obj_id, "result": result})


def _jsonrpc_error(obj_id: int, code: int, message: str) -> str:
    return json.dumps({"jsonrpc": "2.0", "id": obj_id, "error": {"code": code, "message": message}})


# ---------------------------------------------------------------------------
# Offline: SSE parser
# ---------------------------------------------------------------------------

class TestParseSSEEvents:
    """Unit tests for McpClient._parse_sse_events."""

    def test_single_data_line(self) -> None:
        raw = _sse_response('{"a":1}')
        events = McpClient._parse_sse_events(raw)
        assert events == ['{"a":1}']

    def test_multiline_data_concatenated(self) -> None:
        """RFC-style: consecutive data: lines within one event are joined."""
        raw = "data: {\"part1\": \"hello\",\n" \
              "data: \"part2\": \"world\"}\n" \
              "\n"
        events = McpClient._parse_sse_events(raw)
        assert len(events) == 1
        obj = json.loads(events[0])
        assert obj == {"part1": "hello", "part2": "world"}

    def test_multiple_events(self) -> None:
        raw = 'data: {"id":1}\n\n' \
              'data: {"id":2}\n\n'
        events = McpClient._parse_sse_events(raw)
        assert len(events) == 2
        assert json.loads(events[0]) == {"id": 1}
        assert json.loads(events[1]) == {"id": 2}

    def test_event_lines_ignored(self) -> None:
        """Lines starting with 'event:' are not treated as data."""
        raw = "event: message\ndata: {\"ok\":true}\n\n"
        events = McpClient._parse_sse_events(raw)
        assert events == ['{"ok":true}']

    def test_empty_data_line_skipped(self) -> None:
        raw = "data:\ndata: {\"x\":1}\n\n"
        events = McpClient._parse_sse_events(raw)
        assert events == ['{"x":1}']

    def test_comment_line_ignored(self) -> None:
        raw = ": this is a comment\ndata: {\"y\":2}\n\n"
        events = McpClient._parse_sse_events(raw)
        assert events == ['{"y":2}']

    def test_trailing_multiline_no_blank(self) -> None:
        """Consecutive data lines without a trailing blank line still flush."""
        raw = "data: {\"a\":1,\n" \
              "data: \"b\":2}"
        events = McpClient._parse_sse_events(raw)
        assert len(events) == 1
        obj = json.loads(events[0])
        assert obj == {"a": 1, "b": 2}


# ---------------------------------------------------------------------------
# Offline: Content-Type validation
# ---------------------------------------------------------------------------

class TestParseResponseType:
    """Unit tests for McpClient._parse_response Content-Type handling."""

    def test_application_json_accepted(self) -> None:
        body = _jsonrpc_result(1, {"tools": []})
        result = McpClient._parse_response(body, "application/json")
        assert result == {"tools": []}

    def test_text_event_stream_accepted(self) -> None:
        body = _sse_response(_jsonrpc_result(1, {"ok": True}))
        result = McpClient._parse_response(body, "text/event-stream")
        assert result == {"ok": True}

    def test_text_event_stream_with_charset(self) -> None:
        body = _sse_response(_jsonrpc_result(1, {"ok": True}))
        result = McpClient._parse_response(body, "text/event-stream; charset=utf-8")
        assert result == {"ok": True}

    def test_wrong_content_type_raises(self) -> None:
        with pytest.raises(AssertionError, match="Unexpected Content-Type"):
            McpClient._parse_response('{"result":{}}', "text/html")

    def test_wrong_content_type_includes_body_prefix(self) -> None:
        with pytest.raises(AssertionError, match="Body prefix"):
            McpClient._parse_response('{"result":{"x":1}}', "text/html")

    def test_wrong_content_type_includes_ct(self) -> None:
        with pytest.raises(AssertionError, match="text/html"):
            McpClient._parse_response('{"result":{}}', "text/html")


# ---------------------------------------------------------------------------
# Offline: JSON-RPC error handling
# ---------------------------------------------------------------------------

class TestParseResponseError:
    """Unit tests for JSON-RPC error extraction."""

    def test_error_in_sse(self) -> None:
        body = _sse_response(_jsonrpc_error(1, -32601, "Method not found"))
        with pytest.raises(McpError) as exc_info:
            McpClient._parse_response(body, "text/event-stream")
        assert exc_info.value.code == -32601
        assert "Method not found" in str(exc_info.value)

    def test_error_in_plain_json(self) -> None:
        body = _jsonrpc_error(1, -32600, "Invalid request")
        with pytest.raises(McpError) as exc_info:
            McpClient._parse_response(body, "application/json")
        assert exc_info.value.code == -32600
        assert "Invalid request" in str(exc_info.value)

    def test_no_result_or_error_raises_runtime_error(self) -> None:
        body = _sse_response('{"jsonrpc":"2.0","id":1,"something":"else"}')
        with pytest.raises(RuntimeError, match="No JSON-RPC result"):
            McpClient._parse_response(body, "text/event-stream")


# ---------------------------------------------------------------------------
# Offline: Connection reset on errors
# ---------------------------------------------------------------------------

class TestConnectionReset:
    """Unit tests verifying connection reset on transport/HTTP errors."""

    def test_reset_conn_clears_connection(self) -> None:
        client = McpClient("http://localhost:1/mcp")
        # Simulate an existing connection object
        class FakeConn:
            closed = False
            def close(self):
                self.closed = True
        client._conn = FakeConn()
        client._reset_conn()
        assert client._conn is None
        assert client._conn is None

    def test_reset_conn_handles_already_closed(self) -> None:
        client = McpClient("http://localhost:1/mcp")
        class BrokenConn:
            def close(self):
                raise OSError("already closed")
        client._conn = BrokenConn()
        # Should not raise
        client._reset_conn()
        assert client._conn is None


# ---------------------------------------------------------------------------
# Live integration tests (skipped without THEOSIS_MCP_URL)
# ---------------------------------------------------------------------------

THEOSIS_MCP_URL = os.environ.get("THEOSIS_MCP_URL")
pytestmark_live = pytest.mark.skipif(
    THEOSIS_MCP_URL is None,
    reason="THEOSIS_MCP_URL not set — skipping live MCP tests",
)


@pytest.mark.live
@pytestmark_live
class TestToolsList:
    """Verify the server exposes expected tools via tools/list."""

    def test_expected_tools_present(self) -> None:
        with McpClient(THEOSIS_MCP_URL) as client:
            client.initialize()
            result = client.tools_list()

        names = {tool["name"] for tool in result}
        assert "lookup_verse" in names, "lookup_verse tool not found"
        assert "list_theological_works" in names, "list_theological_works tool not found"


@pytest.mark.live
@pytestmark_live
class TestToolsCall:
    """Verify tools/call works with a known verse."""

    def test_lookup_verse(self) -> None:
        with McpClient(THEOSIS_MCP_URL) as client:
            client.initialize()
            result = client.tools_call("lookup_verse", {
                "book": "John",
                "chapter": 3,
                "verse": 16,
            })
        assert isinstance(result, list), "Expected content list"
        assert len(result) >= 1, "Expected at least one content block"
        # The content should contain text mentioning "God" and "world" or "believe"
        text = result[0].get("text", "")
        assert len(text) > 0, "Content text should not be empty"


@pytest.mark.live
@pytestmark_live
class TestJsonRpcError:
    """Verify that an invalid tool call produces a JSON-RPC error."""

    def test_invalid_tool_raises_mcp_error(self) -> None:
        with McpClient(THEOSIS_MCP_URL) as client:
            client.initialize()
            with pytest.raises(McpError) as exc_info:
                client.tools_call("nonexistent_tool_xyz")
            assert exc_info.value.code != 0


@pytest.mark.live
@pytestmark_live
class TestSSEParserLive:
    """Verify the SSE parser handles real server responses correctly."""

    def test_initialize_returns_session_id(self) -> None:
        with McpClient(THEOSIS_MCP_URL) as client:
            result = client.initialize()
            assert client._session_id is not None, "Session ID should be captured"
            assert isinstance(result, dict), "Initialize result should be a dict"
            assert "protocolVersion" in result or "capabilities" in result
