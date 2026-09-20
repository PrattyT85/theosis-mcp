"""
Minimal MCP JSON-RPC client using only Python standard library.

Supports the MCP Streamable HTTP transport:
  - POST /mcp  with  Content-Type: application/json  +  Accept: text/event-stream
  - Server replies with SSE; each event block may carry one or more ``data:``
    lines whose concatenation (joined by ``\\n``) forms a single JSON-RPC message.
  - Session tracking via the ``Mcp-Session-Id`` response header.
"""

from __future__ import annotations

import http.client
import json
from urllib.parse import urlparse


class McpError(Exception):
    """Raised when the server returns a JSON-RPC error."""

    def __init__(self, code: int, message: str, data=None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f"JSON-RPC error {code}: {message}")


class McpClient:
    """Synchronous MCP JSON-RPC client over Streamable HTTP."""

    def __init__(self, endpoint_url: str, *, timeout: float = 30.0):
        parsed = urlparse(endpoint_url)
        self._host: str = parsed.hostname or ""
        self._port = parsed.port or (443 if parsed.scheme == "https" else 80)
        self._path = parsed.path or "/mcp"
        self._use_ssl = parsed.scheme == "https"
        self._timeout = timeout
        self._session_id: str | None = None
        self._conn: http.client.HTTPConnection | http.client.HTTPSConnection | None = None
        self._request_id = 0
        self._initialized = False

    # -- connection lifecycle --------------------------------------------------

    def _ensure_conn(self) -> http.client.HTTPConnection:
        if self._conn is None:
            if self._use_ssl:
                self._conn = http.client.HTTPSConnection(
                    self._host, self._port, timeout=self._timeout
                )
            else:
                self._conn = http.client.HTTPConnection(
                    self._host, self._port, timeout=self._timeout
                )
        return self._conn

    def _reset_conn(self) -> None:
        """Close and discard the underlying connection so the next call reconnects."""
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    def close(self) -> None:
        self._reset_conn()

    def __enter__(self) -> "McpClient":
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    # -- low-level JSON-RPC transport ------------------------------------------

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _capture_session_id(self, resp: http.client.HTTPResponse) -> None:
        """Capture ``Mcp-Session-Id`` from any response that carries it."""
        sid = resp.headers.get("mcp-session-id")
        if sid is not None:
            self._session_id = sid

    def _request_headers(self, body_len: int) -> dict[str, str]:
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Content-Length": str(body_len),
        }
        if self._session_id is not None:
            headers["Mcp-Session-Id"] = self._session_id
        return headers

    def _post_notification(self, method: str, params: dict | None = None) -> None:
        """Send a JSON-RPC notification (no id, no response expected).

        Checks the HTTP status and resets the connection on transport errors
        so the next call can reconnect cleanly.
        """
        conn = self._ensure_conn()
        payload: dict = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        body = json.dumps(payload).encode()
        headers = self._request_headers(len(body))

        try:
            conn.request("POST", self._path, body=body, headers=headers)
            resp = conn.getresponse()
            self._capture_session_id(resp)
            status = resp.status
            resp.read()  # consume body
        except Exception:
            self._reset_conn()
            raise

        if status >= 400:
            self._reset_conn()
            raise ConnectionError(
                f"Notification HTTP {status} for method {method!r}"
            )

    def _post_jsonrpc(self, method: str, params: dict | None = None) -> dict:
        """Send a JSON-RPC request and return the parsed result (or raise).

        Resets the connection on transport or HTTP errors.
        """
        conn = self._ensure_conn()
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        body = json.dumps(payload).encode()
        headers = self._request_headers(len(body))

        try:
            conn.request("POST", self._path, body=body, headers=headers)
            resp = conn.getresponse()
            self._capture_session_id(resp)

            content_type = resp.headers.get("content-type", "")
            status = resp.status
            raw = resp.read().decode()
        except Exception:
            self._reset_conn()
            raise

        if status >= 400:
            self._reset_conn()
            raise ConnectionError(
                f"JSON-RPC HTTP {status} for method {method!r}: {raw[:300]}"
            )

        return self._parse_response(raw, content_type)

    # -- response parsing ------------------------------------------------------

    @staticmethod
    def _parse_sse_events(raw: str) -> list[str]:
        """Parse an SSE text body into a list of concatenated ``data:`` payloads.

        Consecutive ``data:`` lines within one event block are joined with
        ``\\n`` to reconstruct multi-line JSON payloads (RFC 8895 §9.2).
        An empty line delimits event blocks.
        """
        payloads: list[str] = []
        data_lines: list[str] = []

        for line in raw.splitlines():
            if line.startswith("data:"):
                stripped = line[len("data:"):].strip()
                if stripped:
                    data_lines.append(stripped)
            elif line == "" or line.startswith("event:") or line.startswith("id:"):
                # Blank line or other SSE field ⇒ end of current event block
                if data_lines:
                    payloads.append("\n".join(data_lines))
                    data_lines = []
            # Ignore comment lines (starting with ':')

        # Flush any trailing data lines without a trailing blank line
        if data_lines:
            payloads.append("\n".join(data_lines))

        return payloads

    @classmethod
    def _parse_response(cls, raw: str, content_type: str) -> dict:
        """Validate Content-Type and extract the JSON-RPC result.

        Accepts ``application/json`` or ``text/event-stream`` (with optional
        ``charset`` parameter).  Raises ``AssertionError`` for anything else.
        """
        ct_lower = content_type.lower()
        is_sse = "text/event-stream" in ct_lower
        is_json = "application/json" in ct_lower

        if not (is_sse or is_json):
            raise AssertionError(
                f"Unexpected Content-Type: {content_type!r}. "
                f"Expected application/json or text/event-stream. "
                f"Body prefix: {raw[:300]}"
            )

        if is_sse:
            payloads = cls._parse_sse_events(raw)
        else:
            # Plain JSON response — wrap as a single payload
            payloads = [raw.strip()]

        result_obj: dict | None = None
        for payload_str in payloads:
            if not payload_str:
                continue
            try:
                obj = json.loads(payload_str)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and ("result" in obj or "error" in obj):
                result_obj = obj
                break

        if result_obj is None:
            raise RuntimeError(
                f"No JSON-RPC result found in server response:\n{raw[:500]}"
            )

        if "error" in result_obj:
            err = result_obj["error"]
            raise McpError(
                code=err.get("code", -1),
                message=err.get("message", "unknown error"),
                data=err.get("data"),
            )

        return result_obj["result"]

    # -- high-level MCP operations --------------------------------------------

    def initialize(self) -> dict:
        """Send the MCP ``initialize`` handshake.

        Returns the server capabilities dict.
        """
        result = self._post_jsonrpc(
            "initialize",
            params={
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "theosis-live-test-client",
                    "version": "0.1.0",
                },
            },
        )
        # Send the notifications/initialized notification (no id, no response)
        self._post_notification("notifications/initialized")
        self._initialized = True
        return result

    def tools_list(self) -> list[dict]:
        """Call ``tools/list`` and return the list of tool descriptors."""
        result = self._post_jsonrpc("tools/list")
        return result.get("tools", result) if isinstance(result, dict) else result

    def tools_call(self, name: str, arguments: dict | None = None) -> list[dict]:
        """Call a named MCP tool and return the content list."""
        params: dict = {"name": name}
        if arguments:
            params["arguments"] = arguments
        result = self._post_jsonrpc("tools/call", params)
        return result.get("content", result) if isinstance(result, dict) else result


def tool_text(result: list[dict]) -> str:
    """Return the text of the first content block, or empty string."""
    if isinstance(result, list) and result:
        return result[0].get("text", "")
    return ""
