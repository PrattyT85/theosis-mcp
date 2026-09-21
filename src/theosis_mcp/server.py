#!/usr/bin/env python3
"""
Theosis MCP Server — Theological Research AI Interface

PostgreSQL-backed MCP server providing Bible study tools:
- Word studies with LSJ/BDB/Strong's lexicons
- Verse lookup with original Greek/Hebrew and morphology
- Cross-references from 4 scholarly sources
- 140+ Bible translations with side-by-side comparison
- Extra-biblical text library (Church Fathers, Apocrypha, Pseudepigrapha)
- Full-text search across all content
- Semantic search with pgvector embeddings
- ANE historical context and theological themes

Supports stdio, SSE, and Streamable HTTP transports.
"""

import asyncio
import json
import logging
from importlib.metadata import PackageNotFoundError, version as package_version
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import click
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Icon, TextContent, Tool

from .database import TheosisDB, BOOK_ABBREV_MAP, BOOK_NAMES, BOOK_ORDER, get_db, get_db_url
from .tools import TOOLS, _truncate
from .literary_helpers import (
    LIT_STRUCT_ATTRIBUTION,
    normalize_book,
    parse_ref_parts,
    reference_overlaps,
    render_structure_tree,
    format_structure_result,
    resolve_cross_references,
    format_cross_ref_tokens,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("theosis-mcp")

# Server icon: gold cross on purple
try:
    THEOSIS_VERSION = package_version("theosis-mcp")
except PackageNotFoundError:
    THEOSIS_VERSION = "0.9.0.dev0"

ICON_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAAtklEQVR42mNgGOmAEZtgQ9TV/7SwrGGZNiNeB9DKYnwOYcGl6MajG1S1VENOA6s4E4yxounvfw0NDZpYjm4mckgz0drnhMxmIdew5bO3M9w+twfOr5veS5Y5TAOdDUcdMOAOYCE2wWEDqkYueNVEpnpSxwHIqR3ZcmziqMBzNA1QJwqwFTLocT5aEI06YNQBow6gaUGEDUAqGk/qhwCu1iutWsY4+wW0bJYT1S+gZUgMqq7ZKAAA/oE/8EmGTpMAAAAASUVORK5CYII="
)

server = Server(
    "theosis",
    version=THEOSIS_VERSION,
    icons=[
        Icon(
            src="data:image/png;base64," + ICON_BASE64,
            mimeType="image/png",
            sizes=["32x32"],
        )
    ],
)

# Database connection
db: TheosisDB | None = None


def text(msg: str) -> list[TextContent]:
    """Wrap a string in a single-element TextContent list."""
    return [TextContent(type="text", text=msg)]


