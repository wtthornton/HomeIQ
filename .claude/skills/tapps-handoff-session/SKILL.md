---
name: tapps-handoff-session
user-invocable: true
model: claude-haiku-4-5-20251001
description: >-
  Write a structured cross-session handoff and close the TAPPS session
  lifecycle so the next chat can continue without a long paste. Use when
  ending a session, handing off to a fresh chat, or the user says hand
  off, save session state, or continue next time.
allowed-tools: mcp__nlt-memory__tapps_handoff_save mcp__nlt-build__tapps_session_start Bash
argument-hint: "[optional Linear issue id e.g. TAP-1234]"
disable-model-invocation: true
---

End the session with a durable handoff the next chat can load via `/tapps-continue-session`.

0. **Session bootstrap (if needed).** If `tapps_session_start()` was not called this session, call it now (cached is fine) so flywheel scope and checker context are correct. Skip when already called.

1. **Draft handoff (5-10 bullets).** From this session's work, write:
   - **Done** — what shipped or was verified
   - **Open** — in-progress or untested
   - **Next (P0)** — one concrete next action (plain prose)
   - **Blockers** — `- none` when clear
   - **Changed files** — optional; top paths from `git status --short`
   - **Verify** — commands to run first in the next session
   - **Success criterion** — one line

**P0 gate.** Before persisting: when **Open** has real items (not `none` / `- ...` placeholders), **Next (P0)** must name one concrete next action. Set **Linear P0:** to the TAP id when known. If P0 is missing, ask the user once — do not persist an incomplete handoff.

```markdown
# Session handoff
**Updated:** <ISO-8601 UTC from date -u>
**Git:** <short-sha or omit>
**Linear P0:** <TAP-#### or none>

## Done
- ...

## Open
- ...

## Next (P0)
- ... (plain prose; put TAP-#### in **Linear P0** above)

## Blockers
- none

## Changed files
- ... (optional; top paths from git status when multi-file)

## Verify
- ...

## Success criterion
- ...
```

2. **Persist (one atomic call when MCP is available).** Do **not** write the file separately before MCP — `tapps_handoff_save` writes `.tapps-mcp/session-handoff.md`, lints, mirrors to brain, and can close the session lifecycle.

   Draft the full markdown in memory using the shape above:
   - **Updated:** run `date -u +%Y-%m-%dT%H:%M:%SZ` — never a placeholder like `T00:00:00Z`
   - **Git:** `git rev-parse --short HEAD` when inside a git repo
   - **Linear P0:** TAP-#### when known (preferred retrieval key for brain session search)
   - **Blockers:** `- none` alone when clear — put user actions under **Verify** or **Next (P0)**, not Blockers
   - **Changed files:** optional bullets from `git status --short` when the session touched many files

   | Priority | When | How |
   |----------|------|-----|
   | 1 (MCP) | `nlt-memory` available | `tapps_handoff_save(markdown=..., session_end=true)` — single call; do **not** also call `tapps_session_end` |
   | 2 (CLI atomic) | Shell auth; no MCP write | `uv run tapps-mcp handoff write --file .tapps-mcp/session-handoff.md --session-end` after writing the file locally |
   | 3 (manual) | Brain HTTP only | `uv run tapps-mcp memory save --key session-handoff --tier context --tags handoff,cross-session --value "$(cat .tapps-mcp/session-handoff.md)"` — full markdown body |
   | 4 (skip) | Brain offline | File-only via Bash heredoc: `mkdir -p .tapps-mcp && cat > .tapps-mcp/session-handoff.md <<'EOF'` … `EOF` |

   Handoff **Updated** older than 7 days: pass `allow_lint_warnings=true` on `tapps_handoff_save` if lint warns on age.

3. **Report.** One line: `Handoff written: .tapps-mcp/session-handoff.md. Linear P0: <id|none>. brain_mirror: ok|skipped. session_end: ok|skipped. Next session: invoke /tapps-continue-session`
