# Provenance Taxonomy

Every research note MUST declare a provenance label that identifies the primary content layer. The six layers are:

## Six-Layer Taxonomy

| Layer | Label | Description |
|-------|-------|-------------|
| 1. Biblical text | `biblical-text` | Direct quotation or paraphrase from Scripture; cite book, chapter, verse, and translation. |
| 2. Original-language observation | `original-language` | Greek, Hebrew, or Aramaic word study, morphology, or syntax; cite Strong's number, lexicon, and source edition. |
| 3. External source | `external-source` | Commentary, dictionary, encyclopedia, or tool output from Theosis or another source; preserve source name, author, and edition. |
| 4. Historical/cultural context | `historical-context` | Archaeological, historical, or cultural background; distinguish primary source from scholarly interpretation. |
| 5. User synthesis | `user-synthesis` | The user's own interpretation, connecting insights across sources. Clearly separate from sourced material. |
| 6. Application | `application` | Practical, devotional, or study application drawn from the synthesis. |

## Source, Licence, and Retrieval Rules

- Record `source_refs` for every external source used. Each entry MUST preserve the actual tool name and arguments (e.g. `theosis_mcp.get_study_notes(reference='2 Peter 2:13')`), not a generic label.
- Preserve `source_licences` alongside each source reference.
- When the licence is unknown, mark it as `licence: unknown` — never invent licence text.
- Record `retrieved_at` as an ISO datetime for each external retrieval.
- Preserve edition identifiers (e.g. LSJ, BDB, Aquifer, Tyndale) in `source_refs`.
- Keep the provenance label honest: if a section mixes layers, label the dominant one and note the exception.

### Positional Multi-Source Alignment

When multiple sources are used, `source_refs`, `source_licences`, and `retrieved_at` are positionally aligned — entry N in each list corresponds to the same source:

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

### Retrieval Metadata

| Field | Purpose |
|-------|---------|
| `retrieved_at` | When the external source was accessed (ISO-8601 datetime, e.g. `2026-09-20T10:00:00Z`) |
| `source_refs` | Machine-readable tool calls with arguments (e.g. `theosis_mcp.get_study_notes(reference='2 Peter 2:13')`) |
| `source_licences` | Licence string per source (e.g. `CC BY 4.0`, `Public Domain`, `unknown`) |

## Attribution and AI Labelling Rules

- The note author is the user, not AI.
- Never silently attribute AI-generated content to a named human source.
- If content is AI-drafted, label it in the `User synthesis` section with the user's final approval.
- Source-derived text (biblical, original-language, external) must never be rendered as user interpretation or synthesis.
