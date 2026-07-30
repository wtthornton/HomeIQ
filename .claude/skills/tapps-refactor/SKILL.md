---
name: tapps-refactor
user-invocable: true
model: claude-sonnet-4-6
description: >-
  Function-level refactor workflow using call graph tools (Epic 114).
  Use before changing a symbol's signature, deleting a function, or
  refactoring callers — maps blast radius via tapps_call_graph and diff_impact.
allowed-tools: >-
  mcp__nlt-build__tapps_session_start
  mcp__nlt-build__tapps_call_graph
  mcp__nlt-build__tapps_impact_analysis
  mcp__nlt-build__tapps_diff_impact
  mcp__nlt-build__tapps_quick_check
  mcp__nlt-build__tapps_validate_changed
  mcp__nlt-build__tapps_checklist
argument-hint: "[symbol or file-path]"
---

Symbol-level refactor workflow (Epic 114 / ADR-0017):

1. **Session bootstrap.** Call `mcp__nlt-build__tapps_session_start()` — read `data.call_graph` (`ready`, `stale`, `degraded`). Stale is informational; graph tools auto-rebuild on first use.

2. **Before editing a function.** `mcp__nlt-build__tapps_call_graph(symbol='...', query='callers')` — who calls this symbol? Use `query='callees'` for downstream dependencies or `query='chain'` for bounded chains.

3. **Optional module context.** `mcp__nlt-build__tapps_impact_analysis(file_path='...', symbol='...', granularity='both')` for import + symbol blast radius.

4. **Edit loop.** After each Python file change, `mcp__nlt-build__tapps_quick_check(file_path='...')`.

5. **After edits.** `mcp__nlt-build__tapps_diff_impact(file_paths='...')` or finish with `/tapps-finish-task` (`include_impact` default true refreshes cache).

6. **Close out.** `/tapps-finish-task` with `task_type=refactor` — checklist recommends `tapps_call_graph` and `tapps_diff_impact`.

See `docs/CALL_GRAPH.md` for gap_rate / degraded semantics.
