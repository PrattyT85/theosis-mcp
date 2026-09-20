# Empty Theosis tables

The live database contains several empty tables inherited from the broader schema. They are not all missing features; some are legacy or reserved for datasets that have not been verified.

## No import required now

| Table | Decision | Reason |
|---|---|---|
| `ane_context` | Leave empty | The active ANE implementation uses populated `ane_entries` (120 rows), not this legacy table. |
| `bible_extra_biblical` | Leave empty | The active corpus is `extra_biblical_texts`; importing the same data would create two competing sources. |
| `theology_theme_index` | Leave empty | The active theme data is in `theology_themes` and `theological_themes`. |
| `graph_people_groups` / `graph_person_group_edges` | Defer | No verified source or current MCP feature requires these tables. |
| `hlt_annotations` / `hlt_study_notes` | Defer | No validated HLT dataset is currently staged; Heiser material is already represented in the active theology/content tables. |

## Future candidates

### `manuscript_witnesses`

The repository has an importer for SWORD SBLGNT/VarApp modules, but the required modules are not installed on CT125. Do not populate this table with invented witness rows. Acquire and licence-check the modules first, then run a bounded import and verify representative textual variants through MCP.

### `nt_ot_lxx_quote_hints`

The schema is ready for NT↔OT/LXX quotation hints, but no verified dataset is currently staged. The database method now points to this actual table and safely returns no rows until a source is imported. Add a source only after validating reference normalization, LXX alignment, divergence notes, and links to `textual_variants`.

## Review rule

Do not populate an empty table merely to make the row count non-zero. Add a table only when there is a source dataset, clear provenance/licence metadata, an MCP use case, and a representative verification test.
