# Architecture and Integration Research

## Findings

- `/home/hermes/repos/theosis-mcp` is a PostgreSQL-backed Python MCP server. Existing tools are exposed through `src/theosis_mcp/tools.py`, dispatched by `_TOOL_HANDLERS` in `src/theosis_mcp/server.py`, and tested with offline unit tests plus optional live MCP tests.
- Existing Theosis tools are read-only database queries. The repository has no existing notebook module, filesystem-backed MCP write tool, or notebook schema.
- A separate Hermes skill/Obsidian-vault workflow is a cleaner ownership boundary for Markdown CRUD and vault policy because Hermes already has the relevant filesystem and Obsidian skills.
- The current branch and product proposal, however, are in this Theosis MCP repository and the requested delivery is a GitHub PR from this branch.

## Recommendation from the architecture subagent

Implement the notebook as a Hermes skill plus Obsidian-vault filesystem workflow rather than adding file I/O to the database MCP server. This avoids coupling vault writes to the Theosis PostgreSQL process and keeps the notebook available when Theosis is offline.

## Verification and caveat

The subagent referred to a `hermes-vault-sync.py` file; that exact file was not found. The installed skill documents an `obsidian-vault-sync.py` cron workflow and three vault tiers (`readwrite/`, `readonly/`, `private/`). The recommendation remains plausible, but the target-delivery conflict is unresolved.

## Extension points if the current PR remains the target

- A pure filesystem module could live at `src/theosis_mcp/notebook.py`.
- Offline handlers could be added to `src/theosis_mcp/server.py` without opening PostgreSQL for notebook operations.
- Tool descriptors belong in `src/theosis_mcp/tools.py`.
- No `schema.sql` changes are needed for a Markdown-canonical MVP.

## Blocker

The architecture recommendation and the existing PR target disagree. Do not implement until the user chooses whether this PR should contain a filesystem-backed Theosis MCP slice or whether the deliverable should instead be a Hermes skill/Obsidian integration outside this repository.

## Sources

- `README.md`
- `pyproject.toml`
- `src/theosis_mcp/server.py`
- `src/theosis_mcp/tools.py`
- `src/theosis_mcp/database.py`
- `schema.sql`
- `tests/mcp_live_client.py`
- `/home/hermes/.hermes/skills/software-development/theosis-mcp/SKILL.md`
- Hermes Desktop/delegation documentation.
