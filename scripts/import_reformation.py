#!/usr/bin/env python3
"""
Import Reformation-era commentaries from SWORD modules into theosis PostgreSQL.

Converts SWORD modules (MHC, CalvinCommentaries, Wesley) to IMP format via mod2imp,
parses the IMP output, strips OSIS markup, and imports into the commentaries table.

Usage:
  python3 scripts/import_reformation.py
  python3 scripts/import_reformation.py --modules MHC,CalvinCommentaries
  python3 scripts/import_reformation.py --sword-path /tmp/MHC

Requires: libsword-utils (mod2imp), asyncpg, httpx
"""

import argparse
import asyncio
import html
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import asyncpg

DB_URL = os.environ.get(
    "THEOSIS_DATABASE_URL",
    "postgresql://theosis@/theosis?host=/var/run/postgresql"
)

# Book name mapping from SWORD format to OSIS
BOOK_TO_OSIS = {
    "Genesis": "Gen", "Exodus": "Exo", "Leviticus": "Lev",
    "Numbers": "Num", "Deuteronomy": "Deu", "Joshua": "Jos",
    "Judges": "Jdg", "Ruth": "Rut", "I Samuel": "1Sa", "II Samuel": "2Sa",
    "I Kings": "1Ki", "II Kings": "2Ki",
    "I Chronicles": "1Ch", "II Chronicles": "2Ch",
    "Ezra": "Ezr", "Nehemiah": "Neh", "Esther": "Est",
    "Job": "Job", "Psalms": "Psa", "Proverbs": "Pro",
    "Ecclesiastes": "Ecc", "Song of Solomon": "Sng",
    "Isaiah": "Isa", "Jeremiah": "Jer", "Lamentations": "Lam",
    "Ezekiel": "Ezk", "Daniel": "Dan", "Hosea": "Hos", "Joel": "Jol",
    "Amos": "Amo", "Obadiah": "Oba", "Jonah": "Jon", "Micah": "Mic",
    "Nahum": "Nam", "Habakkuk": "Hab", "Zephaniah": "Zep",
    "Haggai": "Hag", "Zechariah": "Zec", "Malachi": "Mal",
    "Matthew": "Mat", "Mark": "Mrk", "Luke": "Luk", "John": "Jhn",
    "Acts": "Act", "Romans": "Rom", "I Corinthians": "1Co",
    "II Corinthians": "2Co", "Galatians": "Gal", "Ephesians": "Eph",
    "Philippians": "Php", "Colossians": "Col",
    "I Thessalonians": "1Th", "II Thessalonians": "2Th",
    "I Timothy": "1Ti", "II Timothy": "2Ti",
    "Titus": "Tit", "Philemon": "Phm", "Hebrews": "Heb",
    "James": "Jas", "I Peter": "1Pe", "II Peter": "2Pe",
    "I John": "1Jn", "II John": "2Jn", "III John": "3Jn",
    "Jude": "Jud", "Revelation": "Rev",
}

