# Consolidated Design Decision

## Target repository and boundary

The five research reports agree on the product requirements and Markdown-first portability, but they do **not** agree on the implementation boundary. The architecture report recommends a Hermes skill plus the existing Obsidian-vault workflow because the current Theosis MCP server is a PostgreSQL read/query service and has no filesystem-write policy. The current branch, proposal, and requested PR delivery all point to `PrattyT85/theosis-mcp`.

Verified facts:

- The current repository contains the MCP server, its tool registry, database layer, schema, and CI.
- It has no notebook implementation or filesystem-backed MCP write tool.
- The installed Hermes skills define the vault tiers and an editable `readwrite/` area, but the exact `hermes-vault-sync.py` filename claimed by one subagent was not found; the installed skill refers to `obsidian-vault-sync.py`.

**Gate status: BLOCKED pending an explicit boundary choice.** Do not implement either a filesystem-backed MCP tool or a Hermes skill until the user chooses the delivery target. This is a genuine scope decision because it changes the codebase, security boundary, and what can be delivered through the current PR.

## MVP user workflow

Regardless of boundary, the smallest useful slice is:

1. Draft an observation with an optional Scripture reference.
2. Show the proposed Markdown and provenance to the user.
3. Obtain explicit approval in a separate turn.
4. Save a portable Markdown note.
5. Search by text, Scripture reference, and tag/topic.
6. Find related notes through shared metadata and explicit wiki-links.

Theosis/MCP unavailability must disable enrichment only; local capture and reading must continue.

## Canonical note schema

Use YAML front matter at the beginning of a UTF-8 Markdown file with a stable `id`, `title`, `note_type`, Scripture references, tag/topic list, source references, provenance labels, and ISO timestamps. Keep optional source metadata flat. Use labelled Markdown sections for biblical text, original-language observation, external source, historical/cultural context, user synthesis, and application. The canonical tag field is unresolved: Obsidian research recommends `tags`, while the proposal names `topics`.

## MCP surface and approval model

If the user selects the current repository, the minimal surface is an approval-gated capture operation plus read-only search and related-note operations. The write operation must accurately advertise that it is not read-only, validate the configured root, and refuse without explicit approval. If the user selects the Hermes skill boundary, these operations should be implemented through the existing filesystem/Obsidian skill policy instead of adding write tools to the database MCP server.

## Search and related-note behavior

Search should scan the Markdown source of truth and support case-insensitive body/title text, exact normalized Scripture-reference membership, and case-insensitive tag/topic membership. Related results should report shared Scripture/tag metadata separately from backlinks discovered via `[[note-id]]` or equivalent stable links. Results must be deterministic and bounded.

## Portability and privacy controls

Never read or write the private vault tier. Restrict writes to an explicitly configured editable root, resolve and validate paths, reject traversal/absolute/symlink escapes, preserve UTF-8, and keep secrets, private notes, credentials, database URLs, and machine-specific paths out of GitHub artifacts. Do not migrate the existing vault in the MVP.

## Test and manual-verification matrix

The offline unit and handler tests can run without PostgreSQL or `THEOSIS_MCP_URL`. Required gates are compileall, focused notebook tests, the full suite, a disposable-directory direct workflow, and a Hermes Desktop draft → approve → write → search → related workflow. Live MCP tests remain optional and must report skips exactly.

## Rejected alternatives and reasons

- PostgreSQL-only note storage: rejected for the MVP because it is not portable without Theosis and adds schema/deployment coupling.
- Obsidian-plugin-only behavior: rejected because plain Markdown must remain usable without Obsidian.
- Silent AI writes: rejected for theological integrity, privacy, and user-control reasons.
- Index-first design: deferred until filesystem scanning is measured and the canonical format is stable.
- Real-vault migration during this PR: rejected because existing notes may lack front matter and private content must not enter the repository.

## Open questions deferred beyond the vertical slice

- Should the final implementation be a Hermes skill/Obsidian integration or a filesystem-backed module exposed by this MCP repository?
- Should the canonical property be `tags`, `topics`, or a compatibility alias?
- Should IDs be UUID/ULID or deterministic filename slugs plus an internal stable ID?
- Is PyYAML acceptable as a dependency, or should the first slice use a narrow parser?
- How should concurrent cross-device edits and future vault synchronization be handled?
