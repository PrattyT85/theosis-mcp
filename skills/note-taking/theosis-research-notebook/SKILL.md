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
| `source_licences` | conditional | Licence metadata for each source. **Required** when `source_refs` is present; otherwise optional (empty placeholder in template). Must be positionally aligned with `source_refs`. |
| `retrieved_at` | conditional | ISO-8601 datetime of source retrieval. **Required** when `source_refs` is present; otherwise optional (empty placeholder in template). Must be positionally aligned with `source_refs` and `source_licences`. |
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

### Provenance Capture Format

`source_refs` entries MUST preserve the actual tool name and arguments, not generic labels:

```yaml
source_refs:
  - "theosis_mcp.get_study_notes(reference='2 Peter 2:13')"
  - "theosis_mcp.word_study(strong='G2689')"
```

`source_licences` entries MUST preserve the source/edition and licence. When the licence is unknown, mark it as `licence: unknown` — never invent licence text.

`retrieved_at` MUST be ISO-8601 and correspond positionally to `source_refs`/`source_licences` when multiple sources are used. For two sources:

```yaml
source_refs:
  - "theosis_mcp.get_study_notes(reference='2 Peter 2:13')"
  - "theosis_mcp.word_study(strong='G2689')"
source_licences:
  - "CC BY 4.0 (Aquifer Open Study Notes)"
  - "Public Domain (Strong's Concordance)"
retrieved_at:
  - "2026-09-20T10:00:00Z"
  - "2026-09-20T10:05:00Z"
```

Raw returned source text belongs in labelled source sections (`## Biblical text`, `## Original-language observation`, `## External source`), not silently in `## User synthesis`.

### Provenance Capture Checklist (copy-pasteable recipe)

Before finalising any note, run through this checklist:

1. [ ] `source_refs` contains the actual tool name and arguments used (e.g. `theosis_mcp.get_study_notes(reference='...')`), not a generic label.
2. [ ] `source_licences` entries exist for each source; unknown licences are marked `licence: unknown`.
3. [ ] `retrieved_at` is ISO-8601 and positionally aligned with `source_refs` and `source_licences`.
4. [ ] Raw source text appears only in the appropriate labelled section (Biblical text, Original-language observation, External source).
5. [ ] `## User synthesis` contains only the user's own words, not raw source output.
6. [ ] Provenance label matches the dominant content layer of the note.

## Opt-in Scripture Linking

Automatic Scripture detection/normalization and automatic wiki-link insertion are **OFF by default**. This avoids noisy backlinks that pollute the vault's link graph.

When the user requests Scripture linking:

1. **Detect** — identify Scripture references in the note text and show them to the user.
2. **Propose** — list candidate related notes that could be linked.
3. **Preserve** — keep the user's exact Scripture reference text unchanged.
4. **Approve** — add wiki-links only after explicit approval of the exact links.
5. **Search/backlinks remain available manually** — the user can always search for `[[reference]]` or related notes without automatic linking.

## Safe Edits to Existing Notes

When editing an existing note, follow this workflow to prevent data loss:

1. **Read current** — read the existing file and confirm its contents.
2. **Produce a unified diff or preview** — show the exact changes to the user.
3. **Separate explicit approval** — wait for the user to approve the exact changes.
4. **Re-read immediately before patch** — re-read the file to detect any changes since the diff was generated.
5. **Patch only the approved note** under `readwrite/theosis-notes/`.
6. **Read back and verify** — confirm the edit landed correctly.

**Abort rather than overwrite** on a changed file, collision, or conflict. Never force overwrite or force-push. Preserve both sides of a conflict and stop for user resolution. When in doubt, leave both versions intact and let the user decide.

## Performance Guidance

Keep file scanning while the vault is small — `search_files` over `.md` files in `readwrite/theosis-notes/` is fast for hundreds of notes. When searching becomes noticeably slow:

1. **Measure first** — check the note count (`search_files(pattern='*.md', target='files', ...)`) and time a search before proposing a local index.
2. **Propose, don't add** — only suggest a local index or SQLite-backed search after measured need; do not add an index in this change.

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
- [ ] `git grep` finds no secrets, credentials, or private vault paths in committed files

## Common Pitfalls

1. **Forgetting approval** — always show the draft and wait for a separate confirmation turn.
2. **Writing outside `theosis-notes/`** — validate the resolved path before every write.
3. **Traversing with `..`** — reject paths containing `..` components.
4. **Inventing licences** — if the source licence is unknown, mark it explicitly.
5. **Overwriting existing notes** — check for filename collision before writing.
6. **Mixing provenance layers** — never render source text as user interpretation.
7. **Committing private content** — keep `private/` out of Git entirely.
