"""Offline tests for Literary Structure cross-reference parsing and resolution."""

from theosis_mcp.literary_helpers import (
    format_cross_ref_tokens,
    parse_cross_reference_tokens,
    resolve_cross_references,
)


def test_parse_multiple_tokens_and_preserve_raw_values():
    tokens = parse_cross_reference_tokens("42_Luke@13, 23_Isaiah@10,23_Isaiah@11")
    assert [(t.canon, t.book_name, t.pericope) for t in tokens] == [
        (42, "Luke", 13),
        (23, "Isaiah", 10),
        (23, "Isaiah", 11),
    ]
    assert [t.raw for t in tokens] == ["42_Luke@13", "23_Isaiah@10", "23_Isaiah@11"]
    assert [t.target_book_code for t in tokens] == ["Luk", "Isa", "Isa"]


def test_parse_malformed_token_without_dropping_it():
    tokens = parse_cross_reference_tokens("42_Luke@13, malformed, 999_Unknown@2")
    assert [t.raw for t in tokens] == ["42_Luke@13", "malformed", "999_Unknown@2"]
    assert tokens[1].pericope is None
    assert tokens[2].target_book_code is None


def test_resolve_headers_to_readable_targets():
    rows = [
        {"id": 101, "book": "Luk", "is_header": True, "structure_label": "[13]", "description_en": "Luke genealogy", "description_ja": "ルカ系図"},
        {"id": 202, "book": "Isa", "is_header": True, "structure_label": "[10]", "description_en": "Isaiah promise", "description_ja": "イザヤの約束"},
    ]
    tokens = resolve_cross_references("42_Luke@13,23_Isaiah@10,40_Matthew@99", rows)
    assert tokens[0].target_id == 101
    assert tokens[0].target_ja == "Luke genealogy"
    assert tokens[1].target_id == 202
    assert tokens[2].target_id is None
    lines = format_cross_ref_tokens(tokens)
    assert "`42_Luke@13`" in lines[0]
    assert "Luke — pericope 13: Luke genealogy" in lines[0]
    assert "Matthew — pericope 99 (unresolved)" in lines[2]


def test_empty_input_returns_no_tokens():
    assert parse_cross_reference_tokens(None) == []
    assert parse_cross_reference_tokens("") == []
