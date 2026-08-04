# Session handoff
**Updated:** 2026-08-04T00:38:53Z
**Git:** b50fbac2
**Linear P0:** TAP-5437

> Sessions 1-4 detail was consolidated here. The full per-session log is recoverable
> with `git log -p .tapps-mcp/session-handoff.md` — this file is tracked.

## Done

- **All work pushed.** `master == origin/master` at `b50fbac2`, 0 ahead / 0 behind, clean tree. Includes 8 commits a prior session could not push.
- **All 6 stale containers rebuilt** (ai-training-service, device-context-classifier, device-health-monitor, device-recommender, device-setup-assistant, ha-ai-agent-service). Verified by image-id change *and* by importing `websockets` + `homeiq_ha` inside each running container. TAP-5424's close-out is now true of the running system, not just the repo.
- **Degraded-start latch fixed** in `libs/homeiq-data/database_manager.py`. `initialize()` now records its args; `_try_recover()` replays them from both session entry points, guarded by a 5s cooldown, an `asyncio.Lock` with re-check, and engine disposal. 5 new tests; suite 36 passed.
- **pg_dumpall backup taken and verified** — `backups/postgres/pg_dumpall-20260803T235445Z.sql`, 2.6 MB, 9 schemas, `PostgreSQL database cluster dump complete` terminator present. This is the precursor for the postgres swap.
- **websockets pins corrected.** Caps `<17.0.0` → `<18.0.0` (5 files). `calendar-service` floor `>=10.0` → `>=13.0`: it imports `homeiq_ha` at `src/main.py:23`, which needs `websockets.asyncio` (absent <13.0), and was safe only because homeiq-ha's own floor constrained the resolve.
- Contract gate **79/79, 0 deviations, exit 0**. Stack: 58 total, 58 healthy, 0 unhealthy.

## Open

- **Postgres image swap not performed.** `compose.yml` declares `pgvector/pgvector:pg17`; the container runs `postgres:17-alpine`. The `memory` schema and pattern ML tables are absent from the live database, so TAP-5437 and TAP-5438 are fixed in source only.
- **`libs/homeiq-resilience` suite is red** — 10 pre-existing collection errors, tests asserting on an un-awaited async `allow_request()`. Untouched by this work.
- **TAP-5440** — api-automation-edge still on its own WebSocket client; needs subscription + reconnect added to the shared client first.
- **TAP-5442** (upstream, TappsMCP Platform) — `_get_brain_bridge()` tenant singleton. tapps-brain's own defect is fixed (TAP-5444); this one is tapps-mcp's.

## Next (P0)

- Perform the postgres migration, in this order, on the live stack: confirm the existing dump is current, swap the image by bringing the core-platform postgres service up, then run `REINDEX DATABASE homeiq` — mandatory, because the new image is Debian/glibc where the old was Alpine/musl and collation differs. Then apply `infrastructure/postgres/migrations/001-pattern-ml-tables.sql` and `002-memory-schema.sql`, confirm `CREATE EXTENSION vector` succeeds, and re-check that `/api/v1/memories` and `/api/analysis/status` no longer 500. That closes TAP-5437 and TAP-5438 and unblocks their contract rows in TAP-5434.

## Blockers

- none

## Changed files

- `libs/homeiq-data/src/homeiq_data/database_manager.py` (+ new `tests/test_database_manager_recovery.py`)
- `requirements-base.txt`, `requirements-test.txt`
- `domains/{core-platform/websocket-ingestion,ml-engine/device-intelligence-service}/requirements{,-prod}.txt`
- `domains/automation-core/ha-ai-agent-service/requirements.txt`
- `domains/data-collectors/calendar-service/requirements-prod.txt`

## Verify

- `git status --porcelain` and `git rev-list --count origin/master..HEAD` — expect clean and 0
- `bash scripts/verify-dashboard-contract.sh` — expect 79/79, 0 deviations, exit 0
- `docker ps --filter name=homeiq --format '{{.Status}}' | grep -c '(healthy)'` — expect 58. **Use `'(healthy)'`, not `healthy`** — the latter also matches `(unhealthy)` and hid two degraded services for a whole session
- `.venv/bin/python -m pytest libs/homeiq-data libs/homeiq-ha -q --no-cov` — expect 36 and 99 passed
- `docker inspect --format '{{.Config.Image}}' homeiq-postgres` — still `postgres:17-alpine` until the P0 above is done

## Success criterion

`/api/v1/memories` and `/api/analysis/status` return 200 instead of 500, with the stack still at 58 healthy and the contract gate green.

## Carry-forward gotchas

1. **Rebuild unrelated services with `--no-deps`** until the postgres swap is done, or compose will recreate postgres on the new image implicitly and trigger the migration unplanned.
2. Host ports: dashboard **13000**, admin-api **18004**, websocket **18001**, postgres **15432**.
3. Test runner is `.venv/bin/python -m pytest`; system `python3` has no pytest. `.venv` has no `pip` — use `uv pip`. `ruff` is at `~/.local/bin/ruff`.
4. Don't lower `CONTRACT_PACE` — admin-api rate-limits at 60/min burst 20. `CONTRACT_TIMEOUT` is 15 because `/api/v1/real-time-metrics` answers at ~10s (TAP-5439).
5. Never use `git stash` for a quality-gate baseline; use `git worktree` or `git show HEAD:path`. Quality scores are location-sensitive — `devex` is 10 at repo root next to `AGENTS.md` and 0 five levels down, so compare at equal depth.
6. The committed `POSTGRES_PASSWORD:-homeiq-secure-2026` default is **not** live — `.env` overrides it. An earlier handoff overstated this.
7. `depends_on` cannot cross compose projects here (core-platform / blueprints / automation-core are separate), and cross-group `depends_on` was removed deliberately. Dependency resilience must be application-side.
