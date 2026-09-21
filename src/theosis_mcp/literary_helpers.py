"""
Offline helpers for literary structure lookup, reference normalization,
tree rendering, and attribution.

These pure functions are testable without a database or MCP server.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .database import BOOK_ABBREV_MAP, BOOK_NAMES

# ---------------------------------------------------------------------------
# Attribution / disclaimer
# ---------------------------------------------------------------------------

LIT_STRUCT_ATTRIBUTION = (
    "Source: Hajime Murai, \"Literary Structure of the Bible\" "
    "(CC BY 4.0)\n"
    "http://www.bible.literarystructure.info/bible/bible_e.html\n\n"
    "⚠️ DISCLAIMER: These structures are scholarly interpretive proposals, "
    "not canonical or doctrinal divisions. They reflect one analyst's "
    "literary reading of the biblical text and should be treated as "
    "study aids, not authoritative chapter/verse divisions."
)

LIT_STRUCT_DISCLAIMER = (
    "These structures are scholarly interpretive proposals by Hajime Murai "
    "(CC BY 4.0) and should not be treated as canonical chapter/verse "
    "divisions. Use as study aids only."
)


# ---------------------------------------------------------------------------
# Reference normalization
# ---------------------------------------------------------------------------

# Regex: optional book prefix + chapter(:verse)?
_REF_RE = re.compile(
    r"""
    ^\s*
    (?:(?P<book>[A-Za-z][A-Za-z0-9\s]*?)\s+)?   # optional book name
    (?P<chapter>\d+)                                # chapter
    (?::(?P<verse>\d+))?                            # optional :verse
    (?:(?:[-–])(?P<end_chapter>\d+))?(?::(?P<end_verse>\d+))?  # optional range
    \s*$
    """,
    re.VERBOSE,
)

# The source workbook combines some numbered books into one worksheet. The
# importer stores those worksheets as stable literary scopes rather than
# pretending a row can be assigned to only one numbered book.
LITERARY_SCOPE_ALIASES = {
    "1Sa": "Sam", "2Sa": "Sam",
    "1Ki": "Kgs", "2Ki": "Kgs",
    "1Ch": "Chr", "2Ch": "Chr",
    "Ezr": "EzrNeh", "Neh": "EzrNeh",
}

# Simpler regex for "chapter:verse" (no book)
_CH_VERSE_RE = re.compile(r"^(\d+):(\d+)$")
_CH_ONLY_RE = re.compile(r"^(\d+)$")
_CH_RANGE_RE = re.compile(r"^(\d+)[-–](\d+)$")
_CH_VERSE_RANGE_RE = re.compile(r"^(\d+):(\d+)[-–](\d+):(\d+)$")
_CH_VERSE_SINGLE_RANGE_RE = re.compile(r"^(\d+):(\d+)[-–](\d+)$")


def _literary_scope(code: str) -> str:
    """Map a canonical OSIS code to the workbook's combined scope, if any."""
    return LITERARY_SCOPE_ALIASES.get(code, code)


def normalize_book(reference: str | None) -> tuple[str, str]:
    """
    Parse a Bible reference into (book_code, reference_part).

    Examples:
        "Gen 1:1"      -> ("Gen", "1:1")
        "Genesis 1:1-5" -> ("Gen", "1:1-5")
        "1:1"           -> ("", "1:1")
        "1 Sa 1:1"      -> ("1Sa", "1:1")
    """
    reference = (reference or "").strip()
    if not reference:
        return ("", "")

    # Try to split off the book part
    parts = reference.split(None, 1)
    if len(parts) == 1:
        # No book part — just a reference like "1:1" or "1"
        return ("", parts[0])

    potential_book = parts[0]
    ref_part = parts[1].strip()

    # Check if potential_book matches a known book code (case-insensitive)
    lower_book = potential_book.lower()
    if lower_book in BOOK_ABBREV_MAP:
        return (_literary_scope(BOOK_ABBREV_MAP[lower_book]), ref_part)

    # Try joining parts for books like "1 Samuel" or "2 Cor"
    two_part = f"{potential_book} {ref_part}".split(None, 1)
    if len(two_part) >= 2:
        try_key = f"{two_part[0].lower()} {two_part[1].split()[0].lower()}"
        if try_key in BOOK_ABBREV_MAP:
            return (_literary_scope(BOOK_ABBREV_MAP[try_key]), " ".join(two_part[1].split()[1:]))

    # Maybe it's a book abbreviation with number prefix like "1Sa"
    combined = potential_book
    if combined.lower() in BOOK_ABBREV_MAP:
        return (_literary_scope(BOOK_ABBREV_MAP[combined.lower()]), ref_part)

    # Not a known book — treat whole thing as reference
    return ("", reference)


