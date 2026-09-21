#!/usr/bin/env python3
"""
Offline tests for the literary-structure corpus importer.

Exercises pure parser functions against representative Excel row shapes
without requiring a database or live workbooks.
"""
import hashlib
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from import_literary_structure import (
    # references
    parse_reference,
    normalize_reference,
    # list sheets
    parse_pericope_list_sheet,
    # structure sheets
    parse_structure_sheet,
    # source manifest
    source_manifest,
    # dry-run
    dry_run_report,
)


# ---------------------------------------------------------------------------
# Source manifest
# ---------------------------------------------------------------------------

class TestSourceManifest:
    """Verify source manifest fields for provenance tracking."""

    def test_returns_required_keys(self):
        m = source_manifest(
            source_id="murai_lit_struct_ot",
            source_type="pericope_list",
            workbook_path="PericopeList_OT.xlsx",
            worksheet_name="Gen",
            licence="CC-BY-4.0",
            url="http://www.bible.literarystructure.info/bible/bible_e.html",
            attribution="Hajime Murai, Literary Structure of the Bible",
            version_hint="2022-02-24",
        )
        assert m["source_id"] == "murai_lit_struct_ot"
        assert m["source_type"] == "pericope_list"
        assert m["licence"] == "CC-BY-4.0"
        assert m["attribution"] == "Hajime Murai, Literary Structure of the Bible"
        assert "workbook_hash" in m

    def test_workbook_hash_sha256(self):
        """workbook_hash must be a SHA-256 hex digest."""
        m = source_manifest(
            source_id="test", source_type="pericope_list",
            workbook_path="fake.xlsx", worksheet_name="Gen",
            licence="CC-BY-4.0", url="http://example.com",
            attribution="Author",
        )
        assert len(m["workbook_hash"]) == 64
        # All hex characters
        assert all(c in "0123456789abcdef" for c in m["workbook_hash"])

    def test_hash_is_deterministic(self):
        """Same path → same hash (for non-existent files, returns sha256 of empty)."""
        # Non-existent path yields sha256(b"")
        m1 = source_manifest(
            source_id="a", source_type="t", workbook_path="/no/such/file.xlsx",
            worksheet_name="x", licence="CC-BY-4.0", url="u", attribution="a",
        )
        m2 = source_manifest(
            source_id="b", source_type="t", workbook_path="/no/such/file.xlsx",
            worksheet_name="y", licence="CC-BY-4.0", url="u", attribution="a",
        )
        # Both paths don't exist, both get sha256(b"")
        expected = hashlib.sha256(b"").hexdigest()
        assert m1["workbook_hash"] == expected
        assert m2["workbook_hash"] == expected


# ---------------------------------------------------------------------------
# Reference parsing
# ---------------------------------------------------------------------------

class TestParseReference:
    """Parse common Bible reference formats from raw strings."""

    def test_simple_verse(self):
        r = parse_reference("1:1")
        assert r["start_chapter"] == 1
        assert r["start_verse"] == 1
        assert r["end_chapter"] is None
        assert r["end_verse"] is None

    def test_chapter_only(self):
        r = parse_reference("3")
        assert r["start_chapter"] == 3
        assert r["start_verse"] is None

    def test_verse_range(self):
        r = parse_reference("1:5-7")
        assert r["start_chapter"] == 1
        assert r["start_verse"] == 5
        assert r["end_chapter"] == 1
        assert r["end_verse"] == 7

    def test_chapter_range(self):
        r = parse_reference("1-3")
        assert r["start_chapter"] == 1
        assert r["end_chapter"] == 3

    def test_partial_verse_suffix(self):
        """Verse suffixes like '4a' or '5b' are preserved."""
        r = parse_reference("2:4a")
        assert r["start_chapter"] == 2
        assert r["start_verse"] == 4
        assert r["start_suffix"] == "a"
        r2 = parse_reference("2:4b")
        assert r2["start_suffix"] == "b"

    def test_cross_chapter_range(self):
        """Range spanning chapters: 1:31-2:4a."""
        r = parse_reference("1:31-2:4a")
        assert r["start_chapter"] == 1
        assert r["start_verse"] == 31
        assert r["end_chapter"] == 2
        assert r["end_verse"] == 4
        assert r["end_suffix"] == "a"

    def test_multi_range_returns_none(self):
        """Multi-range refs (1:1-31 2:1-4a) can't be fully normalized."""
        r = parse_reference("1:1-31 2:1-4a")
        # Should indicate ambiguity
        assert r["ambiguous"] is True or r["end_chapter"] is None

    def test_book_prefixed_range(self):
        """1S1:1-8 → book prefix stripped."""
        r = parse_reference("1S1:1-8", strip_book_prefix=True)
        assert r["start_chapter"] == 1
        assert r["start_verse"] == 1
        assert r["end_verse"] == 8

    def test_unparseable_returns_raw(self):
        """Completely non-numeric ref is returned as-is."""
        r = parse_reference("??")
        assert r["raw"] == "??"


class TestNormalizeReference:
    """Combine book name + raw reference into canonical form."""

    def test_simple(self):
        assert normalize_reference("Gen", "1:1") == "Gen 1:1"

    def test_no_reference(self):
        assert normalize_reference("Gen", "") == "Gen"

    def test_book_with_number_prefix(self):
        assert normalize_reference("1Jn", "1:1") == "1Jn 1:1"


