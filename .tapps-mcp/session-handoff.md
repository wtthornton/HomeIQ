# Session Handoff — HomeIQ backlog burndown (2026-08-12)

Branch `feat/ha-init-agent-activation` (PR #82, draft). All work committed and
pushed. `git log origin/…..HEAD` = 0 unpushed. Live stack: 58 healthy
containers. Test floors green: homeiq-ha 155, homeiq-memory 61,
homeiq-resilience health 24, admin-api 386, data-api suites at baseline.

## Done this run (25 stories, each adversarially verified)

- **Wave 1** (build/CI): TAP-5287 canceled (repo-root contexts refuted), 5288
  (start-stack.ps1 parity), 5289 (compose-parse CI guard), 5290, 5291 re-scoped.
- **Wave 2** (operational honesty, ALL closed): 5437 (memory enum bind), 5438
  (patterns tables), 5439 (real-time-metrics 10s→15ms), 5440 (shared ws client
  + edge migration + event-shape fix), 5445 (Flux time literals), 5446, 5447,
  5448, 5449, 5450, 5902 (env preflight guard), 5992 (deploy explicit-id +
  rollback N-1), 5434 capstone (contract 36→98 rows, 0 deviations). 3-verifier
  wave panel unanimous.
- **Wave 3** (Hue absorption, epic 5973 + 5974/5975/5976 DONE): manifest v3, 89
  devices/17 areas, bedroom+tv artifact areas removed via empty-guarded recipe,
  190 scenes bridge_owned, 6 outdoor sensor groups. Converged live, zero-change
  second apply.
- **Wave 5**: TAP-5982 DONE (report-only mesh-health recipe, live LQI rows).

## Blocked / filed

- **Wave 4 (office presence) BLOCKED on TAP-6018**: the Aqara FP1E
  `lumi.sensor_occupy.agl8` has no ZHA quirk on HA 2026.8.1 (fully updated), so
  no occupancy entity. Gateway can't install a custom quirk (HA-host file
  access). TAP-6018 filed, blocks 5978/5979/5980. Office stays on input_boolean
  proxies (not faked, not demoted). Owner to pursue custom quirk later.
- Filed follow-ups: TAP-5993 (compose credential defaults), 5994
  (data_sources_active always []), 5997 (event search facade), 5999 (docker
  mock mode), 6007 (config_manager sensitive-key predicate), 6018 (FP1E quirk).

## Next (Wave 5 remaining, both software, unblocked)

- **TAP-5983** — coordinator watchdog: ZHA `setup_retry` / SLZB unreachable →
  ALERT (routes_init.py). Highest-value; needs a staged-test alert as proof.
- **TAP-5984** — WS `/core/logs` passthrough returns parseable text or documents
  the REST fallback (ws.py:300-340).
Then the Wave-5 completion panel, then Wave 6 (switch comfort 5985 group),
Wave 7 (wizard 5942), Waves 8-11.

## Key mechanics learned this run

- Live HA reads/writes via the gateway container: `docker exec -i
  homeiq-setup-service python -` with `homeiq_ha.client` (has HA_WS_URL/HA_TOKEN).
- HA writes only through gateway converge `:8024/api/v1/init/converge {"phase":N}`.
  Owner granted broad HA action this session for the ZHA diagnosis.
- The audit runs recipes through a read-only proxy (`readonly.py` `_READ_COMMANDS`
  allowlist) — new read commands must be added there.
- New recipes go in small modules re-exported from the recipes hub
  (`diagnostics.py`); recipes.py is pre-existing gate debt at ~930 lines.
- AF org agents need `max_budget_usd: 3.5`; workflow via
  `scripts/af.sh publish` + the org-author workflow (base http://localhost:8010).
- HA group helpers mint entity_id from the friendly NAME, not a passed slug —
  manifest helper slug must equal the name-derived id or converge mints dupes.
- ai-automation tests: `TEST_DATABASE_URL=postgresql+asyncpg://homeiq_test_ci:homeiq-test-only@localhost:15432/homeiq_test`.
