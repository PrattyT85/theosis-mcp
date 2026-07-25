#!/usr/bin/env python3
"""
Import NT textual variants from SWORD SBLGNT Apparatus module.

Parses the SBLGNT Apparatus (and VarApp) SWORD modules into the textual_variants
and manuscript_witnesses tables.

Usage:
  python3 scripts/import_variants.py
  python3 scripts/import_variants.py --modules SBLGNTApp,VarApp

Requires: libsword-utils (mod2imp), asyncpg
"""

import argparse
import asyncio
import html
import os
import re
import subprocess
import sys
import time

import asyncpg

DB_URL = os.environ.get(
    "THEOSIS_DATABASE_URL",
    "postgresql://theosis@/theosis?host=/var/run/postgresql"
)

BOOK_TO_OSIS = {
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

MODULES = {
    "SBLGNTApp": {
        "source": "SBLGNT Apparatus",
        "description": "NT textual variants from SBL Greek New Testament apparatus",
    },
    "VarApp": {
        "source": "NT Manuscript Variant Apparatus",
        "description": "NT manuscript variant readings",
    },
}


def strip_osis(text):
    """Strip OSIS/HTML markup, keeping Greek text."""
    # Preserve Greek characters, strip tags
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_variant_apparatus(imp_text, module_name):
    """Parse SBLGNT/VarApp IMP format into variant entries.
    
    Format:
        $$$Matthew 1:5
        <item>Βόες … Βόες WH NIV ] Βοὸς … Βοὸς Treg</item>
    
    Returns list of (book_osis, chapter, verse, mt_reading, variant_source, variant_reading)
    """
    meta = MODULES[module_name]
    entries = []
    
    current_ref = None
    current_text_parts = []
    
    lines = imp_text.split("\n")
    
    for line in lines:
        marker_match = re.match(r"^\$\$\$(.+)\s+(\d+):(\d+)$", line)
        if marker_match:
            # Process previous variant if any
            if current_ref and current_text_parts:
                full_text = " ".join(current_text_parts)
                # Parse individual variant items
                items = re.findall(r"<item>(.*?)</item>", full_text, re.DOTALL)
                for item in items:
                    clean = strip_osis(item)
                    if clean:
                        # Parse: "WORD … WORD WH NIV ] WORD … WORD RP"
                        parts = clean.split("]")
                        if len(parts) >= 2:
                            base_part = parts[0].strip()
                            var_part = parts[1].strip() if len(parts) > 1 else ""
                            
                            # Extract source sigla from base part
                            base_words = base_part.split()
                            base_text = []
                            sources = []
                            for w in base_words:
                                if w in ("WH", "Treg", "NIV", "RP", "NA", "SBL", "THGNT", "NA28", "UBS5"):
                                    sources.append(w)
                                else:
                                    base_text.append(w)
                            
                            # Parse variant part: "WORD … WORD RP; WORD … WORD Treg"
                            var_parts = re.split(r"[;,]", var_part)
                            for vp in var_parts:
                                vp = vp.strip()
                                if not vp:
                                    continue
                                vp_words = vp.split()
                                vp_text = []
                                vp_sources = []
                                for w in vp_words:
                                    if w in ("WH", "Treg", "NIV", "RP", "NA", "SBL", "THGNT", "NA28", "UBS5"):
                                        vp_sources.append(w)
                                    else:
                                        vp_text.append(w)
                                
                                base_reading = " ".join(base_text) if base_text else base_part
                                var_reading = " ".join(vp_text) if vp_text else vp.strip()
                                base_sources = ", ".join(sources) if sources else "WH/NIV"
                                var_sources = ", ".join(vp_sources) if vp_sources else "RP"
                                
                                entries.append((
                                    current_ref["osis"],
                                    current_ref["chapter"],
                                    current_ref["verse"],
                                    f"{current_ref['osis']} {current_ref['chapter']}:{current_ref['verse']}",
                                    base_reading if base_reading else "(omitted)",
                                    meta["source"],
                                    var_reading if var_reading else "(reading)",
                                    base_sources,
                                    var_sources,
                                ))
            
            book = marker_match.group(1).strip()
            chapter = int(marker_match.group(2))
            verse = int(marker_match.group(3))
            osis = BOOK_TO_OSIS.get(book)
            
            if osis and chapter > 0 and verse > 0:
                current_ref = {"osis": osis, "chapter": chapter, "verse": verse}
                current_text_parts = []
            else:
                current_ref = None
            continue
        
        if current_ref and line.strip() and not line.startswith("$$$"):
            current_text_parts.append(line)
    
    return entries


async def main():
    parser = argparse.ArgumentParser(description="Import NT textual variants")
    parser.add_argument("--modules", default="SBLGNTApp",
                        help="Comma-separated module names")
    parser.add_argument("--sword-base", default="/tmp",
                        help="Base directory for SWORD modules")
    parser.add_argument("--batch-size", type=int, default=500,
                        help="Batch insert size")
    args = parser.parse_args()

    module_names = [m.strip() for m in args.modules.split(",")]
    pg = await asyncpg.connect(DB_URL)

    try:
        # Clear existing variant data
        existing = await pg.fetchval("SELECT COUNT(*) FROM textual_variants")
        if existing > 0:
            print(f"Clearing {existing:,} existing variants...")
            await pg.execute("TRUNCATE textual_variants, manuscript_witnesses RESTART IDENTITY")

        for module_name in module_names:
            if module_name not in MODULES:
                print(f"Unknown: {module_name}, skipping")
                continue

            sword_path = os.path.join(args.sword_base, module_name)
            if not os.path.isdir(sword_path):
                print(f"Not found: {sword_path}, skipping")
                continue

            meta = MODULES[module_name]
            print(f"\n{'='*50}")
            print(f"Processing: {meta['description']}")

            # Convert to IMP
            imp_file = os.path.join(args.sword_base, f"{module_name}.imp")
            if not os.path.exists(imp_file):
                print("  Converting...")
                result = subprocess.run(
                    ["mod2imp", module_name],
                    capture_output=True, text=True, errors="replace",
                    env={**os.environ, "SWORD_PATH": sword_path},
                    timeout=120
                )
                if result.returncode != 0:
                    print(f"  ERROR: {result.stderr[:200]}")
                    continue
                with open(imp_file, "w") as f:
                    f.write(result.stdout)

            print(f"  Parsing IMP...")
            with open(imp_file, encoding="utf-8", errors="replace") as f:
                entries = parse_variant_apparatus(f.read(), module_name)
            print(f"  Parsed {len(entries):,} variant readings")

            # Import
            print(f"  Importing...")
            batch = []
            imported = 0
            start = time.time()

            for entry in entries:
                batch.append(entry)
                if len(batch) >= args.batch_size:
                    await pg.executemany(
                        """INSERT INTO textual_variants 
                           (book, chapter, verse, reference, mt_reading, variant_source,
                            variant_reading, variant_significance, scholarly_consensus)
                           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)""",
                        batch
                    )
                    imported += len(batch)
                    elapsed = time.time() - start
                    print(f"    {imported:,}/{len(entries):,} "
                          f"({imported/len(entries)*100:.0f}%) — {imported/elapsed:.0f}/sec")
                    batch = []

            if batch:
                await pg.executemany(
                    """INSERT INTO textual_variants 
                       (book, chapter, verse, reference, mt_reading, variant_source,
                        variant_reading, variant_significance, scholarly_consensus)
                       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)""",
                    batch
                )
                imported += len(batch)

            elapsed = time.time() - start
            print(f"  Done: {imported:,} in {elapsed:.1f}s")

        # Final count
        total = await pg.fetchval("SELECT COUNT(*) FROM textual_variants")
        print(f"\nTotal variants: {total:,}")

    finally:
        await pg.close()


if __name__ == "__main__":
    asyncio.run(main())
