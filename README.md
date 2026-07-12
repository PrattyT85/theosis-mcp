# Theosis MCP

**Theological Research AI Interface** — PostgreSQL-backed MCP server for deep Bible study.

Connect any MCP-compatible AI (Claude, GPT, local LLMs via Open WebUI) to a unified
theological database with 140+ Bible translations, Greek/Hebrew lexicons, 340K+ cross-references,
Church Fathers, Apocrypha, Pseudepigrapha, and AI-powered semantic search.

## Features

- **Word Studies**: LSJ Greek, BDB Hebrew, Abbott-Smith NT lexicons (19K+ entries)
- **Original Languages**: Morphologically-tagged Greek NT and Hebrew OT (31K verses)
- **Cross-References**: 340K+ connections from TSK, Harrison/Romhild, and scholarly sources
- **Study Notes**: Aquifer Open Study Notes (102K entries) + Tyndale Bible Dictionary
- **140+ Translations**: Side-by-side comparison with full-text PostgreSQL tsvector search
- **Extra-Biblical Library**: Church Fathers, Apocrypha, Pseudepigrapha (69+ texts)
- **Semantic Search**: pgvector embeddings for finding thematically related passages
- **ANE Context**: Ancient Near East cultural background across 9 historical periods
- **Theographic Data**: 1,100+ biblical persons with genealogy and relationship graphs

## Quick Start

```bash
# Set database URL
export THEOSIS_DATABASE_URL="postgresql://theosis:***@192.168.1.130:5432/theosis"

# Run as stdio MCP server (for Claude Desktop, Cursor, etc.)
uvx theosis-mcp --transport stdio

# Run as Streamable HTTP server (for Open WebUI)
uvx theosis-mcp --transport streamable-http --host 0.0.0.0 --port 8000
```

## Open WebUI Integration

1. In Open WebUI Admin Settings → External Tools, add an MCP connection:
   - URL: `http://192.168.1.130:8000/mcp`
   - Transport: Streamable HTTP

2. All tools become available to any model in Open WebUI

## Tools

| Tool | Description |
|------|-------------|
| `word_study` | Deep dive into Greek/Hebrew words with full lexicon data |
| `lookup_verse` | Get verse text with original language and morphology |
| `search_lexicon` | Search LSJ/BDB/Strong's by English concepts |
| `get_cross_references` | Find scholarly cross-reference connections |
| `lookup_name` | Biblical persons, places with relationship data |
| `parse_morphology` | Explain Greek/Hebrew grammatical codes |
| `search_by_strongs` | Find all verses using a specific Greek/Hebrew word |
| `find_similar_passages` | Semantic search with pgvector embeddings |
| `explore_genealogy` | Multi-generational family trees |
| `get_study_notes` | Aquifer study notes and Tyndale dictionary |
| `get_dictionary_article` | Full Tyndale Bible Dictionary articles |
| `get_ane_context` | Ancient Near East cultural background |
| `get_theology_context` | Systematic theological themes |
| `list_translations` | Browse 140+ available Bible translations |
| `get_translation_verse` | Get a verse in a specific translation |
| `compare_translations` | Side-by-side translation comparison |
| `search_bible_fulltext` | Full-text search across all translations |
| `list_extra_biblical_categories` | Browse Church Fathers library |
| `search_extra_biblical` | Search Church Fathers, Apocrypha, Pseudepigrapha |
| `get_extra_biblical_text` | Read specific extra-biblical texts |
| `get_reading_plan` | Generate structured Bible reading plans |

## Credits

Built on the foundation of [StudyBible MCP](https://github.com/djayatillake/studybible-mcp) by David Jayatillake.
Data from [scrollmapper/bible_databases](https://github.com/scrollmapper/bible_databases),
[STEPBible](https://www.stepbible.org/) (CC BY 4.0),
and the [Theographic Bible Knowledge Graph](https://github.com/robertrouse/theographic).

## License

MIT
