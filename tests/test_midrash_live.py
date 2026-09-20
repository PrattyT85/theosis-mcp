"""
Midrash MCP live integration tests.

Tests that require a running Midrash server are skipped unless
MIDRASH_MCP_URL is set.  All tests are read-only.
"""
import os

import pytest
from tests.mcp_live_client import McpClient, tool_text


# ---------------------------------------------------------------------------
# Live integration tests (skipped without MIDRASH_MCP_URL)
# ---------------------------------------------------------------------------

MIDRASH_MCP_URL = os.environ.get("MIDRASH_MCP_URL")
pytestmark_live = pytest.mark.skipif(
    MIDRASH_MCP_URL is None,
    reason="MIDRASH_MCP_URL not set — skipping live Midrash MCP tests",
)

# Module-scoped client: initialized once per pytest session, shared by all
# live tests.  Falls back to a fresh client per test if the session client
# is closed or fails handshake.
_mcp_client: McpClient | None = None


def _get_client() -> McpClient:
    """Return a reusable, initialized McpClient for the live Midrash server."""
    global _mcp_client
    if _mcp_client is not None:
        return _mcp_client
    client = McpClient(MIDRASH_MCP_URL)
    client.initialize()
    _mcp_client = client
    return client


@pytest.fixture(autouse=True, scope="module")
def _midrash_client(request):
    """Module-scoped fixture: initialize once, close at session end.

    Only connects when MIDRASH_MCP_URL is set.
    """
    if MIDRASH_MCP_URL is None:
        yield None
        return
    client = _get_client()
    yield client
    if _mcp_client is not None:
        _mcp_client.close()


# ---------------------------------------------------------------------------
# Live: list_midrash_works
# ---------------------------------------------------------------------------

@pytest.mark.live
@pytestmark_live
class TestMidrashWorksList:
    """List imported Midrash works."""

    def test_list_works_returns_entries(self) -> None:
        """list_midrash_works should return a non-empty list of works."""
        client = _get_client()
        result = client.tools_call("list_midrash_works", {})
        text = tool_text(result)
        assert len(text) > 0
        # Should contain known Midrash works
        known_works = ["Bereshit Rabbah", "Bamidbar Rabbah", "Devarim Rabbah"]
        assert any(w in text for w in known_works), (
            f"Expected at least one of {known_works} in works list"
        )

    def test_works_contain_licence_info(self) -> None:
        """Work entries should include licence markers."""
        client = _get_client()
        result = client.tools_call("list_midrash_works", {})
        text = tool_text(result)
        # Should contain licence indicators (CC-BY or similar)
        assert "CC" in text or "licence" in text.lower() or "license" in text.lower()


# ---------------------------------------------------------------------------
# Live: text retrieval
# ---------------------------------------------------------------------------

@pytest.mark.live
@pytestmark_live
class TestMidrashTextRetrieval:
    """Exact-text retrieval for a known Midrash reference."""

    def test_bereshit_rabbah_1_1_english(self) -> None:
        """Bereshit Rabbah 1:1 English text should be retrievable."""
        client = _get_client()
        result = client.tools_call("get_midrash_text", {
            "ref": "Bereshit Rabbah 1:1",
            "language": "en",
        })
        text = tool_text(result)
        assert len(text) > 0
        assert "Bereshit Rabbah" in text
        # Edition provenance header
        assert "edition" in text.lower() or "Edition" in text

    def test_bereshit_rabbah_1_1_hebrew(self) -> None:
        """Bereshit Rabbah 1:1 Hebrew text should contain Hebrew characters."""
        client = _get_client()
        result = client.tools_call("get_midrash_text", {
            "ref": "Bereshit Rabbah 1:1",
            "language": "he",
        })
        text = tool_text(result)
        assert len(text) > 0
        assert "Bereshit Rabbah" in text
        assert any("\u0590" <= ch <= "\u05FF" for ch in text), (
            "Expected Hebrew characters in Hebrew Midrash text"
        )

    def test_edition_provenance_fields(self) -> None:
        """Midrash text should include licence and source provenance."""
        client = _get_client()
        result = client.tools_call("get_midrash_text", {
            "ref": "Bereshit Rabbah 1:1",
            "language": "en",
        })
        text = tool_text(result)
        assert "licence" in text.lower() or "license" in text.lower(), (
            "Expected licence provenance in Midrash text"
        )
        assert "http" in text, "Expected source URL in Midrash text"


# ---------------------------------------------------------------------------
# Live: bilingual parallel retrieval
# ---------------------------------------------------------------------------

@pytest.mark.live
@pytestmark_live
class TestMidrashParallel:
    """Bilingual parallel retrieval (Hebrew + English)."""

    def test_parallel_returns_both_languages(self) -> None:
        """get_midrash_parallel should return both English and Hebrew."""
        client = _get_client()
        result = client.tools_call("get_midrash_parallel", {
            "ref": "Bereshit Rabbah 1:1",
        })
        text = tool_text(result)
        assert len(text) > 0
        assert "English" in text or "english" in text.lower()
        assert "Hebrew" in text or "hebrew" in text.lower()
        assert "Bereshit Rabbah" in text

    def test_parallel_hebrew_characters_present(self) -> None:
        """Parallel text should contain Hebrew characters."""
        client = _get_client()
        result = client.tools_call("get_midrash_parallel", {
            "ref": "Bereshit Rabbah 1:1",
        })
        text = tool_text(result)
        assert any("\u0590" <= ch <= "\u05FF" for ch in text), (
            "Expected Hebrew characters in parallel text"
        )


# ---------------------------------------------------------------------------
# Live: search
# ---------------------------------------------------------------------------

@pytest.mark.live
@pytestmark_live
class TestMidrashSearch:
    """Search Midrash corpus."""

    def test_search_returns_results(self) -> None:
        """search_midrash for 'Creation' should return results."""
        client = _get_client()
        result = client.tools_call("search_midrash", {
            "query": "Creation",
        })
        text = tool_text(result)
        assert len(text) > 0
        assert "search" in text.lower() or "results" in text.lower()
        assert "Bereshit" in text or "Rabbah" in text

    def test_search_includes_edition_and_licence(self) -> None:
        """Search results should include edition and licence provenance."""
        client = _get_client()
        result = client.tools_call("search_midrash", {
            "query": "Creation",
        })
        text = tool_text(result)
        assert "edition" in text.lower() or "Edition" in text
        assert "licence" in text.lower() or "license" in text.lower() or "CC" in text
