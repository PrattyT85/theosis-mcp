#!/usr/bin/env python3
"""
Offline tests for literary structure helpers:
  - Reference normalisation (normalize_book, parse_ref_parts)
  - Reference overlap matching (reference_overlaps)
  - Nested tree rendering (render_structure_tree, format_structure_result)
  - Attribution and disclaimer presence

Live tests are in test_literary_structure_live.py and skip without
THEOSIS_MCP_URL.
"""
import pytest

from theosis_mcp.literary_helpers import (
    LIT_STRUCT_ATTRIBUTION,
    LIT_STRUCT_DISCLAIMER,
    normalize_book,
    parse_ref_parts,
    reference_overlaps,
    render_structure_tree,
    format_structure_result,
    _row_ref_str,
)


# ---------------------------------------------------------------------------
# Reference normalisation
# ---------------------------------------------------------------------------

class TestNormalizeBook:
    """Parse 'Gen 1:1' into (book_code, '1:1')."""

    def test_full_name(self):
        assert normalize_book("Genesis 1:1") == ("Gen", "1:1")

    def test_osis_code(self):
        assert normalize_book("Gen 1:1") == ("Gen", "1:1")

    def test_full_name_range(self):
        assert normalize_book("Genesis 1:1-31") == ("Gen", "1:1-31")

    def test_no_book(self):
        assert normalize_book("1:1") == ("", "1:1")

    def test_chapter_only(self):
        assert normalize_book("Gen 3") == ("Gen", "3")

    def test_two_word_book(self):
        assert normalize_book("1 Samuel 1:1") == ("Sam", "1:1")

    def test_two_word_book_2cor(self):
        assert normalize_book("2 Cor 1:1") == ("2Co", "1:1")

    def test_combined_workbook_scope(self):
        assert normalize_book("1 Samuel 1:1") == ("Sam", "1:1")
        assert normalize_book("2 Kings 1:1") == ("Kgs", "1:1")
        assert normalize_book("Nehemiah 1:1") == ("EzrNeh", "1:1")

    def test_case_insensitive(self):
        assert normalize_book("genesis 1:1") == ("Gen", "1:1")

    def test_empty(self):
        assert normalize_book("") == ("", "")

    def test_none(self):
        assert normalize_book(None) is not None  # returns ("", "") for None input


class TestParseRefParts:
    """Parse chapter/verse parts into structured fields."""

    def test_single_verse(self):
        r = parse_ref_parts("1:1")
        assert r["start_chapter"] == 1
        assert r["start_verse"] == 1
        assert r["end_chapter"] is None
        assert r["end_verse"] is None

    def test_chapter_only(self):
        r = parse_ref_parts("3")
        assert r["start_chapter"] == 3
        assert r["start_verse"] is None

    def test_verse_range_same_chapter(self):
        r = parse_ref_parts("1:5-7")
        assert r["start_chapter"] == 1
        assert r["start_verse"] == 5
        assert r["end_chapter"] == 1
        assert r["end_verse"] == 7

    def test_chapter_range(self):
        r = parse_ref_parts("1-3")
        assert r["start_chapter"] == 1
        assert r["end_chapter"] == 3
        assert r["start_verse"] is None

    def test_cross_chapter_range(self):
        r = parse_ref_parts("1:31-2:4")
        assert r["start_chapter"] == 1
        assert r["start_verse"] == 31
        assert r["end_chapter"] == 2
        assert r["end_verse"] == 4

    def test_empty(self):
        r = parse_ref_parts("")
        assert r["start_chapter"] is None


# ---------------------------------------------------------------------------
# Reference overlap matching
# ---------------------------------------------------------------------------

def _mk_row(**kw):
    """Build a minimal row dict for overlap testing."""
    base = {
        "id": 1, "book": "Gen", "source_id": "s",
        "structure_label": "A(1:3-5)", "is_header": False,
        "parent_label": "[1]", "unit_sequence": 1, "depth": 1,
        "raw_reference": "1:3-5",
        "start_chapter": 1, "start_verse": 3,
        "end_chapter": 1, "end_verse": 5,
        "description_ja": "", "description_en": "First day",
        "transliteration": "", "cross_references": None,
        "excel_row": 3,
    }
    base.update(kw)
    return base


