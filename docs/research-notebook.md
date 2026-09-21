# Theosis Research Notebook — Installation and Use

## Overview

The Theosis Research Notebook is a Hermes skill that captures theological observations and research syntheses as portable Obsidian Markdown notes, linked to Scripture and Theosis sources. It follows a six-step observe → capture → restate → expand → link → review workflow and requires explicit user approval before writing to the vault.

## Installation

1. The skill ships in-repo at `skills/note-taking/theosis-research-notebook/`.
2. Hermes discovers skills in `~/.hermes/skills/`. To install:
   ```bash
   cp -r skills/note-taking/theosis-research-notebook ~/.hermes/skills/note-taking/
   ```
3. Restart Hermes Desktop or start a new session. The skill appears automatically.
4. No extra Python dependencies are required — the skill uses Hermes file tools only.

## OBSIDIAN_VAULT_PATH

The vault path resolves from the `OBSIDIAN_VAULT_PATH` environment variable. Default: `~/obsidian-vault`.

Set it in your shell profile or Hermes configuration:
```bash
export OBSIDIAN_VAULT_PATH=~/obsidian-vault
```

All notebook writes target `$OBSIDIAN_VAULT_PATH/readwrite/theosis-notes/`. Paths that escape this directory (e.g. `..`, absolute paths, symlinks) are rejected.

## Safe Vault Tiers

| Tier | Policy |
|------|--------|
| `readwrite/theosis-notes/` | Write target — all research notes go here |
| `readwrite/` (other) | Read-only; do not write outside `theosis-notes/` |
| `readonly/` | Read-only; never modify |
| `private/` | Never read, write, list, or search |

Content from `private/` must never appear in commits, PRs, examples, or documentation.

## Draft → Approval → Write Workflow

1. The user asks Hermes to capture an observation or research synthesis.
2. Hermes drafts a note using the template (`templates/research-note.md`) with complete YAML front matter and six labelled body sections.
3. Hermes shows the full draft to the user.
4. **The user must explicitly approve in a separate turn** before any vault write occurs.
5. Only after approval, Hermes writes the file to `$OBSIDIAN_VAULT_PATH/readwrite/theosis-notes/`.

This two-turn protocol ensures the user retains full control over their theological notes.

## Note Schema

Notes use UTF-8 Markdown with YAML front matter. Required fields:

- `id` — stable UUID or ULID
- `title` — human-readable title
- `note_type` — `observation`, `research`, `synthesis`, or `application`
- `status` — `draft`, `reviewed`, or `published`
- `scripture_refs` — list of Scripture references
- `tags` — case-insensitive tags
- `source_refs` — machine-readable source references
- `provenance` — six-layer provenance label
- `created` / `updated` — ISO dates

Optional: `source_licences`, `retrieved_at`.

Body sections (all required): Biblical text, Original-language observation, External source, Historical/cultural context, User synthesis, Application.

See `templates/research-note.md` for the copy-pasteable template.

## Search and Backlinks

- **Search by text**: `search_files(pattern=<term>, target='content', path=<vault>/readwrite/theosis-notes/)`
- **Read a note**: `read_file(path=<vault>/readwrite/theosis-notes/<file>.md)`
- **List all notes**: `search_files(pattern='*.md', target='files', path=<vault>/readwrite/theosis-notes/)`
- **Find related notes**: search for `[[<note-id>]]` or `[[<title>]]` across the notes directory.

Backlinks are discovered by searching for `[[wiki-link]]` references to a note's ID or title.

## Portability

- Notes are plain UTF-8 Markdown — readable in any text editor.
- YAML front matter is standard and compatible with Obsidian, Jekyll, Hugo, and other tools.
- No proprietary format or service lock-in.
- Export/import is a simple file copy.

## Offline Behaviour

The notebook works fully offline. Theosis MCP tools provide enrichment (lexicon lookups, cross-references, commentary) but are not required for note creation, reading, or searching. When Theosis is unavailable, the user can still draft and save notes manually.

## Deferred Features (not in this MVP)

- Local index or SQLite-backed search
- Automatic cross-linking between notes
- Voice capture or mobile capture
- Obsidian plugin behaviour
- Vault migration from existing notes
- Concurrent cross-device sync
