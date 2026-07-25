#!/usr/bin/env python3
"""
Generate pgvector embeddings for all tagged verses using all-MiniLM-L6-v2.

Creates 384-dimensional embeddings in verse_embeddings table,
enabling find_similar_passages semantic search.

Usage:
  python3 scripts/generate_embeddings.py
  python3 scripts/generate_embeddings.py --batch-size 64 --limit 500  # test mode

Model: sentence-transformers/all-MiniLM-L6-v2 (~80MB, fits in 4GB RAM)
"""

import argparse
import asyncio
import os
import sys
import time

DB_URL = os.environ.get(
    "THEOSIS_DATABASE_URL",
    "postgresql://theosis@/theosis?host=/var/run/postgresql"
)


async def main():
    parser = argparse.ArgumentParser(description="Generate verse embeddings")
    parser.add_argument("--batch-size", type=int, default=64,
                        help="Batch size for embedding generation (default: 64)")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit number of verses (for testing)")
    parser.add_argument("--skip-if-exists", action="store_true",
                        help="Skip if verse_embeddings already has data")
    args = parser.parse_args()

    # Lazy import (heavy deps)
    print("Loading sentence-transformers model...")
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("ERROR: sentence-transformers not installed.")
        print("Run: pip install sentence-transformers")
        sys.exit(1)

    model = SentenceTransformer("all-MiniLM-L6-v2")
    print(f"Model loaded: {model}")

    import asyncpg
    import numpy as np

    conn = await asyncpg.connect(DB_URL)

    try:
        # Check if embeddings already exist
        if args.skip_if_exists:
            existing = await conn.fetchval("SELECT COUNT(*) FROM verse_embeddings")
            if existing and existing > 0:
                print(f"verse_embeddings already has {existing:,} rows. Skipping.")
                return

        # Verify pgvector is available
        has_pgvector = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname='pgvector')"
        )
        if not has_pgvector:
            print("ERROR: pgvector extension is not installed.")
            print("Run: CREATE EXTENSION IF NOT EXISTS vector;")
            sys.exit(1)

        # Ensure table exists
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS verse_embeddings (
                id SERIAL PRIMARY KEY,
                book TEXT NOT NULL,
                chapter INTEGER NOT NULL,
                verse INTEGER NOT NULL,
                verse_id INTEGER REFERENCES verses(id),
                embedding vector(384)
            )
        """)

        # Get verses to embed (from the tagged verses table)
        query = """
            SELECT v.id, v.book, v.chapter, v.verse, v.text_english
            FROM verses v
            WHERE v.text_english IS NOT NULL AND v.text_english != ''
              AND v.id NOT IN (SELECT ve.verse_id FROM verse_embeddings ve WHERE ve.verse_id IS NOT NULL)
            ORDER BY v.id
        """
        if args.limit:
            query += f" LIMIT {args.limit}"

        rows = await conn.fetch(query)
        total = len(rows)
        print(f"Generating embeddings for {total:,} verses...")

        if total == 0:
            print("No new verses to embed.")
            return

        # Process in batches
        processed = 0
        start_time = time.time()

        for i in range(0, total, args.batch_size):
            batch = rows[i : i + args.batch_size]
            texts = [row["text_english"] for row in batch]

            # Generate embeddings
            embeddings = model.encode(texts, normalize_embeddings=True)

            # Insert into PostgreSQL
            for j, row in enumerate(batch):
                vec = embeddings[j]
                # Format as pgvector literal
                vec_str = "[" + ",".join(f"{x:.8f}" for x in vec) + "]"
                await conn.execute(
                    """INSERT INTO verse_embeddings (book, chapter, verse, verse_id, embedding)
                       VALUES ($1, $2, $3, $4, $5::vector)""",
                    row["book"], row["chapter"], row["verse"], row["id"], vec_str
                )

            processed += len(batch)
            elapsed = time.time() - start_time
            rate = processed / elapsed if elapsed > 0 else 0
            pct = processed / total * 100
            print(f"  {processed:,}/{total:,} ({pct:.1f}%) — {rate:.0f} verses/sec")

        # Drop existing index and rebuild (better recall)
        print("Building IVFFlat index...")
        await conn.execute("DROP INDEX IF EXISTS idx_verse_embeddings_ivfflat")
        await conn.execute("""
            CREATE INDEX idx_verse_embeddings_ivfflat
            ON verse_embeddings
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        """)

        # Final count
        final_count = await conn.fetchval("SELECT COUNT(*) FROM verse_embeddings")
        elapsed = time.time() - start_time
        print(f"\n{'='*50}")
        print(f"Embedding generation complete:")
        print(f"  Total:    {final_count:,} verses")
        print(f"  Time:     {elapsed/60:.1f} minutes")
        print(f"  Rate:     {final_count/elapsed:.0f} verses/sec")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
