#!/usr/bin/env python3
"""
Import the Torah Weave dataset (Moshe Kline) into theosis PostgreSQL.

Reads torah-units.json and populates torah_weave_units and torah_weave_cells.
The Torah Weave reveals the literary structure of the Pentateuch as a 2D grid
— chiastic patterns, parallel units, and divine-name registers.

Usage:
  python3 scripts/import_torah_weave.py
  python3 scripts/import_torah_weave.py --json /path/to/torah-units.json

Source: Moshe Kline, https://chaver.com (CC BY 4.0)
"""

import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path

import asyncpg

DB_URL = os.environ.get(
    "THEOSIS_DATABASE_URL",
    "postgresql://theosis@/theosis?host=/var/run/postgresql"
)

BOOK_FULL_TO_OSIS = {
    "Genesis": "Gen", "Exodus": "Exo", "Leviticus": "Lev",
    "Numbers": "Num", "Deuteronomy": "Deu",
}

CELL_LABEL_RE = re.compile(r"^(\d+)([A-Z]*)([a-z]?)$")
VERSE_RANGE_RE = re.compile(r"^(\d+):(\d+)(?:-(?:(\d+):)?(\d+))?$")


def parse_verse_range(verse_str):
    """Parse 'C:V' or 'C:V-C:V' or 'C:V-V' into (ch_start, vs_start, ch_end, vs_end)."""
    match = VERSE_RANGE_RE.match(verse_str)
    if not match:
        return None
    ch_start = int(match.group(1))
    vs_start = int(match.group(2))
    ch_end = int(match.group(3)) if match.group(3) else ch_start
    vs_end = int(match.group(4)) if match.group(4) else vs_start
    return (ch_start, vs_start, ch_end, vs_end)


def parse_cell_label(label):
    """Parse '2Ba' into (row=2, column='B', subdivision='a')."""
    match = CELL_LABEL_RE.match(label)
    if not match:
        return (int(label), "", "")
    return (int(match.group(1)), match.group(2) or "", match.group(3) or "")


async def main():
    parser = argparse.ArgumentParser(description="Import Torah Weave data")
    parser.add_argument(
        "--json",
        default="/root/studybible-mcp/data/torah_weave/torah-units.json",
        help="Path to torah-units.json",
    )
    args = parser.parse_args()

    json_path = Path(args.json)
    if not json_path.exists():
        print(f"ERROR: {json_path} not found")
        sys.exit(1)

    with open(json_path) as f:
        data = json.load(f)

    units = data.get("units", [])
    print(f"Loaded {len(units)} Torah Weave units from {data.get('name', 'unknown')}")

    pg = await asyncpg.connect(DB_URL)

    try:
        # Clear existing
        await pg.execute(
            "TRUNCATE torah_weave_units, torah_weave_cells RESTART IDENTITY"
        )

        total_cells = 0

        for u in units:
            book_full = u.get("book", "")
            book_osis = BOOK_FULL_TO_OSIS.get(book_full, book_full)
            unit_num = u.get("unit_number", u.get("serial_number", 0))
            title = u.get("title", "")
            verses = u.get("verses", "")
            verse_range = u.get("verse_range", "")
            fmt = u.get("format", "")
            irregular = 1 if u.get("irregular") else 0
            is_unique = 1 if u.get("unique") else 0
            cell_count = u.get("cells", 0)
            unit_type = u.get("type", "")
            cell_count_sub = u.get("cell_count_with_subdivisions", cell_count)

            # Insert unit
            row = await pg.fetchrow(
                """INSERT INTO torah_weave_units 
                   (book, book_full, unit_number, title, verses, verse_range, 
                    format, irregular, is_unique, cell_count, type, 
                    cell_count_with_subdivisions)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12) 
                   RETURNING id""",
                book_osis, book_full, unit_num, title, verses, verse_range,
                fmt, irregular, is_unique, cell_count, unit_type, cell_count_sub,
            )
            unit_id = row["id"]

            # Parse cells from cells_detail dict
            cells_detail = u.get("cells_detail", {})
            for label, cell_verses in cells_detail.items():
                row, col, sub = parse_cell_label(label)
                vr = parse_verse_range(cell_verses)
                if not vr:
                    continue
                ch_start, vs_start, ch_end, vs_end = vr

                sort_start = ch_start * 1000 + vs_start
                sort_end = ch_end * 1000 + vs_end

                await pg.execute(
                    """INSERT INTO torah_weave_cells
                       (unit_id, cell_label, row_num, column_letter, subdivision,
                        book, verse_range, chapter_start, verse_start,
                        chapter_end, verse_end, sort_start, sort_end)
                       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)""",
                    unit_id, label, row, col, sub,
                    book_osis, cell_verses,
                    ch_start, vs_start, ch_end, vs_end,
                    sort_start, sort_end,
                )
                total_cells += 1

        # Summary
        unit_count = await pg.fetchval("SELECT COUNT(*) FROM torah_weave_units")
        cell_count_db = await pg.fetchval("SELECT COUNT(*) FROM torah_weave_cells")

        print(f"\n{'='*50}")
        print("Torah Weave Import Complete")
        print(f"  Units: {unit_count}")
        print(f"  Cells: {cell_count_db}")

    finally:
        await pg.close()


if __name__ == "__main__":
    asyncio.run(main())
