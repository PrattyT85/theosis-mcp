# Product and UX Research

## Scope

Read-only Hermes Desktop delegation research for the Theosis Research Notebook proposal. Sources were the repository proposal and the Obsidian handoff; no private-vault content was copied.

## Findings

- The core workflow is observe → capture → restate → expand → link → review.
- Quick capture must require very little input: observation text plus an optional Scripture reference should be enough to create a draft.
- AI-generated or AI-transformed content must be presented as a proposal and require explicit approval before writing.
- Theosis/MCP unavailability must degrade enrichment and linking, not prevent local note capture.
- Plain Markdown must remain the usable source of truth; Obsidian-specific plugins should be optional.

## Acceptance criteria

- Capture a theological observation in Markdown with front matter.
- Anchor it to at least one Scripture reference.
- Search by text, Scripture reference, and tag/topic.
- Demonstrate related-note/backlink discovery.
- Make provenance layers visible and keep interpretation distinct from source text.
- Round-trip through ordinary Markdown without proprietary services.
- Exercise automated tests and a manual draft → approval → write → search workflow.

## Risks

- Too many required fields or approval steps may make quick capture unusable.
- Automatic Scripture/reference linking can create noisy backlinks.
- A rigid schema may not fit future note types.
- Concurrent edits across devices can create Git conflicts.

## Recommendation

Keep the first slice small: approval-gated capture, deterministic Markdown storage, search, and related-note lookup. Treat AI enrichment and automatic reference detection as optional follow-up behavior.

## Sources

- `docs/plans/theosis-research-notebook.md`
- The read-only Obsidian Desktop handoff document
- Hermes Desktop and delegation documentation reviewed before delegation.