# ---------------------------------------------------------------------------
# Pericope list sheet parsing
# ---------------------------------------------------------------------------

class TestParsePericopeListSheet:
    """Parse pericope list rows (sequence, reference, title)."""

    def test_basic_row(self):
        rows = list(parse_pericope_list_sheet([
            [1, "1:1-31", "Creation Account"],
            [2, "2:1-3a", "God Rests"],
        ], book="Gen", source_id="murai_ot"))
        assert len(rows) == 2
        assert rows[0]["sequence"] == 1
        assert rows[0]["raw_reference"] == "1:1-31"
        assert rows[0]["title"] == "Creation Account"
        assert rows[0]["book"] == "Gen"
        assert rows[0]["source_id"] == "murai_ot"

    def test_empty_rows_skipped(self):
        rows = list(parse_pericope_list_sheet([
            [1, "1:1", "Title"],
            [None, None, None],
            [2, "2:1", "Title 2"],
        ], book="Gen", source_id="s"))
        assert len(rows) == 2

    def test_numeric_sequence_preserved(self):
        rows = list(parse_pericope_list_sheet([
            [42, "3:1", "Something"],
        ], book="Exo", source_id="s"))
        assert rows[0]["sequence"] == 42


# ---------------------------------------------------------------------------
# Structure sheet parsing
# ---------------------------------------------------------------------------

class TestParseStructureSheet:
    """Parse literary structure rows with [N], A/B/A' labels, descriptions."""

    def test_structure_label_rows(self):
        """Labels like [1], A, B, A' are preserved."""
        data = [
            ["[1]", "", "Introduction", ""],
            ["A(1:3-5)", "", "First unit", ""],
            ["B(1:6-8)", "", "Second unit", ""],
            ["A'(1:9-11)", "", "Recapitulation", ""],
        ]
        rows = list(parse_structure_sheet(data, book="Gen", source_id="s"))
        assert len(rows) == 4
        assert rows[0]["structure_label"] == "[1]"
        assert rows[1]["structure_label"] == "A(1:3-5)"
        assert rows[3]["structure_label"] == "A'(1:9-11)"

    def test_blank_separator_rows_skipped(self):
        data = [
            ["[1]", "", "Intro", ""],
            ["", "", "", ""],
            ["A(1:3)", "", "Unit", ""],
        ]
        rows = list(parse_structure_sheet(data, book="Gen", source_id="s"))
        assert len(rows) == 2

    def test_description_columns(self):
        """Col B = Japanese, Col C = English, Col D = transliteration."""
        data = [
            ["A(1:3-5)", "日本語説明", "English summary", "hebrew_translit"],
        ]
        rows = list(parse_structure_sheet(data, book="Gen", source_id="s"))
        assert rows[0]["description_ja"] == "日本語説明"
        assert rows[0]["description_en"] == "English summary"
        assert rows[0]["transliteration"] == "hebrew_translit"

    def test_br_summary_text_preserved(self):
        """HTML <br> tags in summary text are stored raw, not stripped."""
        data = [
            ["[1]", "", "Line one<br>Line two<br>Line three", ""],
        ]
        rows = list(parse_structure_sheet(data, book="Gen", source_id="s"))
        assert "<br>" in rows[0]["description_en"]
        assert rows[0]["description_en"] == "Line one<br>Line two<br>Line three"

    def test_nt_cross_ref_in_summary(self):
        """NT [N] rows may contain cross-refs like '42_Luke@13,23_Isaiah@10'."""
        data = [
            ["[N]", "", "42_Luke@13,23_Isaiah@10", ""],
        ]
        rows = list(parse_structure_sheet(data, book="Mat", source_id="s"))
        assert rows[0]["cross_references"] == "42_Luke@13,23_Isaiah@10"

    def test_no_verse_text_stored(self):
        """Structure rows must not store actual Bible verse text."""
        data = [
            ["A(1:3-5)", "", "In the beginning God created", ""],
        ]
        rows = list(parse_structure_sheet(data, book="Gen", source_id="s"))
        # The description is a summary/label, not verse text.
        # We verify it's stored as-is (not verse text ingestion).
        assert rows[0]["description_en"] == "In the beginning God created"
        assert rows[0].get("verse_text") is None


# ---------------------------------------------------------------------------
# Dry-run reporting
# ---------------------------------------------------------------------------

class TestDryRunReport:
    """Dry-run reports must count rows and flag malformed entries."""

    def test_report_counts(self):
        items = [
            {"sequence": 1, "reference": "1:1", "title": "A"},
            {"sequence": 2, "reference": "1:2", "title": "B"},
        ]
        malformed = [
            {"row": 3, "reason": "empty reference"},
        ]
        report = dry_run_report(items, malformed, source_id="test")
        assert report["total_rows"] == 2
        assert report["malformed_count"] == 1
        assert report["source_id"] == "test"

    def test_report_no_verse_text_flag(self):
        items = [{"structure_label": "A(1:3)"}]
        report = dry_run_report(items, [], source_id="s")
        assert report["verse_text_present"] is False
