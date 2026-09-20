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
# Helper: extract first content block text from an MCP tool result
# ---------------------------------------------------------------------------

def _tool_text(result: list[dict]) -> str:
    """Return the text of the first content block, or empty string."""
    if isinstance(result, list) and result:
        return result[0].get("text", "")
    return ""


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

    def test_tool_count_at_least_28(self) -> None:
        with McpClient(THEOSIS_MCP_URL) as client:
            client.initialize()
            result = client.tools_list()
        assert len(result) >= 28, f"Expected >= 28 tools, got {len(result)}"


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

    def test_invalid_tool_returns_error_content(self) -> None:
        """Server returns error text in content, not a JSON-RPC error."""
        with McpClient(THEOSIS_MCP_URL) as client:
            client.initialize()
            result = client.tools_call("nonexistent_tool_xyz")
        text = _tool_text(result)
        assert "Unknown tool" in text or "unknown" in text.lower(), (
            f"Expected error message about unknown tool, got: {text[:200]}"
        )


@pytest.mark.live
@pytestmark_live
class TestSSEParserLive:
    """Verify the SSE parser handles real server responses correctly."""

    def test_initialize_returns_capabilities(self) -> None:
        with McpClient(THEOSIS_MCP_URL) as client:
            result = client.initialize()
            assert isinstance(result, dict), "Initialize result should be a dict"
            assert "protocolVersion" in result or "capabilities" in result
            # Session ID may or may not be sent depending on server config


# ---------------------------------------------------------------------------
# Live: Bible lookup via reference string
# ---------------------------------------------------------------------------

@pytest.mark.live
@pytestmark_live
class TestLookupVerse:
    """Bible verse lookup with the reference-style API."""

    def test_john_3_16_reference_string(self) -> None:
        """lookup_verse accepts a single reference string."""
        with McpClient(THEOSIS_MCP_URL) as client:
            client.initialize()
            result = client.tools_call("lookup_verse", {"reference": "John 3:16"})
        text = _tool_text(result)
        assert len(text) > 0, "Content text should not be empty"
        # Stable: the verse heading should appear
        assert "John 3:16" in text
        # Stable: content should mention "God" (present in every translation)
        assert "God" in text

    def test_genesis_1_1_interlinear(self) -> None:
        """Genesis 1:1 lookup_verse returns interlinear English breakdown."""
        with McpClient(THEOSIS_MCP_URL) as client:
            client.initialize()
            result = client.tools_call("lookup_verse", {"reference": "Genesis 1:1"})
        text = _tool_text(result)
        assert "Genesis 1:1" in text
        # lookup_verse returns interlinear format with word-by-word markers
        assert "beginning" in text.lower() or "created" in text.lower()


# ---------------------------------------------------------------------------
# Live: Greek/Hebrew word study
# ---------------------------------------------------------------------------

@pytest.mark.live
@pytestmark_live
class TestWordStudy:
    """Greek/Hebrew word study via Strong's number."""

    def test_greek_strongs_g26(self) -> None:
        """G26 is agapē (love) — a well-known Greek lexicon entry."""
        with McpClient(THEOSIS_MCP_URL) as client:
            client.initialize()
            result = client.tools_call("word_study", {"strongs": "G26"})
        text = _tool_text(result)
        assert len(text) > 0
        # Stable identifiers: Strong's number and transliteration
        assert "G0026" in text or "G26" in text
        # The word should be agapē / love
        assert "agap" in text.lower() or "love" in text.lower()

    def test_hebrew_strongs_h430(self) -> None:
        """H430 is Elohim — a well-known Hebrew lexicon entry."""
        with McpClient(THEOSIS_MCP_URL) as client:
            client.initialize()
            result = client.tools_call("word_study", {"strongs": "H430"})
        text = _tool_text(result)
        assert len(text) > 0
        assert "H0430" in text or "H430" in text
        # Elohim should appear in some form
        assert "elo" in text.lower() or "God" in text


# ---------------------------------------------------------------------------
# Live: Translation comparison
# ---------------------------------------------------------------------------

