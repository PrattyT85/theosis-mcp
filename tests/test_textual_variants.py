#!/usr/bin/env python3
"""
Tests for textual variants and manuscript witnesses MCP tools.

- Offline tests mock the DB layer and exercise formatter/handler logic.
- Live tests hit the MCP endpoint and require THEOSIS_MCP_URL.
  They must pass even when manuscript_witnesses is empty (0 rows).
"""

import json
import os
from unittest.mock import AsyncMock, patch

import pytest

# ---------------------------------------------------------------------------
# Offline: Database method unit tests (no PostgreSQL needed)
# ---------------------------------------------------------------------------

class TestGetTextualVariantsSQL:
    """Verify get_textual_variants builds correct SQL and joins witnesses."""

    @pytest.mark.asyncio
    async def test_calls_fetchall_with_normalized_ref(self):
        """Should normalize the reference and pass it to _fetchall."""
        from src.theosis_mcp.database import TheosisDB
        db = TheosisDB.__new__(TheosisDB)
        db.pool = None
        db._vector_available = False
        db._fetchall = AsyncMock(return_value=[])

        result = await db.get_textual_variants("john 3:16", limit=5)
        assert result == []
        call_args = db._fetchall.call_args
        sql = call_args[0][0]
        params = call_args[0][1:]
        # Should normalize to Jhn 3:16
        assert params[0] == "Jhn 3:16"
        assert params[1] == 5
        # Should query textual_variants
        assert "textual_variants" in sql
        # Should JOIN manuscript_witnesses via subquery
        assert "manuscript_witnesses" in sql

    @pytest.mark.asyncio
    async def test_returns_variants_with_witness_json(self):
        """Should return rows including the nested witnesses JSON."""
        from src.theosis_mcp.database import TheosisDB
        db = TheosisDB.__new__(TheosisDB)
        db.pool = None
        db._vector_available = False
        fake_row = {
            "id": 1,
            "reference": "Mat 1:5",
            "book": "Mat",
            "chapter": 1,
            "verse": 5,
            "mt_reading": "Βόες … Βόες",
            "mt_hebrew": None,
            "variant_source": "SBLGNT Apparatus",
            "variant_reading": "Βοὸς … Βοὸς",
            "variant_original": None,
            "variant_significance": None,
            "scholarly_consensus": None,
            "heiser_analysis": None,
            "preferred_for_hlt": None,
            "hlt_rationale": None,
            "witnesses": [
                {"manuscript": "NIV", "manuscript_date": None, "reading_support": "base"},
                {"manuscript": "Treg", "manuscript_date": None, "reading_support": "variant"},
                {"manuscript": "WH", "manuscript_date": None, "reading_support": "base"},
            ],
        }
        db._fetchall = AsyncMock(return_value=[fake_row])

        result = await db.get_textual_variants("Mat 1:5")
        assert len(result) == 1
        assert result[0]["witnesses"][0]["manuscript"] == "NIV"


class TestListManuscriptWitnesses:
    """Verify list_manuscript_witnesses dispatches correctly."""

    @pytest.mark.asyncio
    async def test_by_variant_id(self):
        from src.theosis_mcp.database import TheosisDB
        db = TheosisDB.__new__(TheosisDB)
        db.pool = None
        db._vector_available = False
        db._fetchall = AsyncMock(return_value=[
            {"id": 1, "variant_id": 42, "manuscript": "WH", "reading_support": "base",
             "reference": "Mat 1:5", "book": "Mat", "chapter": 1, "verse": 5, "manuscript_date": None},
        ])
        result = await db.list_manuscript_witnesses(variant_id=42)
        assert len(result) == 1
        call_args = db._fetchall.call_args
        params = call_args[0][1:]
        assert params[0] == 42  # variant_id

    @pytest.mark.asyncio
    async def test_by_reference(self):
        from src.theosis_mcp.database import TheosisDB
        db = TheosisDB.__new__(TheosisDB)
        db.pool = None
        db._vector_available = False
        db._fetchall = AsyncMock(return_value=[])
        result = await db.list_manuscript_witnesses(reference="John 3:16")
        assert result == []
        call_args = db._fetchall.call_args
        params = call_args[0][1:]
        assert params[0] == "Jhn 3:16"  # normalized

    @pytest.mark.asyncio
    async def test_no_filter_returns_all(self):
        from src.theosis_mcp.database import TheosisDB
        db = TheosisDB.__new__(TheosisDB)
        db.pool = None
        db._vector_available = False
        db._fetchall = AsyncMock(return_value=[])
        result = await db.list_manuscript_witnesses()
        assert result == []
        call_args = db._fetchall.call_args
        params = call_args[0][1:]
        assert params[0] == 50  # default limit


