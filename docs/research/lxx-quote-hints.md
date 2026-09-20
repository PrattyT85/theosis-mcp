# NT↔OT/LXX quotation-hint research

## Decision

**Defer the table for now.** No single verified open dataset supplies both stable NT↔OT mappings and scholarly LXX/MT divergence annotations. A computed partial import is possible, but it would leave the most important scholarly fields empty or misleading.

## Candidate sources

### bible-cli

- Repository: [Divine-Creative-Ministries/bible-cli](https://github.com/Divine-Creative-Ministries/bible-cli)
- Code licence: MIT.
- Data: STEPBible TAGNT/TAHOT CC BY 4.0, Swete LXX CC BY-SA 4.0, OpenBible cross-references CC BY.
- Format: offline SQLite databases and JSON CLI output.
- Method: computed lemma-run tiers (`quotation`, `allusion`, `echo`), not a fully curated textual-critical dataset.
- Limitation: does not reliably supply `follows_lxx`, `divergence_type`, or `divergence_note` as scholarly annotations.

### Other sources reviewed

- [OpenBible.info cross-references](https://www.openbible.info/labs/cross-references/) — CC BY 4.0, already represented in Theosis; thematic/catchword links are not a dedicated NT↔OT quotation corpus.
- [STEPBible Data](https://github.com/STEPBible/STEPBible-Data) — CC BY 4.0; contains relevant texts but not a ready quotation mapping table.
- [Clear-Bible speaker-quotations](https://github.com/Clear-Bible/speaker-quotations) — CC BY 4.0; tracks quotation marks and speaker attribution, not NT use of the OT/LXX.

## Schema mapping if a partial import is approved later

- `nt_reference`, `nt_display`, `nt_book`: computed NT reference.
- `ot_reference`, `ot_display`, `ot_book`: computed OT/LXX reference.
- `follows_lxx`: leave NULL or explicitly mark `computed`, not an unqualified `1`.
- `divergence_type`, `divergence_note`: NULL until scholarly review.
- `textual_variant_id`: link only when a verified NT variant relation exists.

A defensible initial corpus would include only high-confidence explicit quotations, not speculative allusions/echoes, and would label the result as computed rather than curated.

## Example validation reference

A future reviewed row could use:

```text
Matthew 1:23 -> Isaiah 7:14
```

The divergence note would need to document the LXX `παρθένος` reading versus the MT `עַלְמָה` reading and cite the textual source used for the annotation. Do not create this row solely from a lemma-match algorithm.

## Current action

Keep `nt_ot_lxx_quote_hints` empty. The method now points to the correct table and safely returns no rows. Revisit only after a curated dataset or an explicitly approved computed-first workflow is available.