def parse_ref_parts(ref_part: str) -> dict[str, Any]:
    """
    Parse the chapter/verse part of a reference into structured fields.

    Returns dict with keys:
      start_chapter, start_verse, end_chapter, end_verse
    Any value can be None if not specified.
    """
    ref_part = (ref_part or "").strip()
    result: dict[str, Any] = {
        "start_chapter": None,
        "start_verse": None,
        "end_chapter": None,
        "end_verse": None,
    }

    if not ref_part:
        return result

    # chapter:verse - chapter:verse (e.g. 1:1-3:5)
    m = _CH_VERSE_RANGE_RE.match(ref_part)
    if m:
        result["start_chapter"] = int(m.group(1))
        result["start_verse"] = int(m.group(2))
        result["end_chapter"] = int(m.group(3))
        result["end_verse"] = int(m.group(4))
        return result

    # chapter:verse - verse (e.g. 1:1-5)
    m = _CH_VERSE_SINGLE_RANGE_RE.match(ref_part)
    if m:
        result["start_chapter"] = int(m.group(1))
        result["start_verse"] = int(m.group(2))
        result["end_chapter"] = int(m.group(1))
        result["end_verse"] = int(m.group(3))
        return result

    # chapter:verse
    m = _CH_VERSE_RE.match(ref_part)
    if m:
        result["start_chapter"] = int(m.group(1))
        result["start_verse"] = int(m.group(2))
        return result

    # chapter - chapter (e.g. 1-3)
    m = _CH_RANGE_RE.match(ref_part)
    if m:
        result["start_chapter"] = int(m.group(1))
        result["end_chapter"] = int(m.group(2))
        return result

    # chapter only (e.g. 1)
    m = _CH_ONLY_RE.match(ref_part)
    if m:
        result["start_chapter"] = int(m.group(1))
        return result

    return result


def reference_overlaps(
    row: dict[str, Any],
    query_book: str,
    query_parts: dict[str, Any],
) -> bool:
    """
    Check whether a literary structure row overlaps with the queried reference.

    row: dict with keys book, start_chapter, start_verse, end_chapter, end_verse
    query_book: the OSIS book code from the query (may be "")
    query_parts: parsed query reference parts
    """
    # Book filter
    if query_book:
        if row["book"] != query_book:
            return False

    q_ch = query_parts.get("start_chapter")
    q_v = query_parts.get("start_verse")
    q_ech = query_parts.get("end_chapter")
    q_ev = query_parts.get("end_verse")

    # If only book given (no chapter/verse), match all rows for that book
    if q_ch is None:
        return True

    # Row has no parsed reference — fall back to book-only match
    r_ch = row.get("start_chapter")
    r_v = row.get("start_verse")
    r_ech = row.get("end_chapter")
    r_ev = row.get("end_verse")

    if r_ch is None:
        # Row has no parsed reference — include if book matches
        return True

    # Compute the row's range as (start_ch, start_v, end_ch, end_v)
    # Use None as sentinel for "no verse" (chapter-only)
    row_start = (r_ch, r_v if r_v is not None else 0)
    row_end = (r_ech if r_ech is not None else r_ch, r_ev if r_ev is not None else 999)

    # If query is chapter-only (no verse), match any row in that chapter
    if q_v is None:
        # Query is "Gen 3" — match rows whose range includes chapter 3
        q_ch_only_end = q_ech if q_ech is not None else q_ch
        return row_start[0] <= q_ch_only_end and row_end[0] >= q_ch

    # Query is "Gen 1:5" — match rows whose range includes verse 5 of chapter 1
    query_point = (q_ch, q_v)
    if q_ech is not None and q_ev is not None:
        # Range query like "Gen 1:1-5"
        q_range_start = (q_ch, q_v)
        q_range_end = (q_ech, q_ev)
        # Two ranges overlap if one starts before the other ends
        return row_start <= q_range_end and row_end >= q_range_start
    else:
        # Single verse query
        return row_start <= query_point <= row_end


# ---------------------------------------------------------------------------
# Cross-reference token parsing
# ---------------------------------------------------------------------------