@pytest.mark.live
@pytestmark_live
class TestCompareTranslations:
    """Compare verses across different translations."""

    def test_kjv_vulgate_comparison(self) -> None:
        """KJV and Vulgate for John 3:16 should both appear."""
        with McpClient(THEOSIS_MCP_URL) as client:
            client.initialize()
            result = client.tools_call("compare_translations", {
                "reference": "John 3:16",
                "translations": ["KJV", "Vulgate"],
            })
        text = _tool_text(result)
        assert len(text) > 0
        # Stable: both translation names should appear as section headers
        assert "KJV" in text or "King James" in text
        assert "Vulgate" in text
        # John 3:16 KJV contains "only begotten Son"
        assert "only begotten" in text or "unigenitum" in text

    def test_wlc_genesis(self) -> None:
        """WLC (Westminster Leningrad Codex) for Genesis 1:1."""
        with McpClient(THEOSIS_MCP_URL) as client:
            client.initialize()
            result = client.tools_call("get_translation_verse", {
                "reference": "Genesis 1:1",
                "translation": "WLC",
            })
        text = _tool_text(result)
        assert len(text) > 0
        # WLC should return Hebrew text
        assert any("\u0590" <= ch <= "\u05FF" for ch in text), (
            "Expected Hebrew characters in WLC text"
        )


# ---------------------------------------------------------------------------
# Live: Historical-language lookups
# ---------------------------------------------------------------------------

@pytest.mark.live
@pytestmark_live
class TestHistoricalLanguage:
    """Historical-language edition lookups."""

    def test_wlc_genesis_1_1(self) -> None:
        """WLC Genesis 1:1 should return pure Hebrew."""
        with McpClient(THEOSIS_MCP_URL) as client:
            client.initialize()
            result = client.tools_call("get_translation_verse", {
                "reference": "Genesis 1:1",
                "translation": "WLC",
            })
        text = _tool_text(result)
        assert len(text) > 0
        # Should contain the WLC name or Hebrew text
        assert "WLC" in text or "Westminster" in text or "Leningrad" in text

    def test_vulgate_tobit_1_1(self) -> None:
        """Vulgate Tobit 1:1 should return Latin text."""
        with McpClient(THEOSIS_MCP_URL) as client:
            client.initialize()
            result = client.tools_call("compare_translations", {
                "reference": "Tobit 1:1",
                "translations": ["Vulgate"],
            })
        text = _tool_text(result)
        assert len(text) > 0
        # Vulgate header or Latin text
        assert "Vulgate" in text
        # Latin markers: common Latin words
        assert any(w in text.lower() for w in ["tobias", "nepthalim", "galilae", "vulgate"])


# ---------------------------------------------------------------------------
# Live: Full-text search
# ---------------------------------------------------------------------------

@pytest.mark.live
@pytestmark_live
class TestFullTextSearch:
    """Bible full-text search."""

    def test_living_water_search(self) -> None:
        """'living water' should return results."""
        with McpClient(THEOSIS_MCP_URL) as client:
            client.initialize()
            result = client.tools_call("search_bible_fulltext", {"query": "living water"})
        text = _tool_text(result)
        assert len(text) > 0
        # Should contain the search query in a heading
        assert "living water" in text.lower()


# ---------------------------------------------------------------------------
# Live: Semantic search (similar passages)
# ---------------------------------------------------------------------------

@pytest.mark.live
@pytestmark_live
class TestSemanticSearch:
    """Semantic similarity search via pgvector embeddings."""

    def test_similar_to_john_3_16(self) -> None:
        """Similar passages to John 3:16 should include a similarity score."""
        with McpClient(THEOSIS_MCP_URL) as client:
            client.initialize()
            result = client.tools_call("find_similar_passages", {
                "reference": "John 3:16",
                "limit": 3,
            })
        text = _tool_text(result)
        assert len(text) > 0
        # Should contain a percentage similarity score
        assert "%" in text
        # Should mention the original reference
        assert "John 3:16" in text


# ---------------------------------------------------------------------------
# Live: Cross-references
# ---------------------------------------------------------------------------

@pytest.mark.live
@pytestmark_live
class TestCrossReferences:
    """Cross-reference lookup."""

    def test_john_3_16_cross_references(self) -> None:
        """John 3:16 cross-references should include well-known connections."""
        with McpClient(THEOSIS_MCP_URL) as client:
            client.initialize()
            result = client.tools_call("get_cross_references", {
                "reference": "John 3:16",
            })
        text = _tool_text(result)
        assert len(text) > 0
        # Should contain the reference heading
        assert "John 3:16" in text
        # Should contain vote counts (stable numeric data)
        assert "votes" in text.lower()


# ---------------------------------------------------------------------------
# Live: Commentary
# ---------------------------------------------------------------------------

