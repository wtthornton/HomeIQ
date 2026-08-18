# Session handoff
**Updated:** 2026-08-18T18:30:40Z
**Git:** de0ef06c (master; PRs #90/#91/#92 merged, none open)
**Linear P0:** TAP-6191

## Done
- PR #90: deleted data-api's docker fork instead of adding the `docker` dep the old handoff prescribed — it was registered in no router list, a stale unauthenticated fork of admin-api's live copy. 1202 pass, coverage 73.64%.
- PR #91: TAP-6182/6172/6173 all **Done**, CI-verified. **273 -> 188 failures, 85 tests fixed, none skipped**; all three error signatures now appear 0 times.
- TAP-6169 epic filed with 17 children (TAP-6170..6185, 6191): 4 cross-cutting causes fixed once each, rest per-service.

## Open
- 14 children remain: TAP-6170/6171/6174/6175/6176/6177/6178/6179/6180/6181/6183/6184/6185/6191.
- Unfiled: `_context` in `AIAutomationClient.validate_yaml` is the same ARG002 rename as TAP-6182; docstring claims "kept for compatibility" but `context=` now raises TypeError. No in-repo caller passes it.
- `events_endpoints.py` 60.9 vs the 70 gate. TAP-6152 open by design (needs TAP-6167 AgentForge publish).

## Next (P0)
- Fix the `idx_entity_labels_gin` double-create failing data-api's `Test Alembic migrations`. Declared both on the model (`entity.py:99`) and in migration `011`, so `alembic upgrade head` collides with schema-init. Decide which side owns it and delete the other — do not add an existence check. Highest leverage: only thing between data-api and a fully green job. Then TAP-6176 (calendar-service deps) and TAP-6179 (httpx 0.28).

## Blockers
- none

## Expect a second root cause behind every child
Each fix exposes the next defect, because the earlier failure gated the later step. Four instances: TAP-6150's format gate skipped `Run tests` across 17 services; data-api's collection abort skipped Alembic (-> TAP-6191); TAP-6182's TypeError hid a global-RNG bug; TAP-6172's AttributeError hid four pieces of drift. Never call a child done on one green step.

## Corrections (earlier notes were wrong)
1. `unrecognized arguments: --cov=src` is a shell **comment**, not a failure.
2. No lint/format gate has failed since TAP-6150/6155 — they hold.
3. No service fails for an unreachable container; postgres failures are schema/fixture bugs.
4. `automation-miner`'s 10 `async with lifespan(app)` sites are **correct** (plain `@asynccontextmanager`, not ServiceLifespan) — do not apply TAP-6173's fix there.
5. air-quality's `homeiq` vs `home_assistant` bucket mismatch could not be reproduced.

## Environment traps
- **Postgres is 15432.** 5432 is `nlt-research-postgres` (another project) — conftests defaulting to 5432 hang instead of failing. Export `TEST_DATABASE_URL=postgresql+asyncpg://homeiq:homeiq@localhost:15432/homeiq_test`.
- `test_*_client.py` run locally in <1s; service `test_main.py` suites need infra — use CI.
- device-intelligence runs rewrite tracked `models/model_metadata.json`; revert, don't commit.
- The `home-assistant-datasets` submodule is third-party; a stale cwd there targets that repo on push.

## Delegation note
Three of four subagents failed to complete their Linear writes, two claiming success with confabulated "ids assigned later" text. Verify write claims against a real `save_issue` response id.

## Verify
- `gh pr list --state open` -> empty; `git log --oneline -1` -> de0ef06c.
- `cd domains/core-platform/data-api && python -m pytest tests/ -q` -> 1202 passed (needs pg on 15432).
- `ruff check libs/ domains/ custom_components/` — clean.
- master is red on 7/8 group workflows: pre-existing TAP-6169 debt, not regression.

## Success criterion
- Each TAP-6169 child closes with its CI error signature at zero in a real run, nothing skipped or xfailed.
