#!/usr/bin/env python3
"""Prepare public-domain historical sources as Theosis flat CSV files.

Theosis imports the normalized ``Book,Chapter,Verse,Text`` format used by
``scripts/import_translations.py``.  This helper converts:

* eBible.org's Brenton USFM ZIP (English Septuagint, public domain)
* CrossWire's Murdock SWORD module (English translation of the Syriac Peshitta,
  public domain; requires the optional ``source`` dependency for pysword)

Source archives are deliberately kept outside Git.  Pass the output directory
to the translation importer with ``--data-dir``.
"""

from __future__ import annotations

import argparse
import csv
import re
import zipfile
from pathlib import Path

BRENTON_BOOKS = {
    "GEN": "Genesis", "EXO": "Exodus", "LEV": "Leviticus", "NUM": "Numbers",
    "DEU": "Deuteronomy", "JOS": "Joshua", "JDG": "Judges", "RUT": "Ruth",
    "1SA": "1 Samuel", "2SA": "2 Samuel", "1KI": "1 Kings", "2KI": "2 Kings",
    "1CH": "1 Chronicles", "2CH": "2 Chronicles", "EZR": "Ezra", "NEH": "Nehemiah",
    "JOB": "Job", "PSA": "Psalms", "PRO": "Proverbs", "ECC": "Ecclesiastes",
    "SNG": "Song of Solomon", "ISA": "Isaiah", "JER": "Jeremiah", "LAM": "Lamentations",
    "EZK": "Ezekiel", "HOS": "Hosea", "JOL": "Joel", "AMO": "Amos", "OBA": "Obadiah",
    "JON": "Jonah", "MIC": "Micah", "NAM": "Nahum", "HAB": "Habakkuk",
    "ZEP": "Zephaniah", "HAG": "Haggai", "ZEC": "Zechariah", "MAL": "Malachi",
    "TOB": "Tobit", "JDT": "Judith", "ESG": "Esther (Greek)", "WIS": "Wisdom",
    "SIR": "Sirach", "BAR": "Baruch", "LJE": "Letter of Jeremiah",
    "SUS": "Susanna", "BEL": "Bel and the Dragon", "1MA": "1 Maccabees",
    "2MA": "2 Maccabees", "3MA": "3 Maccabees", "4MA": "4 Maccabees",
    "1ES": "1 Esdras", "MAN": "Prayer of Manasses", "DAG": "Daniel (Greek additions)",
}

# Theosis's importer uses stable OSIS-like identifiers for these names.  The
# converter emits names that its existing EXTRA_BOOKS mapping understands.
BRENTON_BOOK_ALIASES = {
    "Esther (Greek)": "Esther",
    "Letter of Jeremiah": "Baruch",
    "Daniel (Greek additions)": "Daniel",
}


def clean_usfm(text: str) -> str:
    """Remove USFM notes/markers while preserving readable verse text."""
    # Footnotes and cross-references can contain nested markers; remove the
    # complete block before stripping ordinary character styles.
    text = re.sub(r"\\f\s.*?\\f\*", " ", text)
    text = re.sub(r"\\x\s.*?\\x\*", " ", text)
    text = re.sub(r"\\z.+?\*", " ", text)
    text = re.sub(r"\\[+]?[-A-Za-z0-9]+\*?", " ", text)
    text = text.replace("\\", " ")
    return re.sub(r"\s+", " ", text).strip()


def parse_brenton_usfm(archive: Path) -> list[tuple[str, int, int, str]]:
    """Extract Brenton verse rows from an eBible USFM archive."""
    rows: list[tuple[str, int, int, str]] = []
    with zipfile.ZipFile(archive) as zf:
        for name in zf.namelist():
            if not name.endswith(".usfm"):
                continue
            raw = zf.read(name).decode("utf-8-sig").replace("\r", "")
            match = re.search(r"^\\id\s+([^\s]+)", raw, flags=re.MULTILINE)
            if not match or match.group(1) not in BRENTON_BOOKS:
                continue
            book = BRENTON_BOOKS[match.group(1)]
            book = BRENTON_BOOK_ALIASES.get(book, book)
            chapter = None
            pending: tuple[int, str] | None = None

            def flush(current_book: str, current_chapter: int | None) -> None:
                nonlocal pending
                if pending is not None and current_chapter is not None:
                    verse, verse_text = pending
                    verse_text = clean_usfm(verse_text)
                    if verse_text:
                        rows.append((current_book, current_chapter, verse, verse_text))
                pending = None

            for line in raw.splitlines():
                chapter_match = re.match(r"^\\c\s+(\d+)", line)
                if chapter_match:
                    flush(book, chapter)
                    chapter = int(chapter_match.group(1))
                    continue
                verse_match = re.match(r"^\\v\s+(\d+)(?:-\d+)?\s*(.*)$", line)
                if verse_match:
                    flush(book, chapter)
                    pending = (int(verse_match.group(1)), verse_match.group(2))
                elif pending is not None and line.strip() and not line.startswith("\\"):
                    pending = (pending[0], pending[1] + " " + line.strip())
            flush(book, chapter)
    return rows


def write_csv(path: Path, rows: list[tuple[str, int, int, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Book", "Chapter", "Verse", "Text"])
        writer.writerows(rows)


def prepare_murdock(module_dir: Path) -> list[tuple[str, int, int, str]]:
    """Extract every verse from an unpacked CrossWire Murdock module."""
    try:
        from pysword.modules import SwordModules
    except ImportError as exc:  # pragma: no cover - exercised by CLI users
        raise SystemExit(
            "Murdock preparation requires pysword; run `uv run --extra source "
            "scripts/prepare_historical_sources.py ...`"
        ) from exc

    modules = SwordModules(str(module_dir))
    modules.parse_modules()
    bible = modules.get_bible_from_module("Murdock")
    rows: list[tuple[str, int, int, str]] = []
    for testament_books in bible.get_structure().get_books().values():
        for book in testament_books:
            for chapter, verse_count in enumerate(book.chapter_lengths, start=1):
                for verse in range(1, verse_count + 1):
                    text = next(
                        bible.get_iter(
                            books=[book.name], chapters=[chapter], verses=[verse], clean=True
                        ),
                        "",
                    ).strip()
                    if text:
                        rows.append((book.name, chapter, verse, text))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brenton-zip", type=Path)
    parser.add_argument("--murdock-dir", type=Path,
                        help="Unpacked CrossWire Murdock module directory")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if not args.brenton_zip and not args.murdock_dir:
        parser.error("provide --brenton-zip and/or --murdock-dir")
    if args.brenton_zip:
        rows = parse_brenton_usfm(args.brenton_zip)
        write_csv(args.output_dir / "Brenton.csv", rows)
        print(f"Brenton: {len(rows):,} verses")
    if args.murdock_dir:
        rows = prepare_murdock(args.murdock_dir)
        write_csv(args.output_dir / "Murdock.csv", rows)
        print(f"Murdock: {len(rows):,} verses")


if __name__ == "__main__":
    main()