# =============================================================================
# Tool listing
# =============================================================================

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available theological research tools."""
    return TOOLS


# =============================================================================
# Tool dispatch
# =============================================================================

@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    global db

    if db is None:
        db_url = get_db_url()
        db = TheosisDB(db_url)
        await db.connect()
        logger.info(f"Connected to database at {db_url.split('@')[1] if '@' in db_url else db_url}")

    handler = _TOOL_HANDLERS.get(name)
    if not handler:
        return text(f"Unknown tool: {name}")

    try:
        return await handler(arguments)
    except Exception as e:
        logger.exception(f"Error in tool {name}")
        return text(f"Error: {str(e)}")


# =============================================================================
# Word Study
# =============================================================================

async def handle_word_study(args: dict[str, Any]) -> list[TextContent]:
    strongs = args.get("strongs")
    word = args.get("word")
    language = args.get("language", "greek")

    if strongs:
        entry = await db.get_lexicon_entry(strongs)
    elif word:
        entries = await db.search_lexicon(word, language=language, limit=1)
        entry = entries[0] if entries else None
    else:
        return text("Please provide either 'strongs' number or 'word' to study.")

    if not entry:
        return text("No entry found for the given word/Strong's number.")

    verses = await db.get_verses_with_strongs(entry["strongs"], limit=5)

    result = f"## {entry['word']} ({entry['transliteration']}, {entry['strongs']})\n\n"
    result += f"**Short Definition**: {entry.get('short_definition', 'N/A')}\n\n"

    if entry.get("full_definition"):
        result += f"**Full Definition**:\n{entry['full_definition']}\n\n"
    if entry.get("abbott_smith_def"):
        result += f"**Abbott-Smith**: {entry['abbott_smith_def']}\n\n"

    if verses:
        result += "### Example Passages\n\n"
        for v in verses:
            ref = f"{v.get('book', '')} {v.get('chapter', '')}:{v.get('verse', '')}"
            result += f"**{ref}**: {v.get('text_english', v.get('text', ''))}\n\n"

    return text(result)


# =============================================================================
# Lookup Verse
# =============================================================================

async def handle_lookup_verse(args: dict[str, Any]) -> list[TextContent]:
    reference = args.get("reference", "")
    include_original = args.get("include_original", True)
    include_morphology = args.get("include_morphology", False)

    if not reference:
        return text("Please provide a verse reference (e.g., 'John 3:16').")

    verse = await db.get_verse(reference)
    if not verse:
        return text(f"Verse not found: {reference}")

    result = f"## {reference}\n\n"
    result += f"**{verse.get('text_english', verse.get('text', ''))}**\n\n"

    if include_original and verse.get("text_greek"):
        result += f"**Greek**: {verse['text_greek']}\n\n"
    elif include_original and verse.get("text_hebrew"):
        result += f"**Hebrew**: {verse['text_hebrew']}\n\n"

    if include_morphology and verse.get("morphology"):
        result += f"**Morphology**: {verse['morphology']}\n\n"

    # Cross-reference hint
    result += (
        f"\n---\n"
        f"*Cross-references: `get_cross_references` (reference='{reference}')*\n"
        f"*Study notes: `get_study_notes` (reference='{reference}')*\n"
        f"*Compare translations: `compare_translations` (reference='{reference}', translations=['KJV', 'ESV', 'NASB'])*\n"
    )

    return text(result)


# =============================================================================
# Search Lexicon
# =============================================================================

async def handle_search_lexicon(args: dict[str, Any]) -> list[TextContent]:
    query = args.get("query", "")
    language = args.get("language")
    limit = args.get("limit", 10)

    if not query:
        return text("Please provide a search query.")

    entries = await db.search_lexicon(query, language=language, limit=limit)
    if not entries:
        return text(f"No entries found for '{query}'.")

    result = f"## Lexicon Search: '{query}'\n\n"
    for entry in entries:
        result += f"### {entry['strongs']} — {entry['word']} ({entry['transliteration']})\n"
        result += f"{entry.get('short_definition', '')}\n\n"

    return text(result)


# =============================================================================
# Cross References
# =============================================================================

async def handle_get_cross_references(args: dict[str, Any]) -> list[TextContent]:
    reference = args.get("reference")
    theme = args.get("theme")
    limit = args.get("limit", 8)

    if theme:
        refs = await db.get_thematic_references(theme)
        if not refs:
            return text(f"No cross-references found for theme '{theme}'.")
        result = f"## Cross-References: {theme}\n\n"
        for ref in refs:
            result += f"- **{ref['reference']}**: {ref.get('note', '')}\n"
        return text(result)

    if reference:
        refs = await db.get_cross_references(reference, limit=limit)
        if not refs:
            return text(f"No cross-references found for {reference}.")
        result = f"## Cross-References for {reference}\n\n"
        for ref in refs:
            target = ref.get("to_book", ref.get("target", ""))
            ch = ref.get("to_chapter", ref.get("chapter", ""))
            vs = ref.get("to_verse", ref.get("verse", ""))
            if ch and vs:
                target = f"{target} {ch}:{vs}"
            result += f"- **{target}**"
            if ref.get("vote_count"):
                result += f" (votes: {ref['vote_count']})"
            result += "\n"
        return text(result)

    return text("Please provide either 'reference' or 'theme'.")


# =============================================================================
# Lookup Name
# =============================================================================

async def handle_lookup_name(args: dict[str, Any]) -> list[TextContent]:
    name = args.get("name", "")
    name_type = args.get("type")

    if not name:
        return text("Please provide a name to look up.")

    entries = await db.lookup_name(name, name_type=name_type)
    if not entries:
        return text(f"No entries found for '{name}'.")

    result = f"## Biblical Names: {name}\n\n"
    for entry in entries:
        result += f"### {entry.get('name', '')}\n"
        if entry.get("type"):
            result += f"**Type**: {entry['type']}\n"
        if entry.get("description"):
            result += f"{entry['description']}\n"
        result += "\n---\n\n"

    return text(result)


# =============================================================================
# Parse Morphology
# =============================================================================

async def handle_parse_morphology(args: dict[str, Any]) -> list[TextContent]:
    code = args.get("code", "")
    language = args.get("language", "greek")

    if not code:
        return text("Please provide a morphology code to parse.")

    parsing = await db.get_morphology(code, language)
    if not parsing:
        return text(f"Unknown morphology code: {code}")

    result = f"## Morphology: {code}\n\n"
    result += f"**Language**: {parsing.get('language', language).title()}\n"
    result += f"**Part of Speech**: {parsing.get('part_of_speech', 'N/A')}\n"
    if parsing.get("person"): result += f"**Person**: {parsing['person']}\n"
    if parsing.get("number"): result += f"**Number**: {parsing['number']}\n"
    if parsing.get("tense"): result += f"**Tense**: {parsing['tense']}\n"
    if parsing.get("voice"): result += f"**Voice**: {parsing['voice']}\n"
    if parsing.get("mood"): result += f"**Mood**: {parsing['mood']}\n"
    if parsing.get("case_value"): result += f"**Case**: {parsing['case_value']}\n"
    if parsing.get("gender"): result += f"**Gender**: {parsing['gender']}\n"
    if parsing.get("parsing"): result += f"\n**Full Parsing**: {parsing['parsing']}\n"

    return text(result)


# =============================================================================
# Search by Strong's
# =============================================================================

async def handle_search_by_strongs(args: dict[str, Any]) -> list[TextContent]:
    strongs = args.get("strongs", "")
    limit = args.get("limit", 20)

    if not strongs:
        return text("Please provide a Strong's number.")

    entry = await db.get_lexicon_entry(strongs)
    if not entry:
        return text(f"Unknown Strong's number: {strongs}")

    verses = await db.get_verses_with_strongs(strongs, limit=limit)
    result = f"## {strongs} — {entry['word']} ({entry['transliteration']})\n\n"
    result += f"*{entry.get('short_definition', '')}*\n\n"

    if verses:
        for v in verses:
            ref = f"{v.get('book', '')} {v.get('chapter', '')}:{v.get('verse', '')}"
            result += f"**{ref}**: {v.get('text_english', v.get('text', ''))}\n\n"
    else:
        result += "No verses found with this Strong's number.\n"

    return text(result)


# =============================================================================
# Find Similar Passages
# =============================================================================

async def handle_find_similar_passages(args: dict[str, Any]) -> list[TextContent]:
    reference = args.get("reference", "")
    limit = args.get("limit", 10)

    if not reference:
        return text("Please provide a verse reference.")

    if not db._vector_available:
        return text("Vector search is not available. Ensure pgvector extension is installed.")

    if not await db.has_vector_tables():
        return text("Vector embeddings have not been generated yet. Run the embedding generation script.")

    passages = await db.find_similar_passages(reference, limit=limit)
    if not passages:
        return text(f"No similar passages found for {reference}.")

    result = f"## Similar Passages to {reference}\n\n"
    result += "*⚠️ Semantic similarity ≠ theological connection. Always verify context.*\n\n"
    for p in passages:
        ref = f"{p.get('book', '')} {p.get('chapter', '')}:{p.get('verse', '')}"
        sim = p.get("similarity", 0)
        result += f"### {ref} ({(sim * 100):.1f}%)\n{p.get('text', '')}\n\n"

    return text(result)


# =============================================================================
# Explore Genealogy
# =============================================================================

async def handle_explore_genealogy(args: dict[str, Any]) -> list[TextContent]:
    name = args.get("name", "")
    direction = args.get("direction", "ancestors")

    if not name:
        return text("Please provide a person name.")

    genealogy = await db.get_genealogy(name, direction=direction)
    if not genealogy:
        return text(f"No genealogy data found for '{name}'.")

    result = f"## Genealogy: {name} ({direction})\n\n"
    for g in genealogy:
        result += f"- {g.get('person_name', '')} → {g.get('related_name', '')}"
        if g.get("relationship"):
            result += f" ({g['relationship']})"
        result += "\n"

    return text(result)


# =============================================================================
# Explore Places
# =============================================================================

async def handle_explore_places(args: dict[str, Any]) -> list[TextContent]:
    name = args.get("name")
    feature_type = args.get("feature_type")

    if name:
        places = await db.explore_places(name=name)
        if not places:
            return text(f"No places found matching '{name}'.")
        result = f"## Places matching '{name}'\n\n"
        for p in places:
            result += f"### {p['name']} ({p['feature_type']})\n"
            if p.get("latitude") and p.get("longitude"):
                result += f"📍 {p['latitude']}, {p['longitude']}\n"
            refs = p.get("verse_refs", [])
            if refs:
                result += f"**Verses**: {', '.join(refs[:10])}"
                if len(refs) > 10:
                    result += f" (+{len(refs)-10} more)"
                result += "\n"
            result += "\n---\n\n"
        return text(result)

    elif feature_type:
        places = await db.explore_places(feature_type=feature_type)
        if not places:
            return text(f"No places found with type '{feature_type}'.")
        result = f"## Places: {feature_type}\n\n"
        for p in places:
            result += f"- **{p['name']}**"
            refs = p.get("verse_refs", [])
            if refs:
                result += f" — {', '.join(refs[:5])}"
            result += "\n"
        return text(result)

    else:
        types = await db.explore_places()
        if not types:
            return text("No place data available.")
        result = "## Biblical Places\n\n"
        result += "| Type | Count |\n|---|---|\n"
        for t in types:
            result += f"| {t['feature_type']} | {t['count']} |\n"
        result += "\nUse `explore_places` with a `name` or `feature_type` to explore."
        return text(result)


# =============================================================================
# Explore Events
# =============================================================================

async def handle_explore_events(args: dict[str, Any]) -> list[TextContent]:
    name = args.get("name")

    events = await db.explore_events(name=name)
    if not events:
        return text(f"No events found" + (f" matching '{name}'" if name else "") + ".")

    if name:
        result = f"## Events matching '{name}'\n\n"
    else:
        result = "## Biblical Events (Chronological)\n\n"

    for e in events:
        year = e.get("start_year", "")
        year_str = f"{abs(year)} {'BCE' if year < 0 else 'CE'}" if year else "unknown"
        result += f"### {e['title']} ({year_str})\n"
        if e.get("duration"):
            result += f"*Duration: {e['duration']}*\n"
        
        participants = e.get("participants", [])
        if participants:
            result += f"**Participants**: {', '.join(participants)}\n"
        
        locations = e.get("locations", [])
        if locations:
            result += f"**Locations**: {', '.join(locations)}\n"
        
        result += "\n---\n\n"

    return text(result)


# =============================================================================
# Study Notes
# =============================================================================

async def handle_get_study_notes(args: dict[str, Any]) -> list[TextContent]:
    reference = args.get("reference", "")
    limit = args.get("limit", 10)

    if not reference:
        return text("Please provide a Bible reference.")

    notes = await db.get_study_notes(reference, limit=limit)
    if not notes:
        return text(f"No study notes found for {reference}.")

    result = f"## Study Notes: {reference}\n\n"
    for note in notes:
        result += f"### {note.get('title', note.get('content_type', 'Note'))}\n"
        result += f"{note.get('content', note.get('body', ''))}\n\n"
        result += "---\n\n"

    return text(result)


# =============================================================================
# Dictionary Article
# =============================================================================

async def handle_get_dictionary_article(args: dict[str, Any]) -> list[TextContent]:
    topic = args.get("topic", "")
    if not topic:
        return text("Please provide a topic name.")

    article = await db.get_dictionary_article(topic)
    if not article:
        return text(f"No dictionary article found for '{topic}'.")

    result = f"## {article.get('title', topic)}\n\n"
    result += f"{article.get('content', article.get('body', ''))}\n"
    return text(result)


# =============================================================================
# ANE Context
# =============================================================================

def _parse_json_list_field(value: Any) -> list[str]:
    """Safely parse a JSON-encoded text list field into a Python list."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if not isinstance(value, str):
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else [value]
    except (json.JSONDecodeError, TypeError):
        return [value] if value.strip() else []


