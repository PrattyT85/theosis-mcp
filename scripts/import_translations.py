#!/usr/bin/env python3
"""
Import scrollmapper bible_databases translations into theosis PostgreSQL.

Downloads CSVs from GitHub and imports into bible_translations → bible_books → bible_verses.
Supports incremental import: skips translations already in the database.

Usage:
  python3 scripts/import_translations.py --download --translations KJV,ESV,NASB
  python3 scripts/import_translations.py --translations ASV,BSB,YLT
  python3 scripts/import_translations.py --list-available

Data source: https://github.com/scrollmapper/bible_databases (MIT license)
"""

import argparse
import asyncio
import csv
import io
import sys
from pathlib import Path

import asyncpg
import httpx

# Default DB connection (override with THEOSIS_DATABASE_URL env var)
import os
DB_URL = os.environ.get(
    "THEOSIS_DATABASE_URL",
    "postgresql://theosis@/theosis?host=/var/run/postgresql"
)

# Protestant canon book order (66 books) with OSIS abbreviations
BOOK_ORDER = [
    ("Genesis", "Gen", "OT", 1), ("Exodus", "Exo", "OT", 2),
    ("Leviticus", "Lev", "OT", 3), ("Numbers", "Num", "OT", 4),
    ("Deuteronomy", "Deu", "OT", 5), ("Joshua", "Jos", "OT", 6),
    ("Judges", "Jdg", "OT", 7), ("Ruth", "Rut", "OT", 8),
    ("1 Samuel", "1Sa", "OT", 9), ("2 Samuel", "2Sa", "OT", 10),
    ("1 Kings", "1Ki", "OT", 11), ("2 Kings", "2Ki", "OT", 12),
    ("1 Chronicles", "1Ch", "OT", 13), ("2 Chronicles", "2Ch", "OT", 14),
    ("Ezra", "Ezr", "OT", 15), ("Nehemiah", "Neh", "OT", 16),
    ("Esther", "Est", "OT", 17), ("Job", "Job", "OT", 18),
    ("Psalms", "Psa", "OT", 19), ("Proverbs", "Pro", "OT", 20),
    ("Ecclesiastes", "Ecc", "OT", 21), ("Song of Solomon", "Sng", "OT", 22),
    ("Isaiah", "Isa", "OT", 23), ("Jeremiah", "Jer", "OT", 24),
    ("Lamentations", "Lam", "OT", 25), ("Ezekiel", "Ezk", "OT", 26),
    ("Daniel", "Dan", "OT", 27), ("Hosea", "Hos", "OT", 28),
    ("Joel", "Jol", "OT", 29), ("Amos", "Amo", "OT", 30),
    ("Obadiah", "Oba", "OT", 31), ("Jonah", "Jon", "OT", 32),
    ("Micah", "Mic", "OT", 33), ("Nahum", "Nam", "OT", 34),
    ("Habakkuk", "Hab", "OT", 35), ("Zephaniah", "Zep", "OT", 36),
    ("Haggai", "Hag", "OT", 37), ("Zechariah", "Zec", "OT", 38),
    ("Malachi", "Mal", "OT", 39), ("Matthew", "Mat", "NT", 40),
    ("Mark", "Mrk", "NT", 41), ("Luke", "Luk", "NT", 42),
    ("John", "Jhn", "NT", 43), ("Acts", "Act", "NT", 44),
    ("Romans", "Rom", "NT", 45), ("1 Corinthians", "1Co", "NT", 46),
    ("2 Corinthians", "2Co", "NT", 47), ("Galatians", "Gal", "NT", 48),
    ("Ephesians", "Eph", "NT", 49), ("Philippians", "Php", "NT", 50),
    ("Colossians", "Col", "NT", 51), ("1 Thessalonians", "1Th", "NT", 52),
    ("2 Thessalonians", "2Th", "NT", 53), ("1 Timothy", "1Ti", "NT", 54),
    ("2 Timothy", "2Ti", "NT", 55), ("Titus", "Tit", "NT", 56),
    ("Philemon", "Phm", "NT", 57), ("Hebrews", "Heb", "NT", 58),
    ("James", "Jas", "NT", 59), ("1 Peter", "1Pe", "NT", 60),
    ("2 Peter", "2Pe", "NT", 61), ("1 John", "1Jn", "NT", 62),
    ("2 John", "2Jn", "NT", 63), ("3 John", "3Jn", "NT", 64),
    ("Jude", "Jud", "NT", 65), ("Revelation", "Rev", "NT", 66),
]

