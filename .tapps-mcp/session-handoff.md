# Session handoff
**Updated:** 2026-08-18T20:15:00Z
**Git:** 2f36233f (master; PRs #94/#95/#96/#97/#98 merged, none open)
**Linear P0:** TAP-6205

## Done
- TAP-6191 (PR #94). Filed cause was wrong: init-schemas.sql has no GIN index. Creator is data-api conftest's `drop_all`+`create_all`, teardown only deletes rows. Gave `Test Alembic migrations` its own `homeiq_migrations` DB; migration 011 untouched.
- TAP-6176 (PR #95). requirements.txt lacked fastapi/uvicorn/websockets + 4 homeiq libs. Underneath: 20 test-drift failures. Now 62 passed, exit 0, 78% cov. No prod code changed.
- TAP-6179 (PR #96). Two fixtures -> `ASGITransport`. CI resolves httpx 0.28.1; `app` TypeError at zero.
- TAP-6204 (PR #98). Filed framing too narrow: nothing opened the DB at all, not just ASGI tests. Autouse function-scoped conftest fixture calling `init_database()` + row cleanup. Event-loop errors shared this cause and cleared too. CI: DB-not-available 266->0, loop-closed 58->0, different-loop 34->0; 92->62 failed, 437->467 passed.

## Open
- 11 epic children: TAP-6170/6171/6174/6175/6177/6178/6180/6181/6183/6184/6185 (Backlog; each names its service + signature).
- **TAP-6205** (new, P0): ha-ai-agent-service 62 failed / 467 passed, all service+mock API drift across 12 files. Biggest: test_ha_client 15, test_conversation_service 12 (incl. missing `ConversationService.update_title`), test_phase_1_2_3_features 8. 6 are the SAME `SecretStr` mock defect fixed in TAP-6176 — do those first. Classify each as stale-test vs real-defect by reading the production code; do not edit assertions until green.
- Latent same-gap-as-TAP-6204: `automation-miner` and `device-intelligence-service` drive an app through ASGITransport, have a DatabaseManager, and never init the DB in tests. Masked by their own tracked failures.
- **TAP-6202** (P3): zeek-network-service, ha-simulator, ha-device-control, nlp-fine-tuning have code but no `ci-*.yml` matrix entry. zeek's alembic migrations have never run anywhere.

## Next (P0)
- TAP-6205. Start with the 6 `get_secret_value` mock failures (known shape from TAP-6176), then the 15 in test_ha_client.py.

## Blockers
- none

## Expect a second root cause behind every child
Held 4/4 this session. Never call a child done on one green step. Twice the FILED cause was wrong (TAP-6191, TAP-6204) — re-derive it from a real run before building the prescribed fix.

## Corrections
1. `create_all` ALONE is a no-op on tables init-schemas.sql already made (`checkfirst`). Only `drop_all` first installs model indexes.
2. data-api's suite never touches postgres locally: 17 files shadow conftest's `fresh_db`, and `_database_ready` skips `init_db()` when `async_engine` is set. Local runs cannot reproduce schema-state bugs.
3. This `gh` build rejects `--json` on `gh pr checks` (works on `gh run view`). A monitor using it fails silently.
4. `httpx.ASGITransport` does NOT emit lifespan events — anything a service does in its lifespan never happens under ASGI tests. Verified directly.
5. `init_database(url)` in ha-ai-agent-service IGNORES its argument; it resolves from POSTGRES_URL/DATABASE_URL. Two fixtures pass a hardcoded localhost:5432 that does nothing — don't copy it.

## Environment traps
- **Postgres is 15432**, container `homeiq-postgres`, password in its `POSTGRES_PASSWORD` env (not `homeiq`). 5432 is another project. Local `homeiq_test` was dropped/recreated this session from init-schemas.sql.
- Verify service fixes in a clean venv (`python3 -m venv`; install `libs/homeiq-*/`, then requirements.txt, then pytest tooling) — the repo `.venv` masks missing deps.
- device-intelligence runs rewrite tracked `models/model_metadata.json`; revert, don't commit.
- `home-assistant-datasets` submodule is third-party; a stale cwd there targets that repo.

## Verify
- `gh pr list --state open` -> empty; `git log --oneline -1` -> 2f36233f; `ruff check libs/ domains/ custom_components/` clean.
- master still red on most group workflows: remaining TAP-6169 debt, not regression.

## Success criterion
- Each child closes with its CI error signature at zero in a real run, nothing skipped or xfailed.