async def handle_get_ane_context(args: dict[str, Any]) -> list[TextContent]:
    reference = args.get("reference", "")
    if not reference:
        return text("Please provide a Bible reference.")

    entries = await db.get_ane_context(reference)
    if not entries:
        return text(f"No ANE context data found for {reference}.")

    result = f"## Ancient Near East Context: {reference}\n\n"
    for entry in entries:
        dim_label = entry.get("dimension_label") or entry.get("dimension", "")
        period_label = entry.get("period_label") or entry.get("period", "")
        result += f"### {dim_label} — {period_label}\n"
        result += f"**Title**: {entry.get('title', '')}\n\n"

        if entry.get("summary"):
            result += f"**Summary**: {entry['summary']}\n\n"
        if entry.get("detail"):
            result += f"**Detail**: {entry['detail']}\n\n"

        ane_parallels = _parse_json_list_field(entry.get("ane_parallels"))
        if ane_parallels:
            result += "**ANE Parallels**:\n"
            for p in ane_parallels:
                result += f"- {p}\n"
            result += "\n"

        if entry.get("interpretive_significance"):
            result += f"**Interpretive Significance**: {entry['interpretive_significance']}\n\n"

        key_refs = _parse_json_list_field(entry.get("key_references"))
        if key_refs:
            result += f"**Key References**: {', '.join(key_refs)}\n\n"

        scholarly = _parse_json_list_field(entry.get("scholarly_sources"))
        if scholarly:
            result += f"**Scholarly Sources**: {', '.join(scholarly)}\n\n"

        result += "---\n\n"

    return text(result)


# =============================================================================
# Theology Context
# =============================================================================

async def handle_get_theology_context(args: dict[str, Any]) -> list[TextContent]:
    reference = args.get("reference", "")
    if not reference:
        return text("Please provide a Bible reference.")

    entries = await db.get_theology_context(reference)
    if not entries:
        return text(f"No theological context data found for {reference}.")

    result = f"## Theological Context: {reference}\n\n"
    for entry in entries:
        result += f"### {entry.get('theme_slug', '')}\n"
        if entry.get("description"):
            result += f"{entry['description']}\n\n"

    return text(result)


# =============================================================================
# NEW: List Translations
# =============================================================================

async def handle_list_translations(args: dict[str, Any]) -> list[TextContent]:
    translations = await db.list_translations()
    if not translations:
        return text("No translations found in the database. Import translations first.")

    result = "## Available Translations\n\n"
    for t in translations:
        result += f"- **{t['abbreviation']}** — {t['name']} ({t.get('language', '')}, {t.get('year', '')})"
        result += f" — {t.get('coverage_type', 'unknown')} coverage; {t.get('book_count', 0)} books; {t.get('verse_count', t.get('live_verse_count', 0)):,} verses"
        if t.get("license"):
            result += f" [{t['license']}]"
        if t.get("source_url"):
            result += f"; source={t['source_url']}"
        result += "\n"

    result += f"\n{len(translations)} translations available.\n"
    return text(result)


# =============================================================================
# NEW: Get Translation Verse
# =============================================================================

async def handle_get_translation_verse(args: dict[str, Any]) -> list[TextContent]:
    reference = args.get("reference", "")
    translation = args.get("translation", "KJV")

    if not reference:
        return text("Please provide a Bible reference.")

    verse = await db.get_translation_verse(reference, translation)
    if not verse:
        return text(f"Verse not found: {reference} in {translation}")

    tname = verse.get("translation_name", translation)
    result = f"## {reference} ({tname})\n\n"
    result += f"**{verse.get('text', '')}**\n"
    return text(result)


# =============================================================================
# NEW: Compare Translations
# =============================================================================

