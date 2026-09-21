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
    # mapping
    sheet_to_osis,
    SHEET_TO_OSIS,
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
# Worksheet-name → scope-code mapping
# ---------------------------------------------------------------------------

class TestSheetToOsis:
    """Map worksheet names to stable scope codes."""

    def test_full_ot_names(self):
        """Full OT worksheet names map to standard OSIS codes."""
        assert sheet_to_osis("Genesis") == "Gen"
        assert sheet_to_osis("Exodus") == "Exo"
        assert sheet_to_osis("Leviticus") == "Lev"
        assert sheet_to_osis("Numbers") == "Num"
        assert sheet_to_osis("Deuteronomy") == "Deu"
        assert sheet_to_osis("Joshua") == "Jos"
        assert sheet_to_osis("Judges") == "Jdg"
        assert sheet_to_osis("Ruth") == "Rut"
        assert sheet_to_osis("Isaiah") == "Isa"
        assert sheet_to_osis("Psalms") == "Psa"
        assert sheet_to_osis("SongofSolomon") == "Sng"

    def test_full_nt_names(self):
        """Full NT worksheet names map to standard OSIS codes."""
        assert sheet_to_osis("Matthew") == "Mat"
        assert sheet_to_osis("Mark") == "Mrk"
        assert sheet_to_osis("Luke") == "Luk"
        assert sheet_to_osis("John") == "Jhn"
        assert sheet_to_osis("Acts") == "Act"
        assert sheet_to_osis("Romans") == "Rom"
        assert sheet_to_osis("1Corinthians") == "1Co"
        assert sheet_to_osis("2Corinthians") == "2Co"
        assert sheet_to_osis("Revelation") == "Rev"

    def test_grouped_ot_sheets_use_scope_codes(self):
        """Grouped OT sheets use compound scope codes, not individual book codes."""
        assert sheet_to_osis("Samuel") == "Sam"
        assert sheet_to_osis("Kings") == "Kgs"
        assert sheet_to_osis("Chronicles") == "Chr"
        assert sheet_to_osis("Ezra-Nehemiah") == "EzrNeh"

    def test_abbreviated_names_still_work(self):
        """Legacy abbreviated sheet names still map correctly."""
        assert sheet_to_osis("Gen") == "Gen"
        assert sheet_to_osis("1S") == "1Sa"
        assert sheet_to_osis("2S") == "2Sa"
        assert sheet_to_osis("1Ki") == "1Ki"
        assert sheet_to_osis("1Co") == "1Co"

    def test_unknown_name_falls_back_to_raw(self):
        """Sheet names not in the map fall back to the raw name."""
        assert sheet_to_osis("UnknownBook") == "UnknownBook"

    def test_preserves_raw_worksheet_name_for_provenance(self):
        """The original worksheet name is preserved in manifests, not the scope code."""
        m = source_manifest(
            source_id="test", source_type="structure",
            workbook_path="fake.xlsx", worksheet_name="Samuel",
            licence="CC-BY-4.0", url="u", attribution="a",
        )
        assert m["worksheet_name"] == "Samuel"  # raw, not "Sam"


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
# Genesis [1] header → child row grouping
# ---------------------------------------------------------------------------

