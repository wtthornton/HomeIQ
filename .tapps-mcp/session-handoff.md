# Session Handoff — HomeIQ backlog burndown (2026-08-13)

Branch `feat/ha-init-agent-activation` (PR #82, draft). All work committed and
pushed. Test floor: homeiq-ha suite green (see pytest at session start for the
current count — it grows; ≥165 as of 2026-08-13).

## Waves complete

- **Wave 1** (build/CI), **Wave 2** (operational honesty, contract 98/98),
  **Wave 3** (Hue absorption, epic 5973) — see prior handoff (git history of
  this file) and brain keys `burndown-wave-*`.
- **Wave 5 (Zigbee health, epic TAP-5981) COMPLETE 2026-08-13**, 3-verifier
  panel run (correctness PASS, no-residue PASS, reproducibility FAIL-narrow),
  all findings fixed same session:
  - TAP-5982 mesh-health recipe (per-device LQI rows in the nightly artifact).
  - TAP-5983 coordinator watchdog — alerts (blocked_on_human row) on any
    zha/smlight entry state outside {loaded, setup_in_progress} OR
    unreachable coordinator socket. Staged-alert procedure + env override
    `HOMEIQ_ZHA_SERIAL_PATH` documented in `docs/operations/init-gateway.md`.
  - TAP-5984 supervisor logs — WS passthrough can't carry text (HA core
    JSON-decodes; verified HA 2026.8.1); supported path is
    `HARestClient.get_supervisor_logs()`; WS guard refuses log endpoints
    (JSON exceptions: /host/logs/boots, /host/logs/identifiers).

## Blocked / standing

- **Wave 4 (office presence, TAP-5977) HUMAN-BLOCKED on TAP-6018** (Aqara FP1E
  has no ZHA quirk on HA 2026.8.1 → no occupancy entity; needs custom quirk +
  physical re-interview). Skip 5978/5979/5980; office stays on input_boolean
  proxies — do NOT demote them.
- PR #82 merge = human decision. Waves 3-7 branch from its tip.
- GitHub Actions slimming recommendations delivered to owner (concurrency,
  draft gating, libs fan-out dedup, park 2 known-red TappsMCP workflows) —
  owner has not yet approved implementation.

## Next (Wave 6, TAP-5985 group — lowest-numbered first)

1. **TAP-5921** — delete dead zigbee2mqtt probes + pay MI debt. Recon done
   (brain key `burndown-wave-5-panel`): delete
   `_check_zigbee2mqtt_integration` (health_service.py:399-430 + caller :408),
   `check_zigbee2mqtt_integration` (integration_checker.py:312-395 + gather
   entry :71 + docstring :47), dead filter scoring_algorithm.py:144-149, dead
   skip health_service.py:525. MI split: recipes.py 939→~395 (BackupSchedule+
   FirstBackup→backup.py; registry/org recipes→organization.py;
   TeamTracker→integration.py; keep hub re-exports). test_agent_recipes.py:
   move SimHA harness to conftest.py, split clusters to test_backup.py etc.
   Acceptance needs quick-check ≥70 on BOTH recipes.py and test_agent_recipes.py.
2. TAP-5987 gesture catalogue (manifest-declared OPTIONS, deploy user-gated),
   5988 smart-bulb eval, 5989 (human-gated, record+skip), 5990 goal-loop ADR,
   5991 re-scope 5429/5430/5431 vs PR #82.
3. Then Wave 7 (wizard 5942 — do 5289-adjacent compose work first per prompt),
   Waves 8-11.

## Key mechanics (stable)

- Live HA reads: `docker exec -i homeiq-setup-service python -` with
  `homeiq_ha.client`. Writes ONLY via `POST :8024/api/v1/init/converge`.
- Gateway rebuild after lib changes:
  `docker compose -f domains/device-management/compose.yml --env-file .env
  --profile production up -d --build ha-setup-service` (--env-file required).
- Init gateway runbook: `docs/operations/init-gateway.md` (endpoints, staged
  alert, nightly artifact; artifacts now gitignored — real-home data).
- Read-only proxy allowlist for new WS read commands:
  `libs/homeiq-ha/src/homeiq_ha/agent/readonly.py` `_READ_COMMANDS`.
- New recipes go in small modules re-exported from the recipes hub.
- ai-automation tests: `TEST_DATABASE_URL=postgresql+asyncpg://homeiq_test_ci:homeiq-test-only@localhost:15432/homeiq_test`.