class TestReferenceOverlaps:
    """Check overlap logic between query and structure rows."""

    def test_exact_verse_match(self):
        row = _mk_row(start_chapter=1, start_verse=3, end_chapter=1, end_verse=5)
        q = {"start_chapter": 1, "start_verse": 3, "end_chapter": None, "end_verse": None}
        assert reference_overlaps(row, "Gen", q) is True

    def test_verse_inside_range(self):
        row = _mk_row(start_chapter=1, start_verse=3, end_chapter=1, end_verse=5)
        q = {"start_chapter": 1, "start_verse": 4, "end_chapter": None, "end_verse": None}
        assert reference_overlaps(row, "Gen", q) is True

    def test_verse_outside_range(self):
        row = _mk_row(start_chapter=1, start_verse=3, end_chapter=1, end_verse=5)
        q = {"start_chapter": 1, "start_verse": 6, "end_chapter": None, "end_verse": None}
        assert reference_overlaps(row, "Gen", q) is False

    def test_chapter_only_matches_all_in_chapter(self):
        row = _mk_row(start_chapter=1, start_verse=3, end_chapter=1, end_verse=5)
        q = {"start_chapter": 1, "start_verse": None, "end_chapter": None, "end_verse": None}
        assert reference_overlaps(row, "Gen", q) is True

    def test_chapter_only_no_match(self):
        row = _mk_row(start_chapter=1, start_verse=3, end_chapter=1, end_verse=5)
        q = {"start_chapter": 2, "start_verse": None, "end_chapter": None, "end_verse": None}
        assert reference_overlaps(row, "Gen", q) is False

    def test_book_only_matches_all(self):
        row = _mk_row(book="Gen")
        q = {"start_chapter": None, "start_verse": None, "end_chapter": None, "end_verse": None}
        assert reference_overlaps(row, "Gen", q) is True

    def test_wrong_book_no_match(self):
        row = _mk_row(book="Gen")
        q = {"start_chapter": 1, "start_verse": 1, "end_chapter": None, "end_verse": None}
        assert reference_overlaps(row, "Exo", q) is False

    def test_empty_book_matches_all_books(self):
        """Empty query_book means all books are candidates."""
        row = _mk_row(book="Gen")
        q = {"start_chapter": 1, "start_verse": 3, "end_chapter": None, "end_verse": None}
        assert reference_overlaps(row, "", q) is True

    def test_empty_book_with_verse_in_range(self):
        """Empty book + verse inside row range → match."""
        row = _mk_row(book="Gen", start_chapter=1, start_verse=3, end_chapter=1, end_verse=5)
        q = {"start_chapter": 1, "start_verse": 4, "end_chapter": None, "end_verse": None}
        assert reference_overlaps(row, "", q) is True

    def test_range_query_overlaps(self):
        row = _mk_row(start_chapter=1, start_verse=3, end_chapter=1, end_verse=5)
        q = {"start_chapter": 1, "start_verse": 1, "end_chapter": 1, "end_verse": 5}
        assert reference_overlaps(row, "Gen", q) is True

    def test_cross_chapter_row(self):
        row = _mk_row(start_chapter=1, start_verse=31, end_chapter=2, end_verse=4)
        q = {"start_chapter": 2, "start_verse": 1, "end_chapter": None, "end_verse": None}
        assert reference_overlaps(row, "Gen", q) is True

    def test_row_without_parsed_ref_matches_book_only(self):
        row = _mk_row(start_chapter=None, start_verse=None, end_chapter=None, end_verse=None)
        q = {"start_chapter": 1, "start_verse": 1, "end_chapter": None, "end_verse": None}
        assert reference_overlaps(row, "Gen", q) is True


# ---------------------------------------------------------------------------
# Tree rendering
# ---------------------------------------------------------------------------

def _mk_header(**kw):
    base = {
        "id": 1, "book": "Gen", "source_id": "murai_structure_ot",
        "structure_label": "[1]", "is_header": True,
        "parent_label": None, "unit_sequence": None, "depth": 0,
        "raw_reference": "Gen 1:1-2:4a",
        "start_chapter": 1, "start_verse": 1,
        "end_chapter": 2, "end_verse": 4,
        "description_ja": "", "description_en": "",
        "transliteration": "", "cross_references": None,
        "excel_row": 2,
    }
    base.update(kw)
    return base


def _mk_child(**kw):
    base = {
        "id": 2, "book": "Gen", "source_id": "murai_structure_ot",
        "structure_label": "A(1:3-5)", "is_header": False,
        "parent_label": "[1]", "unit_sequence": 1, "depth": 1,
        "raw_reference": "1:3-5",
        "start_chapter": 1, "start_verse": 3,
        "end_chapter": 1, "end_verse": 5,
        "description_ja": "第1日", "description_en": "The first day",
        "transliteration": ")wr", "cross_references": None,
        "excel_row": 3,
    }
    base.update(kw)
    return base


