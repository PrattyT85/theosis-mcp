#!/usr/bin/env python3
"""
Import Heiser theological content into theosis PostgreSQL.

Imports themes taxonomy and textual variants with Heiser's analysis.
Content JSON files are imported as theology_content entries.

Usage:
  python3 scripts/import_heiser.py
"""

import asyncio
import json
import os
from pathlib import Path

import asyncpg

DB_URL = os.environ.get(
    "THEOSIS_DATABASE_URL",
    "postgresql://theosis@/theosis?host=/var/run/postgresql"
)

HEISER_DIR = "/root/studybible-mcp/data/heiser"

BOOK_ABBREVS = {
    "Gen": "Gen", "Exo": "Exo", "Lev": "Lev", "Num": "Num", "Deu": "Deu",
    "Jos": "Jos", "Jdg": "Jdg", "Rut": "Rut", "1Sa": "1Sa", "2Sa": "2Sa",
    "1Ki": "1Ki", "2Ki": "2Ki", "1Ch": "1Ch", "2Ch": "2Ch",
    "Ezr": "Ezr", "Neh": "Neh", "Est": "Est", "Job": "Job",
    "Psa": "Psa", "Pro": "Pro", "Ecc": "Ecc", "Sng": "Sng",
    "Isa": "Isa", "Jer": "Jer", "Lam": "Lam", "Ezk": "Ezk",
    "Dan": "Dan", "Hos": "Hos", "Jol": "Jol", "Amo": "Amo",
    "Oba": "Oba", "Jon": "Jon", "Mic": "Mic", "Nah": "Nah",
    "Hab": "Hab", "Zep": "Zep", "Hag": "Hag", "Zec": "Zec", "Mal": "Mal",
    "Mat": "Mat", "Mrk": "Mrk", "Luk": "Luk", "Jhn": "Jhn",
    "Act": "Act", "Rom": "Rom", "1Co": "1Co", "2Co": "2Co",
    "Gal": "Gal", "Eph": "Eph", "Php": "Php", "Col": "Col",
    "1Th": "1Th", "2Th": "2Th", "1Ti": "1Ti", "2Ti": "2Ti",
    "Tit": "Tit", "Phm": "Phm", "Heb": "Heb", "Jas": "Jas",
    "1Pe": "1Pe", "2Pe": "2Pe", "1Jn": "1Jn", "2Jn": "2Jn", "3Jn": "3Jn",
    "Jud": "Jud", "Rev": "Rev",
}


def parse_ref(ref: str) -> tuple:
    """Parse 'Deu.32.8' into (book_osis, chapter, verse)."""
    parts = ref.split(".")
    book = parts[0] if parts else ""
    chapter = int(parts[1]) if len(parts) > 1 else None
    verse = int(parts[2]) if len(parts) > 2 else None
    return book, chapter, verse


