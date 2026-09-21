---
name: theosis-research-notebook
description: Use when capturing theological notes in Obsidian.
version: 1.0.0
author: Theosis Contributors
license: MIT
metadata:
  hermes:
    tags:
      - theology
      - obsidian
      - note-taking
      - scripture-study
      - research
    related_skills:
      - obsidian
      - theosis-mcp
---

# Theosis Research Notebook

Capture theological observations and research syntheses as portable Obsidian Markdown notes, linked to Scripture and Theosis sources.

## Workflow

Follow the six-step observe → capture → restate → expand → link → review cycle:

1. **Observe** — identify something in Scripture, a Theosis lookup, or an external source.
2. **Capture** — draft a note quickly using the bundled template (`templates/research-note.md`).
3. **Restate** — rewrite the observation in the user's own words; never copy source text verbatim without a source label.
4. **Expand** — fill all six body sections and front-matter fields; add source references, licence metadata, and retrieval timestamps.
5. **Link** — connect to Scripture references, other notes via `[[wiki-links]]`, and tags.
6. **Review** — periodically review related notes to surface cross-connections and refine synthesis.

## Draft → Approve → Write Protocol

1. Draft the note as Markdown with complete YAML front matter.
2. Show the full draft to the user.
3. **Wait for explicit approval in a separate turn** — never write to the vault without it.
4. Only after approval, write the file to the vault.

## Vault Resolution

Resolve `OBSIDIAN_VAULT_PATH` from the environment variable. Default: `~/obsidian-vault`.

### Safe Vault Tiers

| Tier | Policy |
|------|--------|
| `readwrite/theosis-notes/` | **Write target** — all research notes go here |
| `readwrite/` (other) | Read-only; do not write outside `theosis-notes/` |
| `readonly/` | Read-only; never modify |
| `private/` | **Never read, write, list, or search** |

All notebook writes MUST resolve to a path under `$OBSIDIAN_VAULT_PATH/readwrite/theosis-notes/`. Reject paths that escape this directory (e.g. `..`, absolute paths, symlink escapes).

## Note Format

Use ordinary UTF-8 Markdown with YAML front matter and Obsidian `[[wiki-links]]`.

### Front Matter Fields

| Field | Required | Description |
|-------|----------|-------------|
| `id` | yes | Stable unique identifier (UUID or ULID) |
| `title` | yes | Human-readable title |
| `note_type` | yes | One of: `observation`, `research`, `synthesis`, `application` |
| `status` | yes | One of: `draft`, `reviewed`, `published` |
| `scripture_refs` | yes | List of Scripture references, e.g. `["2 Peter 2:13"]` |
| `tags` | yes | Case-insensitive tags for search |
| `source_refs` | yes | Machine-readable source/tool references |
| `source_licences` | no | Licence metadata for each source (include when source data is available; the template carries this as an empty placeholder to be populated) |
| `retrieved_at` | no | ISO datetime of source retrieval (include when source data is available; the template carries this as an empty placeholder to be populated) |
| `provenance` | yes | Six-layer provenance label (see `references/provenance.md`) |
| `created` | yes | ISO date of note creation |
| `updated` | yes | ISO date of last update |

### Body Sections

Every note MUST contain these six labelled headings:

1. `## Biblical text`
2. `## Original-language observation`
3. `## External source`
4. `## Historical/cultural context`
5. `## User synthesis`
6. `## Application`

Use the bundled template: `templates/research-note.md`.

## Search Workflow

Use Hermes file tools restricted to `readwrite/theosis-notes/`:

- **Search**: `search_files(pattern=<term>, target='content', path=<vault>/readwrite/theosis-notes/)`
- **Read**: `read_file(path=<vault>/readwrite/theosis-notes/<file>.md)`
- **List**: `search_files(pattern='*.md', target='files', path=<vault>/readwrite/theosis-notes/)`
- **Related/Backlinks**: search for `[[<note-id>]]` or `[[<title>]]` across the notes directory.

## Safe Filename and Collision Rules

- Filenames: lowercase, hyphen-separated, `.md` extension.
- Slug from title; prefix with a date or ID if collision risk exists.
- Never overwrite an existing note without explicit user approval.

## Provenance and Licence Preservation

See `references/provenance.md` for the six-layer taxonomy and source/licence/retrieval rules.

- Always record `source_refs` and `provenance` for every note.
- Preserve source licence metadata; never invent licence text.
- Distinguish biblical text, original-language observation, external source, user synthesis, and application in labelled sections.

## No Silent AI Attribution

- The user owns the note. Never attribute authorship to "AI" or "Hermes" unless the user explicitly requests it.
- Do not insert AI-generated content into the Biblical text or Original-language observation sections without clear source labels.

## Private Vault Content

- **Never** commit, reference, or include content from `private/` in this repository, examples, documentation, or pull requests.
- Example notes use only fictional/example content.

## Manual Verification Checklist

Before merging a skill change:

- [ ] `SKILL.md` front matter starts at byte 0 with `---`
- [ ] Skill name matches `theosis-research-notebook`
- [ ] Description begins with "Use when"
- [ ] Workflow describes observe → capture → restate → expand → link → review
- [ ] Draft/approval protocol requires explicit user approval in a separate turn
- [ ] Vault path resolves to `OBSIDIAN_VAULT_PATH` with default `~/obsidian-vault`
- [ ] Writes restricted to `readwrite/theosis-notes/`
- [ ] `private/` is never read/written/listed/searched
- [ ] `readonly/` is never modified
- [ ] Template has all 12 required front-matter keys and 6 body sections
- [ ] Provenance reference describes six-layer taxonomy
- [ ] Example note has no absolute home paths and uses fictional content only
- [ ] Docs mention `OBSIDIAN_VAULT_PATH`, offline portability, and draft/approval workflow
- [ ] README links to `docs/research-notebook.md` and the example
- [ ] `git grep` finds no secrets, tokens, or private vault paths in committed files

## Common Pitfalls

1. **Forgetting approval** — always show the draft and wait for a separate confirmation turn.
2. **Writing outside `theosis-notes/`** — validate the resolved path before every write.
3. **Traversing with `..`** — reject paths containing `..` components.
4. **Inventing licences** — if the source licence is unknown, mark it explicitly.
5. **Overwriting existing notes** — check for filename collision before writing.
6. **Mixing provenance layers** — never render source text as user interpretation.
7. **Committing private content** — keep `private/` out of Git entirely.
