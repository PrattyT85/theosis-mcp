# Theosis Research Notebook

## Status

Research completed through the required Hermes Desktop multi-agent workflow. The consolidated findings are in `docs/research/theosis-research-notebook/consolidated-design.md`; the selected implementation boundary is a Hermes skill plus Obsidian `readwrite/` integration, not filesystem write tools in the PostgreSQL MCP server.

## Goal

Add a local-first personal theological knowledge layer to Theosis. Theosis already provides Scripture, original-language data, commentaries, study notes, cross-references, Midrash, and historical context. The notebook should preserve a user's observations and syntheses, connect them to Scripture and sources, and remain portable outside the application.

## Workflow

Model the Jonathan Edwards-inspired workflow:

1. Observe something in Scripture or a research source.
2. Capture it quickly.
3. Restate it in the user's own words.
4. Expand it into an indexed note.
5. Link it to Scripture, topics, and sources.
6. Review related notes later and synthesize them.

## MVP acceptance criteria

- Capture a theological observation as a Markdown note.
- Anchor a note to one or more Scripture references.
- Search by text, reference, and tag.
- Show related notes/backlinks.
- Preserve provenance and distinguish biblical text, original-language observation, external source, user synthesis, and application.
- Keep data readable and usable without Theosis.
- Provide Obsidian-compatible import/export.
- Include tests, documentation, examples, and a manual verification workflow.
- Commit no credentials, private notes, or machine-specific paths.

## Proposed note schema

Use Markdown with YAML front matter. Candidate fields:

```yaml
title: "2 Peter 2:13 — Communal meals and false practice"
note_type: observation # observation, research, synthesis, application
scripture_refs:
  - "2 Peter 2:13"
topics:
  - "false teachers"
  - "communal meals"
source_refs:
  - "Theosis: get_study_notes(2 Peter 2:13)"
provenance: user-synthesis
created: 2026-09-20
updated: 2026-09-20
```

The exact schema must be validated against the existing architecture before implementation.

## Architecture questions

- Is the notebook best implemented in this repository, in a separate Theosis repository, or as a Hermes plugin/integration?
- Should Markdown/Obsidian be canonical, with a local index for search?
- How should Theosis MCP results and source metadata be stored in notes?
- How can the notebook work when Theosis MCP or Hermes is unavailable?
- Which APIs can Hermes Desktop use for planning, delegation, and filesystem work?

## Required Hermes Desktop workflow

Use Hermes Desktop to inspect official Hermes documentation and the relevant repositories, then spawn parallel subagents for:

- product/UX and note-taking workflow research;
- Theosis architecture and integration points;
- Markdown/Obsidian/local-first data modeling;
- provenance, privacy, security, and portability;
- test strategy and acceptance criteria.

Consolidate the reports before implementation. Build a small vertical slice first, exercise it with real tests and a manual workflow, then expand only after the design is verified. Prefer explicit approval before AI writes or modifies user notes.

## Portability requirements

- Markdown files must remain understandable without the application.
- Export/import must not require proprietary services.
- GitHub branches and PRs must contain code, schemas, docs, and tests but never secrets or private vault content.
- Obsidian vault integration should respect separate active, reference, and private areas.
- Any generated note must retain source provenance and clearly label interpretation.

## Related handoff

A more detailed desktop-agent brief is stored in the Obsidian vault as `readwrite/Theosis-Research-Notebook-Desktop-Handoff.md`.
