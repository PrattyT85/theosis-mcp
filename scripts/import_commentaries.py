#!/usr/bin/env python3
"""
Import HistoricalChristianFaith Commentaries-Database into theosis PostgreSQL.

Downloads the pre-built SQLite release (142MB, ~90K commentary entries from
335 Church Fathers and historical authors), maps book names to OSIS abbreviations,
and imports into the commentaries table.

Usage:
  python3 scripts/import_commentaries.py
  python3 scripts/import_commentaries.py --sqlite /path/to/commentaries.sqlite
  python3 scripts/import_commentaries.py --download  # download latest release

Data source: https://github.com/HistoricalChristianFaith/Commentaries-Database
License: Public domain (Church Fathers) + various open licenses
"""

import argparse
import asyncio
import os
import sqlite3
import sys
import time

import asyncpg
import httpx

DB_URL = os.environ.get(
    "THEOSIS_DATABASE_URL",
    "postgresql://theosis@/theosis?host=/var/run/postgresql"
)

RELEASE_URL = (
    "https://github.com/HistoricalChristianFaith/Commentaries-Database/"
    "releases/download/latest/commentaries.sqlite"
)


# Lowercase-no-spaces mapping (SQLite format)
LOWERCASE_BOOK_MAP = {
    "genesis": "Gen", "exodus": "Exo", "leviticus": "Lev",
    "numbers": "Num", "deuteronomy": "Deu", "joshua": "Jos",
    "judges": "Jdg", "ruth": "Rut", "1samuel": "1Sa", "2samuel": "2Sa",
    "1kings": "1Ki", "2kings": "2Ki", "1chronicles": "1Ch",
    "2chronicles": "2Ch", "ezra": "Ezr", "nehemiah": "Neh",
    "esther": "Est", "job": "Job", "psalms": "Psa", "proverbs": "Pro",
    "ecclesiastes": "Ecc", "songofsolomon": "Sng",
    "isaiah": "Isa", "jeremiah": "Jer", "lamentations": "Lam",
    "ezekiel": "Ezk", "daniel": "Dan", "hosea": "Hos", "joel": "Jol",
    "amos": "Amo", "obadiah": "Oba", "jonah": "Jon", "micah": "Mic",
    "nahum": "Nam", "habakkuk": "Hab", "zephaniah": "Zep",
    "haggai": "Hag", "zechariah": "Zec", "malachi": "Mal",
    "matthew": "Mat", "mark": "Mrk", "luke": "Luk", "john": "Jhn",
    "acts": "Act", "romans": "Rom", "1corinthians": "1Co",
    "2corinthians": "2Co", "galatians": "Gal", "ephesians": "Eph",
    "philippians": "Php", "colossians": "Col",
    "1thessalonians": "1Th", "2thessalonians": "2Th",
    "1timothy": "1Ti", "2timothy": "2Ti",
    "titus": "Tit", "philemon": "Phm", "hebrews": "Heb",
    "james": "Jas", "1peter": "1Pe", "2peter": "2Pe",
    "1john": "1Jn", "2john": "2Jn", "3john": "3Jn",
    "jude": "Jud", "revelation": "Rev",
    # Apocrypha → skip
    "tobit": None, "judith": None, "wisdom": None, "sirach": None,
    "baruch": None, "prayerofazariah": None,
    "1maccabees": None, "2maccabees": None,
}