class TestCompareVariantReadings:
    """Verify compare_variant_readings enriches rows with split witness lists."""

    @pytest.mark.asyncio
    async def test_enriches_base_and_variant_support(self):
        from src.theosis_mcp.database import TheosisDB
        db = TheosisDB.__new__(TheosisDB)
        db.pool = None
        db._vector_available = False
        fake_row = {
            "id": 1,
            "reference": "Mat 1:5",
            "book": "Mat",
            "chapter": 1,
            "verse": 5,
            "mt_reading": "Βόες … Βόες",
            "mt_hebrew": None,
            "variant_source": "SBLGNT Apparatus",
            "variant_reading": "Βοὸς … Βοὸς",
            "variant_original": None,
            "variant_significance": None,
            "scholarly_consensus": None,
            "heiser_analysis": None,
            "preferred_for_hlt": None,
            "hlt_rationale": None,
            "witnesses": [
                {"manuscript": "NIV", "manuscript_date": None, "reading_support": "base"},
                {"manuscript": "Treg", "manuscript_date": None, "reading_support": "variant"},
                {"manuscript": "WH", "manuscript_date": None, "reading_support": "base"},
            ],
        }
        db._fetchall = AsyncMock(return_value=[fake_row])

        result = await db.compare_variant_readings("Mat 1:5")
        assert len(result) == 1
        row = result[0]
        assert sorted(row["base_support"]) == ["NIV", "WH"]
        assert row["variant_support"] == ["Treg"]

    @pytest.mark.asyncio
    async def test_empty_witnesses_produces_empty_lists(self):
        from src.theosis_mcp.database import TheosisDB
        db = TheosisDB.__new__(TheosisDB)
        db.pool = None
        db._vector_available = False
        fake_row = {
            "id": 2, "reference": "Jhn 3:16", "book": "Jhn", "chapter": 3, "verse": 16,
            "mt_reading": "test", "mt_hebrew": None, "variant_source": "Test",
            "variant_reading": "test2", "variant_original": None,
            "variant_significance": None, "scholarly_consensus": None,
            "heiser_analysis": None, "preferred_for_hlt": None,
            "hlt_rationale": None, "witnesses": [],
        }
        db._fetchall = AsyncMock(return_value=[fake_row])
        result = await db.compare_variant_readings("Jhn 3:16")
        assert result[0]["base_support"] == []
        assert result[0]["variant_support"] == []


class TestHandlerFormatters:
    """Verify server handler formatting logic with mocked DB."""

    @pytest.mark.asyncio
    async def test_get_textual_variants_handler_no_reference(self):
        from src.theosis_mcp.server import handle_get_textual_variants
        result = await handle_get_textual_variants({})
        assert "Please provide a Bible reference" in result[0].text

    @pytest.mark.asyncio
    async def test_get_textual_variants_handler_empty(self):
        from src.theosis_mcp.server import handle_get_textual_variants, db as _db
        import src.theosis_mcp.server as srv
        original_db = srv.db
        mock_db = AsyncMock()
        mock_db.get_textual_variants = AsyncMock(return_value=[])
        srv.db = mock_db
        try:
            result = await handle_get_textual_variants({"reference": "John 3:16"})
            assert "No textual variants found" in result[0].text
        finally:
            srv.db = original_db

    @pytest.mark.asyncio
    async def test_list_manuscript_witnesses_handler_empty(self):
        from src.theosis_mcp.server import handle_list_manuscript_witnesses
        import src.theosis_mcp.server as srv
        original_db = srv.db
        mock_db = AsyncMock()
        mock_db.list_manuscript_witnesses = AsyncMock(return_value=[])
        srv.db = mock_db
        try:
            result = await handle_list_manuscript_witnesses({"reference": "John 3:16"})
            assert "No manuscript witnesses found" in result[0].text
        finally:
            srv.db = original_db

    @pytest.mark.asyncio
    async def test_compare_variant_readings_handler_empty(self):
        from src.theosis_mcp.server import handle_compare_variant_readings
        import src.theosis_mcp.server as srv
        original_db = srv.db
        mock_db = AsyncMock()
        mock_db.compare_variant_readings = AsyncMock(return_value=[])
        srv.db = mock_db
        try:
            result = await handle_compare_variant_readings({"reference": "John 3:16"})
            assert "No variant readings found" in result[0].text
        finally:
            srv.db = original_db


