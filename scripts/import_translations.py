#!/usr/bin/env python3
"""
Import Scrollmapper Bible editions into Theosis PostgreSQL.

The current Scrollmapper export is one flat CSV per edition:
formats/csv/<abbreviation>.csv with columns Book, Chapter, Verse, Text.
The importer preserves language, source licence, canon coverage, and
non-canonical books such as the Vulgate deuterocanonical texts.

Examples:
  python3 scripts/import_translations.py --list-available
  python3 scripts/import_translations.py --download --translations KJV,KJVPCE
  python3 scripts/import_translations.py --download --translations WLC,StatResGNT,Vulgate
  python3 scripts/import_translations.py --download --translations KJV --dry-run

Data source: https://github.com/scrollmapper/bible_databases
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import io
import os
import re
from pathlib import Path
from typing import Any

import asyncpg
import httpx

DB_URL = os.environ.get(
    "THEOSIS_DATABASE_URL",
    "postgresql://theosis@/theosis?host=/var/run/postgresql",
)
BASE_URL = "https://raw.githubusercontent.com/scrollmapper/bible_databases/master/formats/csv"

# Standard Protestant canon, with OSIS abbreviations.
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


CANONICAL_BOOKS = {canonical(name): (name, osis, testament, number)
                   for name, osis, testament, number in BOOK_ORDER}
CANONICAL_BOOKS.update({
    canonical("Psalm"): ("Psalms", "Psa", "OT", 19),
    canonical("Proverb"): ("Proverbs", "Pro", "OT", 20),
    canonical("Song of Songs"): ("Song of Solomon", "Sng", "OT", 22),
    canonical("Revelation of John"): ("Revelation", "Rev", "NT", 66),
    canonical("I Samuel"): ("1 Samuel", "1Sa", "OT", 9),
    canonical("II Samuel"): ("2 Samuel", "2Sa", "OT", 10),
    canonical("I Kings"): ("1 Kings", "1Ki", "OT", 11),
    canonical("II Kings"): ("2 Kings", "2Ki", "OT", 12),
    canonical("I Chronicles"): ("1 Chronicles", "1Ch", "OT", 13),
    canonical("II Chronicles"): ("2 Chronicles", "2Ch", "OT", 14),
    canonical("I Corinthians"): ("1 Corinthians", "1Co", "NT", 46),
    canonical("II Corinthians"): ("2 Corinthians", "2Co", "NT", 47),
    canonical("I Thessalonians"): ("1 Thessalonians", "1Th", "NT", 52),
    canonical("II Thessalonians"): ("2 Thessalonians", "2Th", "NT", 53),
    canonical("I Timothy"): ("1 Timothy", "1Ti", "NT", 54),
    canonical("II Timothy"): ("2 Timothy", "2Ti", "NT", 55),
    canonical("I Peter"): ("1 Peter", "1Pe", "NT", 60),
    canonical("II Peter"): ("2 Peter", "2Pe", "NT", 61),
    canonical("I John"): ("1 John", "1Jn", "NT", 62),
    canonical("II John"): ("2 John", "2Jn", "NT", 63),
    canonical("III John"): ("3 John", "3Jn", "NT", 64),
})

# Stable OSIS-like identifiers for common deuterocanonical and other books.
EXTRA_BOOKS = {
    "tobit": ("Tobit", "Tob", "APO"),
    "judith": ("Judith", "Jdt", "APO"),
    "wisdom": ("Wisdom", "Wis", "APO"),
    "sirach": ("Sirach", "Sir", "APO"),
    "baruch": ("Baruch", "Bar", "APO"),
    "imaccabees": ("1 Maccabees", "1Ma", "APO"),
    "iimaccabees": ("2 Maccabees", "2Ma", "APO"),
    "iesdras": ("1 Esdras", "1Esd", "APO"),
    "iiesdras": ("2 Esdras", "2Esd", "APO"),
    "prayerofmanasses": ("Prayer of Manasses", "PrMan", "APO"),
    "prayerofmanasseh": ("Prayer of Manasseh", "PrMan", "APO"),
    "laodiceans": ("Laodiceans", "EpLao", "APO"),
    "additionalsalm": ("Additional Psalm", "Psa151", "APO"),
}

# English editions in Scrollmapper's 140-edition catalogue.
ENGLISH = {
    "ACV": "A Conservative Version", "AKJV": "American King James Version",
    "ASV": "American Standard Version", "Anderson": "Anderson New Testament",
    "BBE": "Bible in Basic English", "BSB": "Berean Standard Bible",
    "CPDV": "Catholic Public Domain Version", "DRC": "Douay-Rheims Bible, Challoner Revision",
    "Darby": "Darby Bible", "Geneva1599": "Geneva Bible (1599)",
    "Haweis": "Thomas Haweis New Testament", "JPS": "Jewish Publication Society 1917",
    "Jubilee2000": "Jubilee Bible 2000", "KJV": "King James Version",
    "KJVA": "King James Version (Apocrypha)", "KJVPCE": "King James Version: Pure Cambridge Edition",
    "LEB": "Lexham English Bible", "LITV": "Green's Literal Translation",
    "MKJV": "Modern King James Version", "NHEB": "New Heart English Bible",
    "NHEBJE": "New Heart English Bible: Jehovah Edition", "NHEBME": "New Heart English Bible: Messianic Edition",
    "Noyes": "Noyes Translation", "OEB": "Open English Bible (US Spelling)",
    "OEBcth": "Open English Bible (Commonwealth Spelling)", "RLT": "Revised Literal Translation",
    "RNKJV": "Restored Name King James Version", "RWebster": "Revised Webster Version",
    "Rotherham": "Rotherham's Emphasized Bible", "Twenty": "Twentieth Century New Testament",
    "Tyndale": "William Tyndale Bible", "UKJV": "Updated King James Version",
    "Webster": "Webster Bible", "YLT": "Young's Literal Translation",
}

# Historical-language editions selected for the first non-English batch.
HISTORICAL = {
    "WLC": ("Westminster Leningrad Codex", "hbo", "Public Domain"),
    "SP": ("Samaritan Pentateuch", "hbo", "Copyrighted; Free non-commercial distribution"),
    "StatResGNT": ("Statistical Restoration Greek New Testament", "grc", "CC BY 4.0"),
    "Byz": ("Byzantine Textform 2013", "grc", "CC BY-NC-SA 4.0"),
    "TR": ("Textus Receptus", "grc", "CC BY-NC-SA 4.0"),
    "Vulgate": ("Latin Vulgate", "la", "Public Domain"),
    "VulgClementine": ("Clementine Vulgate", "la", "Public Domain"),
    "Peshitta": ("Syriac Peshitta", "syr", "Public Domain"),
    "CopSahBible2": ("Sahidic Bible 2", "cop-sa", "CC BY-SA"),
    "Wulfila": ("Bishop Wulfila Gothic Bible", "got", "Public Domain"),
    "HebModern": ("Modern Hebrew Bible", "he", "Licence not specified"),
}

TRANSLATIONS: dict[str, dict[str, Any]] = {
    key: {
        "name": value,
        "language": "en",
        "license": "See source metadata",
        "source_url": f"{BASE_URL}/{key}.csv",
    }
    for key, value in ENGLISH.items()
}
for key, (name, language, license_name) in HISTORICAL.items():
    TRANSLATIONS[key] = {
        "name": name,
        "language": language,
        "license": license_name,
        "source_url": f"{BASE_URL}/{key}.csv",
    }

ALL_TRANSLATIONS = {key: meta["name"] for key, meta in TRANSLATIONS.items()}


async def download_translation(client: httpx.AsyncClient, translation: str) -> str | None:
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


def resolve_book(source_book: str, discovered_extra: dict[str, tuple[str, str, str, int]]):
    key = canonical(source_book)
    if key in CANONICAL_BOOKS:
        return CANONICAL_BOOKS[key]
    if key in EXTRA_BOOKS:
        name, osis, testament = EXTRA_BOOKS[key]
    else:
        name, osis, testament = source_book, f"Src_{key}", "OTHER"
    if osis not in discovered_extra:
        discovered_extra[osis] = (name, osis, testament, 1000 + len(discovered_extra))
    return discovered_extra[osis]


def parse_rows(content: str):
    """Return rows and the source-book catalogue discovered in the CSV."""
    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        raise ValueError("CSV has no header")
    fields = {field.lower(): field for field in reader.fieldnames if field}
    required = {"book", "chapter", "verse", "text"}
    if not required.issubset(fields):
        raise ValueError(f"CSV header must contain Book, Chapter, Verse, Text; got {reader.fieldnames}")

    rows = []
    book_specs: dict[str, tuple[str, str, str, int]] = {}
    discovered_extra: dict[str, tuple[str, str, str, int]] = {}
    for raw in reader:
        source_book = (raw.get(fields["book"]) or "").strip()
        if not source_book:
            continue
        name, osis, testament, number = resolve_book(source_book, discovered_extra)
        try:
            chapter = int(raw[fields["chapter"]])
            verse = int(raw[fields["verse"]])
        except (TypeError, ValueError):
            continue
        text = raw.get(fields["text"]) or ""
        if not text.strip():
            continue
        book_specs[osis] = (name, osis, testament, number)
        rows.append((osis, chapter, verse, text))
    return rows, book_specs


async def import_translation(
    conn: asyncpg.Connection,
    abbrev: str,
    metadata: dict[str, Any],
    csv_dir: Path | None = None,
    client: httpx.AsyncClient | None = None,
) -> int:
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

    rows, book_specs = parse_rows(content)
    if not rows:
        print(f"  [{abbrev}] No non-empty rows, skipping")
        return 0
    description = (
        f"Scrollmapper import; {len(book_specs)} source books; "
        f"{len(rows):,} non-empty verses"
    )

    async with conn.transaction():
        trans_id = await conn.fetchval(
            """INSERT INTO bible_translations
               (abbreviation, name, language, license, description, source_url)
               VALUES ($1, $2, $3, $4, $5, $6) RETURNING id""",
            abbrev, metadata["name"], metadata["language"], metadata["license"],
            description, metadata["source_url"],
        )

        book_ids = {}
        for name, osis, testament, book_number in book_specs.values():
            book_id = await conn.fetchval(
                "SELECT id FROM bible_books WHERE translation_id = $1 AND osis_ref = $2",
                trans_id, osis,
            )
            if book_id is None:
                book_id = await conn.fetchval(
                    """INSERT INTO bible_books
                       (translation_id, name, testament, book_number, osis_ref)
                       VALUES ($1, $2, $3, $4, $5) RETURNING id""",
                    trans_id, name, testament, book_number, osis,
                )
            book_ids[osis] = book_id

        await conn.copy_records_to_table(
            "bible_verses",
            records=[(book_ids[osis], chapter, verse, text)
                     for osis, chapter, verse, text in rows],
            columns=["book_id", "chapter", "verse", "text"],
        )

    print(f"  [{abbrev}] Imported {len(rows):,} verses across {len(book_specs)} source books")
    return len(rows)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Import Scrollmapper Bible editions")
    parser.add_argument("--data-dir", type=Path, help="Directory containing <translation>.csv files")
    parser.add_argument("--translations", default=None, help="Comma-separated edition abbreviations")
    parser.add_argument("--download", action="store_true", help="Download flat CSVs from GitHub")
    parser.add_argument("--list-available", action="store_true", help="List known English and historical editions")
    parser.add_argument("--dry-run", action="store_true", help="Parse and report without writing")
    args = parser.parse_args()

    if args.list_available:
        print("Available Scrollmapper editions:")
        for abbrev, metadata in sorted(TRANSLATIONS.items()):
            print(f"  {abbrev:14s} {metadata['language']:5s} {metadata['name']}")
        return
    if not args.data_dir and not args.download:
        parser.error("one of --data-dir or --download is required")

    if args.translations:
        wanted = [item.strip() for item in args.translations.split(",") if item.strip()]
        unknown = sorted(set(wanted) - set(TRANSLATIONS))
        if unknown:
            parser.error(f"unknown edition(s): {', '.join(unknown)}")
        to_import = {key: TRANSLATIONS[key] for key in wanted}
    else:
        to_import = TRANSLATIONS

    print(f"Processing {len(to_import)} editions...")
    conn = await asyncpg.connect(DB_URL)
    try:
        async with httpx.AsyncClient(timeout=180, follow_redirects=True) as client:
            total = 0
            for abbrev, metadata in to_import.items():
                print(f"[{abbrev}] {metadata['name']} ({metadata['language']})")
                if args.dry_run:
                    content = read_translation_file(args.data_dir, abbrev) if args.data_dir else await download_translation(client, abbrev)
                    if content is None:
                        print("  Source CSV not found, skipping")
                        continue
                    rows, books = parse_rows(content)
                    print(f"  (dry run: {len(rows):,} rows, {len(books)} source books)")
                    continue
                total += await import_translation(conn, abbrev, metadata, args.data_dir, client)
    finally:
        await conn.close()
    print(f"\nDone. Total verses imported: {total:,}")


if __name__ == "__main__":
    asyncio.run(main())