# Pattern: <canonNumber>_<BookName>@<pericopeNumber>
# Examples: "42_Luke@13", "23_Isaiah@10", "40_Matthew@64"
_CROSSREF_TOKEN_RE = re.compile(
    r"^\s*(?P<canon>\d+)_(?P<book>[A-Za-z]+)@(?P<pericope>\d+)\s*$"
)

# Canon number → OSIS book code for all 66 books (standard Protestant canon)
# OT: 1-39 = Gen..Mal; NT: 40-66 = Mat..Rev
_CANON_BOOK_MAP: dict[int, str] = {
    1: "Gen", 2: "Exo", 3: "Lev", 4: "Num", 5: "Deu",
    6: "Jos", 7: "Jdg", 8: "Rut", 9: "Sam", 10: "Sam",
    11: "Kgs", 12: "Kgs", 13: "Chr", 14: "Chr", 15: "EzrNeh",
    16: "EzrNeh", 17: "Est", 18: "Job", 19: "Psa", 20: "Pro",
    21: "Ecc", 22: "Sng", 23: "Isa", 24: "Jer", 25: "Lam",
    26: "Ezk", 27: "Dan", 28: "Hos", 29: "Jol", 30: "Amo",
    31: "Oba", 32: "Jon", 33: "Mic", 34: "Nam", 35: "Hab",
    36: "Zep", 37: "Hag", 38: "Zec", 39: "Mal",
    40: "Mat", 41: "Mrk", 42: "Luk", 43: "Jhn", 44: "Act",
    45: "Rom", 46: "1Co", 47: "2Co", 48: "Gal", 49: "Eph",
    50: "Php", 51: "Col", 52: "1Th", 53: "2Th", 54: "1Ti",
    55: "2Ti", 56: "Tit", 57: "Phm", 58: "Heb", 59: "Jas",
    60: "1Pe", 61: "2Pe", 62: "1Jn", 63: "2Jn", 64: "3Jn",
    65: "Jud", 66: "Rev",
}


@dataclass
class CrossRefToken:
    """One parsed cross-reference token from a literary structure row."""
    raw: str
    canon: int | None = None
    book_name: str | None = None  # original name from token (e.g. "Luke")
    pericope: int | None = None
    # Resolved fields (populated by resolve_cross_references)
    target_book_code: str | None = None  # OSIS code (e.g. "Luk")
    target_id: int | None = None  # literary_structures.id of the [N] header
    target_label: str | None = None  # structure_label (e.g. "[13]")
    target_ja: str | None = None  # Japanese description of pericope header


def parse_cross_reference_tokens(raw_str: str | None) -> list[CrossRefToken]:
    """
    Parse a comma-separated cross-reference string into CrossRefToken objects.

    Input format (from workbook): "42_Luke@13,23_Isaiah@10,23_Isaiah@11"
    Each token: <canonNumber>_<BookName>@<pericopeNumber>

    Returns a list of CrossRefToken objects with raw, canon, book_name,
    pericope fields populated. Unparseable tokens retain only the raw string.
    """
    if not raw_str or not raw_str.strip():
        return []

    tokens: list[CrossRefToken] = []
    for piece in raw_str.split(","):
        piece = piece.strip()
        if not piece:
            continue

        m = _CROSSREF_TOKEN_RE.match(piece)
        if m:
            canon = int(m.group("canon"))
            book_name = m.group("book")
            pericope = int(m.group("pericope"))

            # Resolve target_book_code from canon number first, then book name
            target_code = _CANON_BOOK_MAP.get(canon)
            if not target_code:
                # Fallback: try book name lookup via BOOK_ABBREV_MAP
                target_code = BOOK_ABBREV_MAP.get(book_name.lower())

            tokens.append(CrossRefToken(
                raw=piece,
                canon=canon,
                book_name=book_name,
                pericope=pericope,
                target_book_code=target_code,
            ))
        else:
            # Unparseable token — keep raw text
            tokens.append(CrossRefToken(raw=piece))

    return tokens