async def handle_compare_translations(args: dict[str, Any]) -> list[TextContent]:
    reference = args.get("reference", "")
    translations = args.get("translations", [])

    if not reference or not translations:
        return text("Please provide both 'reference' and 'translations' list.")

    results = await db.compare_translations(reference, translations)
    if not results:
        return text(f"No translations found for {reference}.")

    result = f"## Translation Comparison: {reference}\n\n"
    for t in results:
        result += f"### {t['translation_name']} ({t['abbreviation']})\n"
        result += f"{t.get('text', '')}\n\n"

    return text(result)


# =============================================================================
# NEW: Search Bible Fulltext
# =============================================================================

async def handle_search_bible_fulltext(args: dict[str, Any]) -> list[TextContent]:
    query = args.get("query", "")
    translation = args.get("translation")
    limit = args.get("limit", 20)

    if not query:
        return text("Please provide a search query.")

    results = await db.search_bible_fulltext(query, translation_abbrev=translation, limit=limit)
    if not results:
        return text(f"No results found for '{query}'.")

    result = f"## Bible Search: '{query}'\n\n"
    for r in results:
        ref = f"{r.get('book_name', r.get('book', ''))} {r.get('chapter', '')}:{r.get('verse', '')}"
        result += f"### {ref} ({r.get('abbreviation', '')})\n"
        result += f"{r.get('snippet', r.get('text', ''))}\n\n"

    return text(result)


# =============================================================================
# NEW: List Extra-Biblical Categories
# =============================================================================

async def handle_list_extra_biblical_categories(args: dict[str, Any]) -> list[TextContent]:
    categories = await db.list_extra_biblical_categories()
    if not categories:
        return text("No extra-biblical texts found in the database.")

    result = "## Extra-Biblical Library\n\n"
    result += "| Category | Texts |\n|----------|-------|\n"
    for c in categories:
        result += f"| {c['category']} | {c['count']} |\n"

    result += f"\n*Use `search_extra_biblical` to search, or `get_extra_biblical_text` to read.*\n"
    return text(result)


# =============================================================================
# NEW: Search Extra-Biblical
# =============================================================================

async def handle_search_extra_biblical(args: dict[str, Any]) -> list[TextContent]:
    query = args.get("query", "")
    category = args.get("category")
    limit = args.get("limit", 20)

    if not query:
        return text("Please provide a search query.")

    results = await db.search_extra_biblical(query, category=category, limit=limit)
    if not results:
        return text(f"No results found for '{query}' in extra-biblical texts.")

    result = f"## Extra-Biblical Search: '{query}'\n\n"
    for r in results:
        result += f"### {r['title']}"
        if r.get("author"):
            result += f" by {r['author']}"
        result += f" ({r.get('category', '')})\n"
        result += f"{r.get('snippet', '')}\n\n"

    return text(result)


# =============================================================================
# NEW: Get Extra-Biblical Text
# =============================================================================

async def handle_get_extra_biblical_text(args: dict[str, Any]) -> list[TextContent]:
    title = args.get("title", "")
    section = args.get("section")

    if not title:
        return text("Please provide a text title.")

    text_data = await db.get_extra_biblical_text(title, section=section)
    if not text_data and section:
        text_data = await db.get_extra_biblical_text(title, section=None)
    if not text_data:
        return text(f"Text not found: '{title}'")

    result = f"## {text_data['title']}\n"
    if text_data.get("author"):
        result += f"**Author**: {text_data['author']}\n"
    if text_data.get("category"):
        result += f"**Category**: {text_data['category']}\n"
    if text_data.get("section"):
        result += f"**Section**: {text_data['section']}\n"
    result += f"\n{text_data.get('text', '')}\n"

    return text(result)


# =============================================================================
# NEW: Reading Plan
# =============================================================================

async def handle_get_reading_plan(args: dict[str, Any]) -> list[TextContent]:
    plan_type = args.get("plan_type", "")
    book = args.get("book")
    testament = args.get("testament")
    days = args.get("days")

    if not plan_type:
        return text("Please provide a plan_type.")

    # Set default days based on plan type
    if days is None:
        if plan_type == "book":
            days = 30
        elif plan_type == "testament":
            days = 90
        elif plan_type == "whole_bible":
            days = 365
        elif plan_type == "nt_challenge":
            days = 90
        else:
            days = 30

    # Select books for the plan
    if plan_type == "book" and book:
        abbrev = BOOK_ABBREV_MAP.get(book.lower(), book)
        selected_books = [abbrev]
    elif plan_type == "testament" and testament:
        if testament.upper() == "OT":
            selected_books = [b for b in BOOK_ORDER if b in BOOK_ORDER[:39]]
        else:
            selected_books = [b for b in BOOK_ORDER if b in BOOK_ORDER[39:]]
    elif plan_type == "whole_bible":
        selected_books = BOOK_ORDER
    elif plan_type == "nt_challenge":
        selected_books = [b for b in BOOK_ORDER if b in BOOK_ORDER[39:]]
    else:
        return text("Please provide more details for this plan type.")

    result = f"## {plan_type.replace('_', ' ').title()} Reading Plan ({days} days)\n\n"
    result += f"Books: {', '.join(selected_books)}\n\n"
    result += f"*This is a structural plan. Use `lookup_verse` to read each day's passages.*\n"
    result += f"*Estimated: {len(selected_books)} books over {days} days*\n"

    return text(result)


# =============================================================================
# Systematic theology handlers
# =============================================================================

async def handle_list_theological_works(args: dict[str, Any]) -> list[TextContent]:
    author = args.get("author")
    limit = args.get("limit", 100)
    works = await db.list_theological_works(author=author, limit=limit)
    if not works:
        return text("No systematic theology works found.")

    result = "## Systematic Theology Works\n\n"
    result += "| Author | Work | Sections | Source |\n|---|---|---:|---|\n"
    for work in works:
        source = work.get("source_url") or ""
        result += f"| {work.get('author', '')} | {work.get('work_title', '')} | {work.get('section_count', 0)} | {source} |\n"
    result += f"\n{len(works)} work/author entries shown.\n"
    return text(result)


async def handle_search_theological_works(args: dict[str, Any]) -> list[TextContent]:
    query = args.get("query", "")
    author = args.get("author")
    limit = args.get("limit", 10)
    if not query:
        return text("Please provide a theological search query.")

    results = await db.search_theological_works(query, author=author, limit=limit)
    if not results:
        return text(f"No systematic theology sections found for '{query}'.")

    result = f"## Systematic Theology Search: {query}\n\n"
    for item in results:
        result += f"### {item.get('work_title', '')} — {item.get('author', '')}\n"
        structure = " — ".join(str(item.get(k) or "") for k in ("volume", "part", "chapter", "section"))
        result += f"*{structure.strip(' — ')}*\n\n"
        result += f"{item.get('snippet', '')}\n\n"
        if item.get("source_url"):
            result += f"Source: {item['source_url']}\n\n"
        result += "---\n\n"
    return text(result)


