---
name: tapps-continue-session
description: >-
  Bootstrap a fresh session from the last handoff by reading session-handoff.md,
  optional Linear context, and TAPPS session start — without pasting a long
  manifesto. Use when the user says continue, pick up where we left off, resume,
  or start a new session on an existing task (optional TAP-#### argument).
mcp_tools:
  - tapps_session_start
  - linear_get_issue
---

Start work in a fresh context by assembling structured state.

1. **Session bootstrap.**
   - **Preferred:** Call `tapps_session_start()`. Note `compaction_rehydration` if present.
   - **CLI fallback** (MCP unavailable): Run `uv run tapps-mcp doctor --quick` and read `.tapps-mcp.yaml` for project context. Proceed without blocking.

2. **Load handoff (priority order).**
   - Read `.tapps-mcp/session-handoff.md` if it exists — primary source.
   - Else best-effort CLI (no `tapps_memory` MCP — removed v3.12.0): `uv run tapps-mcp memory get --key session-handoff` (brain offline or auth missing → skip).
   - Optional supplements (only if present): `docs/NEXT_SESSION_PROMPT.md`, `docs/TAPPS_HANDOFF.md` (**Next:** section).
   - **P0 fallback:** If **Next (P0)** is empty but **Open** has bullets, promote the first Open item as provisional P0 and flag it in the continue block.
   - **Memory context (optional):** `uv run tapps-mcp memory recall --recall-key session-handoff --query "<P0 text or Linear id>"` pins the handoff mirror then adds semantic hits (HTTP-safe). Alternative: `uv run tapps-mcp memory search --query "..."`. Skip silently when brain auth is unavailable.

3. **Linear context.**
   - If the user passed `TAP-####` (argument or handoff **Linear P0**), call `get_issue(id=...)`.
   - For backlog/triage without a known id, invoke the `linear-read` skill — do not call raw `list_issues` (cache gate).

4. **Emit continue block (~15 lines max).** Present:
   - **P0** — next action + Linear link if available (note if promoted from Open)
   - **Done / Open / Blockers** — compressed from handoff
   - **Verify first** — commands from handoff
   - **Success criterion**
   - **Stale warning** if handoff **Updated** is >7 days old or missing

5. **Proceed on P0.** Ask only if P0 is ambiguous; otherwise start using normal TAPPS workflow (`tapps_quick_check` after Python edits). Do **not** ask the user to re-paste prior context when handoff files exist.