class TestToolDefinitions:
    """Verify the three tools are defined with correct schemas."""

    def test_tools_present_in_list(self):
        from src.theosis_mcp.tools import TOOLS
        names = {t.name for t in TOOLS}
        assert "get_textual_variants" in names
        assert "list_manuscript_witnesses" in names
        assert "compare_variant_readings" in names

    def test_tools_are_read_only(self):
        from src.theosis_mcp.tools import TOOLS
        for t in TOOLS:
            if t.name in ("get_textual_variants", "list_manuscript_witnesses", "compare_variant_readings"):
                assert t.annotations.readOnlyHint is True
                assert t.annotations.destructiveHint is False

    def test_get_textual_variants_requires_reference(self):
        from src.theosis_mcp.tools import TOOLS
        tool = next(t for t in TOOLS if t.name == "get_textual_variants")
        assert "reference" in tool.inputSchema["required"]

    def test_list_manuscript_witnesses_no_required(self):
        from src.theosis_mcp.tools import TOOLS
        tool = next(t for t in TOOLS if t.name == "list_manuscript_witnesses")
        # No required fields — can be called without filters
        assert "required" not in tool.inputSchema or tool.inputSchema.get("required") == []

    def test_compare_variant_readings_requires_reference(self):
        from src.theosis_mcp.tools import TOOLS
        tool = next(t for t in TOOLS if t.name == "compare_variant_readings")
        assert "reference" in tool.inputSchema["required"]


# ---------------------------------------------------------------------------
# Live integration tests (require THEOSIS_MCP_URL)
# ---------------------------------------------------------------------------

THEOSIS_MCP_URL = os.environ.get("THEOSIS_MCP_URL")
pytestmark_live = pytest.mark.skipif(
    THEOSIS_MCP_URL is None,
    reason="THEOSIS_MCP_URL not set — skipping live textual variant tests",
)

# Use the test_mcp_live client infrastructure if available
try:
    from tests.mcp_live_client import McpClient, tool_text
except ImportError:
    McpClient = None
    tool_text = None

_mcp_client = None


def _get_client():
    global _mcp_client
    if _mcp_client is not None:
        return _mcp_client
    client = McpClient(THEOSIS_MCP_URL)
    client.initialize()
    _mcp_client = client
    return client


@pytest.fixture(autouse=True, scope="module")
def _theosis_client(request):
    if THEOSIS_MCP_URL is None:
        yield None
        return
    client = _get_client()
    yield client
    if _mcp_client is not None:
        _mcp_client.close()


@pytest.mark.live
@pytestmark_live
class TestLiveTextualVariants:
    """Live tests against the MCP endpoint."""

    def test_get_textual_variants_matthew_1_5(self):
        """Matthew 1:5 has known variants from the Heiser import."""
        client = _get_client()
        result = client.tools_call("get_textual_variants", {
            "reference": "Matthew 1:5",
        })
        text = tool_text(result)
        # Must return something — either variants or a clear empty message
        assert len(text) > 0
        # If variants exist, should contain expected content
        if "No textual variants found" not in text:
            assert "Textual Variants" in text or "Variant" in text
            # Should contain reference
            assert "Mat" in text or "Matthew" in text

    def test_get_textual_variants_john_3_16(self):
        """John 3:16 — stable reference, may or may not have variants."""
        client = _get_client()
        result = client.tools_call("get_textual_variants", {
            "reference": "John 3:16",
        })
        text = tool_text(result)
        assert len(text) > 0
        # Either shows variants or a clear empty message
        assert "textual" in text.lower() or "variant" in text.lower() or "No" in text

    def test_list_manuscript_witnesses_matthew_1_5(self):
        """List witnesses for Matthew 1:5 — must work even with 0 witnesses."""
        client = _get_client()
        result = client.tools_call("list_manuscript_witnesses", {
            "reference": "Matthew 1:5",
        })
        text = tool_text(result)
        assert len(text) > 0
        # Either shows witnesses or a clear empty message
        assert "witness" in text.lower() or "No" in text

    def test_list_manuscript_witnesses_no_filter(self):
        """Unfiltered witness list — should return something or be empty."""
        client = _get_client()
        result = client.tools_call("list_manuscript_witnesses", {})
        text = tool_text(result)
        assert len(text) > 0
        assert "witness" in text.lower() or "No" in text

    def test_compare_variant_readings_matthew_1_5(self):
        """Compare variant readings for Matthew 1:5."""
        client = _get_client()
        result = client.tools_call("compare_variant_readings", {
            "reference": "Matthew 1:5",
        })
        text = tool_text(result)
        assert len(text) > 0
        # Either shows comparison or a clear empty message
        if "No variant readings found" not in text:
            assert "Variant" in text or "variant" in text

    def test_compare_variant_readings_john_3_16(self):
        """Compare variant readings for John 3:16."""
        client = _get_client()
        result = client.tools_call("compare_variant_readings", {
            "reference": "John 3:16",
        })
        text = tool_text(result)
        assert len(text) > 0

    def test_tools_list_includes_new_tools(self):
        """Verify the new tools appear in tools/list."""
        client = _get_client()
        result = client.tools_list()
        names = {tool["name"] for tool in result}
        assert "get_textual_variants" in names
        assert "list_manuscript_witnesses" in names
        assert "compare_variant_readings" in names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