async def handle_get_theological_section(args: dict[str, Any]) -> list[TextContent]:
    work_title = args.get("work_title", "")
    if not work_title:
        return text("Please provide a theological work title.")
    sections = await db.get_theological_sections(
        work_title=work_title,
        author=args.get("author"),
        chapter=args.get("chapter"),
        section=args.get("section"),
        limit=args.get("limit", 5),
    )
    if not sections:
        return text(f"No sections found for '{work_title}'.")

    result = f"## {work_title}\n\n"
    for item in sections:
        result += f"### {item.get('author', '')}"
        if item.get("volume"):
            result += f" — {item['volume']}"
        result += "\n"
        for key in ("part", "chapter", "section"):
            if item.get(key):
                result += f"**{key.title()}**: {item[key]}\n"
        if item.get("source_url"):
            result += f"**Source**: {item['source_url']}\n"
        result += "\n" + _truncate(item.get("text", ""), 14000) + "\n\n---\n\n"
    return text(result)


# =============================================================================
# Tool handler dispatch table
# =============================================================================


# =============================================================================
# Commentary handlers
# =============================================================================

async def handle_get_commentary(args: dict[str, Any]) -> list[TextContent]:
    reference = args.get("reference", "")
    author = args.get("author")
    limit = args.get("limit", 10)

    if not reference:
        return text("Please provide a Bible reference (e.g., 'John 3:16').")

    entries = await db.get_commentary(reference, author=author, limit=limit)
    if not entries:
        msg = f"No commentaries found for {reference}"
        if author:
            msg += f" by {author}"
        return text(msg + ".")

    result = f"## Commentaries on {reference}\n"
    if author:
        result += f"*(Filtered by: {author})*\n"
    result += "\n"

    for entry in entries:
        author_name = entry["author"]
        year = entry.get("author_year")
        cat = entry.get("author_category", "")
        src = entry.get("source_title", "")
        quote = entry.get("quote", "")

        result += f"### {author_name}"
        if year:
            result += f" (c. {year})"
        if cat:
            result += f" — *{cat}*"
        result += "\n"

        if src:
            result += f"> *{src}*\n\n"
        result += f"{quote}\n\n"
        result += "---\n\n"

    return text(result)


async def handle_list_commentary_authors(args: dict[str, Any]) -> list[TextContent]:
    authors = await db.list_commentary_authors()
    if not authors:
        return text("No commentary authors found. Import commentaries first.")

    result = "## Commentary Authors\n\n"
    result += "| Author | Era | Tradition | Entries |\n"
    result += "|---|---|---|---|\n"
    for a in authors:
        name = a["author"]
        year = a.get("earliest_year", "")
        cat = a.get("author_category", "")
        count = a["entry_count"]
        result += f"| {name} | {year} | {cat} | {count:,} |\n"

    result += f"\n{authors.__len__()} authors (showing top 100).\n"
    return text(result)


# =============================================================================
# Textual Variants & Manuscript Witnesses handlers
# =============================================================================

async def handle_get_textual_variants(args: dict[str, Any]) -> list[TextContent]:
    reference = args.get("reference", "")
    limit = args.get("limit", 20)
    if not reference:
        return text("Please provide a Bible reference (e.g., 'John 3:16').")
    variants = await db.get_textual_variants(reference, limit=limit)
    if not variants:
        return text(f"No textual variants found for {reference}.")
    result = f"## Textual Variants: {reference}\n\n"
    for v in variants:
        ref = v.get("reference", reference)
        result += f"### Variant #{v['id']} ({ref})\n"
        result += f"**Source**: {v.get('variant_source', '')}\n"
        result += f"**Base (MT)**: {v.get('mt_reading', '')}\n"
        if v.get("mt_hebrew"):
            result += f"**Hebrew**: {v['mt_hebrew']}\n"
        result += f"**Variant**: {v.get('variant_reading', '')}\n"
        if v.get("variant_original"):
            result += f"**Original**: {v['variant_original']}\n"
        if v.get("variant_significance"):
            result += f"**Significance**: {v['variant_significance']}\n"
        if v.get("scholarly_consensus"):
            result += f"**Consensus**: {v['scholarly_consensus']}\n"
        if v.get("heiser_analysis"):
            result += f"**Heiser Analysis**: {v['heiser_analysis']}\n"
        witnesses = v.get("witnesses") or []
        if isinstance(witnesses, str):
            try:
                witnesses = json.loads(witnesses)
            except json.JSONDecodeError:
                witnesses = []
        if witnesses and all(isinstance(w, str) for w in witnesses):
            parsed = []
            for item in witnesses:
                try:
                    value = json.loads(item)
                except json.JSONDecodeError:
                    continue
                if isinstance(value, dict):
                    parsed.append(value)
            witnesses = parsed
        if witnesses:
            base_w = [w["manuscript"] for w in witnesses if isinstance(w, dict) and w.get("reading_support") == "base"]
            var_w = [w["manuscript"] for w in witnesses if isinstance(w, dict) and w.get("reading_support") == "variant"]
            if base_w:
                result += f"**Base support**: {', '.join(base_w)}\n"
            if var_w:
                result += f"**Variant support**: {', '.join(var_w)}\n"
        result += "\n---\n\n"
    return text(result)


async def handle_list_manuscript_witnesses(args: dict[str, Any]) -> list[TextContent]:
    reference = args.get("reference")
    variant_id = args.get("variant_id")
    limit = args.get("limit", 50)
    witnesses = await db.list_manuscript_witnesses(
        reference=reference, variant_id=variant_id, limit=limit
    )
    if not witnesses:
        msg = "No manuscript witnesses found"
        if reference:
            msg += f" for {reference}"
        if variant_id:
            msg += f" for variant #{variant_id}"
        return text(msg + ".")
    header = "## Manuscript Witnesses\n\n"
    if reference:
        header = f"## Manuscript Witnesses: {reference}\n\n"
    elif variant_id:
        header = f"## Manuscript Witnesses: Variant #{variant_id}\n\n"
    result = header
    for w in witnesses:
        ref = f"{w.get('book', '')} {w.get('chapter', '')}:{w.get('verse', '')}"
        result += f"- **{w['manuscript']}** — {ref} ({w.get('reading_support', 'unknown')})"
        if w.get("manuscript_date"):
            result += f" [{w['manuscript_date']}]"
        result += "\n"
    result += f"\n{len(witnesses)} witness(es).\n"
    return text(result)