NAME_TO_OSIS = {name: osis for name, osis, _, _ in BOOK_ORDER}

# Alternate book name mappings for scrollmapper CSV filenames
ALT_NAMES = {
    "1Samuel": "1Sa", "2Samuel": "2Sa", "1Kings": "1Ki", "2Kings": "2Ki",
    "1Chronicles": "1Ch", "2Chronicles": "2Ch", "Psalm": "Psa", "Proverb": "Pro",
    "SongofSolomon": "Sng", "SongOfSongs": "Sng",
    "1Corinthians": "1Co", "2Corinthians": "2Co",
    "1Thessalonians": "1Th", "2Thessalonians": "2Th",
    "1Timothy": "1Ti", "2Timothy": "2Ti",
    "1Peter": "1Pe", "2Peter": "2Pe",
    "1John": "1Jn", "2John": "2Jn", "3John": "3Jn",
    "RevelationofJohn": "Rev", "Ecclesiastes": "Ecc",
    "I Chronicles": "1Ch", "II Chronicles": "2Ch",
    "I Samuel": "1Sa", "II Samuel": "2Sa",
    "I Kings": "1Ki", "II Kings": "2Ki",
    "I Corinthians": "1Co", "II Corinthians": "2Co",
    "I Thessalonians": "1Th", "II Thessalonians": "2Th",
    "I Timothy": "1Ti", "II Timothy": "2Ti",
    "I Peter": "1Pe", "II Peter": "2Pe",
    "I John": "1Jn", "II John": "2Jn", "III John": "3Jn",
}

# Apocrypha books to skip (keep Protestant canon)
APOCRYPHA = {"Tobit", "Tob", "Judith", "Jdt", "Wisdom", "Wis",
             "Sirach", "Sir", "Baruch", "Bar", "1 Maccabees", "1Mac",
             "2 Maccabees", "2Mac", "1 Esdras", "2 Esdras",
             "Prayer of Manasseh", "Bel and the Dragon", "Susanna",
             "Additions to Esther", "Additions to Daniel", "Letter of Jeremiah"}

BASE_URL = "https://raw.githubusercontent.com/scrollmapper/bible_databases/master/formats/csv"

# All available English translations from scrollmapper
ALL_TRANSLATIONS = {
    "ACV": "A Conservative Version",
    "AKJV": "American King James Version",
    "ASV": "American Standard Version",
    "BBE": "Bible in Basic English",
    "BSB": "Berean Study Bible",
    "Darby": "Darby Bible",
    "DRB": "Douay-Rheims Bible",
    "ERV": "Easy-to-Read Version",
    "ESV": "English Standard Version",
    "Geneva1599": "Geneva Bible (1599)",
    "GNV": "Geneva Bible",
    "ISV": "International Standard Version",
    "JPS": "Jewish Publication Society",
    "KJV": "King James Version",
    "KJVA": "King James Version (Apocrypha)",
    "LEB": "Lexham English Bible",
    "MSG": "The Message",
    "NASB": "New American Standard Bible",
    "NET": "New English Translation",
    "NHEB": "New Heart English Bible",
    "NIV": "New International Version",
    "NLT": "New Living Translation",
    "NRSV": "New Revised Standard Version",
    "RNKJV": "Restored Name King James Version",
    "RSV": "Revised Standard Version",
    "UKJV": "Updated King James Version",
    "WEB": "World English Bible",
    "Webster": "Webster's Bible",
    "WYC": "Wycliffe Bible",
    "YLT": "Young's Literal Translation",
}


async def download_csv(client, translation):
    """Download a single book CSV for a translation."""
    url = f"{BASE_URL}/{translation}/{translation}_books.csv"
    try:
        response = await client.get(url)
        response.raise_for_status()
        return response.text
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return None
        raise


