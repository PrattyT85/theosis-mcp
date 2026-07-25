#!/usr/bin/env python3
"""
Import openbible.info cross-references into theosis PostgreSQL.

Downloads cross_references.txt from openbible.info, maps book abbreviations to
OSIS refs, and inserts into bible_cross_references.

Format: Gen.1.1\tPs.8.3\t73  (From Verse<TAB>To Verse<TAB>Votes)

Usage:
  python3 scripts/import_cross_references.py
  python3 scripts/import_cross_references.py --file /path/to/cross_references.txt

Data source: https://a.openbible.info/data/cross-references.zip (CC BY 4.0)
"""

import argparse
import asyncio
import csv
import os
import sys
from pathlib import Path
import zipfile
import io

import asyncpg
import httpx

DB_URL = os.environ.get(
    "THEOSIS_DATABASE_URL",
    "postgresql://theosis@/theosis?host=/var/run/postgresql"
)

# openbible.info abbreviation → OSIS abbreviation
OPENBIBLE_TO_OSIS = {
    "Gen": "Gen", "Exod": "Exo", "Lev": "Lev", "Num": "Num",
    "Deut": "Deu", "Josh": "Jos", "Judg": "Jdg", "Ruth": "Rut",
    "1Sam": "1Sa", "2Sam": "2Sa", "1Kgs": "1Ki", "2Kgs": "2Ki",
    "1Chr": "1Ch", "2Chr": "2Ch", "Ezra": "Ezr", "Neh": "Neh",
    "Esth": "Est", "Job": "Job", "Ps": "Psa", "Prov": "Pro",
    "Eccl": "Ecc", "Song": "Sng", "Isa": "Isa", "Jer": "Jer",
    "Lam": "Lam", "Ezek": "Ezk", "Dan": "Dan", "Hos": "Hos",
    "Joel": "Jol", "Amos": "Amo", "Obad": "Oba", "Jonah": "Jon",
    "Mic": "Mic", "Nah": "Nam", "Hab": "Hab", "Zeph": "Zep",
    "Hag": "Hag", "Zech": "Zec", "Mal": "Mal",
    "Matt": "Mat", "Mark": "Mrk", "Luke": "Luk", "John": "Jhn",
    "Acts": "Act", "Rom": "Rom", "1Cor": "1Co", "2Cor": "2Co",
    "Gal": "Gal", "Eph": "Eph", "Phil": "Php", "Col": "Col",
    "1Thess": "1Th", "2Thess": "2Th", "1Tim": "1Ti", "2Tim": "2Ti",
    "Titus": "Tit", "Phlm": "Phm", "Heb": "Heb", "Jas": "Jam",
    "1Pet": "1Pe", "2Pet": "2Pe", "1John": "1Jn", "2John": "2Jn",
    "3John": "3Jn", "Jude": "Jud", "Rev": "Rev",
}

# Apocrypha abbreviations (skip these)
APOCRYPHA_OSIS = {"Tob", "Jdt", "Wis", "Sir", "Bar", "1Macc", "2Macc",
                  "1Esd", "2Esd", "PrMan", "Bel", "Sus", "EpJer"}


async def main():
    parser = argparse.ArgumentParser(description="Import cross-references from openbible.info")
    parser.add_argument("--file", help="Path to cross_references.txt (downloads if not provided)")
    parser.add_argument("--batch-size", type=int, default=5000,
                        help="Batch insert size (default: 5000)")
    args = parser.parse_args()

    # Get or download the data
    if args.file:
        filepath = Path(args.file)
        if not filepath.exists():
            print(f"ERROR: File not found: {filepath}")
            sys.exit(1)
        content = filepath.read_text(encoding="utf-8")
    else:
        print("Downloading cross_references.zip from openbible.info...")
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get("https://a.openbible.info/data/cross-references.zip")
            response.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            content = zf.read("cross_references.txt").decode("utf-8")
        print(f"Downloaded {len(content):,} bytes")

    conn = await asyncpg.connect(DB_URL)

    try:
        # Build book mapping: osis_ref → book_id (use first translation's book IDs)
        book_map = {}
        rows = await conn.fetch(
            "SELECT id, osis_ref FROM bible_books WHERE translation_id = "
            "(SELECT MIN(id) FROM bible_translations)"
        )
        for row in rows:
            book_map[row["osis_ref"]] = row["id"]

        count = 0
        batch = []
        skipped_apocrypha = 0
        skipped_unknown = 0

        reader = csv.reader(io.StringIO(content), delimiter="\t")
        for row_num, row in enumerate(reader, 1):
            if len(row) < 3:
                continue
            try:
                from_ref = row[0].strip()   # e.g., "Gen.1.1"
                to_ref = row[1].strip()     # e.g., "Ps.8.3"
                votes = int(row[2])

                # Parse "Gen.1.1" → ("Gen", 1, 1)
                from_parts = from_ref.split(".")
                to_parts = to_ref.split(".")
                from_book = from_parts[0]
                from_ch = int(from_parts[1])
                from_vs = int(from_parts[2])
                to_book = to_parts[0]
                to_ch = int(to_parts[1])
                to_vs = int(to_parts[2])

                # Map to OSIS
                from_osis = OPENBIBLE_TO_OSIS.get(from_book)
                to_osis = OPENBIBLE_TO_OSIS.get(to_book)

                if from_osis in APOCRYPHA_OSIS or to_osis in APOCRYPHA_OSIS:
                    skipped_apocrypha += 1
                    continue

                if not from_osis or not to_osis:
                    skipped_unknown += 1
                    continue

                from_book_id = book_map.get(from_osis)
                to_book_id = book_map.get(to_osis)

                if not from_book_id or not to_book_id:
                    skipped_unknown += 1
                    continue

                batch.append((
                    from_book_id, from_ch, from_vs,
                    to_book_id, to_ch, to_vs,
                    "openbible", votes,
                ))

                if len(batch) >= args.batch_size:
                    await conn.copy_records_to_table(
                        "bible_cross_references",
                        records=batch,
                        columns=["from_book_id", "from_chapter", "from_verse",
                                 "to_book_id", "to_chapter", "to_verse",
                                 "source", "votes"],
                    )
                    count += len(batch)
                    print(f"  Imported {count:,} cross-references...")
                    batch = []

            except (ValueError, IndexError) as e:
                continue

        # Final batch
        if batch:
            await conn.copy_records_to_table(
                "bible_cross_references",
                records=batch,
                columns=["from_book_id", "from_chapter", "from_verse",
                         "to_book_id", "to_chapter", "to_verse",
                         "source", "votes"],
            )
            count += len(batch)

        print(f"\nImport complete:")
        print(f"  Cross-references: {count:,}")
        print(f"  Skipped (apocrypha): {skipped_apocrypha:,}")
        print(f"  Skipped (unknown): {skipped_unknown:,}")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
