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

## Source and Licence Rules

- Record `source_refs` for every external source used.
- Preserve `source_licences` alongside each source reference.
- When the licence is unknown, mark it as `licence: unknown` — never invent licence text.
- Record `retrieved_at` as an ISO datetime for each external retrieval.
- Preserve edition identifiers (e.g. LSJ, BDB, Aquifer, Tyndale) in `source_refs`.
- Keep the provenance label honest: if a section mixes layers, label the dominant one and note the exception.

## Retrieval Metadata

| Field | Purpose |
|-------|---------|
| `retrieved_at` | When the external source was accessed (ISO datetime) |
| `source_refs` | Machine-readable tool calls or URLs (e.g. `Theosis: word_study(G3650)`) |
| `source_licences` | Licence string per source (e.g. `CC BY 4.0`, `Public Domain`) |

## Attribution Rules

- The note author is the user, not AI.
- Never silently attribute AI-generated content to a named human source.
- If content is AI-drafted, label it in the `User synthesis` section with the user's final approval.
- Source-derived text (biblical, original-language, external) must never be rendered as user interpretation.