async def main():
    pg = await asyncpg.connect(DB_URL)

    try:
        themes_file = Path(HEISER_DIR) / "themes.json"
        variants_dir = Path(HEISER_DIR) / "variants"
        content_dir = Path(HEISER_DIR) / "content"

        # =====================================================================
        # 1. Import Themes
        # =====================================================================
        print("=" * 50)
        print("Importing Heiser Themes")
        print("=" * 50)

        if themes_file.exists():
            with open(themes_file) as f:
                data = json.load(f)
            themes = data.get("themes", [])
            count = 0
            for t in themes:
                key_works = t.get("heiser_key_works") or t.get("key_works")
                if isinstance(key_works, list):
                    key_works = ", ".join(key_works)
                await pg.execute(
                    """INSERT INTO theology_themes (theme_key, theme_label, description, parent_theme, key_works)
                       VALUES ($1, $2, $3, $4, $5)
                       ON CONFLICT DO NOTHING""",
                    t.get("theme_key", ""),
                    t.get("theme_label", ""),
                    t.get("description", ""),
                    t.get("parent_theme"),
                    key_works,
                )
                count += 1
            print(f"  Imported {count} themes")
        else:
            print("  themes.json not found")

        # =====================================================================
        # 2. Import Content (JSON files only)
        # =====================================================================
        print("\n" + "=" * 50)
        print("Importing Heiser Content (JSON)")
        print("=" * 50)

        if content_dir.exists():
            json_files = sorted(content_dir.glob("*.json"))
            total = 0
            for fp in json_files:
                try:
                    with open(fp) as f:
                        data = json.load(f)
                except json.JSONDecodeError:
                    continue

                if isinstance(data, dict):
                    # Single entry or source metadata
                    entry = data
                    await pg.execute(
                        """INSERT INTO theology_content
                           (source_work, source_author, source_type, title,
                            content_summary, content_detail, url)
                           VALUES ($1, $2, $3, $4, $5, $6, $7)""",
                        entry.get("source_key", fp.stem),
                        entry.get("author", "Michael S. Heiser"),
                        entry.get("type", "article"),
                        entry.get("title", fp.stem),
                        entry.get("abstract") or entry.get("summary", ""),
                        json.dumps(entry)[:10000],
                        entry.get("url"),
                    )
                    total += 1
                elif isinstance(data, list):
                    for entry in data:
                        await pg.execute(
                            """INSERT INTO theology_content
                               (source_work, source_author, source_type, title,
                                content_summary, content_detail, url)
                               VALUES ($1, $2, $3, $4, $5, $6, $7)""",
                            entry.get("source_key", fp.stem),
                            entry.get("author", "Michael S. Heiser"),
                            entry.get("type", "article"),
                            entry.get("title", fp.stem),
                            entry.get("abstract") or entry.get("summary", ""),
                            json.dumps(entry)[:10000],
                            entry.get("url"),
                        )
                        total += 1

            print(f"  Imported {total} content entries from {len(json_files)} files")

        # =====================================================================
        # 3. Import Variants with Heiser's Analysis
        # =====================================================================
        print("\n" + "=" * 50)
        print("Importing Heiser Textual Variants")
        print("=" * 50)

        if variants_dir.exists():
            var_count = 0
            wit_count = 0
            for fp in sorted(variants_dir.glob("*.json")):
                with open(fp) as f:
                    data = json.load(f)
                for variant in data.get("variants", []):
                    ref = variant["reference"]
                    book, chapter, verse = parse_ref(ref)
                    
                    # Get existing variant ID or insert new
                    existing = await pg.fetchrow(
                        "SELECT id FROM textual_variants WHERE reference = $1 AND variant_source = $2",
                        ref, variant.get("variant_source", "")
                    )
                    variant_id = None
                    
                    if existing:
                        variant_id = existing["id"]
                        # Update with Heiser's analysis
                        await pg.execute(
                            """UPDATE textual_variants 
                               SET heiser_analysis = $1, preferred_for_hlt = $2, 
                                   hlt_rationale = $3, mt_hebrew = $4,
                                   variant_original = $5, scholarly_consensus = $6
                               WHERE id = $7""",
                            variant.get("heiser_analysis"),
                            variant.get("preferred_for_hlt"),
                            variant.get("hlt_rationale"),
                            variant.get("mt_hebrew"),
                            variant.get("variant_original"),
                            variant.get("scholarly_consensus"),
                            variant_id,
                        )
                    else:
                        row = await pg.fetchrow(
                            """INSERT INTO textual_variants
                               (reference, book, chapter, verse, mt_reading, mt_hebrew,
                                variant_source, variant_reading, variant_original,
                                variant_significance, heiser_analysis, scholarly_consensus,
                                preferred_for_hlt, hlt_rationale)
                               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
                               RETURNING id""",
                            ref, book, chapter, verse,
                            variant["mt_reading"],
                            variant.get("mt_hebrew"),
                            variant["variant_source"],
                            variant["variant_reading"],
                            variant.get("variant_original"),
                            variant.get("variant_significance", "major_theological"),
                            variant.get("heiser_analysis"),
                            variant.get("scholarly_consensus"),
                            variant.get("preferred_for_hlt"),
                            variant.get("hlt_rationale"),
                        )
                        if row:
                            variant_id = row["id"]
                            var_count += 1

                    # Import manuscript witnesses
                    if variant_id:
                        for witness in variant.get("witnesses", []):
                            await pg.execute(
                                """INSERT INTO manuscript_witnesses
                                   (variant_id, manuscript, manuscript_date, reading_support)
                                   VALUES ($1, $2, $3, $4)""",
                                variant_id,
                                witness["manuscript"],
                                witness.get("manuscript_date"),
                                witness.get("reading_support"),
                            )
                            wit_count += 1

            print(f"  New variants: {var_count}")
            print(f"  Updated existing: {sum(1 for _ in variants_dir.glob('*.json'))}")
            print(f"  Manuscript witnesses: {wit_count}")

        # Summary
        print(f"\n{'='*50}")
        for table in ["theology_themes", "theology_content",
                       "textual_variants", "manuscript_witnesses"]:
            count = await pg.fetchval(f"SELECT COUNT(*) FROM {table}")
            print(f"  {table}: {count}")

    finally:
        await pg.close()


if __name__ == "__main__":
    asyncio.run(main())
