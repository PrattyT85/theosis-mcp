# Theosis Historical and Cultural Context Expansion Plan

> **For Hermes:** Execute this plan task-by-task with focused subagents and independent review; keep live infrastructure work in the parent controller.

**Goal:** Extend the `theosis_ai` research profile from curated ANE and Jewish interpretive context to a verified primary-source Greek/Latin and Mesopotamian context layer, without mixing source traditions or losing provenance.

**Architecture:** Keep the existing Theosis Bible (8000), Midrash (8001), and Sefaria Context (8002) services separate. Add Perseus as a pinned local stdio MCP server for Greek/Latin primary texts and add a separate ORACC MCP wrapper for structured cuneiform data. Record configuration and verification steps in GitHub; do not import copyrighted corpora into Theosis databases.

**Tech Stack:** Python 3.11+, uv, FastMCP/MCP stdio, pytest, Hermes profile configuration, Perseus/Scaife CTS and search APIs, ORACC JSON open data.

---

## Baseline already verified

- `get_ane_context` was repaired before this plan began. Live `Genesis 1:1` now returns title, summary, detail, ANE parallels, interpretive significance, key references, and scholarly sources.
- Theosis MCP CI for commit `9e7a1d4` is green.
- Theosis MCP exposes 31 tools; Midrash exposes 9; Sefaria Context exposes 8.
- Theosis profile config is `/home/hermes/.hermes/profiles/theosis_ai/config.yaml`.

## Task 1: Document and verify the repaired ANE tool

**Objective:** Make the repair durable with a stable live regression and explicit release note.

**Files:**
- Modify: `tests/test_ane_context.py`
- Modify: `docs/` release or capability documentation as appropriate

**Acceptance:**
- Offline ANE tests pass.
- Live test asserts non-empty summary/detail/parallels for Genesis 1:1.
- GitHub Actions is green on the pushed commit.
- Live endpoint reports the deployed commit containing the repair.

## Task 2: Pin and configure Perseus MCP

**Objective:** Add the maintained MIT-licensed Perseus MCP server as a fourth research source without conflicting with Sefaria port 8002.

**Implementation:**
- Use the released `perseus-mcp` package or a pinned upstream commit; do not use an unpinned mutable `latest` command.
- Add a disabled-by-default or explicitly enabled `perseus` entry to the `theosis_ai` profile after local handshake and live API smoke tests pass.
- Set an absolute cache directory and conservative upstream request behavior.
- Document the exact package/revision, command, tools, and verification in Theosis GitHub documentation.

**Acceptance:**
- Stdio MCP handshake succeeds.
- Tool discovery includes passage retrieval, author/work discovery, and search.
- A live read-only smoke test discovers Philo/Josephus where advertised and retrieves a representative passage or returns a documented upstream limitation.
- Profile discovery shows the server enabled and the Theosis/Midrash/Sefaria servers unchanged.

## Task 3: Build an ORACC MCP wrapper

**Objective:** Provide read-only, provenance-preserving access to ORACC projects and cuneiform text editions.

**New repository:** `/home/hermes/repos/theosis-oracc-mcp`, GitHub `PrattyT85/theosis-oracc-mcp`.

**Minimum tools:**
- `list_projects(query=None, limit=50)` — discover public ORACC projects.
- `get_project_metadata(project)` — retrieve and validate `metadata.json`.
- `get_project_manifest(project)` — retrieve available JSON files.
- `list_project_texts(project, query=None, limit=50)` — catalogue-based text discovery.
- `get_text(project, text_id)` — retrieve the exact corpus JSON and return a normalized excerpt plus source URL/project/text ID.
- `search_project(project, query, limit=20)` — search local project catalogue and fetched corpus/index data with bounded requests.

**Rules:**
- Read-only only; no bulk mirroring or database.
- Validate project and text identifiers against strict path-safe patterns.
- Preserve exact ORACC URL, project, text ID, language, genre, period, provenance, and licence attribution.
- Bound response size and request concurrency; cache metadata/catalogue responses only with explicit TTL.
- Never present transliteration, translation, or generated excerpts as the same layer.

**Acceptance:**
- Unit tests cover URL safety, JSON shape validation, response limits, malformed upstream data, and provenance.
- Live smoke test uses `projects.json`, one project manifest, and one representative text from an approved project.
- CI is green and repository is pushed to GitHub.
- The local `theosis_ai` profile launches the wrapper through a pinned local command and discovers all tools.

## Task 4: Integrate and verify the complete profile

**Objective:** Enable Perseus and ORACC alongside the existing three Theosis services and verify the full research toolchain.

**Parent-controlled operations:**
- Update `/home/hermes/.hermes/profiles/theosis_ai/config.yaml` only after each server passes its independent smoke tests.
- Keep Home Assistant, UniFi, and Proxmox MCP servers disabled in the theology profile.
- Use a new profile session after configuration changes.

**Acceptance:**
- `hermes --profile theosis_ai mcp list` shows five enabled research servers: Theosis, Midrash, Sefaria Context, Perseus, and ORACC.
- `hermes --profile theosis_ai mcp test` succeeds for all five.
- Existing three endpoints still expose the expected tools.
- A cross-source smoke report documents one query path through ANE, Sefaria/Midrash, Perseus, and ORACC.

## Task 5: Final review, release, and documentation

**Objective:** Ensure GitHub and deployed state are synchronized and the workflow is reproducible.

**Verification:**
- Run each repository's offline tests and compile checks.
- Run live read-only tests with explicit endpoint variables.
- Check GitHub Actions status for every changed repository.
- Record commit SHAs, package versions, MCP tool counts, and known limitations.
- Do not tag or claim completion until the deployed checkouts match pushed commits.

**Rollback:** Remove only the new Perseus/ORACC profile entries and stop their local processes; leave Theosis, Midrash, and Sefaria databases untouched. Revert the integration documentation commits if necessary.
