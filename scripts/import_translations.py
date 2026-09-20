#!/usr/bin/env python3
"""
Import Scrollmapper Bible translations into Theosis PostgreSQL.

The current Scrollmapper export is one flat CSV per translation:
formats/csv/<abbreviation>.csv with columns Book, Chapter, Verse, Text.
The importer keeps only the 66 Protestant-canon books in the Theosis
bible_books/bible_verses tables; unknown books in editions such as KJVA are
reported and skipped rather than silently mis-mapped.

Examples:
  python3 scripts/import_translations.py --list-available
  python3 scripts/import_translations.py --download --translations KJV,KJVPCE
  python3 scripts/import_translations.py --data-dir /path/to/csv --translations KJV

Data source: https://github.com/scrollmapper/bible_databases (MIT repository;
individual editions retain their own source licence metadata).
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import io
import os
import re
from pathlib import Path

import asyncpg
import httpx

DB_URL = os.environ.get(
    "THEOSIS_DATABASE_URL",
    "postgresql://theosis@/theosis?host=/var/run/postgresql",
)
BASE_URL = "https://raw.githubusercontent.com/scrollmapper/bible_databases/master/formats/csv"

# Protestant canon book order (66 books) with OSIS abbreviations.
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


def canonical(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


BOOK_BY_NAME = {canonical(name): osis for name, osis, _, _ in BOOK_ORDER}
BOOK_BY_NAME.update({
    canonical("Psalm"): "Psa",
    canonical("Proverb"): "Pro",
    canonical("Song of Songs"): "Sng",
    canonical("Revelation of John"): "Rev",
    canonical("I Samuel"): "1Sa",
    canonical("II Samuel"): "2Sa",
    canonical("I Kings"): "1Ki",
    canonical("II Kings"): "2Ki",
    canonical("I Chronicles"): "1Ch",
    canonical("II Chronicles"): "2Ch",
    canonical("I Corinthians"): "1Co",
    canonical("II Corinthians"): "2Co",
    canonical("I Thessalonians"): "1Th",
    canonical("II Thessalonians"): "2Th",
    canonical("I Timothy"): "1Ti",
    canonical("II Timothy"): "2Ti",
    canonical("I Peter"): "1Pe",
    canonical("II Peter"): "2Pe",
    canonical("I John"): "1Jn",
    canonical("II John"): "2Jn",
    canonical("III John"): "3Jn",
})

# English editions currently present in Scrollmapper's 140-entry catalogue.
# This replaces the former list, which contained several stale/non-Scrollmapper
# abbreviations and omitted several real English files.
ALL_TRANSLATIONS = {
    "ACV": "A Conservative Version",
    "AKJV": "American King James Version",
    "ASV": "American Standard Version",
    "Anderson": "Anderson New Testament",
    "BBE": "Bible in Basic English",
    "BSB": "Berean Standard Bible",
    "CPDV": "Catholic Public Domain Version",
    "DRC": "Douay-Rheims Bible, Challoner Revision",
    "Darby": "Darby Bible",
    "Geneva1599": "Geneva Bible (1599)",
    "Haweis": "Thomas Haweis New Testament",
    "JPS": "Jewish Publication Society 1917",
    "Jubilee2000": "Jubilee Bible 2000",
    "KJV": "King James Version",
    "KJVA": "King James Version (Apocrypha)",
    "KJVPCE": "King James Version: Pure Cambridge Edition",
    "LEB": "Lexham English Bible",
    "LITV": "Green's Literal Translation",
    "MKJV": "Modern King James Version",
    "NHEB": "New Heart English Bible",
    "NHEBJE": "New Heart English Bible: Jehovah Edition",
    "NHEBME": "New Heart English Bible: Messianic Edition",
    "Noyes": "Noyes Translation",
    "OEB": "Open English Bible (US Spelling)",
    "OEBcth": "Open English Bible (Commonwealth Spelling)",
    "RLT": "Revised Literal Translation",
    "RNKJV": "Restored Name King James Version",
    "RWebster": "Revised Webster Version",
    "Rotherham": "Rotherham's Emphasized Bible",
    "Twenty": "Twentieth Century New Testament",
    "Tyndale": "William Tyndale Bible",
    "UKJV": "Updated King James Version",
    "Webster": "Webster Bible",
    "YLT": "Young's Literal Translation",
}

TRANSLATION_METADATA = {
    "KJV": ("en", "GPL", "https://raw.githubusercontent.com/scrollmapper/bible_databases/master/sources/en/KJV/README.md"),
    "KJVPCE": ("en", "Public Domain", "https://raw.githubusercontent.com/scrollmapper/bible_databases/master/sources/en/KJVPCE/README.md"),
    "NHEBJE": ("en", "Public Domain", "https://raw.githubusercontent.com/scrollmapper/bible_databases/master/sources/en/NHEBJE/README.md"),
    "NHEBME": ("en", "Public Domain", "https://raw.githubusercontent.com/scrollmapper/bible_databases/master/sources/en/NHEBME/README.md"),
}


async def download_translation(client: httpx.AsyncClient, translation: str) -> str | None:
    """Download one flat Scrollmapper CSV."""
    response = await client.get(f"{BASE_URL}/{translation}.csv")
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.text


def read_translation_file(csv_dir: Path, translation: str) -> str | None:
    path = csv_dir / f"{translation}.csv"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8-sig")


def parse_rows(content: str) -> tuple[list[tuple[str, int, int, str]], set[str], set[str]]:
    """Return canonical rows, mapped OSIS books, and unknown source books."""
    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        raise ValueError("CSV has no header")
    fields = {field.lower(): field for field in reader.fieldnames if field}
    required = {"book", "chapter", "verse", "text"}
    if not required.issubset(fields):
        raise ValueError(f"CSV header must contain Book, Chapter, Verse, Text; got {reader.fieldnames}")

    rows = []
    books = set()
    unknown = set()
    for raw in reader:
        source_book = (raw.get(fields["book"]) or "").strip()
        osis = BOOK_BY_NAME.get(canonical(source_book))
        if not osis:
            if source_book:
                unknown.add(source_book)
            continue
        try:
            chapter = int(raw[fields["chapter"]])
            verse = int(raw[fields["verse"]])
        except (TypeError, ValueError):
            continue
        text = raw.get(fields["text"]) or ""
        if not text.strip():
            continue
        rows.append((osis, chapter, verse, text))
        books.add(osis)
    return rows, books, unknown


async def import_translation(
    conn: asyncpg.Connection,
    abbrev: str,
    name: str,
    csv_dir: Path | None = None,
    client: httpx.AsyncClient | None = None,
) -> int:
    """Import one flat CSV into theosis, skipping an existing abbreviation."""
    existing = await conn.fetchval(
        "SELECT id FROM bible_translations WHERE abbreviation = $1", abbrev
    )
    if existing:
        print(f"  [{abbrev}] Already imported (id={existing}), skipping")
        return 0

    if csv_dir:
        content = read_translation_file(csv_dir, abbrev)
    else:
        if client is None:
            raise ValueError("HTTP client required when --download is used")
        content = await download_translation(client, abbrev)
    if content is None:
        print(f"  [{abbrev}] Source CSV not found, skipping")
        return 0

    rows, books, unknown = parse_rows(content)
    if not rows:
        print(f"  [{abbrev}] No non-empty canonical rows, skipping")
        return 0

    language, license_name, source_url = TRANSLATION_METADATA.get(
        abbrev, ("en", "See source metadata", f"{BASE_URL}/{abbrev}.csv")
    )
    description = f"Scrollmapper import; {len(books)}/66 canonical books; {len(rows):,} verses"
    if unknown:
        description += f"; skipped source books: {', '.join(sorted(unknown))}"

    async with conn.transaction():
        trans_id = await conn.fetchval(
            """INSERT INTO bible_translations
               (abbreviation, name, language, license, description, source_url)
               VALUES ($1, $2, $3, $4, $5, $6) RETURNING id""",
            abbrev, name, language, license_name, description, source_url,
        )

        book_ids = {}
        for book_name, osis, testament, book_num in BOOK_ORDER:
            book_id = await conn.fetchval(
                "SELECT id FROM bible_books WHERE translation_id = $1 AND osis_ref = $2",
                trans_id, osis,
            )
            if book_id is None:
                book_id = await conn.fetchval(
                    """INSERT INTO bible_books
                       (translation_id, name, testament, book_number, osis_ref)
                       VALUES ($1, $2, $3, $4, $5) RETURNING id""",
                    trans_id, book_name, testament, book_num, osis,
                )
            book_ids[osis] = book_id

        db_rows = [(book_ids[osis], chapter, verse, text)
                   for osis, chapter, verse, text in rows]
        await conn.copy_records_to_table(
            "bible_verses",
            records=db_rows,
            columns=["book_id", "chapter", "verse", "text"],
        )

    print(f"  [{abbrev}] Imported {len(rows):,} verses across {len(books)}/66 books")
    return len(rows)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Import Scrollmapper Bible translations")
    parser.add_argument("--data-dir", type=Path, help="Directory containing <translation>.csv files")
    parser.add_argument("--translations", default=None, help="Comma-separated English abbreviations")
    parser.add_argument("--download", action="store_true", help="Download flat CSVs from GitHub")
    parser.add_argument("--list-available", action="store_true", help="List known English source files")
    parser.add_argument("--dry-run", action="store_true", help="Parse and report without writing")
    args = parser.parse_args()

    if args.list_available:
        print("Available English Scrollmapper translations:")
        for abbrev, name in sorted(ALL_TRANSLATIONS.items()):
            print(f"  {abbrev:12s} {name}")
        return
    if not args.data_dir and not args.download:
        parser.error("one of --data-dir or --download is required")

    if args.translations:
        wanted = [item.strip() for item in args.translations.split(",") if item.strip()]
        unknown = sorted(set(wanted) - set(ALL_TRANSLATIONS))
        if unknown:
            parser.error(f"unknown English translation(s): {', '.join(unknown)}")
        to_import = {key: ALL_TRANSLATIONS[key] for key in wanted}
    else:
        to_import = ALL_TRANSLATIONS

    print(f"Processing {len(to_import)} English translations...")
    conn = await asyncpg.connect(DB_URL)
    try:
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            total = 0
            for abbrev, name in to_import.items():
                print(f"[{abbrev}] {name}")
                if args.dry_run:
                    content = read_translation_file(args.data_dir, abbrev) if args.data_dir else await download_translation(client, abbrev)
                    if content is None:
                        print("  Source CSV not found, skipping")
                        continue
                    rows, books, unknown = parse_rows(content)
                    print(f"  (dry run: {len(rows):,} rows, {len(books)}/66 books, unknown={sorted(unknown)})")
                    continue
                total += await import_translation(conn, abbrev, name, args.data_dir, client)
    finally:
        await conn.close()
    print(f"\nDone. Total verses imported: {total:,}")


if __name__ == "__main__":
    asyncio.run(main())