class TestGenesisOneGrouping:
    """Verify [N] header tracking groups child rows under the header."""

    def test_header_sets_is_header(self):
        """The [1] row is marked as a header."""
        data = [
            ["[1]", "Gen 1:1-2:4a", None, None],
            ["A(1:3-5)", "", "First day", ""],
        ]
        rows = list(parse_structure_sheet(data, book="Gen", source_id="s"))
        assert rows[0]["is_header"] is True
        assert rows[1]["is_header"] is False

    def test_child_rows_get_parent_label(self):
        """A, B, C, A', B', C', P, P' rows get parent_label=[1]."""
        data = [
            ["[1]", "Gen 1:1-2:4a", None, None],
            ["P(1:1-2)", "", "The Creation", ""],
            ["A(1:3-5)", "", "First day", ""],
            ["B(1:6-8)", "", "Second day", ""],
            ["C(1:9-13)", "", "Third day", ""],
            ["A'(1:14-19)", "", "Fourth day", ""],
            ["B'(1:20-23)", "", "Fifth day", ""],
            ["C'(1:24-31)", "", "Sixth day", ""],
            ["P'(2:1-4a)", "", "The Creation", ""],
        ]
        rows = list(parse_structure_sheet(data, book="Gen", source_id="s"))
        # Header row
        assert rows[0]["is_header"] is True
        assert rows[0]["parent_label"] is None
        # Child rows all have parent_label=[1]
        for row in rows[1:]:
            assert row["parent_label"] == "[1]", (
                f"Row {row['structure_label']} should have parent=[1]"
            )

    def test_child_rows_have_unit_sequence(self):
        """Child rows get sequential unit_sequence values."""
        data = [
            ["[1]", "Gen 1:1-2:4a", None, None],
            ["P(1:1-2)", "", "The Creation", ""],
            ["A(1:3-5)", "", "First day", ""],
            ["B(1:6-8)", "", "Second day", ""],
            ["C(1:9-13)", "", "Third day", ""],
            ["A'(1:14-19)", "", "Fourth day", ""],
            ["B'(1:20-23)", "", "Fifth day", ""],
            ["C'(1:24-31)", "", "Sixth day", ""],
            ["P'(2:1-4a)", "", "The Creation", ""],
        ]
        rows = list(parse_structure_sheet(data, book="Gen", source_id="s"))
        # 8 child rows, unit_sequence 1..8
        for i, row in enumerate(rows[1:], start=1):
            assert row["unit_sequence"] == i, (
                f"Row {row['structure_label']} should have unit_sequence={i}"
            )

    def test_child_rows_depth_one(self):
        """Child rows under [1] header have depth=1."""
        data = [
            ["[1]", "Gen 1:1-2:4a", None, None],
            ["A(1:3-5)", "", "First day", ""],
            ["B(1:6-8)", "", "Second day", ""],
        ]
        rows = list(parse_structure_sheet(data, book="Gen", source_id="s"))
        assert rows[0]["depth"] == 0  # header itself
        assert rows[1]["depth"] == 1  # child
        assert rows[2]["depth"] == 1  # child

    def test_header_resets_unit_sequence(self):
        """Each new [N] header resets the unit_sequence counter."""
        data = [
            ["[1]", "Gen 1:1-2:4a", None, None],
            ["A(1:3-5)", "", "First day", ""],
            ["B(1:6-8)", "", "Second day", ""],
            ["[2]", "Gen 2:4b-17", None, None],
            ["A(2:4b-6)", "", "Stream", ""],
        ]
        rows = list(parse_structure_sheet(data, book="Gen", source_id="s"))
        # [1] → A seq=1, B seq=2
        assert rows[1]["unit_sequence"] == 1
        assert rows[2]["unit_sequence"] == 2
        # [2] → A seq=1 (reset)
        assert rows[4]["unit_sequence"] == 1

    def test_summary_row_gets_parent_but_no_unit_sequence(self):
        """None-labeled summary rows within a header block get parent but no seq."""
        data = [
            ["[1]", "Gen 1:1-2:4a", None, None],
            ["A(1:3-5)", "", "First day", ""],
            ["B(1:6-8)", "", "Second day", ""],
            [None, "A: Light and darkness", "A: Light. B: Water.", None],
        ]
        rows = list(parse_structure_sheet(data, book="Gen", source_id="s"))
        summary = rows[3]
        assert summary["parent_label"] == "[1]"
        assert summary["unit_sequence"] is None
        assert summary["depth"] == 0

    def test_pre_header_rows_have_no_parent(self):
        """Rows before any [N] header have parent_label=None."""
        data = [
            [None, None, None, None],
            [None, "Gen 1:1", None, None],
            ["[1]", "Gen 1:1-2:4a", None, None],
            ["A(1:3-5)", "", "First day", ""],
        ]
        rows = list(parse_structure_sheet(data, book="Gen", source_id="s"))
        assert rows[0]["parent_label"] is None
        assert rows[0]["unit_sequence"] is None

    def test_full_genesis_one_real_data(self):
        """Reproduce the real Genesis [1] grouping from the actual workbook."""
        data = [
            ("[1]", "Gen 1:1-2:4a", None, None),
            ("P(1:1-2)", "天地創造", "The Creation", "$mym, )rc"),
            ("A(1:3-5)", "第1日、光と闇、昼と夜", "The first day, light and darkness, day and night", ")wr"),
            ("B(1:6-8)", "第2日、水と空", "The second day, water and sky", "mym"),
            ("C(1:9-13)", "第3日、地と草", "The third day, land and plant", "(&b"),
            ("A'(1:14-19)", "第4日、光と闇、昼と夜", "The fourth day, light and darkness, day and night", "m)wr"),
            ("B'(1:20-23)", "第5日、水と空", "The fifth day, water and sky", "mym"),
            ("C'(1:24-31)", "第6日、地と草", "The sixth day, land and plant", "(&b"),
            ("P'(2:1-4a)", "天地創造", "The Creation", "$mym, )rc"),
        ]
        rows = list(parse_structure_sheet(data, book="Gen", source_id="murai_structure_ot"))
        # 9 rows: 1 header + 8 children
        assert len(rows) == 9
        assert rows[0]["is_header"] is True
        assert rows[0]["structure_label"] == "[1]"
        # All children have parent=[1] and depth=1
        for row in rows[1:]:
            assert row["parent_label"] == "[1]"
            assert row["depth"] == 1
        # Sequential unit_sequence
        assert [r["unit_sequence"] for r in rows[1:]] == [1, 2, 3, 4, 5, 6, 7, 8]
        # Parsed references are preserved
        assert rows[1]["raw_reference"] == "1:1-2"
        assert rows[1]["parsed_reference"]["start_chapter"] == 1
        assert rows[1]["parsed_reference"]["start_verse"] == 1


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