# SWORD module metadata
MODULES = {
    "MHC": {
        "author": "Matthew Henry",
        "year": 1714,
        "category": "Reformation & Modern",
        "source_title": "Matthew Henry's Complete Commentary on the Whole Bible",
        "source_url": "https://www.ccel.org/ccel/henry/mhc.html",
    },
    "CalvinCommentaries": {
        "author": "John Calvin",
        "year": 1564,
        "category": "Reformation & Modern",
        "source_title": "Calvin's Commentaries",
        "source_url": "https://www.ccel.org/ccel/calvin/commentaries.html",
    },
    "Wesley": {
        "author": "John Wesley",
        "year": 1791,
        "category": "Reformation & Modern",
        "source_title": "John Wesley's Explanatory Notes on the Bible",
        "source_url": "https://www.ccel.org/ccel/wesley/notes.html",
    },
    "Clarke": {
        "author": "Adam Clarke",
        "year": 1832,
        "category": "Reformation & Modern",
        "source_title": "Adam Clarke's Commentary on the Bible",
        "source_url": "https://www.studylight.org/commentaries/acc.html",
    },
    "Barnes": {
        "author": "Albert Barnes",
        "year": 1870,
        "category": "Reformation & Modern",
        "source_title": "Barnes' Notes on the New Testament",
        "source_url": "https://www.studylight.org/commentaries/bnb.html",
    },
    "RWP": {
        "author": "A.T. Robertson",
        "year": 1934,
        "category": "Reformation & Modern",
        "source_title": "Robertson's Word Pictures of the New Testament",
        "source_url": "https://www.studylight.org/commentaries/rwp.html",
    },
    "Lightfoot": {
        "author": "John Lightfoot",
        "year": 1675,
        "category": "Reformation & Modern",
        "source_title": "John Lightfoot's Commentary on the Gospels",
        "source_url": "https://www.studylight.org/commentaries/jlc.html",
    },
    "KD": {
        "author": "Keil & Delitzsch",
        "year": 1890,
        "category": "Reformation & Modern",
        "source_title": "Keil & Delitzsch Commentary on the Old Testament",
        "source_url": "https://www.studylight.org/commentaries/kdo.html",
    },
    "JFB": {
        "author": "Jamieson, Fausset & Brown",
        "year": 1871,
        "category": "Reformation & Modern",
        "source_title": "Jamieson-Fausset-Brown Bible Commentary",
        "source_url": "https://www.studylight.org/commentaries/jfb.html",
    },
}


def strip_osis(text):
    """Strip OSIS/HTML markup from text, keeping only the content."""
    # Remove XML/HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Decode HTML entities
    text = html.unescape(text)
    # Fix whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_imp(imp_text, module_name):
    """Parse IMP format text into (book_osis, chapter, verse, text) tuples.
    
    IMP format:
        $$$Book Chapter:Verse
        <osis xml content>
    
    Returns list of (book_osis, chapter, verse, clean_text, module_name)
    """
    meta = MODULES[module_name]
    entries = []
    
    current_book_osis = None
    current_chapter = None
    current_verse = None
    current_text_parts = []
    
    lines = imp_text.split("\n")
    
    for line in lines:
        # Check for verse marker: $$$Book Chapter:Verse
        marker_match = re.match(r"^\$\$\$(.+)\s+(\d+):(\d+)$", line)
        if marker_match:
            # Save previous entry if any
            if current_book_osis and current_verse and current_text_parts:
                clean = strip_osis(" ".join(current_text_parts))
                if len(clean) > 20:  # Skip very short entries
                    entries.append((
                        current_book_osis, current_chapter, current_verse,
                        clean,
                        meta["author"], meta["year"], meta["category"],
                        meta["source_title"], meta["source_url"]
                    ))
            
            book_name = marker_match.group(1).strip()
            chapter = int(marker_match.group(2))
            verse = int(marker_match.group(3))
            
            # Map book name to OSIS
            osis = BOOK_TO_OSIS.get(book_name)
            if not osis:
                # Try without roman numerals
                book_clean = book_name.replace("I ", "1 ").replace("II ", "2 ").replace("III ", "3 ")
                osis = BOOK_TO_OSIS.get(book_clean)
            
            if osis and chapter > 0:
                current_book_osis = osis
                current_chapter = chapter
                current_verse = verse if verse > 0 else None
                current_text_parts = []
            continue
        
        # Accumulate text
        if current_verse and line.strip() and not line.startswith("$$$"):
            current_text_parts.append(line)
    
    # Save final entry
    if current_book_osis and current_verse and current_text_parts:
        clean = strip_osis(" ".join(current_text_parts))
        if len(clean) > 20:
            entries.append((
                current_book_osis, current_chapter, current_verse,
                clean,
                meta["author"], meta["year"], meta["category"],
                meta["source_title"], meta["source_url"]
            ))
    
    return entries