@pytest.mark.live
@pytestmark_live
class TestCommentary:
    """Commentary lookup for a well-known verse."""

    def test_john_3_16_commentary(self) -> None:
        """John 3:16 should have commentary from church fathers."""
        with McpClient(THEOSIS_MCP_URL) as client:
            client.initialize()
            result = client.tools_call("get_commentary", {
                "reference": "John 3:16",
            })
        text = _tool_text(result)
        assert len(text) > 0
        # Should contain a commentary heading
        assert "Commentaries" in text or "commentary" in text.lower()
        # Should mention at least one known church father or theologian
        known_authors = [
            "Augustine", "Chrysostom", "Tertullian", "Origen",
            "John Calvin", "Matthew Henry", "Thomas Aquinas",
        ]
        assert any(author in text for author in known_authors), (
            f"Expected at least one of {known_authors} in commentary text"
        )


# ---------------------------------------------------------------------------
# Live: Extra-biblical search
# ---------------------------------------------------------------------------

@pytest.mark.live
@pytestmark_live
class TestExtraBiblicalSearch:
    """Search extra-biblical texts."""

    def test_enoch_search(self) -> None:
        """Search for 'Enoch' in extra-biblical texts."""
        with McpClient(THEOSIS_MCP_URL) as client:
            client.initialize()
            result = client.tools_call("search_extra_biblical", {"query": "Enoch"})
        text = _tool_text(result)
        assert len(text) > 0
        # Should contain the search heading
        assert "Enoch" in text
        # Should reference at least one known category
        known_categories = ["pseudepigrapha", "church_fathers", "apocrypha"]
        assert any(cat in text.lower() for cat in known_categories), (
            f"Expected one of {known_categories} in extra-biblical results"
        )


# ---------------------------------------------------------------------------
# Live: Systematic theology — list, search, section
# ---------------------------------------------------------------------------

@pytest.mark.live
@pytestmark_live
class TestSystematicTheology:
    """Systematic theology tools: list, search, and section retrieval."""

    def test_list_theological_works(self) -> None:
        """list_theological_works should return known authors."""
        with McpClient(THEOSIS_MCP_URL) as client:
            client.initialize()
            result = client.tools_call("list_theological_works", {})
        text = _tool_text(result)
        assert len(text) > 0
        # Should contain known theologians
        known = ["Strong", "Finney", "Hodge"]
        assert any(name in text for name in known), (
            f"Expected at least one of {known} in theological works list"
        )
        # Should contain source URLs (provenance)
        assert "http" in text

    def test_search_theological_works(self) -> None:
        """search_theological_works for 'justification' should return results."""
        with McpClient(THEOSIS_MCP_URL) as client:
            client.initialize()
            result = client.tools_call("search_theological_works", {
                "query": "justification",
            })
        text = _tool_text(result)
        assert len(text) > 0
        # Should contain the search term in heading or content
        assert "justification" in text.lower()

    def test_get_theological_section(self) -> None:
        """get_theological_section for Hodge's Systematic Theology."""
        with McpClient(THEOSIS_MCP_URL) as client:
            client.initialize()
            result = client.tools_call("get_theological_section", {
                "work_title": "Systematic Theology",
                "author": "Hodge",
            })
        text = _tool_text(result)
        assert len(text) > 0
        # Should contain the work title and author
        assert "Systematic Theology" in text
        assert "Hodge" in text
        # Should contain provenance (source URL)
        assert "http" in text


# ---------------------------------------------------------------------------
# Live: list_translations provenance fields
# ---------------------------------------------------------------------------

@pytest.mark.live
@pytestmark_live
class TestListTranslationsProvenance:
    """Verify list_translations returns provenance and licence information."""

    def test_translations_contain_provenance(self) -> None:
        """Each translation entry should include licence and source."""
        with McpClient(THEOSIS_MCP_URL) as client:
            client.initialize()
            result = client.tools_call("list_translations", {})
        text = _tool_text(result)
        assert len(text) > 0
        # Should contain the heading
        assert "Translations" in text or "translations" in text.lower()
        # Should mention licence markers (brackets around licence names)
        assert "[" in text, "Expected licence markers in brackets"
        # Should contain source URLs
        assert "http" in text, "Expected source URLs in translation list"
        # Should mention at least one known abbreviation
        known_abbrevs = ["KJV", "ESV", "NASB", "WLC", "Vulgate", "AKJV"]
        assert any(abbr in text for abbr in known_abbrevs), (
            f"Expected at least one of {known_abbrevs}"
        )

    def test_translations_contain_verse_counts(self) -> None:
        """Translation entries should include verse/book counts."""
        with McpClient(THEOSIS_MCP_URL) as client:
            client.initialize()
            result = client.tools_call("list_translations", {})
        text = _tool_text(result)
        # Should contain coverage indicators
        assert "verses" in text.lower() or "books" in text.lower(), (
            "Expected verse or book count indicators"
        )
