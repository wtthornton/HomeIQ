# Session handoff
**Updated:** 2026-08-13T20:25:00Z
**Git:** 71f02a96 (feat/tap-5431-local-calendar — PUSHED; draft PR #83 open, merge owner-gated)
**Linear P0:** Sub-goal 4 — Wave 8 MCP server (epic TAP-5282, Urgent)

## Resume-as (standing instruction)
- Re-enter the drain loop: `Read prompts/homeiq-backlog-drain.md in full, then execute it as a goal loop — run the Loop section repeatedly until Done-when holds, printing the SCORE line every iteration. Establish preconditions per Sub-goal 0; work sub-goals in order; do not stop unless an Autonomy hard-stop fires.` Linear must be authenticated (`/mcp`).
- Branch base note: this branch stacks TAP-5431 + the defect batch (manifest helper rows are bind-mounted into the live gateway, so the branch line stays contiguous). New work continues HERE until PR #83 merges, then re-base off master.

## Done this session (all with opus refute-verifier evidence on the tickets)
- **Sub-goal 1 — TAP-5431** Done: LocalCalendarRecipe (`calendar.homeiq` live), PowercalcRecipe (HACS download + restart + discovery; `sensor.living_room_left_play_power = 8.05 W`), alias helpers `sensor.total_power` / `sensor.daily_energy` via manifest rows, CALENDAR_ENTITIES wired, zero-change second applies pasted. 9 fix rounds, all root-caused (brain key `burndown-drain2-5431-powercalc`).
- **Sub-goal 2 — TAP-5430** SKIPPED as decide-work (recorded on ticket): no provisioned write path to /config (`core_ssh` authorized_keys/password EMPTY at key-name level); owner decision needed (options + recommendation on the ticket). Batched hard-stop item.
- **Sub-goal 3 — defect batch**: TAP-6036 Done (env templates blanked, scan extended to 12 env files after verifier killed an .example blind spot; rotation owner-gated recorded). TAP-6034 Done (wizard wired to triggers/decisions; DOM + round-trip proof). TAP-6035 Done (rebinding-proof Host/Origin policy; 29 adversarial inputs). TAP-6037 pending verifier verdict — libs-ci.yml GREEN on run for 71f02a96 after catching real rot 3 times (resilience async drift, undeclared requests, undeclared homeiq-data[auth]). Filed TAP-6066 (undeclared-imports audit follow-up).
- Floors moved: homeiq-ha **246**, ha-setup-service **60**; libs suites all green (55/246/61/10/683/86).

## Open / next
- Close TAP-6037 on verifier PASS (verifier running at handoff time).
- **Sub-goal 4 — Wave 8 MCP server** (epic TAP-5282 Urgent; stories 5292→5297 in id order; 5292 tool catalogue gates everything). REQUIRED before code: MCP server SDK lookup. Reconcile TAP-5298/TAP-5322 credential-move duplicate BEFORE Wave 9.
- Then Sub-goals 5-8 per prompts/homeiq-backlog-drain.md.

## Blockers / owner actions (batched hard-stop report)
1. **TAP-5430 write mechanism** — owner decision (recommended: provision dedicated agent SSH credential in core_ssh authorized_keys; alternative: hand-edit the two YAML blocks and re-scope recipes to check-only).
2. **PR #83 merge** — owner-gated (contains 5431 + defect batch; libs-ci green, quality gates pass).
3. **Credential rotation** — TAP-6036/5993 exposed values in git history; rotation owner-gated, recorded on tickets.

## Verify
- `git rev-parse --short HEAD` == 71f02a96; `git status --short` empty.
- Suites SEPARATE: `.venv/bin/python -m pytest libs/homeiq-ha -q` → 246; `.venv/bin/python -m pytest domains/device-management/ha-setup-service -q` → 60.
- `gh run list --workflow libs-ci.yml --limit 1` → success.
- Live: `curl -s :8024/health` 200; `calendar.homeiq` exists; `sensor.total_power` numeric; rebinding curl (Host+Origin evil.example) → 403.

## Success criterion
- Next session resumes at Sub-goal 4 (Wave 8 MCP) with green baselines; never redo Sub-goals 1-3 or closed defects (brain keys `burndown-drain2-*`).
