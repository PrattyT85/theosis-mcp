#!/usr/bin/env python3
"""
Import NT textual variants from SWORD SBLGNT Apparatus module.

Parses the SBLGNT Apparatus (and VarApp) SWORD modules into the textual_variants
and manuscript_witnesses tables.

Usage:
  python3 scripts/import_variants.py
  python3 scripts/import_variants.py --modules SBLGNTApp,VarApp
  python3 scripts/import_variants.py --truncate   # destructive: clears existing data first

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

KNOWN_SIGLA = frozenset((
    # Edition sigla
    "WH", "Treg", "NIV", "RP", "NA", "SBL", "THGNT", "NA28", "UBS5",
    # Additional manuscript sigla
    "B", "א", "A", "C", "D", "E", "F", "G", "H", "I", "K", "L", "M", "N",
    "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z",
    " AssemblyVersion", "Codex", "Lectionary",
))

# Regex to match papyrus sigla (e.g., p1, p45, p66, p75)
_PAPYRUS_RE = re.compile(r"^p\d+$")
# Regex to match uncials (single uppercase letter or Unicode aleph etc.)
_UNCIAL_RE = re.compile(r"^[Α-Ω]$|^א$|^[\u0370-\u03FF]$")  # Greek + Hebrew letters
# Byzantine families
_BYZANTINE_RE = re.compile(r"^f\d+$|^Byz$|^Lect$|^Maj$")

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

# Documented fixture from the research docs — used for parser validation.
MATTHEW_1_5_IMP = (
    "$$$Matthew 1:5\n"
    "<item>\u0392\u03cc\u03b5\u03c2 \u2026 \u0392\u03cc\u03b5\u03c2 WH NIV ] "
    "\u0392\u03bf\u1f78\u03c2 \u2026 \u0392\u03bf\u1f78\u03c2 Treg</item>\n"
)

# VarApp Matthew 1:1 fixture — stable fixture for parser validation.
# Format: each reading is "Greek text] witness_list"
# First reading = base, subsequent readings = variants.
MATTHEW_1_1_VARAPP = (
    "$$$Matthew 1:1\n"
    "Δαυὶδ] p1 Byz\n"
    "Δαυεὶδ] B WH\n"
    "Δαβὶδ] ς\n"
)

# Extended KNOWN_SIGLA set for VarApp manuscript support
VARAPP_KNOWN_SIGLA = KNOWN_SIGLA | frozenset((
    "p1", "p45", "p66", "p75", "p127",
    "א", "B", "A", "C", "D", "E", "F", "G", "H", "I", "K", "L", "M", "N",
    "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z",
    "Byz", "f1", "f13", "Lect", "Maj",
    "cop", "syr", "vg", "it",
    "WH", "NA", "UBS", "ς",
    "RP", "NIV", "SBL", "THGNT", "Treg",
))


def classify_witness(siglum):
    """Classify a witness siglum into its type category.

    Returns one of: 'papyrus', 'uncial', 'byzantine', 'edition',
    'version', or 'unknown'.  Unknown tokens are preserved rather than
    discarded.
    """
    if _PAPYRUS_RE.match(siglum):
        return "papyrus"
    # Check editions before uncial — ς (final sigma) is a Greek letter but is an edition siglum
    if siglum in ("WH", "Treg", "NIV", "RP", "NA", "SBL", "THGNT",
                  "NA28", "UBS5", "UBS", "ς"):
        return "edition"
    if siglum in ("B", "א", "A", "C", "D", "E", "F", "G", "H", "I", "K",
                   "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V",
                   "W", "X", "Y", "Z"):
        return "uncial"
    if _UNCIAL_RE.match(siglum):
        return "uncial"
    if _BYZANTINE_RE.match(siglum):
        return "byzantine"
    if siglum in ("cop", "syr", "vg", "it", "Arm", "Eth", "Goth"):
        return "version"
    return "unknown"


def strip_osis(text):
    """Strip OSIS/HTML markup, keeping Greek text."""
    # Preserve Greek characters, strip tags
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_sigla_from_part(text):
    """Extract known witness sigla from a text fragment.

    Sigla are whitespace-delimited tokens that match KNOWN_SIGLA.
    Returns a list of siglum strings in order of appearance.
    """
    tokens = text.split()
    return [t for t in tokens if t in KNOWN_SIGLA]


def _parse_reading(line):
    """Parse a single VarApp reading line into (greek_text, witnesses_str).

    Format: "Greek text] witness1 witness2 ..."
    The ']' delimiter separates the Greek text from witness sigla.
    Unknown tokens are preserved as-is rather than discarded.
    """
    line = line.strip()
    if "]" not in line:
        return line, ""
    # Split on first ']' only — readings may contain multiple ']' in theory
    parts = line.split("]", 1)
    greek_text = parts[0].strip()
    witnesses = parts[1].strip() if len(parts) > 1 else ""
    return greek_text, witnesses


def parse_varapp_apparatus(imp_text):
    """Parse VarApp IMP format into variant entries.

    VarApp format:
        $$$Matthew 1:1
        Δαυὶδ] p1 Byz
        Δαυεὶδ] B WH

    Each reading line has the format: "Greek text] witness_list"
    The first reading for a verse is the base reading; subsequent readings
    are variants. Multiple readings are separated by <lb/> or line breaks.

    Returns list of (book_osis, chapter, verse, reference, mt_reading,
                      variant_source, variant_reading, base_sources, var_sources)
    """
    entries = []
    current_ref = None
    current_readings = []

    lines = imp_text.split("\n")
    for line in lines:
        # Split on <lb/> first — this is a reading separator, not just whitespace
        sublines = re.split(r"<lb\s*/?>", line)

        for subline in sublines:
            # Check for verse marker
            marker_match = re.match(r"^\$\$\$(.+)\s+(\d+):(\d+)$", subline.strip())
            if marker_match:
                # Flush previous marker's readings
                if current_ref and current_readings:
                    _flush_varapp_readings(current_ref, current_readings, entries)

                book_name = marker_match.group(1).strip()
                chapter = int(marker_match.group(2))
                verse = int(marker_match.group(3))
                osis = BOOK_TO_OSIS.get(book_name)

                if osis and chapter > 0 and verse > 0:
                    current_ref = {"osis": osis, "chapter": chapter, "verse": verse}
                    current_readings = []
                else:
                    current_ref = None
                continue

            # Accumulate reading lines
            if current_ref and subline.strip():
                current_readings.append(subline.strip())

    # Flush the last marker's readings
    if current_ref and current_readings:
        _flush_varapp_readings(current_ref, current_readings, entries)

    return entries


def _flush_varapp_readings(ref, readings, entries):
    """Flush accumulated VarApp readings into entries.

    First reading = base; subsequent readings are variant pairs
    (base, variant) for each variant reading found.
    """
    if len(readings) < 2:
        return

    # First reading is the base
    base_greek, base_witnesses = _parse_reading(readings[0])
    base_sigla_str = base_witnesses if base_witnesses else "(unknown)"

    # Subsequent readings create variant entries
    for reading in readings[1:]:
        var_greek, var_witnesses = _parse_reading(reading)
        var_sigla_str = var_witnesses if var_witnesses else "(unknown)"

        entries.append((
            ref["osis"],
            ref["chapter"],
            ref["verse"],
            f"{ref['osis']} {ref['chapter']}:{ref['verse']}",
            base_greek if base_greek else "(base)",
            MODULES["VarApp"]["source"],
            var_greek if var_greek else "(variant)",
            base_sigla_str,
            var_sigla_str,
        ))


def build_witness_payload(variant_id, base_sigla, var_sigla):
    """Build manuscript_witnesses row dicts for a single textual variant.

    Deduplicates sigla within one run: each siglum appears at most once
    per reading_support value.
    """
    rows = []
    seen = set()
    for s in base_sigla:
        key = (s, "base")
        if key not in seen:
            rows.append({"variant_id": variant_id, "manuscript": s, "reading_support": "base"})
            seen.add(key)
    for s in var_sigla:
        key = (s, "variant")
        if key not in seen:
            rows.append({"variant_id": variant_id, "manuscript": s, "reading_support": "variant"})
            seen.add(key)
    return rows


def parse_variant_apparatus(imp_text, module_name):
    """Parse SBLGNT/VarApp IMP format into variant entries.

    Format:
        $$$Matthew 1:5
        <item>Βόες … Βόες WH NIV ] Βοὸς … Βοὸς Treg</item>

    Returns list of (book_osis, chapter, verse, reference, mt_reading,
                      variant_source, variant_reading, base_sources, var_sources)
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
                                if w in KNOWN_SIGLA:
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
                                    if w in KNOWN_SIGLA:
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

    # Flush the last marker's entries
    if current_ref and current_text_parts:
        full_text = " ".join(current_text_parts)
        items = re.findall(r"<item>(.*?)</item>", full_text, re.DOTALL)
        for item in items:
            clean = strip_osis(item)
            if clean:
                parts = clean.split("]")
                if len(parts) >= 2:
                    base_part = parts[0].strip()
                    var_part = parts[1].strip() if len(parts) > 1 else ""
                    base_words = base_part.split()
                    base_text = []
                    sources = []
                    for w in base_words:
                        if w in KNOWN_SIGLA:
                            sources.append(w)
                        else:
                            base_text.append(w)
                    var_parts = re.split(r"[;,]", var_part)
                    for vp in var_parts:
                        vp = vp.strip()
                        if not vp:
                            continue
                        vp_words = vp.split()
                        vp_text = []
                        vp_sources = []
                        for w in vp_words:
                            if w in KNOWN_SIGLA:
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

    return entries