# Book name mapping: canonical name → OSIS abbreviation
BOOK_TO_OSIS = {
    "Genesis": "Gen", "Exodus": "Exo", "Leviticus": "Lev",
    "Numbers": "Num", "Deuteronomy": "Deu", "Joshua": "Jos",
    "Judges": "Jdg", "Ruth": "Rut", "1 Samuel": "1Sa", "2 Samuel": "2Sa",
    "1 Kings": "1Ki", "2 Kings": "2Ki", "1 Chronicles": "1Ch",
    "2 Chronicles": "2Ch", "Ezra": "Ezr", "Nehemiah": "Neh",
    "Esther": "Est", "Job": "Job", "Psalms": "Psa", "Proverbs": "Pro",
    "Ecclesiastes": "Ecc", "Song of Solomon": "Sng",
    "Isaiah": "Isa", "Jeremiah": "Jer", "Lamentations": "Lam",
    "Ezekiel": "Ezk", "Daniel": "Dan", "Hosea": "Hos", "Joel": "Jol",
    "Amos": "Amo", "Obadiah": "Oba", "Jonah": "Jon", "Micah": "Mic",
    "Nahum": "Nam", "Habakkuk": "Hab", "Zephaniah": "Zep",
    "Haggai": "Hag", "Zechariah": "Zec", "Malachi": "Mal",
    "Matthew": "Mat", "Mark": "Mrk", "Luke": "Luk", "John": "Jhn",
    "Acts": "Act", "Romans": "Rom", "1 Corinthians": "1Co",
    "2 Corinthians": "2Co", "Galatians": "Gal", "Ephesians": "Eph",
    "Philippians": "Php", "Colossians": "Col",
    "1 Thessalonians": "1Th", "2 Thessalonians": "2Th",
    "1 Timothy": "1Ti", "2 Timothy": "2Ti",
    "Titus": "Tit", "Philemon": "Phm", "Hebrews": "Heb",
    "James": "Jas", "1 Peter": "1Pe", "2 Peter": "2Pe",
    "1 John": "1Jn", "2 John": "2Jn", "3 John": "3Jn",
    "Jude": "Jud", "Revelation": "Rev",
    # Deuterocanonical / Apocrypha (skip these for Protestant canon)
    "Tobit": None, "Judith": None, "Wisdom": None, "Sirach": None,
    "Baruch": None, "Prayer of Azariah": None,
    "1 Maccabees": None, "2 Maccabees": None,
}


def decode_location(loc):
    """Decode location_start/location_end to (chapter, verse).
    Format: chapter * 1000000 + verse  (from TOML Chapter_Verse format)"""
    chapter = loc // 1000000
    verse = loc % 1000000
    return chapter, verse