async def handle_compare_variant_readings(args: dict[str, Any]) -> list[TextContent]:
    reference = args.get("reference", "")
    limit = args.get("limit", 20)
    if not reference:
        return text("Please provide a Bible reference (e.g., 'John 3:16').")
    variants = await db.compare_variant_readings(reference, limit=limit)
    if not variants:
        return text(f"No variant readings found for {reference}.")
    result = f"## Variant Readings Comparison: {reference}\n\n"
    for v in variants:
        result += f"### {v.get('variant_source', 'Unknown source')} (#{v['id']})\n"
        result += f"**MT/Base**: {v.get('mt_reading', '')}\n"
        if v.get("mt_hebrew"):
            result += f"**Hebrew**: {v['mt_hebrew']}\n"
        result += f"**Variant**: {v.get('variant_reading', '')}\n"
        if v.get("variant_original"):
            result += f"**Original**: {v['variant_original']}\n"
        if v.get("variant_significance"):
            result += f"**Significance**: {v['variant_significance']}\n"
        if v.get("scholarly_consensus"):
            result += f"**Consensus**: {v['scholarly_consensus']}\n"
        if v.get("preferred_for_hlt"):
            result += f"**Preferred (HLT)**: {v['preferred_for_hlt']}\n"
        if v.get("hlt_rationale"):
            result += f"**HLT Rationale**: {v['hlt_rationale']}\n"
        base = v.get("base_support", [])
        var = v.get("variant_support", [])
        if base:
            result += f"**Base witnesses**: {', '.join(base)}\n"
        if var:
            result += f"**Variant witnesses**: {', '.join(var)}\n"
        result += "\n---\n\n"
    return text(result)


# =============================================================================
# Literary Structure Corpus handlers
# =============================================================================

LIT_STRUCT_ATTRIBUTION = (
    "Source: Hajime Murai, \"Literary Structure of the Bible\" "
    "(CC BY 4.0)\n"
    "http://www.bible.literarystructure.info/bible/bible_e.html\n\n"
    "⚠️ DISCLAIMER: These structures are scholarly interpretive proposals, "
    "not canonical or doctrinal divisions. They reflect one analyst's "
    "literary reading of the biblical text and should be treated as "
    "study aids, not authoritative chapter/verse divisions."
)


async def handle_list_literary_structure_sources(args: dict[str, Any]) -> list[TextContent]:
    limit = args.get("limit", 50)
    async with db.pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT source_id, source_type, licence, url, attribution,
                   workbook_name, worksheet_name, version_hint, imported_at
            FROM public.literary_structure_sources
            ORDER BY source_id, worksheet_name
            LIMIT $1
            """,
            limit,
        )
    if not rows:
        return text("No literary structure sources imported yet.\n\n" + LIT_STRUCT_ATTRIBUTION)

    result = "## Literary Structure Sources\n\n"
    result += LIT_STRUCT_ATTRIBUTION + "\n\n"
    result += "| Source ID | Type | Worksheet | Licence | Imported |\n"
    result += "|-----------|------|-----------|---------|----------|\n"
    for r in rows:
        imported = r["imported_at"].strftime("%Y-%m-%d") if r["imported_at"] else ""
        result += f"| {r['source_id']} | {r['source_type']} | {r['worksheet_name']} | {r['licence']} | {imported} |\n"
    result += f"\n{len(rows)} source(s).\n"
    return text(result)


async def handle_list_literary_structures(args: dict[str, Any]) -> list[TextContent]:
    book = args.get("book", "")
    if not book:
        return text("Please provide a 'book' OSIS code (e.g., 'Gen', 'Mat').")
    source_id = args.get("source_id")
    limit = args.get("limit", 200)
    params: list[Any] = [book, limit]
    sql = """
        SELECT id, source_id, book, structure_label, is_header,
               depth, raw_reference, start_chapter, start_verse,
               end_chapter, end_verse, description_ja, description_en,
               transliteration, cross_references
        FROM public.literary_structures
        WHERE book = $1
    """
    if source_id:
        sql += " AND source_id = $3"
        params = [book, limit, source_id]
    sql += " ORDER BY excel_row LIMIT $2"
    async with db.pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)
    if not rows:
        return text(f"No literary structures found for {book}.")

    result = f"## Literary Structures: {book}\n\n"
    result += LIT_STRUCT_ATTRIBUTION + "\n\n"
    for r in rows:
        label = r["structure_label"] or ""
        hdr = " [header]" if r["is_header"] else ""
        result += f"### {label}{hdr} (ID: {r['id']})\n"
        result += f"**Source**: {r['source_id']}\n"
        ref = r["raw_reference"] or ""
        if r["start_chapter"]:
            ref = f"{r['start_chapter']}:{r['start_verse']}" if r["start_verse"] else str(r["start_chapter"])
            if r["end_chapter"] and r["end_chapter"] != r["start_chapter"]:
                ref += f"-{r['end_chapter']}:{r['end_verse']}"
            elif r["end_verse"]:
                ref += f"-{r['end_verse']}"
        if ref:
            result += f"**Reference**: {book} {ref}\n"
        if r["description_en"]:
            result += f"**English**: {r['description_en']}\n"
        if r["description_ja"]:
            result += f"**Japanese**: {r['description_ja']}\n"
        if r["transliteration"]:
            result += f"**Transliteration**: {r['transliteration']}\n"
        result += "\n---\n\n"
    if len(rows) == limit:
        result += f"\n*Showing {limit} results (use a narrower filter or higher limit).*\n"
    return text(result)


async def handle_get_literary_structure(args: dict[str, Any]) -> list[TextContent]:
    sid = args.get("id")
    if not sid:
        return text("Please provide a structure 'id'.")
    include_links = args.get("include_links", True)
    async with db.pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, source_id, book, structure_label, is_header,
                   parent_label, unit_sequence, depth, raw_reference,
                   start_chapter, start_verse, start_suffix,
                   end_chapter, end_verse, end_suffix,
                   description_ja, description_en, transliteration,
                   cross_references, workbook_name, worksheet_name, excel_row
            FROM public.literary_structures
            WHERE id = $1
            """,
            sid,
        )
        links: list = []
        if include_links and row:
            links = await conn.fetch(
                """
                SELECT target_passage, link_type
                FROM public.literary_structure_links
                WHERE structure_id = $1
                ORDER BY target_passage
                """,
                sid,
            )
    if not row:
        return text(f"Structure ID {sid} not found.")

    result = f"## Literary Structure #{row['id']}\n\n"
    result += LIT_STRUCT_ATTRIBUTION + "\n\n"
    result += f"**Book**: {row['book']}\n"
    result += f"**Label**: {row['structure_label']}\n"
    result += f"**Source**: {row['source_id']}\n"
    if row["is_header"]:
        result += "**Header**: Yes\n"
    if row["depth"]:
        result += f"**Depth**: {row['depth']}\n"
    if row["raw_reference"]:
        result += f"**Raw Reference**: {row['raw_reference']}\n"
    if row["description_en"]:
        result += f"**English**: {row['description_en']}\n"
    if row["description_ja"]:
        result += f"**Japanese**: {row['description_ja']}\n"
    if row["transliteration"]:
        result += f"**Transliteration**: {row['transliteration']}\n"
    if row["cross_references"]:
        result += f"**Cross-references**: {row['cross_references']}\n"
    if row["workbook_name"]:
        result += f"**Workbook**: {row['workbook_name']} / {row['worksheet_name']}\n"
    if row["excel_row"]:
        result += f"**Excel row**: {row['excel_row']}\n"

    if include_links and links:
        result += "\n**Cross-reference links**:\n"
        for link in links:
            result += f"- {link['target_passage']} ({link['link_type']})\n"

    return text(result)


