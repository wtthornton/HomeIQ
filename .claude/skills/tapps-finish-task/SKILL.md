---
name: tapps-finish-task
user-invocable: true
model: claude-haiku-4-5-20251001
description: Run the end-of-task TAPPS pipeline in one shot — validate_changed, then checklist, then an optional memory save for anything architectural or patterned learned this session. The recommended final step before declaring work complete. Use when you have finished implementing a task and want to validate, run the checklist, and save learnings in one shot.
allowed-tools: mcp__nlt-build__tapps_validate_changed mcp__nlt-build__tapps_checklist mcp__nlt-build__tapps_lookup_docs Bash
argument-hint: "[task_type: feature|bugfix|refactor|security|review]"
---

Close out the current task end-to-end. Run each step; do NOT skip one that failed — surface the failure and stop.

1. **Validate changed files.** Identify the files you edited this session (git status, your edit history). Call `mcp__nlt-build__tapps_validate_changed` with explicit `file_paths` (comma-separated) scoped to those files. **Never call without `file_paths`.** Default is quick mode. If any file fails, list it with the top blocking issue and stop — the task is not complete. Do not proceed to step 2 until all changed files pass.

   **Call graph:** `include_impact` defaults to true — `tapps_validate_changed` refreshes the cache via `tapps_diff_impact`. Before function-level refactors, call `tapps_call_graph(symbol='...', query='callers')`.

2. **Verify the checklist.** Call `mcp__nlt-build__tapps_checklist(task_type=<feature|bugfix|refactor|security|review>)`. Read the inline **`usage_gaps`** block — not only `complete` / `missing_steps`. If `complete: false`, address each entry in `missing_steps` and re-run.

3. **Clear doc-lookup gaps.** When `usage_gaps.gaps` includes `lookup_docs_underused`,
   `library_uses_without_lookup_docs`, or `libraries_without_lookup` is non-empty:
   - Call `mcp__nlt-build__tapps_lookup_docs(library=<name>, topic=<relevant-api>)` for **each** listed library (retrospective MCP lookups clear telemetry gaps; cache hits are fine — ADR-0021).
   - CLI `tapps-mcp lookup-docs` also records `.lookup-docs-events.jsonl` for the next session.
   - Re-run `mcp__nlt-build__tapps_checklist` until `usage_gaps.gaps` is empty **and** `complete: true`.
   Prefer lookup **before the first edit** that uses each external library in future sessions.

4. **Save learnings (conditional).** If this session produced a non-obvious architectural or pattern-level decision — a new convention, a subtle trade-off, a gotcha someone else would re-discover — run `uv run tapps-mcp memory save --key <slug> --tier <architectural|pattern> --value "<concise decision>"` (CLI via BrainBridge). Skip for routine fixes, refactors where the code documents the decision, or trivial bugfixes. Brain offline → skip silently.

5. **Report.** Emit a one-line summary: `Files validated: N pass. Checklist: <task_type> complete. Doc gaps: cleared|none. Memory saved: yes|no.` If any step failed or was skipped, say so explicitly.

6. **Transfer (optional).** If the user is ending the chat and wants the next session to pick up cleanly, invoke `/tapps-handoff-session` instead of pasting a long prompt.