async def main():
    parser = argparse.ArgumentParser(
        description="Import HistoricalChristianFaith commentaries"
    )
    parser.add_argument("--sqlite", help="Path to commentaries.sqlite")
    parser.add_argument("--download", action="store_true",
                        help="Download latest release from GitHub")
    parser.add_argument("--batch-size", type=int, default=2000,
                        help="Batch insert size (default: 2000)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show counts without importing")
    args = parser.parse_args()

    # Get SQLite file
    sqlite_path = args.sqlite or "/tmp/commentaries.sqlite"
    if args.download or not os.path.exists(sqlite_path):
        print(f"Downloading commentaries.sqlite ({RELEASE_URL})...")
        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.get(RELEASE_URL)
            response.raise_for_status()
        with open(sqlite_path, "wb") as f:
            f.write(response.content)
        print(f"Downloaded {len(response.content) / 1024 / 1024:.1f} MB")

    if not os.path.exists(sqlite_path):
        print(f"ERROR: {sqlite_path} not found. Use --download to fetch it.")
        sys.exit(1)

    # Open SQLite
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row

    # Counts
    author_count = sqlite_conn.execute(
        "SELECT COUNT(*) as cnt FROM father_meta"
    ).fetchone()["cnt"]
    comm_count = sqlite_conn.execute(
        "SELECT COUNT(*) as cnt FROM commentary"
    ).fetchone()["cnt"]

    print(f"SQLite: {author_count} authors, {comm_count:,} commentaries")

    # Build author metadata lookup
    authors = {}
    for row in sqlite_conn.execute("SELECT * FROM father_meta"):
        authors[row["name"]] = {
            "default_year": row["default_year"],
            "wiki_url": row["wiki_url"],
            "father_category": row["father_category"],
        }

    if args.dry_run:
        # Show what would be imported
        book_counts = sqlite_conn.execute(
            "SELECT book, COUNT(*) as cnt FROM commentary "
            "GROUP BY book ORDER BY cnt DESC"
        ).fetchall()
        print("\nBooks (top 20):")
        for row in book_counts[:20]:
            osis = BOOK_TO_OSIS.get(row["book"])
            skip = "SKIP" if osis is None else "  → " + (osis or "?")
            print(f"  {row['book']:25s} {row['cnt']:6,}  {skip}")
        print(f"\nWould import ~{comm_count:,} commentaries")
        return

    # Connect to PostgreSQL
    pg = await asyncpg.connect(DB_URL)

    try:
        # Create table
        print("\nCreating commentaries table...")
        await pg.execute("""
            CREATE TABLE IF NOT EXISTS commentaries (
                id SERIAL PRIMARY KEY,
                book_osis VARCHAR(10) NOT NULL,
                chapter INTEGER NOT NULL,
                verse_start INTEGER NOT NULL,
                verse_end INTEGER,
                author VARCHAR(300) NOT NULL,
                author_year INTEGER,
                author_category TEXT,
                source_title TEXT,
                source_url TEXT,
                quote TEXT NOT NULL,
                language TEXT DEFAULT 'en'
            )
        """)

        # Create indexes (IF NOT EXISTS for idempotency)
        await pg.execute("""
            CREATE INDEX IF NOT EXISTS idx_commentaries_ref
                ON commentaries(book_osis, chapter, verse_start)
        """)
        await pg.execute("""
            CREATE INDEX IF NOT EXISTS idx_commentaries_author
                ON commentaries(author)
        """)
        await pg.execute("""
            CREATE INDEX IF NOT EXISTS idx_commentaries_fulltext
                ON commentaries USING gin(to_tsvector('english', quote))
        """)

        # Clear existing data
        existing = await pg.fetchval("SELECT COUNT(*) FROM commentaries")
        if existing > 0:
            print(f"Clearing {existing:,} existing commentaries...")
            await pg.execute("TRUNCATE commentaries RESTART IDENTITY")

        # Import
        print(f"Importing {comm_count:,} commentaries...")
        imported = 0
        skipped_apocrypha = 0
        skipped_unknown = 0
        batch = []
        start_time = time.time()

        cursor = sqlite_conn.execute(
            "SELECT * FROM commentary ORDER BY book, location_start"
        )

        for row in cursor:
            book_name = row["book"]  # Already lowercased in SQLite
            
            # Try lowercase mapping first (most common)
            osis = LOWERCASE_BOOK_MAP.get(book_name)
            
            if osis is None:
                # Try title case match
                book_title = book_name.title()
                osis = BOOK_TO_OSIS.get(book_title)
            
            if osis is None:
                # Try matching against lowercase keys
                for canonical, abbr in BOOK_TO_OSIS.items():
                    if canonical.lower() == book_name:
                        osis = abbr
                        break

            if osis is None:
                skipped_unknown += 1
                continue

            if osis is None:  # Explicitly mapped to None = Apocrypha
                skipped_apocrypha += 1
                continue

            chapter, verse_start = decode_location(row["location_start"])
            chapter_end, verse_end = decode_location(row["location_end"])

            # Get author metadata
            author_meta = authors.get(row["father_name"], {})
            author_year = None
            try:
                year_str = row["ts"] or author_meta.get("default_year", "")
                if year_str and year_str != "9999":
                    author_year = int(year_str)
            except (ValueError, TypeError):
                pass

            batch.append((
                osis, chapter, verse_start,
                verse_end if (chapter_end, verse_end) != (chapter, verse_start) else None,
                row["father_name"], author_year,
                author_meta.get("father_category"),
                row["source_title"], row["source_url"],
                row["txt"]
            ))

            if len(batch) >= args.batch_size:
                await pg.copy_records_to_table(
                    "commentaries",
                    records=batch,
                    columns=["book_osis", "chapter", "verse_start", "verse_end",
                             "author", "author_year", "author_category",
                             "source_title", "source_url", "quote"],
                )
                imported += len(batch)
                elapsed = time.time() - start_time
                rate = imported / elapsed if elapsed > 0 else 0
                print(f"  {imported:,}/{comm_count:,} ({imported/comm_count*100:.0f}%) "
                      f"— {rate:.0f}/sec")
                batch = []

        # Final batch
        if batch:
            await pg.copy_records_to_table(
                "commentaries",
                records=batch,
                columns=["book_osis", "chapter", "verse_start", "verse_end",
                         "author", "author_year", "author_category",
                         "source_title", "source_url", "quote"],
            )
            imported += len(batch)

        # Summary
        elapsed = time.time() - start_time
        author_count_imported = await pg.fetchval(
            "SELECT COUNT(DISTINCT author) FROM commentaries"
        )
        book_count_imported = await pg.fetchval(
            "SELECT COUNT(DISTINCT book_osis) FROM commentaries"
        )

        print(f"\n{'='*50}")
        print("Commentary Import Complete")
        print(f"  Imported:          {imported:,}")
        print(f"  Authors:           {author_count_imported}")
        print(f"  Books covered:     {book_count_imported}")
        print(f"  Skipped (apoc):    {skipped_apocrypha:,}")
        print(f"  Skipped (unknown): {skipped_unknown:,}")
        print(f"  Time:              {elapsed/60:.1f} minutes")

    finally:
        await pg.close()
        sqlite_conn.close()


if __name__ == "__main__":
    asyncio.run(main())
