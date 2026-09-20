# ORACC MCP Integration

The Theosis research profile can launch the read-only ORACC wrapper from:

- Repository: https://github.com/PrattyT85/theosis-oracc-mcp
- Pinned source commit: `26f379a` (archive-backed implementation)
- Local checkout: `/home/hermes/repos/theosis-oracc-mcp`
- Transport: local stdio; no HTTP port
- Source: https://oracc.museum.upenn.edu/
- ORACC JSON documentation: https://oracc.museum.upenn.edu/doc/opendata/json/

## Hermes profile entry

The `theosis_ai` profile uses the checked-out repository rather than an unpinned
package download:

```yaml
oracc:
  command: uv
  args:
    - --directory
    - /home/hermes/repos/theosis-oracc-mcp
    - run
    - oracc-mcp
  enabled: true
  timeout: 120
  connect_timeout: 60
```

The server is read-only and exposes six tools: project discovery, project
metadata/manifest, catalogue text discovery, bounded text retrieval, and
catalogue search. It preserves the source URL, project, text ID, catalogue
metadata, and separate transliteration/translation fields where supplied by
ORACC. It does not mirror ORACC into PostgreSQL.

## Verification

Verified locally:

```text
42 offline tests passed
compileall passed
MCP stdio initialize succeeded
6 tools discovered
```

The wrapper's live smoke test is:

```bash
cd /home/hermes/repos/theosis-oracc-mcp
ORACC_LIVE=1 uv run python scripts/smoke_live.py
```

This host's Python trust store needed the public InCommon RSA Server CA 2
intermediate added to a local bundle at
`/home/hermes/.cache/oracc-ca-bundle.pem`; the profile passes that path as
`SSL_CERT_FILE`. Do not disable TLS verification.

ORACC's current JSON delivery is archive-based. The wrapper uses
`https://oracc.museum.upenn.edu/json/<project-archive>.zip`, extracts only the
requested bounded member in memory, and preserves the archive URL plus member
path as provenance. The live smoke test passed against the `rimanum` archive:
144 projects discovered, 378 catalogue entries, and non-empty CDL text
retrieved from `P296047`.

Some catalogue entries are zero-byte witnesses; the smoke test skips those and
selects the first non-empty text. The local MCP handshake and tool discovery do
not require ORACC to be online; individual content tools do.

## Attribution and licensing

ORACC data is attributed to the University of Pennsylvania and its project
contributors. Follow the licence and attribution information returned by the
specific project before copying or redistributing any text. The wrapper itself
is MIT licensed. Treat transliteration, translation, catalogue metadata, and
scholarly annotations as distinct source layers.
