# Perseus Digital Library Integration

Perseus MCP provides direct access to the [Perseus Digital Library](http://www.perseus.tufts.edu/hopper/) — ancient Greek and Latin texts, CTS navigation, and Scaife search — as a local stdio MCP server. This document covers how to install, pin, run, and smoke-test it within the Theosis research stack.

## Why Perseus

Theosis already has strong biblical coverage (140+ translations, Hebrew/Greek lexicons, church fathers, ANE parallels). Perseus complements it by exposing classical Greek and Latin literary sources — Homer, Thucydides, Plato, the Septuagint in its own critical editions — that are outside the Bible-focused Scrollmapper and StudyBible-MCP catalogue. For NT textual criticism, Perseus Scaife also provides morphological search and manuscript-variant browsing for the LXX and other Hellenistic corpora.

## Upstream

| Field | Value |
|---|---|
| Repository | [tonyjurg/Perseus-mcp](https://github.com/tonyjurg/Perseus-mcp) |
| Licence | MIT |
| PyPI | [perseus-mcp](https://pypi.org/project/perseus-mcp/) |
| Latest tagged release (research date 2026-09-20) | **v1.0.2** — commit `20c211c` (2026-06-26) |
| Python requirement | ≥ 3.11 |
| Server type | Local stdio (FastMCP) |
| Network dependency | Yes — every `tools/call` fetches from `scaife.perseus.org` or `cts.perseus.org` |
| Total MCP tools | 23 |

## Pinned version strategy

Perseus MCP is a **fast-moving external dependency** that does not publish a changelog or API compatibility guarantee. Pin it to a known-good immutable reference, never to `latest`.

### Recommended approach

1. **Pin the git tag + commit hash** when cloning the upstream repo:

```bash
PERSEUS_TAG="v1.0.2"
PERSEUS_COMMIT="20c211cc5eb30fca86f03ff20c7c7ba759a9f9e3"
git clone --branch "$PERSEUS_TAG" --depth 1 https://github.com/tonyjurg/Perseus-mcp.git
```

2. **Or pin the PyPI version** in a constraints file:

```bash
echo "perseus-mcp==1.0.2" > constraints-perseus.txt
uv --directory /path/to/Perseus-mcp --constraint constraints-perseus.txt run perseus-mcp
```

3. **Record both the tag and commit SHA** in your deployment manifest or commit message so future auditors can verify exactly which revision is deployed.

### Upgrade process

When a new upstream release appears:

1. Review the upstream changelog/commits for breaking tool changes (renamed tools, changed parameters, removed tools).
2. Pin the new tag in this repo's documentation and your deployment manifest.
3. Run the smoke test (`scripts/perseus_smoke_test.py`) against the new revision before deploying.
4. Do not auto-update; treat it like a manual dependency bump.

## Installation

Clone and install into a dedicated directory:

```bash
INSTALL_DIR="/opt/perseus-mcp"
git clone --branch v1.0.2 https://github.com/tonyjurg/Perseus-mcp.git "$INSTALL_DIR"
cd "$INSTALL_DIR"
uv sync  # creates .venv with all dependencies
```

### Verification

```bash
cd "$INSTALL_DIR"
uv run python -c "import perseus_mcp; print('perseus-mcp importable')"
```

## Running the server

Perseus MCP is a local **stdio** transport server — no HTTP port, no port conflict with Sefaria Context (port 8002) or Theosis (ports 8000–8001).

```bash
# Standard invocation via uv (uses the cloned checkout's .venv):
uv --directory /opt/perseus-mcp run perseus-mcp

# Or activate the venv first:
source /opt/perseus-mcp/.venv/bin/activate
perseus-mcp
```

The server reads MCP JSON-RPC on stdin and writes to stdout. The Hermes MCP client handles the transport.

### Cache directory

Perseus MCP maintains a local metadata cache. The default location is:

```
~/.cache/perseus-mcp/
```

For a dedicated service user, set `XDG_CACHE_HOME` in the systemd unit:

```ini
[Service]
Environment=XDG_CACHE_HOME=/opt/perseus-mcp/cache
```

Or set the upstream `PERSEUS_MCP_CACHE_DIR` environment variable if supported.

To inspect the cache:

```bash
ls -la ~/.cache/perseus-mcp/
# or via MCP tool:
# get_cache_status()
```

## Key tools for theological research

Of the 23 tools, these are most relevant to biblical and ancient Near Eastern research:

| Tool | Purpose | Theosis use case |
|---|---|---|
| `get_passage(urn)` | Fetch a CTS passage (XML) | Raw apparatus, alignment |
| `get_passage_plus(urn)` | Fetch passage with contextual metadata | Text with surrounding info |
| `get_passage_plaintext(urn)` | Fetch a CTS passage as plain text | Read LXX, Homer, Thucydides in context |
| `get_valid_references(urn)` | Retrieve navigable citation references | Discover chapter/line structure |
| `get_valid_references_json(urn)` | Paged citation references as JSON | Browse large reference trees |
| `count_valid_references(urn)` | Count valid references without full list | Quick size estimate |
| `get_capabilities()` | List all available texts/editions | Discover which LXX editions are available |
| `get_cache_status()` | Inspect local metadata cache state | Verify cache is populated |
| `refresh_metadata_cache()` | Refresh cached CTS/Scaife metadata | Update cached text catalogue |
| `clear_metadata_cache()` | Clear in-memory and disk cache | Reset cache on stale metadata |
| `list_text_groups(language)` | Browse authors by language | Discover Greek and Latin corpora |
| `get_author_resources(author)` | List works and editions for an author | Enumerate all available Philo editions |
| `find_author_names(query)` | Find author/textgroup names by partial match | Locate Philo, Josephus, Origen by name |
| `get_work_resources(urn_or_title)` | List editions, translations for a work | Find all available Iliad or LXX Genesis editions |
| `get_label(urn)` | Fetch human-readable metadata labels | Display title/author for a URN |
| `get_first_urn(urn)` | Get the first navigable URN under a work | Start of a text for iteration |
| `get_prev_next_urn(urn)` | Get neighboring passage URNs | Sequential navigation |
| `search_perseus(query, language, ...)` | Full-text search via Scaife | Find Greek terms across classical and biblical corpora |
| `search_within_text(query, text_urn)` | Search within one edition | Morphological search in a specific LXX book |
| `get_passage_highlights(query, passage_urn)` | Get Scaife token highlight positions | Highlight search matches in context |
| `get_scaife_library_metadata(urn)` | Get Scaife JSON metadata for a library | Machine-readable catalogue |
| `get_scaife_passage_json(urn)` | Get Scaife JSON for a passage | Structured passage data |
| `get_scaife_passage_text(urn)` | Fetch Scaife plaintext | Alternative plaintext path via Scaife |

### CTS URN format

Perseus uses Canonical Text Services URNs. Examples:

```
urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1.1    # Homer, Iliad, Book 1, Line 1
urn:cts:greekLit:tlg1271.tlg001.perseus-grc1:1:1     # Philo, De Opificio Mundi 1.1
urn:cts:latinLit:phi1294.phi002.perseus-lat2:1.1      # Vergil, Aeneid, Book 1, Line 1
```

For LXX, the Perseus catalog uses different textgroup identifiers than the traditional Rahlfs numbering. Use `search_perseus` or `get_work_resources` with the book title to discover the correct URN.

## Upstream rate limits and caveats

Perseus MCP proxies requests to Scaife and CTS servers. Be aware of:

1. **Rate limits**: The Perseus/Scaife servers enforce rate limits. Heavy batch queries (e.g., iterating over all 24,000+ verses of the Iliad) will trigger throttling or temporary bans. Space requests with delays or cache aggressively.

2. **No local data**: Unlike Theosis (which stores text in PostgreSQL), every Perseus MCP tool call makes a live HTTP request. There is no offline fallback for text retrieval.

3. **Cache is metadata-only**: The local cache stores library metadata (text lists, editions), not actual text content. You still fetch text on every `get_passage` call.

4. **XML payloads**: Some tools return raw CTS XML, which requires parsing. Use `get_passage_plaintext` or `get_scaife_passage_text` for plain text when possible.

5. **Greek search encoding**: The `search_perseus` tool accepts Unicode Greek or Beta Code. Use `query_format="auto"` (the default) for convenience, or specify `"betacode"` / `"unicode"` explicitly for ambiguous input.

6. **Server availability**: Perseus Digital Library servers occasionally go down for maintenance. Do not depend on Perseus MCP for critical-path workflows without a local fallback.

## Source and licence boundaries

| Source | Licence | Notes |
|---|---|---|
| Perseus MCP (tonyjurg) | MIT | The MCP server wrapper itself |
| Perseus Digital Library (Tufts) | [CC BY](http://www.perseus.tufts.edu/hopper/text?doc=Perseus%3Aabout%3Aterms) | Original scholarly content and texts |
| Scaife (Perseus) | CC BY | Search API and JSON metadata |
| Individual texts | Varies by edition | Check Perseus catalog for per-work licence |

**Do not** cache or redistribute Perseus text content in the Theosis PostgreSQL database without verifying the per-work licence. Theosis's own corpus (Scrollmapper, StudyBible-MCP) has its own licence terms. Treat Perseus as a read-only, on-demand reference source.

## Discovery and smoke-test workflow

Run this deterministic sequence to verify the installation without hitting the network:

```bash
# 1. Verify the package is importable
cd /opt/perseus-mcp
uv run python -c "import perseus_mcp; print('OK')"

# 2. Run the offline smoke test (no network required)
uv run python /path/to/theosis-mcp/scripts/perseus_smoke_test.py

# 3. Verify the command is on PATH
uv --directory /opt/perseus-mcp run which perseus-mcp

# 4. (Optional, requires network) Quick live probe
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{}}}' | \
  uv --directory /opt/perseus-mcp run perseus-mcp
```

The smoke test (`scripts/perseus_smoke_test.py`) validates:
- Package importability
- Expected tool names are present
- CTS URN parsing logic
- Greek normalization (NFC) for search queries
- Beta Code detection heuristic

No network calls are made by the smoke test.

## Hermes profile entry template

Add Perseus as a **stdio** MCP entry in the `theosis_ai` profile's `config.yaml`. Use the path that matches your deployment:

```yaml
# ~/.hermes/profiles/theosis_ai/config.yaml  (MCP section)
mcp:
  servers:
    # --- Existing theological servers (HTTP) ---
    theosis-bible:
      transport: streamable-http
      url: http://192.168.1.130:8000/mcp

    theosis-midrash:
      transport: streamable-http
      url: http://192.168.1.130:8001/mcp

    sefaria-context:
      transport: streamable-http
      url: http://192.168.1.130:8002/mcp

    # --- Perseus (stdio, local) ---
    perseus:
      transport: stdio
      command: uv
      args:
        - --directory
        - /opt/perseus-mcp   # <-- CHANGE to your actual install path
        - run
        - perseus-mcp
      env:
        XDG_CACHE_HOME: /opt/perseus-mcp/cache   # <-- CHANGE or omit for default
```

**Important**: Replace `/opt/perseus-mcp` with the actual absolute path where you cloned Perseus-mcp. This path must exist on the Hermes host before starting the session.

After adding the entry, restart the Hermes Desktop session or run:

```bash
hermes --profile theosis_ai mcp list
hermes --profile theosis_ai mcp test perseus
```

## Integration boundaries

| Concern | Handled by Theosis | Handled by Perseus MCP |
|---|---|---|
| Bible text lookup | ✅ (PostgreSQL) | ❌ |
| Hebrew/Greek lexicons | ✅ (StudyBible-MCP) | ❌ |
| Classical Greek literature | ❌ | ✅ (Perseus Digital Library) |
| Latin literature | ❌ | ✅ (Perseus Digital Library) |
| LXX critical editions | ❌ | ✅ (Perseus CTS) |
| Church fathers (Greek) | Partially (via extra_biblical_texts) | Partially (Philo, Origen if in Perseus catalog) |
| Morphological search | Strong's-based | Scaife-based (complementary) |
| ANE parallels | ✅ (ane_entries table) | ❌ |
| Data storage | PostgreSQL (persistent) | Cache only (metadata); text fetched live |

Do not use Perseus MCP as a replacement for Theosis's biblical tools. They serve different text domains and should coexist in the profile.