async def import_translation(conn, abbrev, name, csv_dir=None, download=False):
    """Import a single translation's CSV files."""
    # Check if already imported
    existing = await conn.fetchval(
        "SELECT id FROM bible_translations WHERE abbreviation = $1", abbrev
    )
    if existing:
        print(f"  [{abbrev}] Already imported (id={existing}), skipping")
        return 0

    # Insert translation record
    trans_id = await conn.fetchval(
        """INSERT INTO bible_translations (abbreviation, name, language)
           VALUES ($1, $2, 'English') RETURNING id""",
        abbrev, name
    )

    # Pre-insert 66 canon books for this translation
    book_ids = {}
    for book_name, osis, testament, book_num in BOOK_ORDER:
        book_id = await conn.fetchval(
            """INSERT INTO bible_books (translation_id, name, testament, book_number, osis_ref)
               VALUES ($1, $2, $3, $4, $5)
               ON CONFLICT (translation_id, osis_ref) DO UPDATE SET name = $2
               RETURNING id""",
            trans_id, book_name, testament, book_num, osis
        )
        book_ids[osis] = book_id

    verse_count = 0
    csv_dir = Path(csv_dir) if csv_dir else None

    for book_name, osis, _, _ in BOOK_ORDER:
        # Build filename: "Genesis.csv", "1 Samuel.csv", etc.
        filename = f"{book_name}.csv"
        csv_path = csv_dir / filename if csv_dir else None

        if csv_path and csv_path.exists():
            with open(csv_path, newline="", encoding="utf-8") as f:
                content = f.read()
        elif download:
            url = f"{BASE_URL}/{abbrev}/{book_name}.csv"
            content = await download_csv_single(abbrev, book_name)
            if content is None:
                continue
        else:
            continue

        # Parse CSV: format is chapter,verse,text
        reader = csv.reader(io.StringIO(content))
        rows = []
        for row in reader:
            if not row or len(row) < 3:
                continue
            try:
                chapter = int(row[0])
                verse = int(row[1])
                text = row[2]
                rows.append((book_ids[osis], chapter, verse, text))
            except (ValueError, IndexError):
                continue

        if rows:
            await conn.copy_records_to_table(
                "bible_verses",
                records=rows,
                columns=["book_id", "chapter", "verse", "text"],
            )
            verse_count += len(rows)

    # Update verse count
    if verse_count > 0:
        await conn.execute(
            "UPDATE bible_translations SET verse_count = $1 WHERE id = $2",
            verse_count, trans_id
        )

    print(f"  [{abbrev}] Imported {verse_count} verses in 66 books")
    return verse_count


async def download_csv_single(abbrev, book_name):
    """Download a single book CSV."""
    url = f"{BASE_URL}/{abbrev}/{book_name}.csv"
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.text
        except httpx.HTTPStatusError:
            return None


async def main():
    parser = argparse.ArgumentParser(description="Import scrollmapper Bible translations")
    parser.add_argument("--data-dir", help="Local directory with already-downloaded CSVs")
    parser.add_argument("--translations", default=None,
                        help="Comma-separated translations to import (default: all known)")
    parser.add_argument("--download", action="store_true",
                        help="Download CSVs from GitHub")
    parser.add_argument("--list-available", action="store_true",
                        help="List all known translations and exit")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be imported without importing")
    args = parser.parse_args()

    if args.list_available:
        print("Available translations:")
        for abbrev, name in sorted(ALL_TRANSLATIONS.items()):
            print(f"  {abbrev:15s} {name}")
        return

    # Determine which translations to import
    if args.translations:
        wanted = set(args.translations.split(","))
        to_import = {k: v for k, v in ALL_TRANSLATIONS.items() if k in wanted}
    else:
        to_import = ALL_TRANSLATIONS

    # Filter out KJVA (has Apocrypha) unless explicitly requested
    if "KJVA" not in (args.translations or ""):
        to_import.pop("KJVA", None)

    print(f"Importing {len(to_import)} translations...")

    conn = await asyncpg.connect(DB_URL)
    total = 0

    try:
        # Grant sequence permissions (may be needed on fresh DB)
        await conn.execute(
            "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO theosis"
        )

        for i, (abbrev, name) in enumerate(sorted(to_import.items()), 1):
            print(f"[{i}/{len(to_import)}] {abbrev}: {name}")
            if args.dry_run:
                print(f"  (dry run, skipping)")
                continue
            count = await import_translation(
                conn, abbrev, name,
                csv_dir=args.data_dir,
                download=args.download
            )
            total += count

    finally:
        await conn.close()

    print(f"\nDone. Total verses imported: {total:,}")


if __name__ == "__main__":
    asyncio.run(main())