async def handle_search_literary_structures(args: dict[str, Any]) -> list[TextContent]:
    query = args.get("query", "")
    if not query:
        return text("Please provide a 'query' to search.")
    book = args.get("book")
    limit = args.get("limit", 20)

    # Build a tsvector search across description_ja, description_en, transliteration
    # Use plainto_tsquery for safe full-text search
    params: list[Any] = [query, limit]
    sql = """
        SELECT id, source_id, book, structure_label, description_en,
               description_ja, transliteration, raw_reference,
               ts_rank_cd(
                   to_tsvector('simple', coalesce(description_en,'') || ' ' || coalesce(description_ja,'') || ' ' || coalesce(transliteration,'') || ' ' || coalesce(structure_label,'')),
                   plainto_tsquery('simple', $1)
               ) AS rank
        FROM public.literary_structures
        WHERE to_tsvector('simple', coalesce(description_en,'') || ' ' || coalesce(description_ja,'') || ' ' || coalesce(transliteration,'') || ' ' || coalesce(structure_label,''))
              @@ plainto_tsquery('simple', $1)
    """
    if book:
        sql += " AND book = $3"
        params = [query, limit, book]
    sql += " ORDER BY rank DESC, book LIMIT $2"
    async with db.pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)
    if not rows:
        return text(f"No literary structures found matching '{query}'.")

    result = f"## Literary Structure Search: '{query}'\n\n"
    result += LIT_STRUCT_ATTRIBUTION + "\n\n"
    for r in rows:
        label = r["structure_label"] or ""
        result += f"### {r['book']} — {label} (ID: {r['id']})\n"
        result += f"**Source**: {r['source_id']}\n"
        if r["description_en"]:
            result += f"**English**: {r['description_en'][:200]}\n"
        if r["description_ja"]:
            result += f"**Japanese**: {r['description_ja'][:100]}\n"
        if r["transliteration"]:
            result += f"**Translit**: {r['transliteration'][:100]}\n"
        result += "\n---\n\n"
    if len(rows) == limit:
        result += f"\n*Showing top {limit} results.*\n"
    return text(result)


