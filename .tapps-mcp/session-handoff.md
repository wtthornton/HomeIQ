# Session handoff
**Updated:** 2026-08-18T20:05:00Z
**Git:** de79217b (master; PRs #94/#95/#96 merged, none open)
**Linear P0:** TAP-6204

## Done
- TAP-6191 **Done** (PR #94). Not the filed cause: init-schemas.sql has no GIN index and alembic passes clean against it. The creator is data-api conftest's `drop_all`+`create_all`, whose teardown only deletes rows. Fixed by giving `Test Alembic migrations` its own `homeiq_migrations` DB; migration 011 untouched.
- TAP-6176 **Done** (PR #95). requirements.txt lacked fastapi/uvicorn/websockets + 4 homeiq libs. Underneath: 3 failures + 17 errors, all test drift. 62 passed, exit 0, 78% coverage. No production code changed.
- TAP-6179 **Done** (PR #96). Two fixtures -> `AsyncClient(transport=ASGITransport(app=app))`. CI resolves httpx 0.28.1; `app` TypeError at zero. Merged knowingly with the service still red.

## Open
- 11 epic children remain: TAP-6170/6171/6174/6175/6177/6178/6180/6181/6183/6184/6185 (all Backlog; see each for its service + signature).
- **TAP-6204** (new, P0): ha-ai-agent-service 90 failed / 439 passed. `ASGITransport` does not emit lifespan events (verified directly), so `main.py:170 init_database` never runs and DB endpoints 500 with "Database not available" (136x in CI). Repo has NO `asgi-lifespan`/`LifespanManager` anywhere — needs a decision, not an alignment. Event-loop errors (`Event loop is closed` 58x, `different loop` 34x) are a SEPARATE cause; do not assume they vanish.
- **TAP-6202** (new, P3): zeek-network-service, ha-simulator, ha-device-control, nlp-fine-tuning have code but appear in no `ci-*.yml` services matrix. zeek has an alembic.ini whose migrations have never run anywhere.

## Next (P0)
- TAP-6204. Decide fixture-runs-lifespan (add `asgi-lifespan`) vs fixture-inits-DB-directly, apply consistently, then re-count the event-loop failures and file what survives.

## Blockers
- none

## Expect a second root cause behind every child
Held again 3/3 this session. Never call a child done on one green step.

## Corrections to earlier notes
1. TAP-6191's filed cause was wrong; see Done above.
2. `create_all` ALONE is a no-op on tables init-schemas.sql already made (`checkfirst`). Only `drop_all` first installs model indexes.
3. data-api's suite never touches postgres locally: 17 test files shadow conftest's `fresh_db`, and `_database_ready` skips `init_db()` when `async_engine` is set. A full local run leaves the DB unchanged — CI behaves differently. Local runs cannot reproduce schema-state bugs.
4. This `gh` build does NOT support `--json` on `gh pr checks` (it does on `gh run view`). A monitor using it fails silently.

## Environment traps
- **Postgres is 15432**, container `homeiq-postgres`, password in its `POSTGRES_PASSWORD` env (not `homeiq`). 5432 is another project.
- I dropped and recreated local DB `homeiq_test` this session (seeded from init-schemas.sql). Any prior local data in it is gone.
- Verify service fixes in a clean venv (`python3 -m venv`, install `libs/homeiq-*/` then requirements.txt then pytest tooling) — the repo `.venv` masks missing deps.
- device-intelligence runs rewrite tracked `models/model_metadata.json`; revert, don't commit.
- `home-assistant-datasets` submodule is third-party; a stale cwd there targets that repo.

## Verify
- `gh pr list --state open` -> empty; `git log --oneline -1` -> de79217b.
- `ruff check libs/ domains/ custom_components/` — clean.
- master still red on most group workflows: remaining TAP-6169 debt, not regression.

## Success criterion
- Each child closes with its CI error signature at zero in a real run, nothing skipped or xfailed.
