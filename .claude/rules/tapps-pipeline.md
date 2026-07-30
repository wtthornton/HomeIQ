---
paths:
  - "**/*.py"
  - "Dockerfile*"
  - "docker-compose*.yml"
  - "pyproject.toml"
  - ".tapps-mcp.yaml"
---
# TAPPS Pipeline Details

## Session start & memory

Call `tapps_session_start()` first. Brain memory is bridge-only: use `uv run tapps-mcp memory search --query "..."` or pinned keys in `.tapps-mcp.yaml` → `memory_hooks.auto_recall.recall_keys`. When `nlt-memory` is enabled, `tapps_memory` MCP is a slim facade on that server.

## Validation semantics

`tapps_quick_check` = per-file during edits. `tapps_validate_changed` = batch before done. Stop-hook telemetry counts either as gate activity; /tapps-finish-task requires validate_changed for the edited set.

## 5-Stage Pipeline

Recommended order for every code task:

1. **Discover** - `tapps_session_start()`, consider `uv run tapps-mcp memory search --query "..."` for project context
2. **Research** - `tapps_lookup_docs()` for libraries and domain decisions
3. **Develop** - `tapps_score_file(file_path, quick=True)` during edit-lint-fix loops
4. **Validate** - `tapps_quick_check()` per file OR `tapps_validate_changed()` for batch
5. **Verify** - `tapps_checklist(task_type)`, consider `uv run tapps-mcp memory save --key ... --tier ... --value "..."` for learnings

## Refactoring

Call `tapps_impact_analysis(file_path)` before refactoring or deleting any file.
For **function/method** refactors use `tapps_call_graph(symbol=...)` or `tapps_impact_analysis` with
`symbol` and `granularity="symbol"|"both"`. For changed files use `tapps_diff_impact` or
`tapps_validate_changed(include_impact=true)` for ranked `affected_tests` (Epic 114 / ADR-0017).

## Consequences of Skipping

| Skipped Tool | Consequence |
|---|---|
| `tapps_session_start` | No project context - tools give generic advice |
| `tapps_lookup_docs` | Hallucinated APIs - code may fail at runtime |
| `tapps_quick_check` / scoring | Quality issues may ship silently |
| `tapps_quality_gate` | No quality bar enforced |
| `tapps_security_scan` | Vulnerabilities may ship to production |
| `tapps_checklist` | No verification that process was followed |
| `tapps_impact_analysis` | Refactoring may break unknown dependents |
| `tapps_call_graph` | Function refactors may break unknown callers |
| `tapps_dead_code` | Unused code may accumulate |
| `tapps_dependency_scan` | Vulnerable dependencies may ship |
| `tapps_dependency_graph` | Circular imports may cause runtime crashes |

## Response Guidance

Every tool response includes:
- `next_steps`: Up to 3 imperative actions to take next - consider following them
- `pipeline_progress`: Which stages are complete and what comes next

Record progress in `docs/TAPPS_HANDOFF.md` and `docs/TAPPS_RUNLOG.md`.
For task-specific tool call order, use the `tapps_workflow` MCP prompt.

## Agent Teams (Optional)

If using Claude Code Agent Teams (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`),
consider designating one teammate as a **quality watchdog**. To enable Agent Teams hooks, re-run `tapps_init` with `agent_teams=True`.

## CI Integration

TappsMCP can run in CI. Use `TAPPS_MCP_PROJECT_ROOT` and `tapps-mcp validate-changed --quick`, or Claude Code headless mode with `tapps_validate_changed`.
