#!/usr/bin/env python3
"""
Tests for the ANE context database method and server handler.

Offline tests exercise the database SQL and the server's formatting helper
without needing PostgreSQL.  Live tests hit the real MCP endpoint.
"""
import json
import os
from unittest.mock import AsyncMock

import pytest


# ---------------------------------------------------------------------------
# Offline: _parse_json_list_field helper
# ---------------------------------------------------------------------------

class TestParseJsonListField:
    """Unit tests for the JSON list field parser in the server handler."""

    def test_none_returns_empty_list(self):
        from src.theosis_mcp.server import _parse_json_list_field
        assert _parse_json_list_field(None) == []

    def test_list_passed_through(self):
        from src.theosis_mcp.server import _parse_json_list_field
        assert _parse_json_list_field(["a", "b"]) == ["a", "b"]

    def test_valid_json_array_string(self):
        from src.theosis_mcp.server import _parse_json_list_field
        raw = '["Gen 1:6", "Gen 1:8"]'
        result = _parse_json_list_field(raw)
        assert result == ["Gen 1:6", "Gen 1:8"]

    def test_non_json_string_returns_singleton(self):
        from src.theosis_mcp.server import _parse_json_list_field
        result = _parse_json_list_field("just plain text")
        assert result == ["just plain text"]

    def test_empty_string_returns_empty(self):
        from src.theosis_mcp.server import _parse_json_list_field
        assert _parse_json_list_field("") == []

    def test_whitespace_only_returns_empty(self):
        from src.theosis_mcp.server import _parse_json_list_field
        assert _parse_json_list_field("   ") == []

    def test_non_string_non_list_returns_empty(self):
        from src.theosis_mcp.server import _parse_json_list_field
        assert _parse_json_list_field(42) == []

    def test_malformed_json_returns_singleton(self):
        from src.theosis_mcp.server import _parse_json_list_field
        result = _parse_json_list_field("[invalid json")
        assert result == ["[invalid json"]

    def test_json_object_fallback_to_singleton(self):
        from src.theosis_mcp.server import _parse_json_list_field
        result = _parse_json_list_field('{"key": "value"}')
        assert result == ['{"key": "value"}']

    def test_valid_json_with_unicode(self):
        from src.theosis_mcp.server import _parse_json_list_field
        raw = json.dumps(["Walton, The Lost World of Genesis One", "raqia\u200bscholar"])
        result = _parse_json_list_field(raw)
        assert len(result) == 2
        assert "raqia" in result[1]


# ---------------------------------------------------------------------------
# Offline: get_ane_context database method
# ---------------------------------------------------------------------------

class TestGetAneContextSQL:
    """Verify get_ane_context normalizes references and searches broad columns."""

    @pytest.mark.asyncio
    async def test_normalizes_book_and_searches_wide(self):
        from src.theosis_mcp.database import TheosisDB
        db = TheosisDB.__new__(TheosisDB)
        db.pool = None
        db._vector_available = False
        db._fetchall = AsyncMock(return_value=[])

        await db.get_ane_context("Genesis 1:1")
        call_args = db._fetchall.call_args
        sql = call_args[0][0]
        params = call_args[0][1:]

        assert params[0] == "%Gen%"
        # The SQL should search more than just title/summary
        assert "key_references" in sql
        assert "detail" in sql
        assert "interpretive_significance" in sql

    @pytest.mark.asyncio
    async def test_returns_all_columns_from_entry(self):
        """Returned dict should contain all ane_entries fields."""
        from src.theosis_mcp.database import TheosisDB
        db = TheosisDB.__new__(TheosisDB)
        db.pool = None
        db._vector_available = False
        fake_row = {
            "id": "cosmo_001",
            "dimension": "cosmology_worldview",
            "dimension_label": "Cosmology & Worldview",
            "title": "Three-Tier Universe",
            "summary": "The ancient Near East view of a three-tier universe.",
            "detail": "Extended detail about cosmology.",
            "ane_parallels": json.dumps(["Enuma Elish", "Egyptian cosmology"]),
            "interpretive_significance": "Reading 'firmament' as atmosphere misses the point.",
            "period": "Bronze Age",
            "period_label": "Bronze Age (~2000-1200 BCE)",
            "key_references": json.dumps(["Gen 1:6-8", "Gen 1:14-17"]),
            "scholarly_sources": json.dumps(["Walton", "Horowitz"]),
        }
        db._fetchall = AsyncMock(return_value=[fake_row])

        result = await db.get_ane_context("Genesis 1:1")
        assert len(result) == 1
        row = result[0]
        for field in (
            "id", "dimension", "dimension_label", "title", "summary", "detail",
            "ane_parallels", "interpretive_significance", "period", "period_label",
            "key_references", "scholarly_sources",
        ):
            assert field in row, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# Offline: handle_get_ane_context formatting
