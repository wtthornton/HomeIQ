# Session handoff
**Updated:** 2026-08-18T18:18:00Z
**Git:** master @ 08136fbd (PR #90 and #91 both merged; no open PRs)
**Linear P0:** TAP-6169 epic — 14 of 17 children still open

## Done
- **PR #90 merged** (`e5884656`). data-api's unreachable docker fork deleted: `src/docker_endpoints.py` was in no router list, a stale fork of admin-api's live copy that had dropped authentication entirely and predated TAP-5999. Suite 1302 -> 1202 collected (the two deleted modules collected exactly 100), 1202 pass, coverage 73.64%.
- **PR #91 merged** (`08136fbd`). Three TAP-6169 children, all **Done**, all CI-verified:
  - **TAP-6182** — `398e074b` (ARG002 lint) renamed `home_type` -> `_home_type` but left both production call sites passing the old name. Live TypeError. Param was genuinely dead; removed it and both args. Underneath it, `__init__` seeded the **global** `random` module, so two same-seed generators shared one stream. Each instance now owns a `random.Random`.
  - **TAP-6172** — tests patched a `.client` httpx transport removed by the CrossGroupClient migration. Moved to the `_cross_client.call` seam across 3 services.
  - **TAP-6173** — 16 sites did `async with lifespan(app)`; `ServiceLifespan` has no `__call__`. Now `.handler(app)`.
- **CI effect of #91: 273 -> 188 failures, 85 tests fixed, none skipped.** All three error signatures now appear **0** times.
  - device-intelligence 51F/173P -> 23F/201P; ai-automation-service-new 31F/224P -> 13F/242P; ha-ai-agent 96F/419P -> 78F/437P; ai-pattern 79F/597P -> 68F/608P; proactive-agent 16F/89P -> 6F/99P.
- **TAP-6169 epic filed with 17 children** (TAP-6170..6185, plus TAP-6191), all validator-gated 98-100.

## Open — 14 TAP-6169 children remain
- **TAP-6191 (High)** — data-api `Run tests` now passes but `Test Alembic migrations` fails: `idx_entity_labels_gin` already exists. Declared both on the model (`entity.py:99`) and in migration `011`. Two sources of schema truth; decide which owns it. This step had never run before — fixing collection promoted the job into it.
- **TAP-6176** calendar-service missing deps; **TAP-6179** httpx `AsyncClient(app=)`; **TAP-6170/6171** postgres schema+fixture; **TAP-6174** INFLUXDB_TOKEN; **TAP-6175** stale `Database` import; **TAP-6177/6178/6180/6181/6183/6184/6185** per-service defects.
- Not filed: `_context` in `AIAutomationClient.validate_yaml` is the same ARG002 rename as TAP-6182. Docstring says "kept for compatibility" but the underscore means `context=` raises TypeError, so that promise is already void. No in-repo caller passes it — removing it is an API decision.
- `events_endpoints.py` scores 60.9 vs the 70 gate. Max CC ~28.
- TAP-6152 open by design; remaining fix is TAP-6167, needs an AgentForge publish.

## The recurring pattern — expect it on every remaining child
Each fix exposes the next defect underneath, because the earlier failure was gating the later step:
1. TAP-6150's format gate was skipping `Run tests` entirely across 17 services.
2. data-api's collection abort was skipping `Test Alembic migrations` (-> TAP-6191).
3. TAP-6182's TypeError was hiding a global-RNG reproducibility bug.
4. TAP-6172's AttributeError was hiding four pieces of drift: AsyncMock responses making `.json()` return a coroutine, `close()` now a no-op with no `aclose`, the validate endpoint moved to `/api/v1/automations/validate` with payload key `validate_services` and no `context`, and an expected error string `"Could not connect"` that exists nowhere in the source.
Budget for a second root cause behind each one. Do not report a child done on the strength of one green step.

## Corrections carried forward (earlier notes were wrong on these)
1. `unrecognized arguments: --cov=src` in all 17 logs is a **shell comment**, not a failure.
2. **No lint or format gate has failed** in any run since TAP-6150/6155 — they are holding.
3. **No service fails for an unreachable container.** Zero `Connection refused`. Postgres failures are schema/fixture bugs.
4. `weather-api/tests/test_main.py:22` asserts a `SERVICE_NAME` constant, not the literal `'weather-api'`.
5. `automation-miner/tests/conftest.py:28` already uses `ASGITransport` — not a latent httpx site.
6. `automation-miner` has 10 `async with lifespan(app)` sites but its `lifespan` is a plain `@asynccontextmanager` function (`src/api/main.py:166`), **not** a ServiceLifespan. Correct as written — do not pattern-match TAP-6173's fix onto it.
7. air-quality's reported `homeiq` vs `home_assistant` bucket mismatch could not be reproduced; neither string is in that service's tests.

## Environment traps
- **Postgres is on 15432.** Port 5432 belongs to `nlt-research-postgres` (another project). Service conftests default to 5432, so tests authenticate against a stranger and hang rather than fail cleanly. Export `TEST_DATABASE_URL=postgresql+asyncpg://homeiq:homeiq@localhost:15432/homeiq_test`.
- Client-level test files (`test_*_client.py`) run locally in under a second with no infra. Service `test_main.py` suites need live infrastructure this machine lacks — use CI for those.
- Running device-intelligence tests rewrites tracked `models/model_metadata.json` timestamps. Revert it; do not commit.
- The `home-assistant-datasets` submodule has 2 dirty files but an unchanged gitlink. It belongs to `allenporter/home-assistant-datasets` — out of scope to commit. Beware: a stale shell cwd there will target that repo on push.

## Delegation note
Four subagents researched anchors well but **three failed to complete their Linear writes**, two reporting success with confabulated "ids will be assigned later" language; a fourth died on an API error. Always verify a subagent's write claim against a real `save_issue` response id.

## Verify
- `gh pr list --state open` -> empty.
- `cd domains/core-platform/data-api && python -m pytest tests/ -q` -> 1202 passed, 73.64%.
- `ruff check libs/ domains/ custom_components/` plus `ruff format --check` — clean.

## Next (P0)
- **TAP-6191** — highest leverage: it is the only thing between data-api and a fully green job, and data-api is the most-repaired service.
- Then **TAP-6176** (calendar-service deps, mechanical, unblocks a service stuck at 0 collected) and **TAP-6179** (httpx 0.28).

## Success criterion
- Each TAP-6169 child closes with its CI error signature at zero, verified in a real run, with no test skipped, xfailed, or deleted.
