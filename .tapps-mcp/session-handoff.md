# Session handoff
**Updated:** 2026-08-13T17:15:37Z
**Git:** c2c35577 (feat/ha-init-agent-activation — PUSHED; PR #82 OPEN, merge pending)
**Linear P0:** TAP-5431

## Resume-as (standing instruction)
- Re-enter the drain loop: `Read prompts/homeiq-backlog-drain.md in full, then execute it as a goal loop — run the Loop section repeatedly until Done-when holds, printing the SCORE line every iteration. Establish preconditions per Sub-goal 0; work sub-goals in order; do not stop unless an Autonomy hard-stop fires.` Linear must be authenticated (`/mcp`).
- History was rewritten this session (triage-store scrub, TAP-5942): old hashes 9ff4f658 / d6eac06a are DEAD. Branch is fully pushed now (origin == c2c35577).

## Done
- **Sub-goal 1 (Wave 7 wizard, epic TAP-5942):** TAP-5946 (readiness triggers), TAP-5947 (triage add/ignore/later), epic 5942 — 3-panel gate (correctness/security/repro) round1 FAIL → fixed → round2 3/3 PASS.
- **Sub-goal 2 (Wave 1, epic TAP-5281):** TAP-5291 (CI regression checks, 4-round verifier hardening) + epic close.
- **Sub-goal 3 defect batch (all verifier-passed):** TAP-5993, 6027, 5994, 5999, 6007, 5997.
- **Filed follow-ups:** TAP-6034 (wizard page wiring), 6035 (DNS-rebinding guard), 6036 (env.test/prod committed creds), 6037 (libs tests in CI).
- **Post-checkpoint user asks:** TAP-5993 priority → Low (rotation deferred until dev done); PR #82 branch pushed (31 fast-forward commits); InfluxDB retention investigated + documented — sports data is in `home_assistant_events` (365d), the declared per-type buckets are empty (docs/operations/influxdb-retention.md + influxdb_schema.py comment + brain memory `influxdb-buckets-declared-vs-actual`).
- Floors: homeiq-ha 222, ha-setup-service 56 (trees SEPARATE), admin-api 393, data-api search 6.

## Open
- **TAP-5431** — Local Calendar config-flow + Powercalc HACS install + template aliases. LARGE, live-HA-apply; read flow schemas from a LIVE flow (never guess); Powercalc install may force an HA restart (gateway path). HACS unblocked.
- **TAP-5430** — recorder + http recipes only (automation editor already delivered). CHECK docs/ha-init-agent-design.md rows 3.5/3.6 for the remote-YAML-write mechanism; if undecided, surface as decide-work, don't guess.
- Then Sub-goals 4–8: Wave 8 MCP server (epic TAP-5282, Urgent — 5292 tool catalogue gates everything), Wave 9 genome/safety, Wave 10 HA integration, Wave 11 data-plane collapse (destructive, last).

## Next (P0)
- Resume the drain loop at TAP-5431: re-establish Sub-goal-0 preconditions (session_start, Linear auth, smoke, baselines), then design the Local-Calendar / Powercalc / template-alias IntegrationRecipes reading schemas from live flows; do the reversible code first and gate any HA-restart apply through the gateway.

## Blockers
- none

## Changed files
- (tree clean; all committed + pushed — 31 commits 966eafe7..c2c35577)

## Verify
- `git rev-parse --short HEAD` == c2c35577; `git status --short` empty.
- Suites (run SEPARATELY): `.venv/bin/python -m pytest libs/homeiq-ha -q` → 222; `.venv/bin/python -m pytest domains/device-management/ha-setup-service -q` → 56.
- `gh pr view 82 --json state,mergeable` → OPEN/MERGEABLE. **Merge is a human action** — `gh pr merge 82 --merge` was classifier-blocked; the user runs it (add `--admin` if the UNSTABLE check blocks — known TappsMCP-install CI red, not a real failure).
- Owner-gated (recorded on tickets, NOT executed): TAP-5993 rotate all previously-committed creds; TAP-6007 `REVOKE CONNECT ON DATABASE homeiq FROM PUBLIC` (safe — implicit-PUBLIC grant) and the sports_data 90d retention = NO-OP (bucket empty; data is in home_assistant_events).

## Success criterion
- Next session resumes the drain loop at TAP-5431 with green baselines, works sub-goals in order, and never re-does Sub-goals 1–3 (brain keys `burndown-*`).
