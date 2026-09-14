<!-- upgrade-policy: managed-block. Edits made inside this BEGIN/END block are regenerated and lost on the next tapps_upgrade — put project-specific customizations below the END marker instead, where they survive every upgrade untouched. -->
<!-- BEGIN: tapps-skill-asset orchestration-prompt/references/host-feature-map.md v3.12.78 -->
# Host feature map — Claude Code vs Cursor

Read when emitting **Run-as**, checkpoint lanes, or plane-map mechanism choices.
Default host = runner session: `.cursor/` present → Cursor; `.claude/` → Claude
Code; an explicit user flag overrides.

| Concern | Claude Code | Cursor |
|---|---|---|
| Goal loop | `/goal "<condition>"` (evaluates surfaced output only) | Explicit loop in prompt + paste ground-truth each iteration; optional `claude -p` for unattended |
| Fan-out verify | Workflow `parallel()` / subagents | `Task` tool (`explore`, `generalPurpose`, `shell`); Multitask Mode when parallel |
| Context reset | `/clear` (operator) · subagent · `claude -p` process boundary | **New chat** + `/tapps-continue-session` (no `/clear` API) |
| Recurring | Routine / `claude -p`+cron | Shell cron + `claude -p`; document in emitted prompt Run-as |
| MCP budget | Full six-server bundle common | ~40-tool cap — prefer `developer` bundle; orchestrator often memory-only |
| Plan vs execute | N/A | Plan Mode for fog; Agent Mode for execute (link to `/tapps-wayfind` for decide work) |
| TAPPS quality gate | Full `nlt-build` in execution repos | Orchestrator Cursor: often `nlt-memory` only — use `fleet-dispatch` for validate in owning repo |
| Session bootstrap | `tapps_session_start()` first MCP call every session | Same — required-fail if skipped when checkers are stale |

## Checkpoint resume by host

| Host | After `/tapps-handoff-session` |
|---|---|
| Claude Code | Operator runs `/clear`, then `/tapps-continue-session` |
| Cursor | **New chat** (Composer reset), then `/tapps-continue-session` |

Cross-ref: shift-boundary carry-forward in `references/cold-start-and-verify.md`;
cumulative handoff fields in `/tapps-handoff-session` and `/tapps-continue-session`.
<!-- END: tapps-skill-asset -->
