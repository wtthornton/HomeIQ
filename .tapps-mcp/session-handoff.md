# Session handoff
**Updated:** 2026-07-31T21:57:47Z
**Git:** 33672a64
**Linear P0:** none

## Done
- websocket-ingestion: **512 passed** (was 36 failed + 7 errors); suite 216s to 17.5s.
- admin-api: **370 passed** (was uncollectable, 0 tests runnable).
- data-api: **1255 passed, 0 masked skips** (was 92 failed + 60 errors).
- Collection errors fixed in 6 services: `pytest.ini` had `pythonpath = . ../..` but services sit 3 levels deep, so repo-root `tests.path_setup` never resolved. ml-service also needed the importlib loader (its own `tests/__init__.py` shadows the repo-root package).
- ~15 prod bugs fixed: `/events/{event_id}` shadowed 4 static routes (unreachable in prod); incomplete `DateTime(timezone=True)` migration on 3 data-api models; config 403 masked as 500; `timer_id.split("_")[0]` truncated metric labels; `timedelta` used but never imported (latent NameError); `/app/logs` mkdir at import time; uptime returning 100% from an except handler; `init-schemas.sql` hardcoded `ALTER DATABASE homeiq` so search_path was never set in CI.
- CI: **1 to 18 workflows automatic**. Repo is PUBLIC and all jobs are `ubuntu-latest`, so Actions is free/unmetered — the README's "~$70+/mo" premise was wrong and had left 5 PRs merged unvalidated.
- CI wiring: CI set `POSTGRES_URL` but data-api reads `TEST_DATABASE_URL`; removed `|| true` that swallowed lib-install failures.
- TAPPS: 16/16 gates pass, 0 security issues.

## Open
- **`ruff format --check` fails on ~85% of files in every service** and runs BEFORE tests in `reusable-group-ci.yml`, so every domain job fails at step 1. Sole blocker to green CI.
- **Nothing committed** — 133 changed paths in the working tree.
- Services beyond the 4 repaired are unverified; local failures are mostly deps that CI installs.
- Prod InfluxDB credential rotation still not executed (needs prod tokens + `/backups/`).
- `ai-automation-ui/tests/components/test_LoadingSpinner.py` imports a `.tsx` as Python (body `assert True`); deletion denied, will fail that domain.
- `admin-api/src/stats_endpoints.py` is dead code (prod uses the shared-lib class); flagged only.

## Next (P0)
- Commit the test/CI fixes as one reviewable commit FIRST, then run `ruff format` over `domains/` and `libs/` as a separate mechanical commit — the format pass rewrites hundreds of files and would otherwise bury the fixes. That unblocks the CI format gate.

## Blockers
- none

## Changed files
- `.github/workflows/` (9 ci-*.yml + reusable-group-ci, quality-gate, test, codeql, docker-*, README)
- `domains/core-platform/{websocket-ingestion,admin-api,data-api}/`
- `domains/{blueprints/blueprint-index,data-collectors/log-aggregator,device-management/*}/`
- `libs/homeiq-observability/.../logging_service.py`, `infrastructure/postgres/init-schemas.sql`, `CONTRIBUTING.md`, 6 `pytest.ini`

## Verify
- `cd domains/core-platform/websocket-ingestion && pytest tests/ -q` (expect 512)
- `cd domains/core-platform/admin-api && pytest tests/ -q` (expect 370)
- data-api needs postgres on a spare port (5432 is taken by other projects): `docker run -d --rm --name homeiq-ci-pg -e POSTGRES_USER=homeiq -e POSTGRES_PASSWORD=homeiq_test -e POSTGRES_DB=homeiq_test -p 5439:5432 postgres:17-alpine`; load `infrastructure/postgres/init-schemas.sql`; then `TEST_DATABASE_URL="postgresql+asyncpg://homeiq:homeiq_test@localhost:5439/homeiq_test" pytest tests/ -q` (expect 1255). Stop the container after.
- `uvx ruff format --check domains/core-platform/data-api/`

## Success criterion
- A core-platform PR runs `ci-core` to completion: format gate, lint gate, and all three core-platform suites green.
