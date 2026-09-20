"""
Midrash MCP live integration tests.

Tests that require a running Midrash server are skipped unless
MIDRASH_MCP_URL is set.  All tests are read-only.
"""
import os

import pytest

from tests.mcp_live_client import McpClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tool_text(result: list[dict]) -> str:
    """Return the text of the first content block, or empty string."""
    if isinstance(result, list) and result:
        return result[0].get("text", "")
    return ""


# ---------------------------------------------------------------------------
# Live integration tests (skipped without MIDRASH_MCP_URL)
# ---------------------------------------------------------------------------

MIDRASH_MCP_URL = os.environ.get("MIDRASH_MCP_URL")
pytestmark_live = pytest.mark.skipif(
    MIDRASH_MCP_URL is None,
    reason="MIDRASH_MCP_URL not set — skipping live Midrash MCP tests",
)


@pytest.mark.live
@pytestmark_live
class TestMidrashWorksList:
    """List imported Midrash works."""

    def test_list_works_returns_entries(self) -> None:
        """list_midrash_works should return a non-empty list of works."""
        with McpClient(MIDRASH_MCP_URL) as client:
            client.initialize()
            result = client.tools_call("list_midrash_works", {})
        text = _tool_text(result)
        assert len(text) > 0
        # Should contain known Midrash works
        known_works = ["Bereshit Rabbah", "Bamidbar Rabbah", "Devarim Rabbah"]
        assert any(w in text for w in known_works), (
            f"Expected at least one of {known_works} in works list"
        )

    def test_works_contain_licence_info(self) -> None:
        """Work entries should include licence markers."""
        with McpClient(MIDRASH_MCP_URL) as client:
            client.initialize()
            result = client.tools_call("list_midrash_works", {})
        text = _tool_text(result)
        # Should contain licence indicators (CC-BY or similar)
        assert "CC" in text or "licence" in text.lower() or "license" in text.lower()


@pytest.mark.live
@pytestmark_live
class TestMidrashTextRetrieval:
    """Exact-text retrieval for a known Midrash reference."""

    def test_bereshit_rabbah_1_1_english(self) -> None:
        """Bereshit Rabbah 1:1 English text should be retrievable."""
        with McpClient(MIDRASH_MCP_URL) as client:
            client.initialize()
            result = client.tools_call("get_midrash_text", {
                "ref": "Bereshit Rabbah 1:1",
                "language": "en",
            })
        text = _tool_text(result)
        assert len(text) > 0
        # Should contain the reference
        assert "Bereshit Rabbah" in text
        # Should contain edition provenance
        assert "edition" in text.lower() or "Edition" in text

    def test_bereshit_rabbah_1_1_hebrew(self) -> None:
        """Bereshit Rabbah 1:1 Hebrew text should contain Hebrew characters."""
        with McpClient(MIDRASH_MCP_URL) as client:
            client.initialize()
            result = client.tools_call("get_midrash_text", {
                "ref": "Bereshit Rabbah 1:1",
                "language": "he",
            })
        text = _tool_text(result)
        assert len(text) > 0
        # Should contain the reference
        assert "Bereshit Rabbah" in text
        # Should contain Hebrew characters
        assert any("\u0590" <= ch <= "\u05FF" for ch in text), (
            "Expected Hebrew characters in Hebrew Midrash text"
        )

    def test_edition_provenance_fields(self) -> None:
        """Midrash text should include licence and source provenance."""
        with McpClient(MIDRASH_MCP_URL) as client:
            client.initialize()
            result = client.tools_call("get_midrash_text", {
                "ref": "Bereshit Rabbah 1:1",
                "language": "en",
            })
        text = _tool_text(result)
        # Should contain licence info
        assert "licence" in text.lower() or "license" in text.lower(), (
            "Expected licence provenance in Midrash text"
        )
        # Should contain source URL
        assert "http" in text, "Expected source URL in Midrash text"


@pytest.mark.live
@pytestmark_live
class TestMidrashParallel:
    """Bilingual parallel retrieval (Hebrew + English)."""

    def test_parallel_returns_both_languages(self) -> None:
        """get_midrash_parallel should return both English and Hebrew."""
        with McpClient(MIDRASH_MCP_URL) as client:
            client.initialize()
            result = client.tools_call("get_midrash_parallel", {
                "ref": "Bereshit Rabbah 1:1",
            })
        text = _tool_text(result)
        assert len(text) > 0
        # Should contain both language sections
        assert "English" in text or "english" in text.lower()
        assert "Hebrew" in text or "hebrew" in text.lower()
        # Should contain the reference
        assert "Bereshit Rabbah" in text

    def test_parallel_hebrew_characters_present(self) -> None:
        """Parallel text should contain Hebrew characters."""
        with McpClient(MIDRASH_MCP_URL) as client:
            client.initialize()
            result = client.tools_call("get_midrash_parallel", {
                "ref": "Bereshit Rabbah 1:1",
            })
        text = _tool_text(result)
        # Hebrew characters should be present
        assert any("\u0590" <= ch <= "\u05FF" for ch in text), (
            "Expected Hebrew characters in parallel text"
        )


@pytest.mark.live
@pytestmark_live
class TestMidrashSearch:
    """Search Midrash corpus."""

    def test_search_returns_results(self) -> None:
        """search_midrash for 'Creation' should return results."""
        with McpClient(MIDRASH_MCP_URL) as client:
            client.initialize()
            result = client.tools_call("search_midrash", {
                "query": "Creation",
            })
        text = _tool_text(result)
        assert len(text) > 0
        # Should contain search results heading
        assert "search" in text.lower() or "results" in text.lower()
        # Should reference a known work
        assert "Bereshit" in text or "Rabbah" in text

    def test_search_includes_edition_and_licence(self) -> None:
        """Search results should include edition and licence provenance."""
        with McpClient(MIDRASH_MCP_URL) as client:
            client.initialize()
            result = client.tools_call("search_midrash", {
                "query": "Creation",
            })
        text = _tool_text(result)
        # Should contain edition info
        assert "edition" in text.lower() or "Edition" in text
        # Should contain licence
        assert "licence" in text.lower() or "license" in text.lower() or "CC" in text
