# Session handoff
**Updated:** 2026-08-13T03:27:50Z
**Git:** e8e50e0b
**Linear P0:** TAP-5945

## Resume-as (re-enter the goal loop — the standing instruction)
- Next session re-enters the multi-run loop, not just the P0: paste/execute — `Read prompts/homeiq-backlog-burndown.md in full, then execute it as a goal loop — run the Loop section repeatedly until Done-when holds, printing the SCORE line every iteration. Establish your own preconditions per Wave 0; work the lowest-numbered unfinished wave only; do not stop unless an Autonomy hard-stop fires.`
- Loop state: Waves 1–3, 5, 6 DONE + verified (never redo; brain keys `burndown-wave-*`). Wave 4 HUMAN-BLOCKED on TAP-6018 (skip 5978/5979/5980). Current = Wave 7 (epic TAP-5942): 5943 Done; **5944/5945 verified working (endpoints both 200 OK, converge runs, group permissions fixed), awaiting Linear closure**; then 5946, 5947, wave panel, close epic; then Waves 8–11. ~39/61 stories verifiable (2944+2945 awaiting closure).

## Done
- Wave 5 complete (5982/5983/5984 + epic TAP-5981; panel findings fixed; init-gateway runbook; `HOMEIQ_ZHA_SERIAL_PATH` override).
- Wave 6 complete (5921, 5987, 5988, 5989, 5990, 5991 + epic TAP-5985; 5429 canceled / 5430 narrowed / 5431 kept; TAP-6027 filed).
- Wave 7: TAP-5943 Done. TAP-5945 hardened post-verifier-FAIL (compose `group_add: "1000"` — manifest write was dead code at uid 1001; injection quoting + rollback in manifest_edit.py; websockets frame-logger pinned). TAP-5944 built (GET /setup; headless-chrome proof: 12 items, 7 readiness badges).
- Floors: homeiq-ha 194, ha-setup-service 29 (run trees SEPARATELY — documented collision).
- GH Actions slimming recs delivered — NOT approved, do not implement.

## Open
- Combined 5944+5945 verifier killed by session limit — neither closed in Linear.
- TAP-5946 (permit root cause at ws.py:200-206; `zha/devices/permit` duration=N) and TAP-5947 (verify `config_entries/ignore_flow`) not started.

## Next (P0)
- TAP-5944+5945 verifier re-dispatch in progress (opus, refute mode) — finding test coverage gaps in answers handler. Manual verification: GET /setup OK (200, HTML, headless-renderable); POST /answers OK (200, runs converge, group_add fix confirmed). Awaiting verifier's structured findings to finalize closure. Then TAP-5946 (permit root cause).

## Blockers
- none

## Verify
- `tapps_session_start()` then `tapps_memory(action="search", query="burndown wave 7")`.
- Both pytest trees green (194 / 29); `curl :8024/api/v1/init/queue` items ≈11–12; `curl :8024/setup` → 200.
- `docker exec homeiq-setup-service python -c "import os; print(os.getgroups(), os.access('config/ha-organization-manifest.yaml', os.W_OK))"` → `[1000, 1001] True`.

## Success criterion
- Loop re-entered per Resume-as and runs to cap/Done-when: 5944/5945 closed, 5946/5947 done, Wave-7 panel, epic TAP-5942 closed, then Waves 8–11.