# ---------------------------------------------------------------------------

class TestHandleGetAneContext:
    """Verify the server handler renders all ANE fields as Markdown."""

    @pytest.mark.asyncio
    async def test_renders_all_fields(self):
        from src.theosis_mcp.server import handle_get_ane_context
        from src.theosis_mcp import server

        fake_entry = {
            "id": "cosmo_001",
            "dimension": "cosmology_worldview",
            "dimension_label": "Cosmology & Worldview",
            "title": "Three-Tier Universe",
            "summary": "The ancient Near East view of a three-tier universe.",
            "detail": "Extended detail about cosmology.",
            "ane_parallels": '["Enuma Elish: Marduk splits Tiamat", "Egyptian cosmology: Nut arches over Geb"]',
            "interpretive_significance": "Reading 'firmament' (raqia) as atmosphere misses the original audience's understanding.",
            "period": "Bronze Age",
            "period_label": "Bronze Age (~2000-1200 BCE)",
            "key_references": '["Gen 1:6-8", "Gen 1:14-17"]',
            "scholarly_sources": '["Walton, The Lost World of Genesis One", "Horowitz"]',
        }

        # Patch the module-level db object
        original_db = server.db
        server.db = AsyncMock()
        server.db.get_ane_context = AsyncMock(return_value=[fake_entry])

        try:
            result_list = await handle_get_ane_context({"reference": "Genesis 1:1"})
        finally:
            server.db = original_db

        md = result_list[0].text

        # Dimension and period labels rendered
        assert "Cosmology & Worldview" in md
        assert "Bronze Age" in md

        # Title rendered
        assert "Three-Tier Universe" in md

        # Summary and detail rendered
        assert "ancient Near East view" in md
        assert "Extended detail" in md

        # ANE parallels rendered as list items
        assert "Enuma Elish" in md
        assert "Marduk" in md
        assert "Nut" in md

        # Interpretive significance rendered
        assert "raqia" in md

        # Key references rendered
        assert "Gen 1:6-8" in md
        assert "Gen 1:14-17" in md

        # Scholarly sources rendered
        assert "Walton" in md
        assert "Horowitz" in md

    @pytest.mark.asyncio
    async def test_empty_result_returns_no_data_message(self):
        from src.theosis_mcp.server import handle_get_ane_context
        from src.theosis_mcp import server

        original_db = server.db
        server.db = AsyncMock()
        server.db.get_ane_context = AsyncMock(return_value=[])
        try:
            result_list = await handle_get_ane_context({"reference": "Job 40:1"})
        finally:
            server.db = original_db

        md = result_list[0].text
        assert "No ANE context" in md

    @pytest.mark.asyncio
    async def test_missing_reference_returns_help(self):
        from src.theosis_mcp.server import handle_get_ane_context
        from src.theosis_mcp import server

        original_db = server.db
        server.db = AsyncMock()
        try:
            result_list = await handle_get_ane_context({})
        finally:
            server.db = original_db

        md = result_list[0].text
        assert "Please provide" in md


# ---------------------------------------------------------------------------
# Live: MCP integration test
# ---------------------------------------------------------------------------

THEOSIS_MCP_URL = os.environ.get("THEOSIS_MCP_URL")
pytestmark_live = pytest.mark.skipif(
    THEOSIS_MCP_URL is None,
    reason="THEOSIS_MCP_URL not set — skipping live ANE context test",
)


@pytest.mark.live
@pytestmark_live
class TestLiveAneContext:
    """Live test: get_ane_context for Genesis 1:1 via MCP endpoint."""

    def test_genesis_1_1_full_ane_response(self):
        from tests.mcp_live_client import McpClient, tool_text

        client = McpClient(THEOSIS_MCP_URL)
        client.initialize()
        try:
            result = client.tools_call("get_ane_context", {
                "reference": "Genesis 1:1",
            })
            md = tool_text(result)

            # Must contain a cosmology/dimension heading
            assert "Three-Tier Universe" in md or "Cosmolog" in md.lower(), (
                f"Expected ANE dimension heading, got: {md[:300]}"
            )

            # Must mention ANE parallels
            assert "ANE" in md or "parallels" in md.lower(), (
                f"Expected ANE parallels content, got: {md[:300]}"
            )

            # Must mention 'raqia' or 'firmament' in interpretive significance
            assert "raqia" in md.lower() or "firmament" in md.lower(), (
                f"Expected 'raqia' or 'firmament' in interpretive significance, got: {md[:300]}"
            )

            # Must contain at least one key reference
            assert "Gen" in md, (
                f"Expected a Genesis key reference, got: {md[:300]}"
            )
        finally:
            client.close()
