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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("theosis-mcp")

# Server icon: gold cross on purple
ICON_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAAtklEQVR42mNgGOmAEZtgQ9TV/7SwrGGZNiNeB9DKYnwOYcGl6MajG1S1VENOA6s4E4yxounvfw0NDZpYjm4mckgz0drnhMxmIdew5bO3M9w+twfOr5veS5Y5TAOdDUcdMOAOYCE2wWEDqkYueNVEpnpSxwHIqR3ZcmziqMBzNA1QJwqwFTLocT5aEI06YNQBow6gaUGEDUAqGk/qhwCu1iutWsY4+wW0bJYT1S+gZUgMqq7ZKAAA/oE/8EmGTpMAAAAASUVORK5CYII="
)

server = Server(
    "theosis",
    version="0.1.0",
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

async def handle_get_ane_context(args: dict[str, Any]) -> list[TextContent]:
    reference = args.get("reference", "")
    if not reference:
        return text("Please provide a Bible reference.")

    entries = await db.get_ane_context(reference)
    if not entries:
        return text(f"No ANE context data found for {reference}.")

    result = f"## Ancient Near East Context: {reference}\n\n"
    for entry in entries:
        result += f"### {entry.get('dimension', '')} — {entry.get('period', '')}\n"
        result += f"{entry.get('content', entry.get('description', ''))}\n\n"
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
        if t.get("license"):
            result += f" [{t['license']}]"
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
# Tool handler dispatch table
# =============================================================================

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
    logger.info("Starting Theosis MCP server (stdio)")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


async def run_sse(host: str, port: int):
    """Run server over SSE transport."""
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
    try:
        from starlette.applications import Starlette
        from starlette.routing import Route
        from mcp.server.streamable_http import StreamableHTTPServerTransport
    except ImportError:
        logger.error("HTTP transport requires 'starlette'. Install with: pip install theosis-mcp[sse]")
        sys.exit(1)

    transport_http = StreamableHTTPServerTransport("/mcp")

    async def handle_mcp(request):
        async with transport_http.connect(request.scope, request.receive, request._send) as streams:
            await server.run(streams[0], streams[1], server.create_initialization_options())

    app = Starlette(
        routes=[
            Route("/mcp", endpoint=handle_mcp),
        ]
    )

    import uvicorn
    logger.info(f"Starting Theosis MCP server (Streamable HTTP) on {host}:{port}")
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server_uvicorn = uvicorn.Server(config)
    await server_uvicorn.serve()


if __name__ == "__main__":
    main()