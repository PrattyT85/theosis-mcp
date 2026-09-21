# Ancient Context MCP Integration

The `theosis_ai` profile now includes the first ancient-corpus status/local-adapter service:

- Repository: https://github.com/PrattyT85/theosis-ancient-context-mcp
- Current source commit: `8b25606` (CDLI adapter and TLHdig support)
- Local checkout: `/home/hermes/repos/theosis-ancient-context-mcp`
- Transport: local stdio; no HTTP port
- Profile server name: `ancient_context`

## Current tools

- `list_corpora`
- `get_corpus_status`
- `search_corpus`
- `get_text`
- `get_text_metadata`

The service registers TLA, Coptic SCRIPTORIUM, HPM/HDivT, CUC, DASI, OCIANA,
CDLI, DPPC, and CIP. It returns explicit status/provenance envelopes rather
than pretending that a source is available when its API, licence, or local
corpus is not ready.

## Current source statuses

- **TLA:** remote/status-only until the public JSON/TEI release or a stable API contract is verified.
- **Coptic SCRIPTORIUM:** optional local adapter; set `COPTSCRIPTORIUM_CORPUS_DIR` to a checked-out, licence-reviewed release.
- **HPM/HDivT:** remote/status-only; the focused TLHdig XML release is now supported as an optional local adapter.
- **TLHdig:** configured locally from Zenodo record 15459134 at `/home/hermes/data/tlh-dig/TLHbasisONLINE25.1_ZENODO`; bounded XML search and CTH/reference retrieval are live-tested.
- **CUC:** configured locally from commit `ad69400f5446e1c8217af01659c7c10ab00c015b`; the corpus is CC BY-NC 4.0 and must not be used as a general public/commercial service without licence review.
- **DASI/OCIANA:** remote/status-only until API contracts are verified.
- **CDLI:** status-only pending REST endpoint verification.
- **DPPC/CIP:** deferred; no public data/API/licence contract confirmed.

The service deliberately does **not** treat ORACC as a Ugaritic corpus. ORACC's
Ugaritic annotation scheme is not a published Ugaritic-language corpus.

## Verification

```text
143 offline tests passed
compileall passed
MCP stdio initialize succeeded
5 tools discovered in Hermes
CUC local search live-tested
TLHdig local status/search/text retrieval live-tested
CDLI search/metadata/ATF adapter live-tested
```

Local corpus adapters are opt-in and do not download or bundle source corpora.
Every result includes source layer, source URL, licence, licence warning, and
access status.
