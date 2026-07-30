---
name: tapps-finish-task
description: >-
  Run the end-of-task TAPPS pipeline in one shot: validate changed files,
  verify the checklist, and optionally save learnings to memory. Use when
  you have finished implementing a task and want to validate, checklist,
  and save learnings in one shot.
mcp_tools:
  - tapps_validate_changed
  - tapps_checklist
  - tapps_lookup_docs
---

Close out the current task end-to-end. Run each step; do NOT skip one that failed — surface the failure and stop.

1. **Validate changed files.** Identify files edited this session (git status, edit history). Call `tapps_validate_changed` with explicit `file_paths` (comma-separated). Never call without `file_paths`. If any file fails, list it with the top blocking issue and stop.

   **Call graph:** `include_impact` defaults to true — `tapps_validate_changed` refreshes the cache via `tapps_diff_impact`. Before function-level refactors, call `tapps_call_graph(symbol='...', query='callers')`.

2. **Verify the checklist.** Call `tapps_checklist(task_type=<feature|bugfix|refactor|security|review>)`. Read the inline **`usage_gaps`** block — not only `complete` / `missing_steps`. If `complete: false`, address each entry in `missing_steps` and re-run.

3. **Clear doc-lookup gaps.** When `usage_gaps.gaps` includes `lookup_docs_underused`,
   `library_uses_without_lookup_docs`, or `libraries_without_lookup` is non-empty:
   - Call `tapps_lookup_docs(library=<name>, topic=<relevant-api>)` for **each** listed library (retrospective MCP lookups clear telemetry gaps; cache hits are fine — ADR-0021).
   - CLI `tapps-mcp lookup-docs` also records `.lookup-docs-events.jsonl` for the next session.
   - Re-run `tapps_checklist` until `usage_gaps.gaps` is empty **and** `complete: true`.
   Prefer lookup **before the first edit** that uses each external library in future sessions.

4. **Save learnings (conditional).** If the session produced a non-obvious architectural or pattern-level decision, run `uv run tapps-mcp memory save --key <slug> --tier <architectural|pattern> --value "<decision>"` (CLI via BrainBridge). Skip for routine fixes. Brain offline → skip silently.
5. **Report.** Emit a one-line summary: `Files validated: N pass. Checklist: <task_type> complete. Doc gaps: cleared|none. Memory saved: yes|no.`

6. **Transfer (optional).** If the user is ending the chat, invoke the `tapps-handoff-session` skill so the next session can run `tapps-continue-session`.