def build_arg_parser():
    """Return the ArgumentParser used by the importer (testable)."""
    parser = argparse.ArgumentParser(description="Import NT textual variants")
    parser.add_argument("--modules", default="SBLGNTApp",
                        help="Comma-separated module names")
    parser.add_argument("--sword-base", default="/tmp",
                        help="Base directory for SWORD modules")
    parser.add_argument("--batch-size", type=int, default=500,
                        help="Batch insert size")
    parser.add_argument("--truncate", action="store_true", default=False,
                        help="DESTRUCTIVE: TRUNCATE textual_variants and "
                             "manuscript_witnesses before import (default: "
                             "preserve existing data)")
    return parser


async def main():
    args = build_arg_parser().parse_args()

    # Lazy import: asyncpg is only needed when actually connecting to a database.
    import asyncpg

    module_names = [m.strip() for m in args.modules.split(",")]
    pg = await asyncpg.connect(DB_URL)

    try:
        # Only truncate when explicitly requested via --truncate
        if args.truncate:
            existing = await pg.fetchval("SELECT COUNT(*) FROM textual_variants")
            if existing > 0:
                print(f"Destructive mode: clearing {existing:,} existing variants...")
            await pg.execute(
                "TRUNCATE textual_variants, manuscript_witnesses RESTART IDENTITY"
            )
        else:
            existing = await pg.fetchval("SELECT COUNT(*) FROM textual_variants")
            if existing > 0:
                print(
                    f"Preserving {existing:,} existing variants "
                    f"(use --truncate to clear first)"
                )

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
            imported = 0
            start = time.time()

            for entry in entries:
                (
                    book, chapter, verse, reference,
                    mt_reading, vsource, vreading, base_sigla_str, var_sigla_str,
                ) = entry

                # Parse sigla strings into lists
                base_sigla = [s.strip() for s in base_sigla_str.split(",") if s.strip()]
                var_sigla = [s.strip() for s in var_sigla_str.split(",") if s.strip()]

                # Insert textual variant and get the generated id
                row_id = await pg.fetchval(
                    """INSERT INTO textual_variants
                       (book, chapter, verse, reference, mt_reading, variant_source,
                        variant_reading, variant_significance, scholarly_consensus)
                       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
                       RETURNING id""",
                    book, chapter, verse, reference, mt_reading,
                    vsource, vreading, base_sigla_str, var_sigla_str,
                )

                # Insert manuscript witnesses for this variant
                witness_rows = build_witness_payload(row_id, base_sigla, var_sigla)
                if witness_rows:
                    await pg.executemany(
                        """INSERT INTO manuscript_witnesses
                           (variant_id, manuscript, reading_support)
                           VALUES ($1,$2,$3)""",
                        [list(r.values()) for r in witness_rows],
                    )

                imported += 1
                if imported % args.batch_size == 0:
                    elapsed = time.time() - start
                    print(
                        f"    {imported:,}/{len(entries):,} "
                        f"({imported/len(entries)*100:.0f}%) — "
                        f"{imported/elapsed:.0f}/sec"
                    )

            elapsed = time.time() - start
            print(f"  Done: {imported:,} in {elapsed:.1f}s")

        # Final count
        total = await pg.fetchval("SELECT COUNT(*) FROM textual_variants")
        witnesses = await pg.fetchval("SELECT COUNT(*) FROM manuscript_witnesses")
        print(f"\nTotal variants: {total:,}")
        print(f"Total witnesses: {witnesses:,}")

    finally:
        await pg.close()


if __name__ == "__main__":
    asyncio.run(main())