async def handle_get_literary_parallel(args: dict[str, Any]) -> list[TextContent]:
    book = args.get("book", "")
    if not book:
        return text("Please provide a 'book' OSIS code.")
    limit = args.get("limit", 20)
    async with db.pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, source_id, book, structure_label, description_en,
                   cross_references, raw_reference
            FROM public.literary_structures
            WHERE book = $1
              AND cross_references IS NOT NULL
              AND cross_references != ''
            ORDER BY excel_row
            LIMIT $2
            """,
            book, limit,
        )
    if not rows:
        return text(f"No literary structures with cross-references found for {book}.")

    # Collect unique target book codes from cross-references to pre-fetch
    # pericope headers for resolution.
    target_books: set[str] = set()
    for r in rows:
        cr = r["cross_references"] or ""
        for piece in cr.split(","):
            piece = piece.strip()
            if not piece:
                continue
            m = re.match(r"^\d+_([A-Za-z]+)@\d+", piece)
            if m:
                book_name = m.group(1).lower()
                from .database import BOOK_ABBREV_MAP as _BAM
                code = _BAM.get(book_name)
                if code:
                    target_books.add(code)

    # Pre-fetch pericope headers for all target books
    pericope_rows: list[dict] = []
    if target_books:
        async with db.pool.acquire() as conn:
            for tb in sorted(target_books):
                fetched = await conn.fetch(
                    """
                    SELECT id, source_id, book, structure_label, is_header,
                           description_ja, description_en
                    FROM public.literary_structures
                    WHERE book = $1 AND is_header = TRUE
                    ORDER BY excel_row
                    """,
                    tb,
                )
                pericope_rows.extend(dict(r) for r in fetched)

    result = f"## Literary Parallels for {book}\n\n"
    result += LIT_STRUCT_ATTRIBUTION + "\n\n"
    for r in rows:
        result += f"### {r['structure_label']} (ID: {r['id']})\n"
        if r["description_en"]:
            result += f"**Description**: {r['description_en'][:300]}\n"
        result += f"**Cross-references**: {r['cross_references']}\n"

        # Resolve cross-reference tokens to readable labels
        tokens = resolve_cross_references(r["cross_references"], pericope_rows)
        if tokens:
            result += "\n**Resolved parallels**:\n"
            for line in format_cross_ref_tokens(tokens):
                result += f"  {line}\n"

        result += "\n---\n\n"
    return text(result)


async def handle_get_literary_structure_by_reference(args: dict[str, Any]) -> list[TextContent]:
    """Look up literary structures by Bible reference (e.g. 'Gen 1:1')."""
    reference = args.get("reference", "")
    if not reference:
        return text("Please provide a 'reference' (e.g., 'Gen 1:1', 'Genesis 1:1-31').")

    source_id = args.get("source_id")
    limit = args.get("limit", 50)

    # Parse book from reference
    query_book, ref_part = normalize_book(reference)
    query_parts = parse_ref_parts(ref_part)

    # Fetch the complete book/source slice before overlap filtering. Applying
    # LIMIT in SQL first could hide matching rows later in the workbook.
    params: list[Any] = []
    sql = """
        SELECT id, source_id, book, structure_label, is_header,
               parent_label, unit_sequence, depth, raw_reference,
               start_chapter, start_verse, end_chapter, end_verse,
               description_ja, description_en, transliteration,
               cross_references, excel_row
        FROM public.literary_structures
        WHERE 1 = 1
    """
    if query_book:
        params.append(query_book)
        sql += f" AND book = ${len(params)}"
    if source_id:
        params.append(source_id)
        sql += f" AND source_id = ${len(params)}"
    sql += " ORDER BY excel_row"

    async with db.pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)

    if not rows:
        return text(f"No structures found for '{reference}'.\n\n" + LIT_STRUCT_ATTRIBUTION)

    # Filter by reference overlap (offline Python filter)
    row_dicts = [dict(r) for r in rows]
    matched = [r for r in row_dicts if reference_overlaps(r, query_book, query_parts)][:limit]

    if not matched:
        return text(f"No structures matching reference '{reference}' found.\n\n" + LIT_STRUCT_ATTRIBUTION)

    result = format_structure_result(matched, reference, output_mode="flat")
    return text(result)


async def handle_get_literary_tree(args: dict[str, Any]) -> list[TextContent]:
    """Render literary structures for a book as a nested tree."""
    book = args.get("book", "")
    if not book:
        return text("Please provide a 'book' OSIS code (e.g., 'Gen', 'Mat').")

    source_id = args.get("source_id")
    limit = args.get("limit", 500)

    params: list[Any] = [book]
    sql = """
        SELECT id, source_id, book, structure_label, is_header,
               parent_label, unit_sequence, depth, raw_reference,
               start_chapter, start_verse, end_chapter, end_verse,
               description_ja, description_en, transliteration,
               cross_references, excel_row
        FROM public.literary_structures
        WHERE book = $1
    """
    if source_id:
        params.append(source_id)
        sql += f" AND source_id = ${len(params)}"
    sql += " ORDER BY excel_row LIMIT $" + str(len(params) + 1)
    params.append(limit)

    async with db.pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)

    if not rows:
        return text(f"No literary structures found for {book}.")

    row_dicts = [dict(r) for r in rows]
    tree_text = render_structure_tree(row_dicts)
    return text(tree_text)


_TOOL_HANDLERS = {
    "word_study": handle_word_study,
    "lookup_verse": handle_lookup_verse,
    "search_lexicon": handle_search_lexicon,
    "get_cross_references": handle_get_cross_references,
    "lookup_name": handle_lookup_name,
    "parse_morphology": handle_parse_morphology,
    "search_by_strongs": handle_search_by_strongs,
    "find_similar_passages": handle_find_similar_passages,
    "explore_genealogy": handle_explore_genealogy,
    "explore_places": handle_explore_places,
    "explore_events": handle_explore_events,
    "get_study_notes": handle_get_study_notes,
    "get_dictionary_article": handle_get_dictionary_article,
    "get_ane_context": handle_get_ane_context,
    "get_theology_context": handle_get_theology_context,
    # New theosis tools
    "list_translations": handle_list_translations,
    "get_translation_verse": handle_get_translation_verse,
    "compare_translations": handle_compare_translations,
    "search_bible_fulltext": handle_search_bible_fulltext,
    "list_extra_biblical_categories": handle_list_extra_biblical_categories,
    "search_extra_biblical": handle_search_extra_biblical,
    "get_extra_biblical_text": handle_get_extra_biblical_text,
    "get_reading_plan": handle_get_reading_plan,
    "get_commentary": handle_get_commentary,
    "list_commentary_authors": handle_list_commentary_authors,
    "list_theological_works": handle_list_theological_works,
    "search_theological_works": handle_search_theological_works,
    "get_theological_section": handle_get_theological_section,
    "get_textual_variants": handle_get_textual_variants,
    "list_manuscript_witnesses": handle_list_manuscript_witnesses,
    "compare_variant_readings": handle_compare_variant_readings,
    # Literary structure tools
    "list_literary_structure_sources": handle_list_literary_structure_sources,
    "list_literary_structures": handle_list_literary_structures,
    "get_literary_structure": handle_get_literary_structure,
    "search_literary_structures": handle_search_literary_structures,
    "get_literary_parallel": handle_get_literary_parallel,
    "get_literary_structure_by_reference": handle_get_literary_structure_by_reference,
    "get_literary_tree": handle_get_literary_tree,
}

# =============================================================================
# Entry points
# =============================================================================

@click.command()
@click.option("--transport", default="stdio", help="Transport type: stdio, sse, or streamable-http")
@click.option("--host", default="0.0.0.0", help="Host for SSE/HTTP transports")
@click.option("--port", default=8000, help="Port for SSE/HTTP transports")
@click.option("--db-url", envvar="THEOSIS_DATABASE_URL", help="PostgreSQL connection URL")
def main(transport: str, host: str, port: int, db_url: str | None):
    """Theosis MCP Server — Theological Research AI Interface."""
    if transport == "stdio":
        asyncio.run(run_stdio())
    elif transport == "sse":
        asyncio.run(run_sse(host, port))
    elif transport == "streamable-http":
        asyncio.run(run_http(host, port))
    else:
        logger.error(f"Unknown transport: {transport}")
        sys.exit(1)


async def run_stdio():
    """Run server over stdio transport."""
    global db
    db = await get_db()
    logger.info("Database connection established")
    logger.info("Starting Theosis MCP server (stdio)")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


async def run_sse(host: str, port: int):
    """Run server over SSE transport."""
    global db
    db = await get_db()
    logger.info("Database connection established")
    try:
        from starlette.applications import Starlette
        from starlette.routing import Route
        from mcp.server.sse import SseServerTransport
    except ImportError:
        logger.error("SSE transport requires 'starlette' and 'sse-starlette'. Install with: pip install theosis-mcp[sse]")
        sys.exit(1)

    sse = SseServerTransport("/messages/")

    async def handle_sse(request):
        async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
            await server.run(streams[0], streams[1], server.create_initialization_options())

    async def handle_messages(request):
        await sse.handle_post_message(request.scope, request.receive, request._send)

    app = Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Route("/messages/", endpoint=handle_messages, methods=["POST"]),
        ]
    )

    import uvicorn
    logger.info(f"Starting Theosis MCP server (SSE) on {host}:{port}")
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server_uvicorn = uvicorn.Server(config)
    await server_uvicorn.serve()


async def run_http(host: str, port: int):
    """Run server over Streamable HTTP transport."""
    global db
    
    try:
        from mcp.server.streamable_http import StreamableHTTPServerTransport
        from starlette.responses import PlainTextResponse
    except ImportError:
        logger.error("HTTP transport requires 'starlette'. Install with: pip install theosis-mcp[sse]")
        sys.exit(1)

    # Initialize database connection
    db = await get_db()
    logger.info("Database connection established")

    # Create transport once and connect it to the MCP server
    transport = StreamableHTTPServerTransport(None)

    async def mcp_app(scope, receive, send):
        await transport.handle_request(scope, receive, send)

    async def health(scope, receive, send):
        response = PlainTextResponse("OK")
        await response(scope, receive, send)

    async def app(scope, receive, send):
        if scope["type"] == "http" and scope["path"] == "/health":
            await health(scope, receive, send)
        else:
            await mcp_app(scope, receive, send)

    import uvicorn

    # Start the MCP server with the transport's connected streams
    async with transport.connect() as (read_stream, write_stream):
        server_task = asyncio.create_task(
            server.run(read_stream, write_stream, server.create_initialization_options())
        )
        logger.info(f"Starting Theosis MCP server (Streamable HTTP) on {host}:{port}")
        config = uvicorn.Config(app, host=host, port=port, log_level="info")
        server_uvicorn = uvicorn.Server(config)
        await server_uvicorn.serve()
        server_task.cancel()


if __name__ == "__main__":
    main()