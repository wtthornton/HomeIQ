---
name: tapps-continue-session
user-invocable: true
model: claude-haiku-4-5-20251001
description: >-
  Bootstrap a fresh session from the last handoff by reading session-handoff.md,
  optional Linear context, and TAPPS session start — without pasting a long
  manifesto. Use when the user says continue, pick up where we left off, resume,
  or start a new session on an existing task (optional TAP-#### argument).
allowed-tools: mcp__nlt-build__tapps_session_start mcp__plugin_linear_linear__get_issue Bash Read
argument-hint: "[optional Linear issue id e.g. TAP-1234]"
---

Start work in a fresh context window by assembling structured state — not a user paste.

1. **Session bootstrap.**
   - **Preferred:** Call `mcp__nlt-build__tapps_session_start()`. If `data.compaction_rehydration` is present, summarize it in one sentence.
   - **CLI fallback** (MCP unavailable): Run `uv run tapps-mcp doctor --quick` and read `.tapps-mcp.yaml` for project context (quality preset, brain URL, engagement). Proceed without blocking.

2. **Load handoff (priority order).**
   - Read `.tapps-mcp/session-handoff.md` if it exists — primary source.
   - Else best-effort CLI (no `tapps_memory` MCP — removed v3.12.0): `uv run tapps-mcp memory get --key session-handoff` (brain offline or auth missing → skip).
   - Optional supplements (only if present): `docs/NEXT_SESSION_PROMPT.md`, `docs/TAPPS_HANDOFF.md` (**Next:** section).
   - **P0 fallback:** If **Next (P0)** is empty but **Open** has bullets, promote the first Open item as provisional P0 and flag it in the continue block.
   - **Memory context (optional):** `uv run tapps-mcp memory recall --recall-key session-handoff --query "<P0 text or Linear id>"` pins the handoff mirror then adds semantic hits (HTTP-safe). Alternative: `uv run tapps-mcp memory search --query "..."`. Skip silently when brain auth is unavailable.

3. **Linear context.**
   - If the user passed `TAP-####` (argument or in handoff **Linear P0**), call `mcp__plugin_linear_linear__get_issue(id=...)`.
   - For backlog/triage without a known id, invoke the `linear-read` skill instead of raw `list_issues` (do not call `list_issues` directly — cache gate).

4. **Emit continue block (~15 lines max).** Present:
   - **P0** — next action + Linear link if available (note if promoted from Open)
   - **Done / Open / Blockers** — compressed from handoff
   - **Verify first** — commands from handoff
   - **Success criterion**
   - **Stale warning** if handoff **Updated** is >7 days old or missing

5. **Proceed on P0.** Ask only if P0 is ambiguous; otherwise start using normal TAPPS workflow (`tapps_quick_check` after Python edits). Do **not** ask the user to re-paste prior context when handoff files exist.
