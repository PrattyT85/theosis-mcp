#!/usr/bin/env python3
"""Backfill witness rows from already-imported textual-variant sigla.

Defaults to a dry run. Use --apply only after taking a PostgreSQL backup.
This does not download SWORD modules and does not truncate existing data.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import re
from collections.abc import Iterable

DB_URL = os.environ.get(
    "THEOSIS_DATABASE_URL",
    "postgresql://theosis@/theosis?host=/var/run/postgresql",
)
KNOWN_SIGLA = frozenset(("WH", "Treg", "NIV", "RP", "NA", "SBL", "THGNT", "NA28", "UBS5"))


def split_sigla(value: str | None) -> list[str]:
    """Extract known witness sigla from a comma/space/semicolon-delimited field."""
    if not value:
        return []
    tokens = re.split(r"[,;/\s]+", value)
    result: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if token in KNOWN_SIGLA and token not in seen:
            result.append(token)
            seen.add(token)
    return result


def witness_rows(rows: Iterable[tuple[int, str | None, str | None]]) -> list[tuple[int, str, str]]:
    """Convert variant rows to deduplicated (variant_id, manuscript, support) tuples."""
    result: list[tuple[int, str, str]] = []
    seen: set[tuple[int, str, str]] = set()
    for variant_id, base, variant in rows:
        for manuscript, support in [(s, "base") for s in split_sigla(base)] + [(s, "variant") for s in split_sigla(variant)]:
            row = (variant_id, manuscript, support)
            if row not in seen:
                result.append(row)
                seen.add(row)
    return result


async def main() -> int:
    import asyncpg

    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write witness rows; default is dry-run")
    parser.add_argument("--db-url", default=DB_URL)
    args = parser.parse_args()
    conn = await asyncpg.connect(args.db_url)
    try:
        rows = await conn.fetch("SELECT id, variant_significance, scholarly_consensus FROM textual_variants")
        payload = witness_rows([(r["id"], r["variant_significance"], r["scholarly_consensus"]) for r in rows])
        print(f"variants={len(rows)} candidate_witnesses={len(payload)} apply={args.apply}")
        if not args.apply:
            return 0
        async with conn.transaction():
            for variant_id, manuscript, support in payload:
                await conn.execute(
                    """INSERT INTO manuscript_witnesses(variant_id, manuscript, reading_support)
                       SELECT $1, $2, $3
                       WHERE NOT EXISTS (
                         SELECT 1 FROM manuscript_witnesses
                         WHERE variant_id=$1 AND manuscript=$2 AND reading_support=$3
                       )""",
                    variant_id, manuscript, support,
                )
        count = await conn.fetchval("SELECT count(*) FROM manuscript_witnesses")
        print(f"manuscript_witnesses={count}")
        return 0
    finally:
        await conn.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