class TestRenderStructureTree:
    """Tree rendering groups children under [N] headers."""

    def test_empty_returns_disclaimer(self):
        result = render_structure_tree([])
        assert "No structures" in result
        assert "Hajime Murai" in result

    def test_header_and_children_grouped(self):
        header = _mk_header()
        child1 = _mk_child(structure_label="A(1:3-5)", unit_sequence=1)
        child2 = _mk_child(
            id=3, structure_label="B(1:6-8)", unit_sequence=2,
            raw_reference="1:6-8", start_chapter=1, start_verse=6,
            end_chapter=1, end_verse=8,
            description_en="The second day", excel_row=4,
        )
        result = render_structure_tree([header, child1, child2])
        assert "[1]" in result
        assert "A(1:3-5)" in result
        assert "B(1:6-8)" in result
        assert "The first day" in result
        assert "The second day" in result

    def test_orphan_children_appear(self):
        child = _mk_child(parent_label=None, is_header=False)
        result = render_structure_tree([child])
        assert "A(1:3-5)" in result
        assert "The first day" in result

    def test_attribution_present(self):
        header = _mk_header()
        result = render_structure_tree([header])
        assert "Hajime Murai" in result
        assert "CC BY 4.0" in result
        assert "interpretive" in result.lower()

    def test_sorting_by_excel_row(self):
        child_later = _mk_child(
            id=5, structure_label="B(1:6-8)", unit_sequence=2, excel_row=10,
        )
        child_earlier = _mk_child(
            id=4, structure_label="A(1:3-5)", unit_sequence=1, excel_row=3,
        )
        result = render_structure_tree([child_later, child_earlier])
        # Earlier excel_row should come first
        pos_a = result.index("A(1:3-5)")
        pos_b = result.index("B(1:6-8)")
        assert pos_a < pos_b


class TestFormatStructureResult:
    """format_structure_result dispatches flat vs tree mode."""

    def test_flat_mode(self):
        rows = [_mk_child()]
        result = format_structure_result(rows, "Gen 1:1", output_mode="flat")
        assert "A(1:3-5)" in result
        assert "Hajime Murai" in result

    def test_tree_mode(self):
        header = _mk_header()
        child = _mk_child()
        result = format_structure_result([header, child], "Gen", output_mode="tree")
        assert "[1]" in result
        assert "A(1:3-5)" in result

    def test_empty_returns_not_found(self):
        result = format_structure_result([], "Gen 99:99", output_mode="flat")
        assert "No structures" in result
        assert "Gen 99:99" in result


class TestRowRefStr:
    """_row_ref_str builds human-readable references."""

    def test_chapter_verse(self):
        row = {"book": "Gen", "raw_reference": "1:1", "start_chapter": 1, "start_verse": 1,
               "end_chapter": None, "end_verse": None}
        assert _row_ref_str(row) == "Gen 1:1"

    def test_verse_range(self):
        row = {"book": "Gen", "raw_reference": "", "start_chapter": 1, "start_verse": 3,
               "end_chapter": 1, "end_verse": 5}
        assert _row_ref_str(row) == "Gen 1:3-5"

    def test_chapter_range(self):
        row = {"book": "Gen", "raw_reference": "", "start_chapter": 1, "start_verse": None,
               "end_chapter": 3, "end_verse": None}
        assert _row_ref_str(row) == "Gen 1-3"

    def test_fallback_to_raw(self):
        row = {"book": "Gen", "raw_reference": "1:1-31 2:1-4a", "start_chapter": None,
               "start_verse": None, "end_chapter": None, "end_verse": None}
        assert _row_ref_str(row) == "Gen 1:1-31 2:1-4a"


# ---------------------------------------------------------------------------
# Attribution and disclaimer constants
# ---------------------------------------------------------------------------

class TestAttribution:
    """Attribution and disclaimer text is correct."""

    def test_attribution_has_cc_by(self):
        assert "CC BY 4.0" in LIT_STRUCT_ATTRIBUTION

    def test_attribution_has_url(self):
        assert "literarystructure.info" in LIT_STRUCT_ATTRIBUTION

    def test_disclaimer_warns(self):
        assert "interpretive" in LIT_STRUCT_DISCLAIMER.lower()

    def test_disclaimer_not_doctrinal(self):
        assert "canonical" in LIT_STRUCT_DISCLAIMER.lower()