def resolve_cross_references(
    raw_str: str | None,
    pericope_rows: list[dict[str, Any]],
) -> list[CrossRefToken]:
    """
    Parse and resolve cross-reference tokens against pericope header rows.

    Args:
        raw_str: comma-separated cross-reference string from literary_structures
        pericope_rows: list of structure row dicts (headers with is_header=True
            and structure_label matching '[N]' pattern) that are candidates for
            resolution. These should be pre-fetched from the relevant book(s).

    Returns:
        List of CrossRefToken objects with resolution fields populated
        when possible. Unresolvable tokens retain raw text only.

    Resolution strategy:
        1. Parse token to get canon/book_name/pericope
        2. Match pericope header by: target_book_code == row['book']
           AND structure_label == f'[{pericope}]'
        3. If found, populate target_id, target_label, target_ja
    """
    tokens = parse_cross_reference_tokens(raw_str)
    if not tokens or not pericope_rows:
        return tokens

    # Build a lookup: (book_code, pericope_number) → row
    pericope_map: dict[tuple[str, int], dict[str, Any]] = {}
    for row in pericope_rows:
        if not row.get("is_header"):
            continue
        label = row.get("structure_label") or ""
        # Match "[N]" pattern
        m = re.match(r"^\[(\d+)\]$", label)
        if m:
            num = int(m.group(1))
            book = row.get("book", "")
            pericope_map[(book, num)] = row

    for token in tokens:
        if token.target_book_code is None or token.pericope is None:
            continue
        key = (token.target_book_code, token.pericope)
        row = pericope_map.get(key)
        if row:
            token.target_id = row.get("id")
            token.target_label = row.get("structure_label")
            # Prefer readable English for the MCP result; retain Japanese as
            # a fallback when the workbook has no English description.
            token.target_ja = row.get("description_en") or row.get("description_ja")

    return tokens


def format_cross_ref_tokens(tokens: list[CrossRefToken]) -> list[str]:
    """
    Format resolved cross-reference tokens into readable lines.

    Each line includes:
      - Raw token (e.g. `42_Luke@13`)
      - Readable label: "Book — pericope N: description" when resolved
      - Target ID when available

    Returns a list of formatted strings for display.
    """
    lines: list[str] = []
    for token in tokens:
        book_display = token.book_name or "???"
        pericope_display = str(token.pericope) if token.pericope is not None else "?"

        if token.target_id is not None:
            # Resolved
            desc = ""
            if token.target_ja:
                desc = f": {token.target_ja}"
            line = (
                f"- `{token.raw}` → "
                f"{book_display} — pericope {pericope_display}{desc} "
                f"(ID: {token.target_id})"
            )
        elif token.pericope is not None:
            # Partially resolved (parsed but not found in data)
            line = (
                f"- `{token.raw}` → "
                f"{book_display} — pericope {pericope_display} "
                f"(unresolved)"
            )
        else:
            # Unparseable
            line = f"- `{token.raw}` (unparseable)"
        lines.append(line)
    return lines


# ---------------------------------------------------------------------------
# Nested tree rendering
# ---------------------------------------------------------------------------

def _row_sort_key(row: dict[str, Any]) -> tuple[int, int]:
    """Sort key for rows: by excel_row if available, else by id."""
    return (row.get("excel_row") or 0, row.get("id") or 0)


def _row_display_label(row: dict[str, Any]) -> str:
    """Build a display label for a structure row."""
    label = row.get("structure_label") or ""
    if row.get("is_header"):
        return f"{label} [header]"
    return label


def _row_ref_str(row: dict[str, Any]) -> str:
    """Build a human-readable reference string for a row."""
    book = row.get("book", "")
    raw = row.get("raw_reference") or ""
    ch = row.get("start_chapter")
    v = row.get("start_verse")
    ech = row.get("end_chapter")
    ev = row.get("end_verse")

    if ch is not None:
        ref = str(ch)
        if v is not None:
            ref += f":{v}"
        if ech is not None and ech != ch:
            ref += f"-{ech}"
            if ev is not None:
                ref += f":{ev}"
        elif ev is not None:
            ref += f"-{ev}"
        return f"{book} {ref}" if book else ref

    if raw:
        return f"{book} {raw}" if book else raw

    return ""


def _row_details(row: dict[str, Any]) -> list[str]:
    """Collect non-empty detail lines for a row."""
    details = []
    if row.get("source_id"):
        details.append(f"Source: {row['source_id']}")
    if row.get("description_en"):
        details.append(f"Description: {row['description_en']}")
    if row.get("description_ja"):
        details.append(f"Japanese: {row['description_ja']}")
    if row.get("transliteration"):
        details.append(f"Translit: {row['transliteration']}")
    if row.get("cross_references"):
        details.append(f"Cross-refs: {row['cross_references']}")
    if row.get("depth") is not None and row["depth"] > 0:
        details.append(f"Depth: {row['depth']}")
    if row.get("unit_sequence") is not None:
        details.append(f"Unit: {row['unit_sequence']}")
    return details


