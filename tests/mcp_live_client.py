"""
Minimal MCP JSON-RPC client using only Python standard library.

Supports the MCP Streamable HTTP transport:
  - POST /mcp  with  Content-Type: application/json  +  Accept: text/event-stream
  - Server replies with SSE; each "data:" line carries a JSON-RPC response.
  - Session tracking via the ``Mcp-Session-Id`` response header.
"""

from __future__ import annotations

import http.client
import json
import uuid
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

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "McpClient":
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    # -- low-level JSON-RPC transport ------------------------------------------

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _post_notification(self, method: str, params: dict | None = None) -> None:
        """Send a JSON-RPC notification (no id, no response expected)."""
        conn = self._ensure_conn()
        payload: dict = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        body = json.dumps(payload).encode()
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Content-Length": str(len(body)),
        }
        if self._session_id is not None:
            headers["Mcp-Session-Id"] = self._session_id

        conn.request("POST", self._path, body=body, headers=headers)
        resp = conn.getresponse()
        # Consume the response body but ignore it (notification has no result)
        resp.read()

    def _post_jsonrpc(self, method: str, params: dict | None = None) -> dict:
        """Send a JSON-RPC request and return the parsed result (or raise)."""
        conn = self._ensure_conn()
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        body = json.dumps(payload).encode()
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Content-Length": str(len(body)),
        }
        if self._session_id is not None:
            headers["Mcp-Session-Id"] = self._session_id

        conn.request("POST", self._path, body=body, headers=headers)
        resp = conn.getresponse()

        # Capture session id from the very first response (initialize)
        if "mcp-session-id" in resp.headers:
            self._session_id = resp.headers["mcp-session-id"]

        raw = resp.read().decode()
        return self._parse_sse_response(raw)

    @staticmethod
    def _parse_sse_response(raw: str) -> dict:
        """Extract the JSON-RPC result from an SSE text body.

        SSE format has lines like::

            event: message
            data: {"jsonrpc":"2.0","id":1,"result":...}

        The last ``data:`` line carrying a JSON object with ``"result"`` or
        ``"error"`` is the one we want.
        """
        result_obj: dict | None = None
        for line in raw.splitlines():
            if line.startswith("data:"):
                data_str = line[len("data:"):].strip()
                if not data_str:
                    continue
                try:
                    obj = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                if "result" in obj or "error" in obj:
                    result_obj = obj

        if result_obj is None:
            # Maybe the server returned plain JSON (non-SSE)?
            for line in raw.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if "result" in obj or "error" in obj:
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
                "protocolVersion": "2025-03-26",
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
