"""
Live MCP JSON-RPC integration tests.

These tests require a running Theosis MCP server and are skipped
unless THEOSIS_MCP_URL is set in the environment.
"""

import os

import pytest

from tests.mcp_live_client import McpClient

THEOSIS_MCP_URL = os.environ.get("THEOSIS_MCP_URL")

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        THEOSIS_MCP_URL is None,
        reason="THEOSIS_MCP_URL not set — skipping live MCP tests",
    ),
]


class TestToolsList:
    """Verify the server exposes expected tools via tools/list."""

    def test_expected_tools_present(self) -> None:
        with McpClient(THEOSIS_MCP_URL) as client:
            client.initialize()
            result = client.tools_list()

        names = {tool["name"] for tool in result}
        assert "lookup_verse" in names, "lookup_verse tool not found"
        assert "list_theological_works" in names, "list_theological_works tool not found"
