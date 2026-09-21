# Provenance, Security, and Portability Review

## Controls

- Require explicit approval before any AI-initiated write. A protocol flag can enforce the integration contract, but the Desktop workflow must show a preview and obtain a separate confirmation turn.
- Keep source text, original-language observations, historical context, user synthesis, and application in visibly labelled layers.
- Store source/tool references, retrieval timestamps, editions/licences, and authors where available. Unknown licence metadata must be explicit rather than invented.
- Constrain writes to a configured notebook root, resolve paths, reject traversal/absolute paths/symlink escapes, and never accept arbitrary raw paths from a model.
- Keep the user's `private/` vault tier out of reads, writes, indexing, examples, commits, and PRs. Only a designated editable/shared area may be targeted.
- Use UTF-8 and ordinary Markdown so files remain readable without Theosis or Hermes.
- Keep secrets, database URLs, credentials, private notes, and machine-specific paths out of GitHub artifacts.

## Testable failures

- Unapproved write creates no file.
- `..`, absolute paths, encoded traversal, `.env`, `.git`, and symlink escapes are rejected.
- Missing required front matter is rejected for new notes.
- A write-capable MCP tool is not annotated `readOnlyHint=True`.
- Notes with source-only provenance do not silently contain unlabeled user interpretation.
- Example and documentation files contain no credentials or private-vault content.

## Portability decision

Markdown is the canonical export/import format. SQLite/PostgreSQL indexing, Obsidian plugins, voice capture, and automatic AI linking are deferred until the smallest slice is verified.

## Important boundary issue

The installed Hermes Obsidian skill already defines the vault access policy (`readwrite/` editable, `readonly/` read-only, `private/` inaccessible). A filesystem-backed module inside the Theosis MCP repository would need to reproduce or delegate that policy. This supports the architecture subagent's recommendation for a Hermes-skill boundary, but conflicts with the current PR target and must be resolved explicitly.

## Sources

- `docs/plans/theosis-research-notebook.md`
- The installed Hermes Obsidian skill
- The installed Hermes Theosis MCP skill
- `README.md`, `.gitignore`, and existing MCP tool annotations.
