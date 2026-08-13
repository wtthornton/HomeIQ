# Session handoff
**Updated:** 2026-08-13T03:55:00Z
**Git:** 6d8e5bab
**Linear P0:** TAP-5944 + TAP-5945 (closure only — work done + verified)

## Resume-as (re-enter the goal loop — the standing instruction)
- Next session re-enters the multi-run loop, not just the P0: paste/execute — `Read prompts/homeiq-backlog-burndown.md in full, then execute it as a goal loop — run the Loop section repeatedly until Done-when holds, printing the SCORE line every iteration. Establish your own preconditions per Wave 0; work the lowest-numbered unfinished wave only; do not stop unless an Autonomy hard-stop fires.`
- Loop state: Waves 1–3, 5, 6 DONE + verified (never redo; brain keys `burndown-wave-*`). Wave 4 HUMAN-BLOCKED on TAP-6018 (skip 5978/5979/5980). Current = Wave 7 (epic TAP-5942): 5943 Done; **5944/5945 verifier-passed after gap fixes (commit 6d8e5bab) — Linear closure pending plugin auth**; then 5946, 5947, wave panel, close epic; then Waves 8–11. ~37/61 closed (+2 ready to close).

## Done
- Wave 5 complete (5982/5983/5984 + epic TAP-5981; panel findings fixed; init-gateway runbook; `HOMEIQ_ZHA_SERIAL_PATH` override).
- Wave 6 complete (5921, 5987, 5988, 5989, 5990, 5991 + epic TAP-5985; 5429 canceled / 5430 narrowed / 5431 kept; TAP-6027 filed).
- Wave 7: TAP-5943 Done. TAP-5945 hardened post-verifier-FAIL (compose `group_add: "1000"` — manifest write was dead code at uid 1001; injection quoting + rollback in manifest_edit.py; websockets frame-logger pinned). TAP-5944 built (GET /setup; headless-chrome proof: 12 items, 7 readiness badges).
- Floors: homeiq-ha 194, ha-setup-service 29 (run trees SEPARATELY — documented collision).
- GH Actions slimming recs delivered — NOT approved, do not implement.

## Open
- TAP-5944/5945: work verified complete, NOT closed in Linear (plugin unauthenticated this session). Closure notes ready — 5944: acceptance count corrected to 11 (12th card is the static teams form; proof key is `.items|length`, `.queue` doesn't exist); 5945: schema hardening `extra="forbid"` + 5 route tests (6d8e5bab).
- TAP-5946 (permit root cause at ws.py:200-206; `zha/devices/permit` duration=N) and TAP-5947 (verify `config_entries/ignore_flow`) not started.

## Next (P0)
- With Linear auth restored: close TAP-5944 + TAP-5945 via linear-issue skill using the closure notes above, then start TAP-5946.

## Verifier verdict (2026-08-13, opus refute mode — full detail in brain key `burndown-wave-7-5944-5945-verified`)
- PASSED: badges (7/7), compose `group_add` ([1000,1001], manifest writable, byte-identical mount, logs volume restored, RestartCount 0), websockets frame-logger pin (ws.py:56-65 — load-bearing, backup/config/info carries plaintext key), converge gating (wrote_nothing honest, blocked_on_human correct).
- GAPS (both fixed in 6d8e5bab, redeployed, live-re-verified): queue count is 11 not 12; AnswersRequest accepted off-contract bodies (200 not 422) and handler was untested.
- Post-fix live state: off-contract POST → 422, /setup → 200, queue = 11, suites 194 + 34 green, gates pass, checklist complete.

## Blockers
- Linear MCP plugin unauthenticated in non-interactive session — user must re-auth via /mcp in an interactive session before 5944/5945 can be closed.

## Verify
- `tapps_session_start()` then `tapps_memory(action="search", query="burndown wave 7")`.
- Both pytest trees green (194 / 34); `curl :8024/api/v1/init/queue | jq '.items|length'` ≈ 11 (live-derived, drifts); `curl :8024/setup` → 200; off-contract POST to /answers → 422.
- `docker exec homeiq-setup-service python -c "import os; print(os.getgroups(), os.access('config/ha-organization-manifest.yaml', os.W_OK))"` → `[1000, 1001] True`.

## Success criterion
- Loop re-entered per Resume-as and runs to cap/Done-when: 5944/5945 closed, 5946/5947 done, Wave-7 panel, epic TAP-5942 closed, then Waves 8–11.
