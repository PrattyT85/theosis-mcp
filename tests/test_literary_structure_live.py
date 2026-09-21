"""Read-only live tests for the Literary Structure corpus."""

import os

import pytest

from tests.mcp_live_client import McpClient

THEOSIS_MCP_URL = os.environ.get("THEOSIS_MCP_URL")
pytestmark_live = pytest.mark.skipif(
    THEOSIS_MCP_URL is None,
    reason="THEOSIS_MCP_URL not set — skipping literary structure live tests",
)


def _client():
    if not THEOSIS_MCP_URL:
        pytest.skip("THEOSIS_MCP_URL not set")
    client = McpClient(THEOSIS_MCP_URL)
    client.initialize()
    return client


def _tool_text(result):
    return "\n".join(item.get("text", "") for item in result if item.get("type") == "text")


@pytest.mark.live
@pytestmark_live
def test_literary_sources_have_attribution():
    with _client() as client:
        text = _tool_text(client.tools_call("list_literary_structure_sources", {"limit": 3}))
    assert "Hajime Murai" in text
    assert "CC BY 4.0" in text
    assert "literarystructure.info" in text


@pytest.mark.live
@pytestmark_live
def test_genesis_structure_is_queryable():
    with _client() as client:
        text = _tool_text(client.tools_call("list_literary_structures", {"book": "Gen", "limit": 3}))
    assert "Three-Tier" not in text  # ANE is separate; this guards corpus separation.
    assert "Gen" in text
    assert "The Creation" in text
    assert "A(1:3-5)" in text


@pytest.mark.live
@pytestmark_live
def test_literary_search_returns_source_and_disclaimer():
    with _client() as client:
        text = _tool_text(client.tools_call("search_literary_structures", {"query": "creation", "book": "Gen", "limit": 3}))
    assert "Hajime Murai" in text
    assert "interpretive" in text.lower()
    assert "The Creation" in text


@pytest.mark.live
@pytestmark_live
def test_literary_parallel_cross_references_are_returned():
    with _client() as client:
        text = _tool_text(client.tools_call("get_literary_parallel", {"book": "Mat", "limit": 3}))
    assert "Cross-references" in text
    assert "Luke@" in text or "Isaiah@" in text or "Micah@" in text


@pytest.mark.live
@pytestmark_live
def test_reference_first_genesis_lookup():
    with _client() as client:
        text = _tool_text(client.tools_call("get_literary_structure_by_reference", {"reference": "Genesis 1:1", "limit": 20}))
    assert "Genesis 1:1" in text or "Gen 1:1" in text
    assert "The Creation" in text
    assert "Hajime Murai" in text
    assert "interpretive" in text.lower()


@pytest.mark.live
@pytestmark_live
def test_nested_genesis_tree_is_rendered():
    with _client() as client:
        text = _tool_text(client.tools_call("get_literary_tree", {"book": "Gen", "limit": 40}))
    assert "# Literary Structures" in text
    assert "[1]" in text
    assert "A(1:3-5)" in text
    assert "CC BY 4.0" in text
    assert "interpretive" in text.lower()