def render_structure_tree(rows: list[dict[str, Any]]) -> str:
    """
    Render a flat list of structure rows as a nested readable tree,
    grouped by [N] headers using parent_label/depth/unit_sequence.

    Returns a plain-text tree string with attribution and disclaimer.
    """
    if not rows:
        return "No structures found.\n\n" + LIT_STRUCT_ATTRIBUTION

    # Sort rows
    sorted_rows = sorted(rows, key=_row_sort_key)

    # Group children under headers by parent_label
    headers: dict[str, list[dict[str, Any]]] = {}  # label -> children
    header_order: list[str] = []  # preserve insertion order
    orphan_children: list[dict[str, Any]] = []

    # First pass: identify headers
    for row in sorted_rows:
        if row.get("is_header"):
            label = row.get("structure_label") or ""
            if label not in headers:
                headers[label] = []
                header_order.append(label)

    # Second pass: assign children to headers
    for row in sorted_rows:
        if row.get("is_header"):
            continue
        parent = row.get("parent_label")
        if parent and parent in headers:
            headers[parent].append(row)
        else:
            orphan_children.append(row)

    # Build output
    lines = []
    lines.append("# Literary Structures\n")
    lines.append(LIT_STRUCT_DISCLAIMER + "\n")

    for header_label in header_order:
        header_row = None
        for row in sorted_rows:
            if row.get("is_header") and row.get("structure_label") == header_label:
                header_row = row
                break

        if header_row:
            ref_str = _row_ref_str(header_row)
            lines.append(f"## {header_label}")
            if ref_str:
                lines.append(f"   Ref: {ref_str}")
            lines.append("")

        children = headers[header_label]
        for child in sorted(children, key=lambda r: (r.get("unit_sequence") or 9999, _row_sort_key(r))):
            # Depth is supplied by the importer from the workbook's structural
            # label (A, B1, A', ...). Use it for readable nesting without
            # inventing parent relationships not present in the source.
            depth = child.get("depth") or 1
            indent = "   " * max(1, int(depth))
            label = _row_display_label(child)
            ref_str = _row_ref_str(child)
            line = f"{indent}- {label}"
            if ref_str:
                line += f"  ({ref_str})"
            lines.append(line)
            details = _row_details(child)
            for detail in details:
                lines.append(f"{indent}  {detail}")
        lines.append("")

    # Orphan rows (no parent header found)
    if orphan_children:
        lines.append("## Other structures\n")
        for child in orphan_children:
            label = _row_display_label(child)
            ref_str = _row_ref_str(child)
            line = f"   - {label}"
            if ref_str:
                line += f"  ({ref_str})"
            lines.append(line)
            details = _row_details(child)
            for detail in details:
                lines.append(f"     {detail}")
        lines.append("")

    lines.append("---")
    lines.append(f"\n{LIT_STRUCT_ATTRIBUTION}")
    return "\n".join(lines)


def format_structure_result(
    rows: list[dict[str, Any]],
    query_ref: str,
    output_mode: str = "flat",
) -> str:
    """
    Format structure rows into a readable string.

    output_mode:
      - "flat" — one entry per row with headers/labels
      - "tree" — nested tree grouped by [N] headers
    """
    if output_mode == "tree":
        return render_structure_tree(rows)

    # Flat mode
    if not rows:
        return f"No structures found for '{query_ref}'.\n\n{LIT_STRUCT_ATTRIBUTION}"

    lines = [f"## Literary Structures: {query_ref}\n"]
    lines.append(LIT_STRUCT_DISCLAIMER + "\n")

    for row in rows:
        label = _row_display_label(row)
        rid = row.get("id", "?")
        ref_str = _row_ref_str(row)
        lines.append(f"### {label} (ID: {rid})")
        lines.append(f"**Source**: {row.get('source_id', '')}")
        if ref_str:
            lines.append(f"**Reference**: {ref_str}")
        for detail in _row_details(row):
            # Remove redundant source line
            if detail.startswith("Source:"):
                continue
            key, _, val = detail.partition(": ")
            lines.append(f"**{key}**: {val}")
        lines.append("\n---\n")

    lines.append(f"\n{LIT_STRUCT_ATTRIBUTION}")
    return "\n".join(lines)
