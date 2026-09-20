# Ancient Egyptian, Hittite, and Northwest Semitic Expansion Plan

> **For Hermes:** Execute this plan with focused subagents, independent reviews, and live/read-only verification. Do not claim a corpus is integrated until a representative text retrieval and provenance test pass.

**Goal:** Add a source-layered ancient-context MCP service covering Egyptian, Hittite, Northwest Semitic/epigraphic, and Coptic sources alongside the existing Theosis, Midrash, Sefaria, Perseus, and ORACC services.

**Architecture:** Keep each corpus separate from the Bible and Midrash databases. Build a new read-only local stdio MCP repository, `PrattyT85/theosis-ancient-context-mcp`, with adapter modules and explicit corpus metadata. Do not bulk-copy restricted texts into PostgreSQL. Use remote/on-demand retrieval where licensing or service stability requires it; use a local corpus only when the source release and licence permit it.

**Client integration:** Add one local stdio MCP entry to the `theosis_ai` profile after independent smoke tests. Avoid new HTTP ports unless a source adapter requires one. The service must label every result as primary text, epigraphic record, translation, commentary, or corpus metadata and include source URL, stable identifier, language, period, edition, and licence where available.

---

## Existing baseline

- Theosis Bible MCP: 31 tools, including repaired `get_ane_context`.
- Theosis Midrash: 9 tools, 21 works, 45 editions, 29,367 segments.
- Sefaria Context: 9 tools, Targums and selected Mishnah/commentary.
- Perseus MCP: pinned `perseus-mcp==1.0.2`, 23 tools.
- ORACC MCP: archive-backed implementation, latest source commit to be recorded after this expansion.
- All current repositories are clean and CI-backed.

## Corpus targets

### Egyptian

- Thesaurus Linguae Aegyptiae (TLA): hieroglyphic/hieratic/Demotic text corpus and lemma search; stable text/sentence IDs and object metadata.
- Coptic SCRIPTORIUM: later Egyptian/Coptic annotated corpora, aligned translations where available, and released TEI/CoNLL-U/ANNIS data.

### Hittite

- Hethitologie-Portal Mainz (HPM): Hittite text editions, catalogues, images, and metadata.
- Hittite Corpus of Divinatory Texts (HDivT): focused annotated divination corpus and cultural-historical metadata.
- Hittite treaty and ritual collections only after source/edition and licence validation.

### Northwest Semitic and adjacent epigraphy

- Ugaritic: use only a verified open/reusable corpus or a source-approved remote retrieval path; do not present ORACC Ugarit-related projects as a complete Ugaritic-language corpus without language metadata validation.
- Phoenician/Punic: investigate the Digital Phoenician-Punic Corpus and other open epigraphic data; integrate only where stable access and licensing are confirmed.
- DASI/CSAI and OCIANA: Ancient South/North Arabian epigraphic comparanda, explicitly labelled as adjacent Semitic evidence rather than Northwest Semitic proper.

## Phase 0: Source and licence reconnaissance

Run independent read-only audits for each source. Record exact URLs, access method, stable identifiers, licence terms, representative references, and whether an API/export is available. Do not write adapters until each source has a passing probe and a documented failure mode.

**Gate:** Every source receives one of `ready_for_adapter`, `remote_only`, `licence_review`, or `defer`; no source is silently treated as integrated.

## Phase 1: Common MCP service

Create `PrattyT85/theosis-ancient-context-mcp` with:

- `list_corpora()`
- `get_corpus_status(corpus)`
- `search_corpus(corpus, query, limit=20)`
- `get_text(corpus, reference)`
- `get_text_metadata(corpus, reference)`
- `get_lexical_entry(corpus, query)` where supported

Implement shared response envelopes with `corpus`, `source_type`, `language`, `period`, `reference`, `edition`, `source_url`, `licence`, `retrieved_at`, and `content`. Enforce bounded response size, URL/path safety, timeouts, no credentials, and no persistent cache by default.

Add deterministic offline tests for every adapter and a `LIVE=1` smoke suite that calls one representative reference per enabled source. CI must never depend on live upstream services.

## Phase 2: Implement adapters in priority order

1. TLA adapter: search and stable-ID retrieval; preserve transliteration, translation, lemma, dating, script, object and cultural-context metadata.
2. HPM/HDivT adapter: start with catalogue/search and one divination/treaty retrieval path; explicitly report fragments and edition status.
3. DASI/OCIANA adapter: search epigraphic records and retrieve stable records with geographic/provenance metadata.
4. Coptic SCRIPTORIUM adapter: use a pinned public corpus release or a read-only remote endpoint; support corpus search and stable document retrieval.
5. Ugaritic adapter: only after the source/format/licence gate passes; use a curated open dataset or remote source and label language/edition precisely.
6. Phoenician/Punic adapter: only after stable public access and licence validation; otherwise provide a documented discovery-only status rather than scraping around restrictions.

## Phase 3: Integration and profile verification

- Add the new stdio MCP entry to `/home/hermes/.hermes/profiles/theosis_ai/config.yaml` only after the service handshake and each enabled adapter smoke test pass.
- Keep existing theological MCP servers unchanged.
- Verify `hermes --profile theosis_ai mcp test ancient_context` and all existing server tests.
- Run a cross-source query matrix: Egyptian creation/temple, Hittite divination/treaty, Ugaritic divine council if available, Arabian epigraphy, and Coptic Christian text.

## Phase 4: Documentation and release

- Add source-layer guidance to theosis-mcp documentation.
- Record exact repository commit, corpus versions, licence decisions, smoke references, and known gaps.
- Push all repositories and wait for CI success.
- Do not declare completion for a source whose live retrieval remains blocked; report it as remote-only or deferred.

## Rollback

Remove only the new profile entry and stop the new local process. Do not alter Theosis, Midrash, Sefaria, Perseus, or ORACC databases. Revert only the new documentation/repository commits if required.
