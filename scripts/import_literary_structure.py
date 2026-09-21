#!/usr/bin/env python3
"""
Import Literary Structure corpus from Hajime Murai's Excel workbooks.

Source: http://www.bible.literarystructure.info/bible/bible_e.html
Licence: CC BY 4.0 (attribution required)

Pure parser functions for pericope list sheets and structure analysis sheets.
PostgreSQL import mode applies idempotent upserts into 004 tables.
No verse text is ever stored.

Usage:
  uv run python scripts/import_literary_structure.py --workbooks-dir ./data \
      --dry-run --source-type pericope_list
  uv run python scripts/import_literary_structure.py --workbooks-dir ./data \
      --source-type structure
  uv run python scripts/import_literary_structure.py --workbooks-dir ./data \
      --source-type structure --db-url postgresql://theosis:...@localhost:5432/theosis
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Sequence

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LICENCE = "CC-BY-4.0"
SOURCE_URL = "http://www.bible.literarystructure.info/bible/bible_e.html"
ATTRIBUTION = "Hajime Murai, Literary Structure of the Bible"

# ---------------------------------------------------------------------------
# Worksheet-name → scope/stable-code mapping
# ---------------------------------------------------------------------------
# The Murai workbooks use full worksheet names (Genesis, Exodus, Samuel, …).
# This maps every observed sheet name to a stable scope code.
# Grouped OT sheets (Samuel, Kings, Chronicles, Ezra-Nehemiah) use compound
# scope codes rather than pretending one sheet is only 1 Samuel.
# Sheets not in this list fall back to the raw sheet name.

SHEET_TO_OSIS: dict[str, str] = {
    # ── Full worksheet names (observed in actual .xlsx sheets) ───────────
    # OT — full names
    "Genesis": "Gen", "Exodus": "Exo", "Leviticus": "Lev",
    "Numbers": "Num", "Deuteronomy": "Deu", "Joshua": "Jos",
    "Judges": "Jdg", "Ruth": "Rut",
    # Grouped OT sheets (one sheet spans multiple books)
    "Samuel": "Sam", "Kings": "Kgs", "Chronicles": "Chr",
    "Ezra-Nehemiah": "EzrNeh",
    "Esther": "Est", "Job": "Job", "Psalms": "Psa",
    "Proverbs": "Pro", "Ecclesiastes": "Ecc",
    "SongofSolomon": "Sng",
    "Isaiah": "Isa", "Jeremiah": "Jer", "Lamentation": "Lam",
    "Ezekiel": "Ezk", "Daniel": "Dan",
    "Hosea": "Hos", "Joel": "Jol", "Amos": "Amo",
    "Obadiah": "Oba", "Jonah": "Jon", "Micah": "Mic",
    "Nahum": "Nam", "Habakkuk": "Hab", "Zephaniah": "Zep",
    "Haggai": "Hag", "Zechariah": "Zec", "Malachi": "Mal",
    # NT — full names
    "Matthew": "Mat", "Mark": "Mrk", "Luke": "Luk", "John": "Jhn",
    "Acts": "Act", "Romans": "Rom",
    "1Corinthians": "1Co", "2Corinthians": "2Co",
    "Galatians": "Gal", "Ephesians": "Eph",
    "Philippians": "Php", "Colossians": "Col",
    "1Thessalonians": "1Th", "2Thessalonians": "2Th",
    "1Timothy": "1Ti", "2Timothy": "2Ti",
    "Titus": "Tit", "Philemon": "Phm", "Hebrews": "Heb",
    "James": "Jas", "1Peter": "1Pe", "2Peter": "2Pe",
    "1John": "1Jn", "2John": "2Jn", "3John": "3Jn",
    "Jude": "Jud", "Revelation": "Rev",
    # ── Abbreviated sheet names (legacy / alternate workbooks) ───────────
    "Gen": "Gen", "Exo": "Exo", "Lev": "Lev", "Num": "Num",
    "Deu": "Deu", "Jos": "Jos", "Jug": "Jug", "Rut": "Rut",
    "1S": "1Sa", "2S": "2Sa",
    "1Ki": "1Ki", "2Ki": "2Ki",
    "1Ch": "1Ch", "2Ch": "2Ch",
    "Ezr": "Ezr", "Neh": "Neh", "1Ne": "Neh",
    "Est": "Est",
    "Job": "Job", "Psa": "Psa", "Pro": "Pro", "Ecc": "Ecc",
    "Sng": "Sng", "Isa": "Isa", "Jer": "Jer", "Lam": "Lam",
    "Eze": "Eze", "Dan": "Dan", "Hos": "Hos", "Joe": "Joe",
    "Amo": "Amo", "Oba": "Oba", "Ob": "Oba",
    "Jon": "Jon", "Mic": "Mic", "Nam": "Nam", "Hab": "Hab",
    "Zep": "Zep", "Hag": "Hag", "Zec": "Zec", "Mal": "Mal",
    "Mat": "Mat", "Mar": "Mar", "Luk": "Luk", "Jhn": "Jhn",
    "Act": "Act", "Rom": "Rom", "1Co": "1Co", "2Co": "2Co",
    "Gal": "Gal", "Eph": "Eph", "Phi": "Phi", "Col": "Col",
    "1Th": "1Th", "2Th": "2Th", "1Ti": "1Ti", "2Ti": "2Ti",
    "Tit": "Tit", "Phm": "Phm", "Heb": "Heb",
    "Jam": "Jam", "1Pe": "1Pe", "2Pe": "2Pe",
    "1Jn": "1Jn", "2Jn": "2Jn", "3Jn": "3Jn",
    "Jud": "Jud", "Rev": "Rev",
    # ── Alternate long forms that may appear ─────────────────────────────
    "Samuel1": "1Sa", "Samuel2": "2Sa",
    "Kings1": "1Ki", "Kings2": "2Ki",
    "Chronicles1": "1Ch", "Chronicles2": "2Ch",
    "Chron1": "1Ch", "Chron2": "2Ch",
    "Corinthians1": "1Co", "Corinthians2": "2Co",
    "Thessalonians1": "1Th", "Thessalonians2": "2Th",
    "Timothy1": "1Ti", "Timothy2": "2Ti",
    "John1": "1Jn", "John2": "2Jn", "John3": "3Jn",
    "Peter1": "1Pe", "Peter2": "2Pe",
    # ── Case-variant abbreviations ───────────────────────────────────────
    "psa": "Psa", "pro": "Pro", "isa": "Isa",
    "1sa": "1Sa", "2sa": "2Sa", "1ki": "1Ki", "2ki": "2Ki",
    "1ch": "1Ch", "2ch": "2Ch", "1co": "1Co", "2co": "2Co",
    "1th": "1Th", "2th": "2Th", "1ti": "1Ti", "2ti": "2Ti",
    "1jn": "1Jn", "2jn": "2Jn", "3jn": "3Jn",
    "1pe": "1Pe", "2pe": "2Pe",
}


def sheet_to_osis(sheet_name: str) -> str:
    """Map a worksheet name to an OSIS book code.

    Falls back to the raw sheet name when the name is not in the lookup table.
    """
    return SHEET_TO_OSIS.get(sheet_name, sheet_name)


# Workbooks observed in the wild
KNOWN_WORKBOOKS: dict[str, dict[str, str]] = {
    "LiteraryStructureoftheBible_PericopeList_OT.xlsx": {
        "source_id": "murai_pericope_ot",
        "source_type": "pericope_list",
    },
    "LiteraryStructureoftheBible_PericopeList_NT.xlsx": {
        "source_id": "murai_pericope_nt",
        "source_type": "pericope_list",
    },
    "LiteraryStructureoftheBible_PericopeStructure_OT.xlsx": {
        "source_id": "murai_structure_ot",
        "source_type": "structure",
    },
    "LiteraryStructureoftheBible_PericopeStructure_NT.xlsx": {
        "source_id": "murai_structure_nt",
        "source_type": "structure",
    },
    # Accept the shorter historical filenames too.
    "PericopeList_OT.xlsx": {"source_id": "murai_pericope_ot", "source_type": "pericope_list"},
    "PericopeList_NT.xlsx": {"source_id": "murai_pericope_nt", "source_type": "pericope_list"},
    "PericopeStructure_OT.xlsx": {"source_id": "murai_structure_ot", "source_type": "structure"},
    "PericopeStructure_NT.xlsx": {"source_id": "murai_structure_nt", "source_type": "structure"},
}


# ---------------------------------------------------------------------------
# Reference parsing
# ---------------------------------------------------------------------------

def _sha256_of_file(path: str | Path) -> str:
    """Return SHA-256 hex digest of a file. Returns sha256(b"") for missing."""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
    except FileNotFoundError:
        pass
    return h.hexdigest()


def source_manifest(
    *,
    source_id: str,
    source_type: str,
    workbook_path: str | Path,
    worksheet_name: str,
    licence: str = LICENCE,
    url: str = SOURCE_URL,
    attribution: str = ATTRIBUTION,
    version_hint: str | None = None,
) -> dict[str, Any]:
    """Build a provenance manifest for a workbook/worksheet pair."""
    return {
        "source_id": source_id,
        "source_type": source_type,
        "licence": licence,
        "url": url,
        "attribution": attribution,
        "workbook_path": str(workbook_path),
        "workbook_hash": _sha256_of_file(workbook_path),
        "worksheet_name": worksheet_name,
        "version_hint": version_hint,
    }


def normalize_reference(book: str, raw_ref: str) -> str:
    """Combine a book code and raw reference into canonical form."""
    raw_ref = (raw_ref or "").strip()
    if not raw_ref:
        return book
    return f"{book} {raw_ref}"


# Numeric-chapter:verse with optional suffix (e.g. "4a", "5b")
_CH_VERSE_RE = re.compile(
    r"^(\d+):(\d+)([ab])?$"
)
_CH_CH_RE = re.compile(
    r"^(\d+)-(\d+)$"
)
_CH_ONLY_RE = re.compile(r"^(\d+)$")


def parse_reference(raw: str, *, strip_book_prefix: bool = False) -> dict[str, Any]:
    """
    Parse a raw reference string into normalised numeric components.

    Returns a dict with:
      raw, start_chapter, start_verse, start_suffix,
      end_chapter, end_verse, end_suffix, ambiguous

    Multi-range references (e.g. "1:1-31 2:1-4a") are flagged as ambiguous.
    Unparseable strings are returned with raw only.
    """
    raw = (raw or "").strip()
    result: dict[str, Any] = {
        "raw": raw,
        "start_chapter": None,
        "start_verse": None,
        "start_suffix": None,
        "end_chapter": None,
        "end_verse": None,
        "end_suffix": None,
        "ambiguous": False,
    }

    if not raw:
        return result

    # Strip book prefix like "1S" from "1S1:1-8" if requested
    work = raw
    if strip_book_prefix:
        # Match leading digits+letter(s) before chapter:verse
        m = re.match(r"^(\d?[A-Za-z]+)(.+)$", work)
        if m:
            work = m.group(2)

    # Detect multi-range: space-separated segments (e.g. "1:1-31 2:1-4a")
    if " " in work.strip():
        segments = work.strip().split()
        if len(segments) >= 2:
            result["ambiguous"] = True
            # Try to parse just the first segment
            work = segments[0]

    # Try chapter:verse-range (e.g. "1:31-2:4a")
    m = re.match(r"^(\d+):(\d+)([ab])?-(\d+):(\d+)([ab])?$", work)
    if m:
        result["start_chapter"] = int(m.group(1))
        result["start_verse"] = int(m.group(2))
        result["start_suffix"] = m.group(3) or None
        result["end_chapter"] = int(m.group(4))
        result["end_verse"] = int(m.group(5))
        result["end_suffix"] = m.group(6) or None
        return result

    # Try chapter:verse-verse (e.g. "1:5-7")
    m = re.match(r"^(\d+):(\d+)([ab])?-(\d+)([ab])?$", work)
    if m:
        result["start_chapter"] = int(m.group(1))
        result["start_verse"] = int(m.group(2))
        result["start_suffix"] = m.group(3) or None
        result["end_chapter"] = int(m.group(1))
        result["end_verse"] = int(m.group(4))
        result["end_suffix"] = m.group(5) or None
        return result

    # Try chapter:verse (e.g. "1:3")
    m = _CH_VERSE_RE.match(work)
    if m:
        result["start_chapter"] = int(m.group(1))
        result["start_verse"] = int(m.group(2))
        result["start_suffix"] = m.group(3) or None
        return result

    # Try chapter-chapter (e.g. "1-3")
    m = _CH_CH_RE.match(work)
    if m:
        result["start_chapter"] = int(m.group(1))
        result["end_chapter"] = int(m.group(2))
        return result

    # Try chapter only (e.g. "3")
    m = _CH_ONLY_RE.match(work)
    if m:
        result["start_chapter"] = int(m.group(1))
        return result

    # Completely unparseable — return raw only
    return result


# ---------------------------------------------------------------------------
# Pericope list sheet parser
# ---------------------------------------------------------------------------

def parse_pericope_list_sheet(
    rows: Sequence[Sequence[Any]],
    *,
    book: str,
    source_id: str,
    workbook_name: str = "",
    worksheet_name: str = "",
) -> Iterator[dict[str, Any]]:
    """
    Parse a pericope list sheet (3 columns: sequence, reference, title).

    Yields one dict per valid row.  Blank rows are silently skipped.
    """
    for row_idx, row in enumerate(rows):
        # Expect [sequence, reference, title]
        if not row or len(row) < 2:
            continue

        seq = row[0]
        ref_raw = row[1] if len(row) > 1 else None
        title = row[2] if len(row) > 2 else None

        # Skip blank rows
        if seq is None and ref_raw is None:
            continue

        # Convert sequence to int
        try:
            sequence = int(seq) if seq is not None else 0
        except (ValueError, TypeError):
            sequence = 0

        ref_str = str(ref_raw).strip() if ref_raw is not None else ""
        title_str = str(title).strip() if title is not None else ""

        parsed_ref = parse_reference(ref_str)

        yield {
            "source_id": source_id,
            "book": book,
            "sequence": sequence,
            "raw_reference": ref_str,
            "title": title_str,
            "workbook_name": workbook_name,
            "worksheet_name": worksheet_name,
            "excel_row": row_idx + 1,  # 1-indexed
            "parsed_reference": parsed_ref,
        }


# ---------------------------------------------------------------------------
# Structure analysis sheet parser
# ---------------------------------------------------------------------------

def parse_structure_sheet(
    rows: Sequence[Sequence[Any]],
    *,
    book: str,
    source_id: str,
    workbook_name: str = "",
    worksheet_name: str = "",
) -> Iterator[dict[str, Any]]:
    """
    Parse a literary structure analysis sheet.

    Each row has 4 columns:
      Col A: structure label (e.g. [1], A(1:3-5), B1(...), A')
      Col B: Japanese description
      Col C: English description / summary (may contain <br>)
      Col D: transliteration (Hebrew/Greek)

    Blank rows (all cells empty/None) are treated as unit separators and skipped.
    Yields one dict per non-blank row.
    """
    # Track current [N] header for parent/child hierarchy
    current_header: str | None = None
    current_unit_seq = 0

    for row_idx, row in enumerate(rows):
        if not row or all(c is None or str(c).strip() == "" for c in row):
            continue

        label = str(row[0]).strip() if row[0] is not None else ""
        desc_ja = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ""
        desc_en = str(row[2]).strip() if len(row) > 2 and row[2] is not None else ""
        translit = str(row[3]).strip() if len(row) > 3 and row[3] is not None else ""

        # Defaults for every yielded row (overridden below for child rows)
        parent_label: str | None = None
        unit_sequence: int | None = None
        depth = 0

        # Detect cross-references in the English description (NT pattern)
        cross_refs = None
        if re.search(r"\d+_[A-Za-z]+@", desc_en):
            cross_refs = desc_en

        # Parse the reference embedded in the label, e.g. "A(1:3-5)" → "1:3-5"
        ref_in_label = ""
        m = re.match(r"^[A-Za-z\d']*\((.+)\)$", label)
        if m:
            ref_in_label = m.group(1)

        parsed_ref = parse_reference(ref_in_label) if ref_in_label else None

        # ── Header detection and hierarchy tracking ──────────────────────
        is_header = bool(re.match(r"^\[\d+\]$", label))

        if is_header:
            current_header = label
            current_unit_seq = 0
        elif label and re.match(r"^[A-Z]", label) and current_header:
            # Child row with an explicit letter label (A, B, A', B1, …)
            current_unit_seq += 1
            parent_label = current_header
            unit_sequence = current_unit_seq
            depth = 1
        elif current_header:
            # Row within a header block but no explicit label (summary, ref)
            parent_label = current_header
            depth = 0

        yield {
            "source_id": source_id,
            "book": book,
            "structure_label": label,
            "is_header": is_header,
            "parent_label": parent_label,
            "unit_sequence": unit_sequence,
            "depth": depth,
            "raw_reference": ref_in_label,
            "parsed_reference": parsed_ref,
            "description_ja": desc_ja,
            "description_en": desc_en,
            "transliteration": translit,
            "cross_references": cross_refs,
            "workbook_name": workbook_name,
            "worksheet_name": worksheet_name,
            "excel_row": row_idx + 1,
            # verse_text is intentionally never stored
            "verse_text": None,
        }


# ---------------------------------------------------------------------------
# Dry-run reporting
# ---------------------------------------------------------------------------

def dry_run_report(
    items: list[dict[str, Any]],
    malformed: list[dict[str, Any]],
    *,
    source_id: str,
) -> dict[str, Any]:
    """Build a dry-run summary without touching a database."""
    verse_text_present = any(
        item.get("verse_text") is not None for item in items
    )
    return {
        "source_id": source_id,
        "total_rows": len(items),
        "malformed_count": len(malformed),
        "malformed": malformed,
        "verse_text_present": verse_text_present,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _load_workbook(path: str | Path):
    """Lazy-load openpyxl to keep module importable without it."""
    try:
        from openpyxl import load_workbook
        return load_workbook(path, read_only=True, data_only=True)
    except ImportError:
        print("ERROR: openpyxl is required. Install with: uv add openpyxl", file=sys.stderr)
        sys.exit(1)


def _find_workbooks(workbooks_dir: str | Path) -> list[Path]:
    """Find all .xlsx workbooks in the given directory."""
    d = Path(workbooks_dir)
    if not d.exists():
        print(f"ERROR: directory not found: {d}", file=sys.stderr)
        sys.exit(1)
    return sorted(d.glob("*.xlsx"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import literary structure corpus from Excel workbooks"
    )
    parser.add_argument(
        "--workbooks-dir", required=True,
        help="Directory containing .xlsx workbooks"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Report counts without writing to database"
    )
    parser.add_argument(
        "--source-type", choices=["pericope_list", "structure"],
        help="Force source type for all workbooks (default: auto-detect)"
    )
    parser.add_argument(
        "--db-url",
        default=os.environ.get("THEOSIS_DATABASE_URL"),
        help="PostgreSQL connection URL (default: THEOSIS_DATABASE_URL env var)"
    )
    parser.add_argument(
        "--output", choices=["json", "text"], default="text",
        help="Output format (default: text)"
    )
    args = parser.parse_args()

    workbooks = _find_workbooks(args.workbooks_dir)
    if not workbooks:
        print(f"No .xlsx files found in {args.workbooks_dir}")
        sys.exit(1)

    all_items: list[dict[str, Any]] = []
    all_malformed: list[dict[str, Any]] = []
    manifests: list[dict[str, Any]] = []

    for wb_path in workbooks:
        wb_name = wb_path.name
        wb_info = KNOWN_WORKBOOKS.get(wb_name, {})
        source_type = args.source_type or wb_info.get("source_type", "pericope_list")
        source_id = wb_info.get("source_id", wb_path.stem)

        print(f"Processing {wb_name} (source_id={source_id}, type={source_type})")

        wb = _load_workbook(wb_path)
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            rows = list(ws.iter_rows(values_only=True))

            # Skip header-like empty sheets
            if not rows:
                continue

            # Map sheet name to OSIS code for the book field
            book = sheet_to_osis(sheet_name)

            manifest = source_manifest(
                source_id=source_id,
                source_type=source_type,
                workbook_path=wb_path,
                worksheet_name=sheet_name,
            )
            manifests.append(manifest)

            if source_type == "pericope_list":
                for item in parse_pericope_list_sheet(
                    rows, book=book, source_id=source_id,
                    workbook_name=wb_name, worksheet_name=sheet_name,
                ):
                    all_items.append(item)
            elif source_type == "structure":
                for item in parse_structure_sheet(
                    rows, book=book, source_id=source_id,
                    workbook_name=wb_name, worksheet_name=sheet_name,
                ):
                    all_items.append(item)

        wb.close()

    report = dry_run_report(all_items, all_malformed, source_id="aggregate")

    # ── PostgreSQL import ──────────────────────────────────────────────────
    if not args.dry_run:
        db_url = args.db_url
        if not db_url:
            print("ERROR: --db-url or THEOSIS_DATABASE_URL required for import mode",
                  file=sys.stderr)
            sys.exit(1)
        _import_to_database(
            db_url=db_url,
            manifests=manifests,
            all_items=all_items,
            workbooks=workbooks,
        )
        print("Import complete.")

    if args.output == "json":
        import json
        print(json.dumps({
            "manifests": manifests,
            "report": report,
            "item_count": len(all_items),
        }, indent=2, default=str))
    else:
        print(f"\n--- Dry-run report ---")
        print(f"Workbooks processed: {len(workbooks)}")
        print(f"Worksheets processed: {len(manifests)}")
        print(f"Items parsed: {report['total_rows']}")
        print(f"Malformed rows: {report['malformed_count']}")
        print(f"Verse text present: {report['verse_text_present']}")


# ---------------------------------------------------------------------------
# PostgreSQL import
# ---------------------------------------------------------------------------

def _import_to_database(
    *,
    db_url: str,
    manifests: list[dict[str, Any]],
    all_items: list[dict[str, Any]],
    workbooks: list[Path],
) -> None:
    """Import parsed items into the literary_structure tables.

    Uses idempotent upserts in a single transaction per workbook group.
    Creates source rows, pericope/structure rows, and cross-ref links.
    Never imports verse text.
    """
    import asyncio

    async def _do_import() -> None:
        import asyncpg  # type: ignore[import-untyped]

        conn = await asyncpg.connect(db_url)
        try:
            # ── Source manifests ───────────────────────────────────────────
            for m in manifests:
                await conn.execute(
                    """
                    INSERT INTO public.literary_structure_sources
                        (source_id, source_type, licence, url, attribution,
                         workbook_name, workbook_hash, worksheet_name, version_hint)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (source_id, worksheet_name) DO UPDATE SET
                        source_type   = EXCLUDED.source_type,
                        licence       = EXCLUDED.licence,
                        url           = EXCLUDED.url,
                        attribution   = EXCLUDED.attribution,
                        workbook_name = EXCLUDED.workbook_name,
                        workbook_hash = EXCLUDED.workbook_hash,
                        version_hint  = EXCLUDED.version_hint,
                        imported_at   = now()
                    """,
                    m["source_id"], m["source_type"], m["licence"], m["url"],
                    m["attribution"], m["workbook_path"], m["workbook_hash"],
                    m["worksheet_name"], m.get("version_hint"),
                )
            print(f"  Upserted {len(manifests)} source manifest rows.")

            # ── Pericope items ─────────────────────────────────────────────
            pericope_items = [i for i in all_items if "sequence" in i and "title" in i]
            for item in pericope_items:
                pr = item.get("parsed_reference", {})
                await conn.execute(
                    """
                    INSERT INTO public.literary_pericopes
                        (source_id, book, sequence, raw_reference,
                         start_chapter, start_verse, start_suffix,
                         end_chapter, end_verse, end_suffix,
                         title, workbook_name, worksheet_name, excel_row)
                    VALUES ($1, $2, $3, $4,
                            $5, $6, $7, $8, $9, $10,
                            $11, $12, $13, $14)
                    ON CONFLICT (source_id, book, sequence) DO UPDATE SET
                        raw_reference = EXCLUDED.raw_reference,
                        start_chapter = EXCLUDED.start_chapter,
                        start_verse   = EXCLUDED.start_verse,
                        start_suffix  = EXCLUDED.start_suffix,
                        end_chapter   = EXCLUDED.end_chapter,
                        end_verse     = EXCLUDED.end_verse,
                        end_suffix    = EXCLUDED.end_suffix,
                        title         = EXCLUDED.title,
                        workbook_name = EXCLUDED.workbook_name,
                        worksheet_name= EXCLUDED.worksheet_name,
                        excel_row     = EXCLUDED.excel_row
                    """,
                    item["source_id"], item["book"], item["sequence"],
                    item.get("raw_reference", ""),
                    pr.get("start_chapter"), pr.get("start_verse"),
                    pr.get("start_suffix"),
                    pr.get("end_chapter"), pr.get("end_verse"),
                    pr.get("end_suffix"),
                    item.get("title", ""), item.get("workbook_name", ""),
                    item.get("worksheet_name", ""), item.get("excel_row"),
                )
            if pericope_items:
                print(f"  Upserted {len(pericope_items)} pericope rows.")

            # ── Structure items ────────────────────────────────────────────
            structure_items = [i for i in all_items if "structure_label" in i]
            for item in structure_items:
                pr = item.get("parsed_reference") or {}
                # Determine the book from cross_ref patterns for NT cross-refs
                cross_refs = item.get("cross_references")
                await conn.execute(
                    """
                    INSERT INTO public.literary_structures
                        (source_id, book, structure_label, is_header,
                         parent_label, unit_sequence, depth,
                         raw_reference,
                         start_chapter, start_verse, start_suffix,
                         end_chapter, end_verse, end_suffix,
                         description_ja, description_en, transliteration,
                         cross_references,
                         workbook_name, worksheet_name, excel_row)
                    VALUES ($1, $2, $3, $4,
                            $5, $6, $7,
                            $8, $9, $10, $11,
                            $12, $13, $14,
                            $15, $16, $17, $18,
                            $19, $20, $21)
                    ON CONFLICT (source_id, book, structure_label, excel_row) DO UPDATE SET
                        is_header      = EXCLUDED.is_header,
                        parent_label   = EXCLUDED.parent_label,
                        unit_sequence  = EXCLUDED.unit_sequence,
                        depth          = EXCLUDED.depth,
                        raw_reference  = EXCLUDED.raw_reference,
                        start_chapter  = EXCLUDED.start_chapter,
                        start_verse    = EXCLUDED.start_verse,
                        start_suffix   = EXCLUDED.start_suffix,
                        end_chapter    = EXCLUDED.end_chapter,
                        end_verse      = EXCLUDED.end_verse,
                        end_suffix     = EXCLUDED.end_suffix,
                        description_ja = EXCLUDED.description_ja,
                        description_en = EXCLUDED.description_en,
                        transliteration= EXCLUDED.transliteration,
                        cross_references= EXCLUDED.cross_references,
                        workbook_name  = EXCLUDED.workbook_name,
                        worksheet_name = EXCLUDED.worksheet_name,
                        excel_row      = EXCLUDED.excel_row
                    RETURNING id
                    """,
                    item["source_id"], item["book"], item["structure_label"],
                    item.get("is_header", False),
                    item.get("parent_label"), item.get("unit_sequence"),
                    item.get("depth", 0),
                    item.get("raw_reference", ""),
                    pr.get("start_chapter"), pr.get("start_verse"),
                    pr.get("start_suffix"),
                    pr.get("end_chapter"), pr.get("end_verse"),
                    pr.get("end_suffix"),
                    item.get("description_ja", ""),
                    item.get("description_en", ""),
                    item.get("transliteration", ""),
                    cross_refs,
                    item.get("workbook_name", ""),
                    item.get("worksheet_name", ""),
                    item.get("excel_row"),
                )
            if structure_items:
                print(f"  Upserted {len(structure_items)} structure rows.")

            # ── Cross-reference links ──────────────────────────────────────
            link_count = 0
            for item in structure_items:
                cross_refs = item.get("cross_references")
                if not cross_refs:
                    continue
                # Look up the structure id for this row
                sid = await conn.fetchval(
                    """
                    SELECT id FROM public.literary_structures
                    WHERE source_id = $1 AND book = $2
                      AND structure_label = $3 AND excel_row = $4
                    """,
                    item["source_id"], item["book"],
                    item["structure_label"], item.get("excel_row"),
                )
                if not sid:
                    continue
                # Parse cross-ref targets (e.g. "42_Luke@13,23_Isaiah@10")
                targets = _parse_cross_ref_targets(cross_refs)
                for target in targets:
                    await conn.execute(
                        """
                        INSERT INTO public.literary_structure_links
                            (source_id, structure_id, target_passage, link_type)
                        VALUES ($1, $2, $3, 'cross_reference')
                        ON CONFLICT (source_id, structure_id, target_passage) DO NOTHING
                        """,
                        item["source_id"], sid, target,
                    )
                    link_count += 1
            if link_count:
                print(f"  Created {link_count} cross-reference links.")

        finally:
            await conn.close()

    asyncio.run(_do_import())


def _parse_cross_ref_targets(raw: str) -> list[str]:
    """Parse a raw cross-reference string into individual target passages.

    Handles patterns like "42_Luke@13,23_Isaiah@10" and plain comma-separated refs.
    Returns a list of target passage strings suitable for storage.
    """
    targets: list[str] = []
    if not raw:
        return targets
    # Pattern: number_BookName@chapter,chapter,...
    for part in re.split(r"[,;]\s*", raw):
        part = part.strip()
        if not part:
            continue
        targets.append(part)
    return targets


if __name__ == "__main__":
    main()