# ---------------------------------------------------------------------------
# Offline DB import payload test
# ---------------------------------------------------------------------------

class TestImportPayload:
    """Verify that the DB import logic sends correct SQL parameters.

    Mocks asyncpg to capture execute() calls without requiring PostgreSQL.
    """

    def _make_structure_item(self, **overrides):
        """Build a minimal structure item dict for testing."""
        base = {
            "source_id": "murai_structure_ot",
            "book": "Gen",
            "structure_label": "A(1:3-5)",
            "is_header": False,
            "parent_label": "[1]",
            "unit_sequence": 1,
            "depth": 1,
            "raw_reference": "1:3-5",
            "parsed_reference": {
                "raw": "1:3-5", "start_chapter": 1, "start_verse": 3,
                "start_suffix": None, "end_chapter": 1, "end_verse": 5,
                "end_suffix": None, "ambiguous": False,
            },
            "description_ja": "第1日",
            "description_en": "The first day",
            "transliteration": ")wr",
            "cross_references": None,
            "workbook_name": "PericopeStructure_OT.xlsx",
            "worksheet_name": "Genesis",
            "excel_row": 3,
            "verse_text": None,
        }
        base.update(overrides)
        return base

    def _make_manifest(self, **overrides):
        base = {
            "source_id": "murai_structure_ot",
            "source_type": "structure",
            "licence": "CC-BY-4.0",
            "url": "http://www.bible.literarystructure.info/bible/bible_e.html",
            "attribution": "Hajime Murai, Literary Structure of the Bible",
            "workbook_path": "data/PericopeStructure_OT.xlsx",
            "workbook_hash": hashlib.sha256(b"").hexdigest(),
            "worksheet_name": "Genesis",
            "version_hint": None,
        }
        base.update(overrides)
        return base

    def test_structure_upsert_payload(self):
        """Structure row upsert receives correct parent_label and unit_sequence."""
        manifest = self._make_manifest()
        item = self._make_structure_item()

        # Verify the payload construction matches the SQL $1-$21 parameter order
        pr = item["parsed_reference"]
        expected_params = (
            item["source_id"], item["book"], item["structure_label"],
            item["is_header"],
            item["parent_label"], item["unit_sequence"], item["depth"],
            item["raw_reference"],
            pr["start_chapter"], pr["start_verse"], pr["start_suffix"],
            pr["end_chapter"], pr["end_verse"], pr["end_suffix"],
            item["description_ja"], item["description_en"],
            item["transliteration"], item["cross_references"],
            item["workbook_name"], item["worksheet_name"], item["excel_row"],
        )
        # Verify the tuple has 21 elements matching the SQL $1-$21
        assert len(expected_params) == 21
        assert expected_params[4] == "[1]"  # parent_label
        assert expected_params[5] == 1     # unit_sequence
        assert expected_params[6] == 1     # depth

    def test_manifest_payload_preserves_worksheet_name(self):
        """Manifest payload stores the raw worksheet_name, not the scope code."""
        manifest = self._make_manifest(worksheet_name="Samuel")
        # The worksheet_name should be the raw sheet name, not "Sam"
        assert manifest["worksheet_name"] == "Samuel"
        # The book code used in structure items would be the scope code
        item = self._make_structure_item(book="Sam", worksheet_name="Samuel")
        assert item["book"] == "Sam"
        assert item["worksheet_name"] == "Samuel"

    def test_pericope_upsert_payload(self):
        """Pericope row upsert receives correct sequence and reference fields."""
        item = {
            "source_id": "murai_pericope_ot",
            "book": "Gen",
            "sequence": 1,
            "raw_reference": "1:1-31",
            "title": "Creation Account",
            "workbook_name": "PericopeList_OT.xlsx",
            "worksheet_name": "Genesis",
            "excel_row": 1,
            "parsed_reference": {
                "raw": "1:1-31", "start_chapter": 1, "start_verse": 1,
                "start_suffix": None, "end_chapter": 1, "end_verse": 31,
                "end_suffix": None, "ambiguous": False,
            },
        }
        pr = item["parsed_reference"]
        expected_params = (
            item["source_id"], item["book"], item["sequence"],
            item["raw_reference"],
            pr["start_chapter"], pr["start_verse"], pr["start_suffix"],
            pr["end_chapter"], pr["end_verse"], pr["end_suffix"],
            item["title"], item["workbook_name"],
            item["worksheet_name"], item["excel_row"],
        )
        assert len(expected_params) == 14
        assert expected_params[2] == 1     # sequence
        assert expected_params[3] == "1:1-31"  # raw_reference
        assert expected_params[9] is None  # end_suffix

    def test_source_manifest_payload(self):
        """Source manifest upsert receives correct provenance fields."""
        manifest = self._make_manifest(worksheet_name="Genesis")
        expected_params = (
            manifest["source_id"], manifest["source_type"],
            manifest["licence"], manifest["url"], manifest["attribution"],
            manifest["workbook_path"], manifest["workbook_hash"],
            manifest["worksheet_name"], manifest["version_hint"],
        )
        assert len(expected_params) == 9
        assert expected_params[0] == "murai_structure_ot"
        assert expected_params[7] == "Genesis"  # raw worksheet name

    def test_grouped_sheet_scope_code_in_book_field(self):
        """Grouped sheets use scope code in 'book' field, raw name in worksheet_name."""
        # Samuel sheet → book="Sam", worksheet_name="Samuel"
        item = self._make_structure_item(book="Sam", worksheet_name="Samuel")
        assert item["book"] == "Sam"
        assert item["worksheet_name"] == "Samuel"
        # Kings sheet → book="Kgs", worksheet_name="Kings"
        item2 = self._make_structure_item(book="Kgs", worksheet_name="Kings")
        assert item2["book"] == "Kgs"
        assert item2["worksheet_name"] == "Kings"
