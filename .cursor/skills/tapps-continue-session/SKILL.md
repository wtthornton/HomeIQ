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
<!-- upgrade-policy: overwrite. tapps_upgrade replaces this file wholesale on every run and local edits are lost (tapps_init leaves an existing copy alone; upgrade does not). Fold the change upstream into the platform template, or pin the whole directory with an upgrade_skip_files token. -->

Start work in a fresh context by assembling structured state.

1. **Session bootstrap.**
   - **Preferred:** Call `tapps_session_start()`. Note `compaction_rehydration` if present.
   - **CLI fallback** (MCP unavailable): Run `uv run tapps-mcp doctor --quick` and read `.tapps-mcp.yaml` for project context. Proceed without blocking.
- **Usage gaps:** `usage_gaps.recurring_validation_skips` is 7-day rolling fleet telemetry — not proof this call failed. Still run validate + checklist at epic boundaries in execution repos.

2. **Load handoff (priority order).**
   - Read `.tapps-mcp/session-handoff.md` if it exists — primary source.
   - Else best-effort CLI (no `tapps_memory` MCP — removed v3.12.0): `uv run tapps-mcp memory get --key session-handoff` (brain offline or auth missing → skip).
   - Optional supplements (only if present): `docs/NEXT_SESSION_PROMPT.md`, `docs/TAPPS_HANDOFF.md` (**Next:** section).
   - **P0 fallback:** If **Next (P0)** is empty but **Open** has bullets, promote the first Open item as provisional P0 and flag it in the continue block.
   - **Memory context (optional):** `uv run tapps-mcp memory recall --recall-key session-handoff --query "<P0 text or Linear id>"` pins the handoff mirror then adds semantic hits (HTTP-safe). Alternative: `uv run tapps-mcp memory search --query "..."`. Skip silently when brain auth is unavailable.

3. **Ground-truth gate (run before emitting anything).** The handoff is a claim about the past, not evidence. Age is the weak signal — a handoff goes wrong the moment work lands after it was written, which is usually minutes, not days. Run all three checks and carry a verdict per claim:

   - **Commit drift.** `git log -1 --format=%h`, compared against the handoff **Git:** sha. On a mismatch, name what landed: `git log --oneline <handoff-sha>..HEAD`. A different sha means the file predates real work — treat **every Open item as unverified** until re-probed. *One benign case:* when the only commit in that range is the one that committed the handoff itself, the sha is stale by construction (the file records HEAD at write time, then becomes part of the next commit) — say so and move on. Any other commit in the range is real drift.
   - **P0 status.** Re-read the **Linear P0:** id from the tracker (`get_issue`), never from the handoff text. Flag it when the issue is already **Done** or **Canceled**. Treat a Done status as a **claim in both directions**: report it, and never conclude from it alone either that the work exists or that it does not — issues get auto-closed by a commit reference with no code behind them, and finished work sits under issues nobody moved.
   - **Named PR / branch.** For every PR the handoff names, `gh pr view <N> --json state,mergedAt` before offering it as a next action. A merged PR presented as "needs review" is the most common stale-handoff failure.

   **On any mismatch, correct `.tapps-mcp/session-handoff.md` before proceeding** — rewrite the wrong lines, then continue from the corrected file. Never leave a known-wrong artifact for the next session to inherit.

   **Why this outranks age.** The 7-day age warning never fires on the failure that actually happens — a handoff wrong within the hour. It matters more as orchestration loops recycle context at sub-goal boundaries: once a run clears its context the handoff is the only channel between runs, and no surviving context is left to contradict it.

4. **Linear context.**
   - If the user passed `TAP-####` (argument or handoff **Linear P0**), call `get_issue(id=...)`.
   - For backlog/triage without a known id, invoke the `linear-read` skill — do not call raw `list_issues` (cache gate).

5. **Emit continue block (~15 lines max).** Present:
   - **P0** — next action + Linear link if available (note if promoted from Open)
   - **Drift** — lead here whenever step 3 found a mismatch: the sha diff, the commits landed since, any already-Done P0 or already-merged PR. It outranks every other line in this block.
   - **Done / Open / Blockers** — compressed from handoff, each item tagged **verified**, **corrected**, or **unverified** from step 3. Never restate an Open item as fact when step 3 did not confirm it.
   - **Cumulative** (when present) — sub-goal, attempt vs cap, budget spent, refuted strategies, resume line
   - **Verify first** — commands from handoff
   - **Success criterion**
   - **Host reset** — Claude Code: operator may `/clear` then continue; Cursor: **new chat** then re-invoke this skill
   - **Stale warning** if handoff **Updated** is >7 days old or missing — the weaker signal; report it *below* the drift line, never in place of it

6. **Re-verify live state** when **Cumulative** is present — handoff is a pointer, not proof (orchestration §7 / cold-start companion). Step 3 covers sha, P0 status, and named PRs; also re-read any *metric* the handoff quotes (test count, score, coverage) from its newest artifact rather than inheriting the prose.

7. **Proceed on P0.** Ask only if P0 is ambiguous; otherwise start using normal TAPPS workflow (`tapps_quick_check` after Python edits). Do **not** ask the user to re-paste prior context when handoff files exist.
