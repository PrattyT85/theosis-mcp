# Theosis MCP

**Theological Research AI Interface** — PostgreSQL-backed MCP server for deep Bible study.

Connect any MCP-compatible AI (Claude, GPT, Hermes Desktop, or Open WebUI) to a unified
theological database with a growing Bible translation catalogue, Greek/Hebrew lexicons,
340K+ cross-references, Church Fathers, Apocrypha, Pseudepigrapha, and AI-powered semantic search.

## Features

- **Word Studies**: LSJ Greek, BDB Hebrew, Abbott-Smith NT lexicons (19K+ entries)
- **Original Languages**: Morphologically-tagged Greek NT and Hebrew OT (31K verses)
- **Cross-References**: 340K+ connections from TSK, Harrison/Romhild, and scholarly sources
- **Study Notes**: Aquifer Open Study Notes (102K entries) + Tyndale Bible Dictionary
- **Translation catalogue**: 140 Scrollmapper source editions; imported batches retain language, coverage, and licence metadata
- **Extra-Biblical Library**: Church Fathers, Apocrypha, Pseudepigrapha (69+ texts)
- **Semantic Search**: pgvector embeddings for finding thematically related passages
- **ANE Context**: Ancient Near East cultural background across 9 historical periods
- **Theographic Data**: 1,100+ biblical persons with genealogy and relationship graphs

## Quick Start

The repository contains the current schema in `schema.sql`. A fresh installation requires PostgreSQL 16+, the pgvector extension, and a database role named `theosis`.

```bash
git clone https://github.com/PrattyT85/theosis-mcp.git
cd theosis-mcp
uv sync

# Apply the schema to an already-created UTF-8 database
sudo -u postgres psql -d theosis -f schema.sql

export THEOSIS_DATABASE_URL="postgresql://theosis@/theosis?host=/var/run/postgresql"

# Run locally over stdio (for Hermes Desktop, Claude Desktop, Cursor, etc.)
.venv/bin/theosis-mcp --transport stdio

# Run Streamable HTTP on the required LAN address
.venv/bin/theosis-mcp --transport streamable-http --host 192.168.1.130 --port 8000
```

The schema file creates tables and indexes, not the large source corpus. Use the import scripts to acquire licensed source editions, and keep a PostgreSQL backup before large imports.

## Operations

The deployment templates include a daily logical backup (keep-last 3) and a health check every 15 minutes. The health check verifies UTF-8 encoding, pgvector, required data, the active systemd service, MCP initialization, and the newest backup archive.

```bash
sudo systemctl enable --now theosis-backup.timer theosis-healthcheck.timer
sudo systemctl start theosis-backup.service
sudo systemctl start theosis-healthcheck.service
journalctl -u theosis-backup.service -u theosis-healthcheck.service -n 50 --no-pager
```

Backups are written to `/root/theosis-backups/` and are not committed to Git.

## Translation imports

Scrollmapper currently publishes 140 source editions in flat CSV format. Theosis imports them in reviewed batches so each edition can retain its language, canon coverage, and source licence metadata. The importer supports English and selected historical-language editions, for example:

```bash
# From a checkout of this repository
python3 scripts/import_translations.py --download \\
  --translations KJV,KJVPCE,NHEBJE,NHEBME

# Historical Hebrew, Greek, Latin, Syriac, Coptic, Gothic editions
python3 scripts/import_translations.py --download \\
  --translations WLC,StatResGNT,Vulgate,Peshitta,CopSahBible2,Wulfila,HebModern

# Inspect an import without writing to PostgreSQL
python3 scripts/import_translations.py --download \\
  --translations WLC --dry-run
```

The importer preserves non-canonical books when the source edition includes them. Partial editions (for example, New Testament- or Psalms-only) are reported by their actual source-book coverage rather than being described as complete Bibles.

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
| `list_translations` | Browse imported translations, languages, coverage, and licences |
| `get_translation_verse` | Get a verse in a specific translation |
| `compare_translations` | Side-by-side translation comparison |
| `search_bible_fulltext` | Full-text search across all translations |
| `list_extra_biblical_categories` | Browse Church Fathers library |
| `search_extra_biblical` | Search Church Fathers, Apocrypha, Pseudepigrapha |
| `get_extra_biblical_text` | Read specific extra-biblical texts |
| `get_reading_plan` | Generate structured Bible reading plans |
| `list_theological_works` | List imported systematic theology works |
| `search_theological_works` | Search systematic theology by doctrine or phrase |
| `get_theological_section` | Retrieve a full systematic theology section |

## Credits

Built on the foundation of [StudyBible MCP](https://github.com/djayatillake/studybible-mcp) by David Jayatillake.
Data from [scrollmapper/bible_databases](https://github.com/scrollmapper/bible_databases),
[STEPBible](https://www.stepbible.org/) (CC BY 4.0),
and the [Theographic Bible Knowledge Graph](https://github.com/robertrouse/theographic).

## License

MIT
