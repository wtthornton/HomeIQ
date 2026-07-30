---
name: tapps-refactor
description: >-
  Function-level refactor workflow using call graph tools (Epic 114).
  Use before changing a symbol's signature, deleting a function, or
  refactoring callers — maps blast radius via tapps_call_graph and diff_impact.
mcp_tools:
  - tapps_session_start
  - tapps_call_graph
  - tapps_impact_analysis
  - tapps_diff_impact
  - tapps_quick_check
  - tapps_validate_changed
  - tapps_checklist
---

Symbol-level refactor workflow (Epic 114 / ADR-0017):

1. **Session bootstrap.** Call `tapps_session_start()` — read `call_graph` (`ready`, `stale`, `degraded`). Stale is informational; graph tools auto-rebuild on first use.

2. **Before editing a function.** `tapps_call_graph(symbol='...', query='callers')` — who calls this symbol? Use `query='callees'` or `query='chain'` as needed.

3. **Optional module context.** `tapps_impact_analysis(file_path='...', symbol='...', granularity='both')`.

4. **Edit loop.** After each Python file change, `tapps_quick_check(file_path='...')`.

5. **After edits.** `tapps_diff_impact(file_paths='...')` or `/tapps-finish-task` (`include_impact` default true refreshes cache).

6. **Close out.** `/tapps-finish-task` with `task_type=refactor`.

See `docs/CALL_GRAPH.md` for gap_rate / degraded semantics.