async def main():
    parser = argparse.ArgumentParser(
        description="Import Reformation commentaries from SWORD modules"
    )
    parser.add_argument("--modules", default="MHC,CalvinCommentaries,Wesley",
                        help="Comma-separated module names to import")
    parser.add_argument("--sword-base", default="/tmp",
                        help="Base directory containing SWORD module dirs")
    parser.add_argument("--batch-size", type=int, default=500,
                        help="Batch insert size (default: 500)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse and count only, don't import")
    args = parser.parse_args()

    module_names = [m.strip() for m in args.modules.split(",")]
    
    # Connect to PostgreSQL
    pg = await asyncpg.connect(DB_URL)

    try:
        total_imported = 0

        for module_name in module_names:
            if module_name not in MODULES:
                print(f"Unknown module: {module_name}, skipping")
                continue

            sword_path = os.path.join(args.sword_base, module_name)
            if not os.path.isdir(sword_path):
                print(f"Module directory not found: {sword_path}, skipping")
                continue

            meta = MODULES[module_name]
            print(f"\n{'='*50}")
            print(f"Processing: {meta['author']} — {meta['source_title']}")
            print(f"{'='*50}")

            # Convert to IMP format
            imp_file = os.path.join(args.sword_base, f"{module_name}.imp")
            if not os.path.exists(imp_file):
                print(f"  Converting SWORD module to IMP...")
                result = subprocess.run(
                    ["mod2imp", module_name],
                    capture_output=True, text=True,
                    env={**os.environ, "SWORD_PATH": sword_path},
                    timeout=300,
                    errors="replace"
                )
                if result.returncode != 0:
                    print(f"  ERROR: mod2imp failed: {result.stderr[:200]}")
                    continue
                with open(imp_file, "w") as f:
                    f.write(result.stdout)
                print(f"  IMP file: {len(result.stdout)/1024/1024:.1f} MB")
            else:
                print(f"  Using existing IMP file: {os.path.getsize(imp_file)/1024/1024:.1f} MB")

            # Parse IMP
            print(f"  Parsing IMP format...")
            with open(imp_file, encoding="utf-8", errors="replace") as f:
                imp_text = f.read()
            
            entries = parse_imp(imp_text, module_name)
            print(f"  Parsed {len(entries):,} commentary entries")

            if args.dry_run:
                # Show book distribution
                from collections import Counter
                book_counts = Counter(e[0] for e in entries)
                print(f"  Book distribution:")
                for book, count in book_counts.most_common(10):
                    print(f"    {book}: {count:,}")
                continue

            # Remove existing entries from this author
            existing = await pg.fetchval(
                "SELECT COUNT(*) FROM commentaries WHERE author = $1",
                meta["author"]
            )
            if existing > 0:
                print(f"  Removing {existing:,} existing entries for {meta['author']}...")
                await pg.execute(
                    "DELETE FROM commentaries WHERE author = $1",
                    meta["author"]
                )

            # Import
            print(f"  Importing {len(entries):,} entries...")
            imported = 0
            batch = []
            start_time = time.time()

            for entry in entries:
                batch.append(entry)
                if len(batch) >= args.batch_size:
                    await pg.copy_records_to_table(
                        "commentaries",
                        records=batch,
                        columns=["book_osis", "chapter", "verse_start",
                                 "quote", "author", "author_year",
                                 "author_category", "source_title", "source_url"],
                    )
                    imported += len(batch)
                    elapsed = time.time() - start_time
                    rate = imported / elapsed if elapsed > 0 else 0
                    pct = imported / len(entries) * 100
                    print(f"    {imported:,}/{len(entries):,} ({pct:.0f}%) — {rate:.0f}/sec")
                    batch = []

            # Final batch
            if batch:
                await pg.copy_records_to_table(
                    "commentaries",
                    records=batch,
                    columns=["book_osis", "chapter", "verse_start",
                             "quote", "author", "author_year",
                             "author_category", "source_title", "source_url"],
                )
                imported += len(batch)

            elapsed = time.time() - start_time
            print(f"  Imported {imported:,} entries in {elapsed:.1f}s")
            total_imported += imported

        print(f"\n{'='*50}")
        print(f"Total imported: {total_imported:,} entries")

    finally:
        await pg.close()


if __name__ == "__main__":
    asyncio.run(main())
