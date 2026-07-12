"""
Tool definitions for the Theosis MCP server.

Includes all StudyBible MCP tools plus theosis-specific additions:
- Translation comparison across 140+ versions
- Extra-biblical text library (Fathers, Apocrypha, Pseudepigrapha)
- Full-text search with PostgreSQL tsvector
- Semantic search with pgvector
"""

import json

from mcp.types import Tool, ToolAnnotations


def _parse_json_field(value, default=None):
    """Parse a JSON string field, returning default if parsing fails."""
    if value is None:
        return default
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default


def _truncate(text: str, limit: int, suffix: str = "\n\n*[Truncated]*") -> str:
    """Truncate text to limit characters, appending suffix if truncated."""
    if len(text) <= limit:
        return text
    return text[:limit] + suffix


# =============================================================================
# Core Bible Study Tools (ported from StudyBible MCP)
# =============================================================================

TOOLS = [
    Tool(
        name="word_study",
        annotations=ToolAnnotations(title="Word Study", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Study a Greek or Hebrew word by Strong's number or English word.

Returns full lexical data: original script, transliteration, Strong's number,
definition, and key passages showing usage.""",
        inputSchema={
            "type": "object",
            "properties": {
                "strongs": {"type": "string", "description": "Strong's number (e.g., 'G26', 'H430')"},
                "word": {"type": "string", "description": "English word to study (e.g., 'love', 'faith')"},
                "language": {"type": "string", "enum": ["greek", "hebrew"], "description": "Language filter"}
            }
        }
    ),
    Tool(
        name="lookup_verse",
        annotations=ToolAnnotations(title="Lookup Verse", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Get a Bible verse with original Greek/Hebrew text and word-by-word breakdown.

ALWAYS use this when any Bible verse is mentioned. Returns:
- English text
- Original Greek/Hebrew (when available)
- Word-by-word morphology with Strong's numbers
- Genre-specific interpretation guidance

Supports: 'John 3:16', 'Gen 1:1', 'Romans 3:21-26', etc.""",
        inputSchema={
            "type": "object",
            "properties": {
                "reference": {"type": "string", "description": "Bible reference (e.g., 'John 3:16')"},
                "include_original": {"type": "boolean", "description": "Include Greek/Hebrew text. Default: true"},
                "include_morphology": {"type": "boolean", "description": "Include grammatical parsing. Default: false"}
            },
            "required": ["reference"]
        }
    ),
    Tool(
        name="search_lexicon",
        annotations=ToolAnnotations(title="Search Lexicon", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Search across Greek and Hebrew lexicons for English concepts or terms.

Finds original language words behind English concepts (e.g., 'love' → agape, phileo).
Includes LSJ (Liddell-Scott-Jones) Greek, BDB (Brown-Driver-Briggs) Hebrew,
and Abbott-Smith NT Greek lexicons.""",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search term (English word, transliteration, or concept)"},
                "language": {"type": "string", "enum": ["greek", "hebrew"]},
                "limit": {"type": "integer", "description": "Max results. Default: 10"}
            },
            "required": ["query"]
        }
    ),
    Tool(
        name="get_cross_references",
        annotations=ToolAnnotations(title="Cross References", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Find passages connected to a verse through curated cross-references.

Sources include Harrison/Romhild curated dataset, Treasury of Scripture Knowledge,
and thematic chains. Use before drawing theological conclusions from a single verse.""",
        inputSchema={
            "type": "object",
            "properties": {
                "reference": {"type": "string", "description": "Bible reference (e.g., 'John 3:16')"},
                "theme": {"type": "string", "description": "Theological theme (e.g., 'atonement', 'resurrection')"},
                "limit": {"type": "integer", "description": "Max results. Default: 8"}
            }
        }
    ),
    Tool(
        name="lookup_name",
        annotations=ToolAnnotations(title="Lookup Name", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Look up biblical persons, places, or things with relationship data.

Returns family connections (parents, siblings, spouse, children), geographical info,
and biblical significance. Database contains 4,000+ persons and 1,000+ places.""",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name to look up (e.g., 'David', 'Jerusalem')"},
                "type": {"type": "string", "enum": ["person", "place", "thing"]}
            },
            "required": ["name"]
        }
    ),
    Tool(
        name="parse_morphology",
        annotations=ToolAnnotations(title="Parse Morphology", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Explain a grammatical parsing code.

Greek: Robinson codes (e.g., 'V-AAI-3S' = Verb, Aorist, Active, Indicative, 3rd Singular)
Hebrew: Westminster/OpenScriptures codes""",
        inputSchema={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Morphology code (e.g., 'V-AAI-3S', 'N-GSF')"},
                "language": {"type": "string", "enum": ["greek", "hebrew"], "description": "Default: greek"}
            },
            "required": ["code"]
        }
    ),
    Tool(
        name="search_by_strongs",
        annotations=ToolAnnotations(title="Search by Strong's", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Find all verses where a specific Greek/Hebrew word appears.

After identifying a key word via word_study, use this to see how biblical authors
actually used it in context.""",
        inputSchema={
            "type": "object",
            "properties": {
                "strongs": {"type": "string", "description": "Strong's number (e.g., 'G26', 'H430')"},
                "limit": {"type": "integer", "description": "Max verses. Default: 20"}
            },
            "required": ["strongs"]
        }
    ),
    Tool(
        name="find_similar_passages",
        annotations=ToolAnnotations(title="Find Similar Passages", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Find semantically similar passages using AI embeddings (pgvector).

Discovers thematic connections beyond explicit cross-references. Uses vector similarity
to find passages with related meaning, imagery, or theological concepts.

IMPORTANT: Semantic similarity does NOT equal theological connection. Always verify
context, genre, and authorial intent before using parallels in interpretation.""",
        inputSchema={
            "type": "object",
            "properties": {
                "reference": {"type": "string", "description": "Bible reference (e.g., 'John 3:16')"},
                "limit": {"type": "integer", "description": "Number of similar passages. Default: 10"}
            },
            "required": ["reference"]
        }
    ),
    Tool(
        name="explore_genealogy",
        annotations=ToolAnnotations(title="Explore Genealogy", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Traverse multi-generational family trees for 1,100+ biblical persons.

Traces lineage across many generations — ancestors, descendants, siblings, tribal
affiliations. Essential for understanding biblical narrative connections.""",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Person name (e.g., 'David', 'Abraham')"},
                "direction": {"type": "string", "enum": ["ancestors", "descendants", "siblings"], "description": "Default: ancestors"}
            },
            "required": ["name"]
        }
    ),
    Tool(
        name="get_study_notes",
        annotations=ToolAnnotations(title="Study Notes", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Get scholarly study notes and commentary for a Bible passage.

Sources include Aquifer Open Study Notes (102K+ entries), Tyndale Bible Dictionary,
and translation notes. Provides historical context, theological insights, and
interpretive guidance.""",
        inputSchema={
            "type": "object",
            "properties": {
                "reference": {"type": "string", "description": "Bible reference (e.g., 'Romans 3:23')"},
                "limit": {"type": "integer", "description": "Max notes. Default: 10"}
            },
            "required": ["reference"]
        }
    ),
    Tool(
        name="get_dictionary_article",
        annotations=ToolAnnotations(title="Dictionary Article", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Get a full Tyndale Bible Dictionary article on a topic.""",
        inputSchema={
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Topic name (e.g., 'baptism', 'covenant')"}
            },
            "required": ["topic"]
        }
    ),
    Tool(
        name="get_ane_context",
        annotations=ToolAnnotations(title="Ancient Near East Context", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Get Ancient Near East cultural and historical context for a passage.

Covers cosmology, religious practices, social structure, covenant forms, and more
across 9 major historical periods.""",
        inputSchema={
            "type": "object",
            "properties": {
                "reference": {"type": "string", "description": "Bible reference (e.g., 'Genesis 1:1')"}
            },
            "required": ["reference"]
        }
    ),
    Tool(
        name="get_theology_context",
        annotations=ToolAnnotations(title="Theological Context", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Get systematic theological context and thematic connections for a passage.""",
        inputSchema={
            "type": "object",
            "properties": {
                "reference": {"type": "string", "description": "Bible reference"}
            },
            "required": ["reference"]
        }
    ),

    # =========================================================================
    # NEW: Translation Tools (theosis-specific)
    # =========================================================================

    Tool(
        name="list_translations",
        annotations=ToolAnnotations(title="List Translations", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""List all available Bible translations in the database.

Returns translation ID, abbreviation, name, language, year, and license info.
Use this to discover which translations are available for comparison.""",
        inputSchema={
            "type": "object",
            "properties": {}
        }
    ),
    Tool(
        name="get_translation_verse",
        annotations=ToolAnnotations(title="Get Translation Verse", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Get a specific verse in a specific translation.

USE THIS to see how different versions render a passage. Compare the KJV with
modern translations, or check how a particular tradition translates key terms.""",
        inputSchema={
            "type": "object",
            "properties": {
                "reference": {"type": "string", "description": "Bible reference (e.g., 'John 3:16')"},
                "translation": {"type": "string", "description": "Translation abbreviation (e.g., 'KJV', 'ESV', 'NASB'). Use list_translations to see options."}
            },
            "required": ["reference", "translation"]
        }
    ),
    Tool(
        name="compare_translations",
        annotations=ToolAnnotations(title="Compare Translations", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Compare a verse side-by-side across multiple translations.

See how different traditions, eras, and translation philosophies handle a passage.
Useful for identifying translation decisions that affect interpretation.""",
        inputSchema={
            "type": "object",
            "properties": {
                "reference": {"type": "string", "description": "Bible reference (e.g., 'John 3:16')"},
                "translations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of translation abbreviations (e.g., ['KJV', 'ESV', 'NASB', 'NIV'])"
                }
            },
            "required": ["reference", "translations"]
        }
    ),
    Tool(
        name="search_bible_fulltext",
        annotations=ToolAnnotations(title="Search Bible", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Full-text search across all Bible translations using PostgreSQL tsvector.

Finds verses containing specific words, phrases, or concepts. Much more powerful
than simple keyword matching — understands word stems and ranks results by relevance.

USE THIS when you need to find all passages about a topic, or locate a verse when
you only remember key words.""",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search terms (e.g., 'resurrection of the dead', 'living water')"},
                "translation": {"type": "string", "description": "Limit to one translation (optional)"},
                "limit": {"type": "integer", "description": "Max results. Default: 20"}
            },
            "required": ["query"]
        }
    ),

    # =========================================================================
    # NEW: Extra-Biblical Text Tools (theosis-specific)
    # =========================================================================

    Tool(
        name="list_extra_biblical_categories",
        annotations=ToolAnnotations(title="List Extra-Biblical Categories", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""List all categories of extra-biblical texts in the library.

Categories include: Deuterocanonical/Apocrypha, Pseudepigrapha (Enoch, Jasher,
Jubilees, etc.), Apostolic Fathers, Ante-Nicene Fathers, Nicene & Post-Nicene Fathers.

Each category shows the count of available texts.""",
        inputSchema={
            "type": "object",
            "properties": {}
        }
    ),
    Tool(
        name="search_extra_biblical",
        annotations=ToolAnnotations(title="Search Extra-Biblical", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Full-text search across the entire extra-biblical library.

Search Church Fathers, Apocrypha, Pseudepigrapha, and early Christian writings.
Returns ranked results with contextual snippets.

USE THIS to find how early Christians interpreted a passage, what the Apostolic
Fathers taught about a doctrine, or parallel traditions in Jewish pseudepigrapha.""",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search terms"},
                "category": {"type": "string", "description": "Filter by category (optional)"},
                "limit": {"type": "integer", "description": "Max results. Default: 20"}
            },
            "required": ["query"]
        }
    ),
    Tool(
        name="get_extra_biblical_text",
        annotations=ToolAnnotations(title="Get Extra-Biblical Text", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Retrieve a specific extra-biblical text or passage.

Returns full text of the requested section. Use after searching to read the
complete context of a result.""",
        inputSchema={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Text title (e.g., '1 Enoch', '1 Clement')"},
                "section": {"type": "string", "description": "Specific section or chapter (optional)"}
            },
            "required": ["title"]
        }
    ),
    Tool(
        name="get_reading_plan",
        annotations=ToolAnnotations(title="Reading Plan", readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        description="""Generate a structured Bible reading plan.

Creates a daily reading schedule through a book, testament, or the entire Bible.
Adjustable duration and starting point.""",
        inputSchema={
            "type": "object",
            "properties": {
                "plan_type": {
                    "type": "string",
                    "enum": ["book", "testament", "whole_bible", "chronological", "nt_challenge"],
                    "description": "Type of reading plan"
                },
                "book": {"type": "string", "description": "Book name for 'book' plan type"},
                "testament": {"type": "string", "enum": ["OT", "NT"], "description": "For 'testament' plan type"},
                "days": {"type": "integer", "description": "Duration in days. Default: 30 for book, 90 for testament, 365 for whole Bible"}
            },
            "required": ["plan_type"]
        }
    ),
]
