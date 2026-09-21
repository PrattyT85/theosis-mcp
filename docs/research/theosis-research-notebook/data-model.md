# Markdown and Obsidian Data-Model Research

## Recommendation

Use YAML front matter between the first two `---` delimiters, keep properties flat, use UTF-8 Markdown, and use stable IDs that survive file renames. Use Obsidian-compatible plural `tags` rather than singular `tag`; quote wiki-links if they appear in YAML.

## Candidate fields

Required or MVP fields:

- `id`: stable UUID/ULID or another collision-safe stable identifier.
- `title`: human-readable title.
- `note_type`: observation, research, synthesis, or application.
- `scripture_refs`: list of references.
- `tags`: list of tags; the earlier `topics` name has been retired — `tags` is the canonical Obsidian-compatible field.
- `source_refs`: machine-readable source/tool references.
- `provenance`: explicit source/user layer labels.
- `created`: ISO date.
- `updated`: ISO datetime.

Optional source metadata should remain flat (`source_url`, `source_author`, `source_licence`, `retrieved_at`, edition/translation identifiers) so Obsidian Properties can display it.

## Provenance layers

The note must distinguish biblical text, original-language observation, external scholarly source, historical/cultural context, user synthesis, and application. The safest human-readable representation is labelled Markdown sections plus front-matter provenance/source metadata; source-derived text must never be rendered as user interpretation or Scripture.

## Parser recommendation

PyYAML with `safe_load`/`safe_dump` is sufficient for simple front matter read/write if adding a dependency is acceptable. A narrow parser is a viable dependency-free alternative, but it must reject unsupported YAML rather than silently corrupt it. `ruamel.yaml` is unnecessary for the first slice because preserving comments and formatting is not required.

## Compatibility risks

- Existing Obsidian notes may have no front matter; do not migrate the user's vault as part of this PR.
- YAML special characters, dates, booleans, and unquoted `[[wiki-links]]` need tests.
- Search should support the canonical field chosen by the design record and avoid silently rewriting user reference text.
- Flat Markdown remains portable to Obsidian and other editors; database-only storage would violate portability.

## Sources

- `docs/plans/theosis-research-notebook.md`
- The read-only Obsidian Desktop handoff document
- Repository `.gitignore` and Python dependency configuration.
