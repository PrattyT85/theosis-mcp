# Testing and Acceptance Research

## Existing project gates

- CI runs `uv run python -m compileall -q src scripts tests` and `uv run pytest -q` on Python 3.11.
- Live MCP tests are gated by `THEOSIS_MCP_URL` and should not make offline CI dependent on LAN services.
- Existing tests use pure-function fixtures, `tmp_path` where appropriate, and `AsyncMock` for database methods.

## Recommended test matrix

### Notebook module

- YAML/front-matter render/parse round trip.
- Required-field and malformed-front-matter failures.
- Safe YAML behavior and special characters.
- Approval refusal with no file created.
- UTF-8 write/read, stable IDs, duplicate-title handling.
- Path traversal, absolute-path, symlink, and root-boundary rejection.
- Search by text, Scripture reference, tag/topic, and combined filters.
- Related-note discovery through shared metadata and explicit wiki-link backlinks.

### MCP handlers

- Tool registration and accurate read/write annotations.
- Disabled behavior when the notebook root is unset.
- Capture → search → related round trip using a temporary directory.
- No PostgreSQL connection required for notebook handlers.

### Manual workflow

Use a disposable directory, ask Hermes Desktop to draft without writing, approve in a separate turn, capture the Markdown, search it by reference/tag/text, find related notes, and open the files in a plain editor or Obsidian. Do not use the real private vault.

## Required commands

```bash
uv run python -m compileall -q src scripts tests
uv run pytest tests/test_notebook.py tests/test_notebook_tools.py -q
uv run pytest -q
```

Report exact pass and skip counts. If live tests are run without `THEOSIS_MCP_URL`, report their skips rather than claiming live coverage.

## Open decisions

The implementation still needs a final choice of PyYAML versus a narrow parser, exact section headings, `tags` versus the proposal's `topics`, and whether the tool surface belongs in this repository or a Hermes skill.

## Sources

- `.github/workflows/ci.yml`
- `pyproject.toml`
- `tests/mcp_live_client.py`
- `tests/test_mcp_live.py`
- `tests/test_textual_variants.py`
- `.hermes/plans/2026-09-21_230413-theosis-research-notebook.md`
