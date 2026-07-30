<!-- tapps-generated: v3.12.52 -->
# Copilot Instructions

This project uses **TappsMCP** (Code Quality MCP Server) for automated
quality analysis. When TappsMCP is available as an MCP server, follow
the pipeline below.

## TappsMCP Quality Pipeline

### Stage 1: Discover
- Run `tapps_session_start` at the beginning of each session to initialize context
- Brain memory is bridge-only: use `uv run tapps-mcp memory search --query "..."` or pinned keys in `.tapps-mcp.yaml` → `memory_hooks.auto_recall.recall_keys`. When `nlt-memory` is enabled, `tapps_memory` MCP is a slim facade on that server.
- Recall prior decisions: `uv run tapps-mcp memory search --query "..."` or read `.tapps-mcp/session-handoff.md`

### Stage 2: Research
- Use `tapps_lookup_docs` to verify library API signatures
- Use `tapps_impact_analysis` before refactoring

### Stage 3: Develop
- After editing Python files, run `tapps_quick_check`
- If quick check flags issues, run `tapps_score_file` for details
- Fix issues before moving to the next file

### Stage 4: Validate
- Run `tapps_validate_changed` with explicit `file_paths` before declaring work complete (default is quick mode; `quick=false` is a last resort)
- Run `tapps_security_scan` on security-sensitive files
- Ensure overall score >= 70 and no HIGH security findings

### Stage 5: Verify
- Run `tapps_quality_gate` for pass/fail verdict
- Run `tapps_checklist` to confirm all steps were completed

## Memory

**TappsMCP shared memory** — **`uv run tapps-mcp memory`** CLI via BrainBridge (default; do not add direct `tapps-brain` to `.mcp.json`). When **`nlt-memory`** is enabled, `tapps_memory` MCP on that server is a slim facade (TAP-3895). Architecture decisions, quality patterns, cross-agent knowledge. See [docs/MEMORY_REFERENCE.md](docs/MEMORY_REFERENCE.md) and `/tapps-memory` skill.

## Code Standards

- Python 3.12+ with `from __future__ import annotations`
- Type annotations on all functions (`mypy --strict`)
- `structlog` for logging, `pathlib.Path` for file paths
- `ruff` for linting and formatting (line length: 100)
- All file operations through the path validator

## Project Scope (do not break out of this repo/project)

This Copilot instance was configured for THIS repo by `tapps_init` /
`tapps_upgrade`. Reading docs across projects is fine; **writing** outside
this repo or the linked tracker project is not. Specifically:

- Do not create, update, comment on, or move issues that belong to a
  different project than this repo.
- Do not modify files, branches, or pull requests in any other repository.
- Read team / project identity from `.tapps-mcp.yaml` or the current git
  remote, not from arbitrary search results.
- If a task seems to require a write outside this repo/project, ask the
  user before proceeding.
