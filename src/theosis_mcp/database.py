"""
Database layer for Theosis MCP server.
PostgreSQL backend with asyncpg + pgvector for semantic search.
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

import asyncpg

logger = logging.getLogger("theosis-mcp")

# Canonical book abbreviation map
BOOK_ABBREV_MAP = {
    "genesis": "Gen", "gen": "Gen",
    "exodus": "Exo", "exod": "Exo", "ex": "Exo",
    "leviticus": "Lev", "lev": "Lev",
    "numbers": "Num", "num": "Num",
    "deuteronomy": "Deu", "deut": "Deu", "dt": "Deu",
    "joshua": "Jos", "josh": "Jos",
    "judges": "Jdg", "judg": "Jdg",
    "ruth": "Rut",
    "1 samuel": "1Sa", "1sam": "1Sa", "1 sam": "1Sa",
    "2 samuel": "2Sa", "2sam": "2Sa", "2 sam": "2Sa",
    "1 kings": "1Ki", "1kgs": "1Ki", "1 kgs": "1Ki",
    "2 kings": "2Ki", "2kgs": "2Ki", "2 kgs": "2Ki",
    "1 chronicles": "1Ch", "1chr": "1Ch", "1 chr": "1Ch",
    "2 chronicles": "2Ch", "2chr": "2Ch", "2 chr": "2Ch",
    "ezra": "Ezr",
    "nehemiah": "Neh", "neh": "Neh",
    "esther": "Est", "esth": "Est",
    "job": "Job",
    "psalms": "Psa", "psalm": "Psa", "ps": "Psa",
    "proverbs": "Pro", "prov": "Pro", "pr": "Pro",
    "ecclesiastes": "Ecc", "eccl": "Ecc",
    "song of solomon": "Sng", "song": "Sng", "sos": "Sng",
    "isaiah": "Isa", "isa": "Isa",
    "jeremiah": "Jer", "jer": "Jer",
    "lamentations": "Lam", "lam": "Lam",
    "ezekiel": "Ezk", "ezek": "Ezk", "eze": "Ezk",
    "daniel": "Dan", "dan": "Dan",
    "hosea": "Hos", "hos": "Hos",
    "joel": "Jol",
    "amos": "Amo",
    "obadiah": "Oba", "obad": "Oba",
    "jonah": "Jon",
    "micah": "Mic", "mic": "Mic",
    "nahum": "Nam", "nah": "Nam",
    "habakkuk": "Hab", "hab": "Hab",
    "zephaniah": "Zep", "zeph": "Zep",
    "haggai": "Hag", "hag": "Hag",
    "zechariah": "Zec", "zech": "Zec",
    "malachi": "Mal", "mal": "Mal",
    "matthew": "Mat", "matt": "Mat", "mt": "Mat",
    "mark": "Mrk", "mk": "Mrk",
    "luke": "Luk", "lk": "Luk",
    "john": "Jhn", "jn": "Jhn",
    "acts": "Act",
    "romans": "Rom", "rom": "Rom",
    "1 corinthians": "1Co", "1cor": "1Co", "1 cor": "1Co",
    "2 corinthians": "2Co", "2cor": "2Co", "2 cor": "2Co",
    "galatians": "Gal", "gal": "Gal",
    "ephesians": "Eph", "eph": "Eph",
    "philippians": "Php", "phil": "Php",
    "colossians": "Col", "col": "Col",
    "1 thessalonians": "1Th", "1thess": "1Th", "1 thess": "1Th",
    "2 thessalonians": "2Th", "2thess": "2Th", "2 thess": "2Th",
    "1 timothy": "1Ti", "1tim": "1Ti", "1 tim": "1Ti",
    "2 timothy": "2Ti", "2tim": "2Ti", "2 tim": "2Ti",
    "titus": "Tit",
    "philemon": "Phm", "phlm": "Phm",
    "hebrews": "Heb", "heb": "Heb",
    "james": "Jas", "jas": "Jas",
    "1 peter": "1Pe", "1pet": "1Pe", "1 pet": "1Pe",
    "2 peter": "2Pe", "2pet": "2Pe", "2 pet": "2Pe",
    "1 john": "1Jn", "1jn": "1Jn",
    "2 john": "2Jn", "2jn": "2Jn",
    "3 john": "3Jn", "3jn": "3Jn",
    "jude": "Jud",
    "revelation": "Rev", "rev": "Rev",
}

# Reverse map: abbreviation -> full name
BOOK_NAMES = {
    "Gen": "Genesis", "Exo": "Exodus", "Lev": "Leviticus",
    "Num": "Numbers", "Deu": "Deuteronomy", "Jos": "Joshua",
    "Jdg": "Judges", "Rut": "Ruth", "1Sa": "1 Samuel", "2Sa": "2 Samuel",
    "1Ki": "1 Kings", "2Ki": "2 Kings", "1Ch": "1 Chronicles", "2Ch": "2 Chronicles",
    "Ezr": "Ezra", "Neh": "Nehemiah", "Est": "Esther", "Job": "Job",
    "Psa": "Psalms", "Pro": "Proverbs", "Ecc": "Ecclesiastes",
    "Sng": "Song of Solomon", "Isa": "Isaiah", "Jer": "Jeremiah",
    "Lam": "Lamentations", "Ezk": "Ezekiel", "Dan": "Daniel",
    "Hos": "Hosea", "Jol": "Joel", "Amo": "Amos", "Oba": "Obadiah",
    "Jon": "Jonah", "Mic": "Micah", "Nam": "Nahum", "Hab": "Habakkuk",
    "Zep": "Zephaniah", "Hag": "Haggai", "Zec": "Zechariah", "Mal": "Malachi",
    "Mat": "Matthew", "Mrk": "Mark", "Luk": "Luke", "Jhn": "John",
    "Act": "Acts", "Rom": "Romans", "1Co": "1 Corinthians", "2Co": "2 Corinthians",
    "Gal": "Galatians", "Eph": "Ephesians", "Php": "Philippians",
    "Col": "Colossians", "1Th": "1 Thessalonians", "2Th": "2 Thessalonians",
    "1Ti": "1 Timothy", "2Ti": "2 Timothy", "Tit": "Titus",
    "Phm": "Philemon", "Heb": "Hebrews", "Jas": "James",
    "1Pe": "1 Peter", "2Pe": "2 Peter", "1Jn": "1 John", "2Jn": "2 John",
    "3Jn": "3 John", "Jud": "Jude", "Rev": "Revelation",
}

# Book order for sorting
BOOK_ORDER = [
    "Gen", "Exo", "Lev", "Num", "Deu", "Jos", "Jdg", "Rut", "1Sa", "2Sa",
    "1Ki", "2Ki", "1Ch", "2Ch", "Ezr", "Neh", "Est", "Job", "Psa", "Pro",
    "Ecc", "Sng", "Isa", "Jer", "Lam", "Ezk", "Dan", "Hos", "Jol", "Amo",
    "Oba", "Jon", "Mic", "Nam", "Hab", "Zep", "Hag", "Zec", "Mal",
    "Mat", "Mrk", "Luk", "Jhn", "Act", "Rom", "1Co", "2Co", "Gal", "Eph",
    "Php", "Col", "1Th", "2Th", "1Ti", "2Ti", "Tit", "Phm", "Heb", "Jas",
    "1Pe", "2Pe", "1Jn", "2Jn", "3Jn", "Jud", "Rev",
]


def get_db_url() -> str:
    """Get database URL from environment or default."""
    url = os.environ.get("THEOSIS_DATABASE_URL")
    if url:
        return url
    # Build from components
    host = os.environ.get("PGHOST", "localhost")
    port = os.environ.get("PGPORT", "5432")
    user = os.environ.get("PGUSER", "theosis")
    password = os.environ.get("PGPASSWORD", "theosis")
    dbname = os.environ.get("PGDATABASE", "theosis")
    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"


class TheosisDB:
    """Async PostgreSQL database interface for theological research."""

    def __init__(self, db_url: str | None = None):
        self.db_url = db_url or get_db_url()
        self.pool: asyncpg.Pool | None = None
        self._vector_available: bool = False

    async def connect(self):
        """Create connection pool."""
        self.pool = await asyncpg.create_pool(
            self.db_url,
            min_size=2,
            max_size=10,
            command_timeout=30,
        )
        # Check pgvector availability
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
                self._vector_available = True
                logger.info("pgvector extension is available")
        except Exception as e:
            logger.warning(f"pgvector not available: {e}")
            self._vector_available = False

    async def close(self):
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def _fetchall(self, sql: str, *params) -> list[dict]:
        """Execute SQL and return all rows as dicts."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [dict(row) for row in rows]

    async def _fetchone(self, sql: str, *params) -> dict | None:
        """Execute SQL and return one row as dict, or None."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(sql, *params)
            return dict(row) if row else None

    async def _table_has_rows(self, table: str) -> bool:
        """Check if a table has at least one row."""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(f"SELECT 1 FROM {table} LIMIT 1")
                return row is not None
        except Exception:
            return False

    # =========================================================================
    # Reference parsing
    # =========================================================================

    @staticmethod
    def _normalize_strongs(strongs: str) -> str:
        """Normalize Strong's number to DB format (G26 -> G0026)."""
        strongs = strongs.upper().strip()
        if len(strongs) >= 2 and strongs[0] in ("G", "H"):
            num = strongs[1:]
            return strongs[0] + num.zfill(4)
        return strongs

    def _normalize_reference(self, reference: str) -> str:
        """Normalize a Bible reference to standard form (e.g., 'John 3:16' -> 'Jhn 3:16')."""
        reference = reference.strip()
        # Try to match "Book Chapter:Verse" or "Book Chapter"
        match = re.match(r'^(.+?)\s+(\d+)(?::(\d+))?\s*$', reference)
        if not match:
            return reference
        book_name = match.group(1).lower().strip()
        chapter = match.group(2)
        verse = match.group(3)
        abbrev = BOOK_ABBREV_MAP.get(book_name, book_name.title())
        if verse:
            return f"{abbrev} {chapter}:{verse}"
        return f"{abbrev} {chapter}"

    # =========================================================================
    # Lexicon queries
    # =========================================================================

    async def get_lexicon_entry(self, strongs: str) -> dict | None:
        """Get a single lexicon entry by Strong's number."""
        strongs = self._normalize_strongs(strongs)
        return await self._fetchone("SELECT * FROM lexicon WHERE strongs = $1", strongs)

    async def search_lexicon(
        self, query: str, language: str | None = None, limit: int = 10
    ) -> list[dict]:
        """Search lexicon by definition, transliteration, or word."""
        query_lower = f"%{query.lower()}%"
        sql = """
            SELECT * FROM lexicon
            WHERE (
                LOWER(short_definition) LIKE $1
                OR LOWER(full_definition) LIKE $1
                OR LOWER(transliteration) LIKE $1
                OR LOWER(word) LIKE $1
                OR LOWER(abbott_smith_def) LIKE $1
            )
        """
        params: list = [query_lower]
        if language:
            strongs_prefix = "G" if language.lower() == "greek" else "H"
            sql += " AND strongs LIKE $2"
            params.append(f"{strongs_prefix}%")
        sql += " ORDER BY strongs LIMIT $2" if language else " ORDER BY strongs LIMIT $2"
        if not language:
            sql = sql.replace("LIMIT $2", f"LIMIT ${len(params)+1}")
        params.append(limit)
        return await self._fetchall(sql, *params)

    # =========================================================================
    # Verse queries
    # =========================================================================

    async def get_verse(self, reference: str) -> dict | None:
        """Get a verse by reference, including original language text."""
        normalized = self._normalize_reference(reference)
        parts = normalized.split()
        if len(parts) < 2:
            return None
        book = parts[0]
        cv = parts[1].split(":")
        chapter = int(cv[0])
        verse = int(cv[1]) if len(cv) > 1 else None

        if verse:
            return await self._fetchone("""
                SELECT * FROM verses
                WHERE book = $1 AND chapter = $2 AND verse = $3
                LIMIT 1
            """, book, chapter, verse)
        else:
            return await self._fetchone("""
                SELECT * FROM verses
                WHERE book = $1 AND chapter = $2
                LIMIT 1
            """, book, chapter)

    async def get_verses_with_strongs(self, strongs: str, limit: int = 20) -> list[dict]:
        """Get all verses containing a given Strong's number."""
        strongs = self._normalize_strongs(strongs)
        return await self._fetchall("""
            SELECT v.* FROM verses v
            JOIN strongs_verse_map svm ON v.id = svm.verse_id
            WHERE svm.strongs_id = $1
            ORDER BY v.book, v.chapter, v.verse
            LIMIT $2
        """, strongs, limit)

    async def get_morphology(self, code: str, language: str = "greek") -> dict | None:
        """Get morphology parsing for a code."""
        return await self._fetchone("""
            SELECT * FROM morphology
            WHERE code = $1 AND language = $2
        """, code, language.lower())

    # =========================================================================
    # Cross-references
    # =========================================================================

    async def get_cross_references(
        self,
        reference: str,
        source_filter: str | None = None,
        limit: int = 8,
        min_strength: int | None = None,
    ) -> list[dict]:
        """Get cross-references for a verse."""
        normalized = self._normalize_reference(reference)

        sql = "SELECT * FROM cross_references WHERE source = $1"
        params: list = [normalized]
        if source_filter:
            sql += " AND type = $2"
            params.append(source_filter)
        sql += " ORDER BY relevance DESC LIMIT $" + str(len(params) + 1)
        params.append(limit)

        refs = await self._fetchall(sql, *params)
        if refs:
            return refs

        # No cross-references found - return empty list (not an error)
        return []

    async def get_thematic_references(self, theme: str) -> list[dict]:
        """Get thematic cross-references."""
        return await self._fetchall("""
            SELECT * FROM theological_themes
            WHERE theme_slug = $1
            LIMIT 50
        """, theme.lower().replace(" ", "_"))

    # =========================================================================
    # Name / entity queries
    # =========================================================================

    async def lookup_name(self, name: str, name_type: str | None = None) -> list[dict]:
        """Look up biblical names (persons, places, things)."""
        query = f"%{name}%"
        sql = """
            SELECT * FROM proper_names
            WHERE LOWER(name) LIKE LOWER($1)
        """
        params: list = [query]
        if name_type:
            sql += " AND type = $2"
            params.append(name_type)
        sql += " LIMIT 20"
        return await self._fetchall(sql, *params)

    async def get_acai_entity(self, name: str) -> dict | None:
        """Get ACAI entity data for a name."""
        return await self._fetchone("""
            SELECT * FROM acai_entities
            WHERE LOWER(name) LIKE LOWER($1)
            LIMIT 1
        """, f"%{name}%")

    async def has_acai_data(self) -> bool:
        """Check if ACAI entity data is available."""
        return await self._table_has_rows("acai_entities")

    # =========================================================================
    # Graph / genealogy queries
    # =========================================================================

    async def get_genealogy(self, name: str, direction: str = "ancestors", depth: int = 5) -> list[dict]:
        """Get genealogy data for a person."""
        return await self._fetchall("""
            SELECT * FROM theographic_relations
            WHERE LOWER(person_name) LIKE LOWER($1)
            AND relation_type = $2
            LIMIT 50
        """, f"%{name}%", direction)

    async def get_person_events(self, name: str) -> list[dict]:
        """Get events associated with a person."""
        return await self._fetchall("""
            SELECT * FROM theographic_events
            WHERE LOWER(person_name) LIKE LOWER($1)
            ORDER BY event_order
            LIMIT 50
        """, f"%{name}%")

    async def get_place_history(self, name: str) -> list[dict]:
        """Get historical events for a place."""
        return await self._fetchall("""
            SELECT * FROM theographic_places
            WHERE LOWER(place_name) LIKE LOWER($1)
            LIMIT 50
        """, f"%{name}%")

    # =========================================================================
    # Study notes (Aquifer) queries
    # =========================================================================

    async def get_study_notes(self, reference: str, limit: int = 10) -> list[dict]:
        """Get study notes for a verse."""
        normalized = self._normalize_reference(reference)
        return await self._fetchall("""
            SELECT * FROM aquifer_content
            WHERE reference = $1
            ORDER BY priority DESC
            LIMIT $2
        """, normalized, limit)

    async def get_dictionary_article(self, topic: str) -> dict | None:
        """Get a Tyndale Bible Dictionary article."""
        return await self._fetchone("""
            SELECT * FROM aquifer_content
            WHERE content_type = 'dictionary' AND LOWER(title) LIKE LOWER($1)
            LIMIT 1
        """, f"%{topic}%")

    async def get_key_terms(self, reference: str) -> list[dict]:
        """Get key theological terms for a verse."""
        normalized = self._normalize_reference(reference)
        return await self._fetchall("""
            SELECT * FROM aquifer_content
            WHERE reference = $1 AND content_type = 'key_term'
            LIMIT 20
        """, normalized)

    # =========================================================================
    # ANE context queries
    # =========================================================================

    async def get_ane_context(self, reference: str) -> list[dict]:
        """Get Ancient Near East context for a verse."""
        normalized = self._normalize_reference(reference)
        return await self._fetchall("""
            SELECT * FROM ane_entries
            WHERE reference = $1
            LIMIT 20
        """, normalized)

    async def get_ane_dimensions(self) -> list[str]:
        """List available ANE dimensions."""
        rows = await self._fetchall("""
            SELECT DISTINCT dimension FROM ane_entries ORDER BY dimension
        """)
        return [r["dimension"] for r in rows]

    # =========================================================================
    # Theology queries
    # =========================================================================

    async def get_theology_context(self, reference: str) -> list[dict]:
        """Get theological context for a verse."""
        normalized = self._normalize_reference(reference)
        return await self._fetchall("""
            SELECT * FROM theological_themes
            WHERE reference = $1
            LIMIT 20
        """, normalized)

    async def get_theology_themes(self) -> list[str]:
        """List available theological themes."""
        rows = await self._fetchall("""
            SELECT DISTINCT theme_slug FROM theological_themes ORDER BY theme_slug
        """)
        return [r["theme_slug"] for r in rows]

    # =========================================================================
    # Torah weave
    # =========================================================================

    async def has_torah_weave_data(self) -> bool:
        """Check if Torah Weave data exists."""
        return await self._table_has_rows("torah_weave")

    async def get_torah_weave(self, reference: str) -> list[dict]:
        """Get Torah Weave structural partners."""
        normalized = self._normalize_reference(reference)
        return await self._fetchall("""
            SELECT * FROM torah_weave
            WHERE reference = $1
            LIMIT 20
        """, normalized)

    # =========================================================================
    # NT-OT LXX quotation hints
    # =========================================================================

    async def get_nt_ot_lxx_quote_hints(self, reference: str) -> list[dict]:
        """Get NT↔OT LXX quotation hints."""
        normalized = self._normalize_reference(reference)
        return await self._fetchall("""
            SELECT * FROM lxx_quotations
            WHERE nt_reference = $1 OR ot_reference = $1
            LIMIT 10
        """, normalized)

    # =========================================================================
    # NEW: Translations (theosis-specific)
    # =========================================================================

    async def list_translations(self) -> list[dict]:
        """List all available Bible translations."""
        return await self._fetchall("""
            SELECT id, abbreviation, name, language, year, license, description
            FROM translations
            ORDER BY language, name
        """)

    async def get_translation_verse(
        self, reference: str, translation_abbrev: str = "KJV"
    ) -> dict | None:
        """Get a specific verse in a specific translation."""
        normalized = self._normalize_reference(reference)
        parts = normalized.split()
        if len(parts) < 2:
            return None
        book = parts[0]
        cv = parts[1].split(":")
        chapter = int(cv[0])
        verse = int(cv[1]) if len(cv) > 1 else None

        return await self._fetchone("""
            SELECT v.*, t.name as translation_name, t.abbreviation
            FROM verses v
            JOIN books b ON v.book_id = b.id
            JOIN translations t ON b.translation_id = t.id
            WHERE b.name = $1 AND v.chapter = $2 AND v.verse = $3
            AND t.abbreviation = $4
            LIMIT 1
        """, book, chapter, verse, translation_abbrev)

    async def compare_translations(
        self, reference: str, translations: list[str]
    ) -> list[dict]:
        """Compare a verse across multiple translations."""
        results = []
        for abbrev in translations:
            verse = await self.get_translation_verse(reference, abbrev)
            if verse:
                results.append(verse)
        return results

    # =========================================================================
    # NEW: Extra-biblical texts (theosis-specific)
    # =========================================================================

    async def list_extra_biblical_categories(self) -> list[dict]:
        """List all extra-biblical text categories with counts."""
        return await self._fetchall("""
            SELECT category, COUNT(*) as count
            FROM extra_biblical_texts
            GROUP BY category
            ORDER BY category
        """)

    async def search_extra_biblical(
        self, query: str, category: str | None = None, limit: int = 20
    ) -> list[dict]:
        """Full-text search across extra-biblical texts."""
        sql = """
            SELECT id, title, author, category, section, subsection,
                   ts_headline('english', text, plainto_tsquery('english', $1),
                              'MaxWords=50, MinWords=20, ShortWord=3, MaxFragments=3') as snippet,
                   ts_rank(to_tsvector('english', text), plainto_tsquery('english', $1)) as rank
            FROM extra_biblical_texts
            WHERE to_tsvector('english', text) @@ plainto_tsquery('english', $1)
        """
        params: list = [query]
        if category:
            sql += " AND category = $2"
            params.append(category)
        sql += " ORDER BY rank DESC LIMIT $" + str(len(params) + 1)
        params.append(limit)
        return await self._fetchall(sql, *params)

    async def get_extra_biblical_text(
        self, title: str, section: str | None = None
    ) -> dict | None:
        """Get a specific extra-biblical text."""
        if section:
            return await self._fetchone("""
                SELECT * FROM extra_biblical_texts
                WHERE LOWER(title) LIKE LOWER($1) AND LOWER(section) LIKE LOWER($2)
                LIMIT 1
            """, f"%{title}%", f"%{section}%")
        return await self._fetchone("""
            SELECT * FROM extra_biblical_texts
            WHERE LOWER(title) LIKE LOWER($1)
            LIMIT 1
        """, f"%{title}%")

    # =========================================================================
    # NEW: Full-text search across all translations (theosis-specific)
    # =========================================================================

    async def search_bible_fulltext(
        self, query: str, translation_abbrev: str | None = None, limit: int = 20
    ) -> list[dict]:
        """Full-text search across Bible verses."""
        sql = """
            SELECT v.*, b.name as book_name, t.abbreviation,
                   ts_headline('english', v.text, plainto_tsquery('english', $1),
                              'MaxWords=50, MinWords=20, ShortWord=3, MaxFragments=3') as snippet,
                   ts_rank(to_tsvector('english', v.text), plainto_tsquery('english', $1)) as rank
            FROM verses v
            JOIN books b ON v.book_id = b.id
            JOIN translations t ON b.translation_id = t.id
            WHERE to_tsvector('english', v.text) @@ plainto_tsquery('english', $1)
        """
        params: list = [query]
        if translation_abbrev:
            sql += " AND t.abbreviation = $2"
            params.append(translation_abbrev)
        sql += " ORDER BY rank DESC LIMIT $" + str(len(params) + 1)
        params.append(limit)
        return await self._fetchall(sql, *params)

    # =========================================================================
    # NEW: Semantic search with pgvector (theosis-specific)
    # =========================================================================

    async def has_vector_tables(self) -> bool:
        """Check if vector embeddings are available."""
        return self._vector_available and await self._table_has_rows("verse_embeddings")

    async def find_similar_passages(
        self, reference: str, limit: int = 10
    ) -> list[dict]:
        """Find semantically similar passages using pgvector."""
        if not self._vector_available:
            return []

        normalized = self._normalize_reference(reference)
        parts = normalized.split()
        if len(parts) < 2:
            return []
        book = parts[0]
        cv = parts[1].split(":")
        chapter = int(cv[0])
        verse = int(cv[1]) if len(cv) > 1 else 0

        # Get the embedding for the target verse
        emb = await self._fetchone("""
            SELECT embedding FROM verse_embeddings
            WHERE book = $1 AND chapter = $2 AND verse = $3
            LIMIT 1
        """, book, chapter, verse)

        if not emb or not emb.get("embedding"):
            return []

        # Find similar verses
        return await self._fetchall("""
            SELECT ve.book, ve.chapter, ve.verse, v.text,
                   1 - (ve.embedding <=> $1) as similarity
            FROM verse_embeddings ve
            JOIN verses v ON ve.verse_id = v.id
            WHERE ve.book != $2 OR ve.chapter != $3 OR ve.verse != $4
            ORDER BY ve.embedding <=> $1
            LIMIT $5
        """, emb["embedding"], book, chapter, verse, limit)


# =============================================================================
# Connection pool singleton
# =============================================================================

_db: TheosisDB | None = None


async def get_db() -> TheosisDB:
    """Get or create the database connection pool."""
    global _db
    if _db is None:
        _db = TheosisDB()
        await _db.connect()
    return _db