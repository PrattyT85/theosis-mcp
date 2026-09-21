#!/usr/bin/env python3
"""
Import Literary Structure corpus from Hajime Murai's Excel workbooks.

Source: http://www.bible.literarystructure.info/bible/bible_e.html
Licence: CC BY 4.0 (attribution required)

Pure parser functions for pericope list sheets and structure analysis sheets.
No database dependency — safe for offline testing and dry-run reporting.

Usage:
  uv run python scripts/import_literary_structure.py --workbooks-dir ./data \
      --dry-run --source-type pericope_list
  uv run python scripts/import_literary_structure.py --workbooks-dir ./data \
      --source-type structure
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

# Workbooks observed in the wild
KNOWN_WORKBOOKS: dict[str, dict[str, str]] = {
    "PericopeList_OT.xlsx": {
        "source_id": "murai_pericope_ot",
        "source_type": "pericope_list",
    },
    "PericopeList_NT.xlsx": {
        "source_id": "murai_pericope_nt",
        "source_type": "pericope_list",
    },
    "PericopeStructure_OT.xlsx": {
        "source_id": "murai_structure_ot",
        "source_type": "structure",
    },
    "PericopeStructure_NT.xlsx": {
        "source_id": "murai_structure_nt",
        "source_type": "structure",
    },
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
    for row_idx, row in enumerate(rows):
        if not row or all(c is None or str(c).strip() == "" for c in row):
            continue

        label = str(row[0]).strip() if row[0] is not None else ""
        desc_ja = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ""
        desc_en = str(row[2]).strip() if len(row) > 2 and row[2] is not None else ""
        translit = str(row[3]).strip() if len(row) > 3 and row[3] is not None else ""

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

        # Determine parent and unit sequence from label
        # e.g. "A" → parent=None, "B1" → parent=None, "A'" → parent=None
        # Nesting depth is inferred from label prefix patterns
        parent_label = None
        unit_sequence = None
        depth = 0

        # Simple depth heuristic: count leading digits or primes
        if re.match(r"^\[", label):
            depth = 0  # Top-level [N] marker
        elif re.match(r"^[A-Z]\d", label):
            depth = 1
        elif re.match(r"^[A-Z]", label):
            depth = 0
        elif re.match(r"^\d+\.", label):
            depth = 1

        # Check if it's a [N] row (pericope header)
        is_header = bool(re.match(r"^\[\d+\]$", label))

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

            manifest = source_manifest(
                source_id=source_id,
                source_type=source_type,
                workbook_path=wb_path,
                worksheet_name=sheet_name,
            )
            manifests.append(manifest)

            if source_type == "pericope_list":
                for item in parse_pericope_list_sheet(
                    rows, book=sheet_name, source_id=source_id,
                    workbook_name=wb_name, worksheet_name=sheet_name,
                ):
                    all_items.append(item)
            elif source_type == "structure":
                for item in parse_structure_sheet(
                    rows, book=sheet_name, source_id=source_id,
                    workbook_name=wb_name, worksheet_name=sheet_name,
                ):
                    all_items.append(item)

        wb.close()

    report = dry_run_report(all_items, all_malformed, source_id="aggregate")

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


if __name__ == "__main__":
    main()
