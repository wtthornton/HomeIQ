# Session handoff
**Updated:** 2026-08-04T01:52:21Z
**Git:** e12c8919
**Linear P0:** TAP-5437 (memory side done), new: `automation.patterns` missing

> Sessions 1-5 detail was consolidated here. The full per-session log is recoverable
> with `git log -p .tapps-mcp/session-handoff.md` — this file is tracked.

## Done

- **Postgres swap performed.** `homeiq-postgres` now runs `pgvector/pgvector:pg17`
  (was `postgres:17-alpine`). Same minor, 17.10 → 17.10, so PGDATA carried over
  untouched: 10 schemas and 65 tables before, same after.
- **Fresh pg_dumpall taken immediately before the swap** —
  `backups/postgres/pg_dumpall-20260804T013641Z.sql`, 2.6 MB, 9 `CREATE SCHEMA`,
  cluster-dump terminator present. Supersedes the `...T235445Z` dump.
- **REINDEX DATABASE homeiq completed.** All 282 indexes valid, 0 invalid.
- **`CREATE EXTENSION vector` succeeded — v0.8.6.** The whole point of the swap.
  `memory.memories` and `memory.memory_archive` exist with the HNSW index.
- **Found and fixed a four-part schema drift (commit e12c8919).** Both provisioning
  paths were transcribed from alembic revision **001 only** and silently omitted
  002/003/004, so the tables were created in a shape the ORM could not query:
  - `domain VARCHAR(30)` missing from both tables — **this was the live 500**
  - `embedding vector(768)` but all-MiniLM-L6-v2 emits **384**
  - CHECK listed `fact/pattern/context/correction`; the enum is
    `behavioral/preference/boundary/outcome/routine` (only `preference` overlapped,
    so writing any other type was impossible)
  - `superseded_by` lacked the `ON DELETE SET NULL` the model declares
- **`/api/v1/memories` returns 200** (was 500). `/api/v1/memories/metrics` 200.
  Proven beyond the read path: a `behavioral` row with a `domain` and a real
  384-dim vector inserts cleanly (probed inside a transaction, rolled back;
  table still 0 rows).
- **001-pattern-ml-tables.sql was already applied** — both tables pre-existed;
  the re-run was a clean no-op, as designed.
- Contract gate **79/79, 0 deviations, exit 0**. Stack **58/58 healthy, 0 unhealthy**.

## Open

- **`automation.patterns` does not exist** — newly found, and the only thing left
  blocking `/api/analysis/status` (ai-pattern-service, host **8034**, not admin-api).
  It 500s on `relation "patterns" does not exist`. This is a *fourth* provisioning
  gap, separate from TAP-5437/5438. **Deliberately not fixed — it needs a decision,
  not a guess:** there is no ORM model (`from ...database.models import Pattern`
  raises, and the code falls through to a raw-SQL path), no migration, and no
  init-schemas entry. The only evidence of its shape is the raw SQL in
  `domains/pattern-analysis/ai-pattern-service/src/crud/patterns.py:144-195`:
  `id, pattern_type, device_id, pattern_metadata, confidence, occurrences,
  created_at, updated_at`. Column types and whether `(pattern_type, device_id)`
  should carry a UNIQUE constraint (the check-then-insert logic implies it, but
  nothing declares it) are unresolved. File a story before creating the table.
- **`libs/homeiq-resilience` suite is red** — 10 pre-existing collection errors,
  tests asserting on an un-awaited async `allow_request()`. Untouched.
- **TAP-5440** — api-automation-edge still on its own WebSocket client.
- **TAP-5442** (upstream, TappsMCP Platform) — `_get_brain_bridge()` tenant singleton.

## Next (P0)

- Decide the `automation.patterns` shape and file a story for it, then create the
  table and re-check `/api/analysis/status` on **8034**. That is the last item
  standing between the current state and the previous session's success criterion.
  Do not infer the schema silently — the raw SQL gives column names but not types.

## Blockers

- none

## Changed files

- `infrastructure/postgres/init-schemas.sql` (fresh-deploy path)
- `infrastructure/postgres/migrations/002-memory-schema.sql` (corrected)
- `infrastructure/postgres/migrations/003-memory-schema-align-alembic.sql` (new,
  corrective forward-migration for already-provisioned databases)
- `domains/core-platform/compose.yml` (comment only — cited the wrong dim and a
  stale model path)

## Verify

- `git status --porcelain` — clean except the untracked
  `.tapps-mcp/compaction-marker.json` tool artifact, deliberately not committed
- `docker inspect --format '{{.Config.Image}}' homeiq-postgres` — now
  `pgvector/pgvector:pg17`
- `curl -s -o /dev/null -w '%{http_code}' http://localhost:13000/api/v1/memories` — 200
- `bash scripts/verify-dashboard-contract.sh` — 79/79, 0 deviations, exit 0
- `docker ps --filter name=homeiq --format '{{.Status}}' | grep -c '(healthy)'` — 58.
  **Use `'(healthy)'`, not `healthy`** — the latter also matches `(unhealthy)`
- **Run the two lib suites separately** — `.venv/bin/python -m pytest libs/homeiq-data`
  (36) and `.venv/bin/python -m pytest libs/homeiq-ha` (99). The combined
  `pytest libs/homeiq-data libs/homeiq-ha` in the old handoff **fails at collection**:
  both libs ship a `tests` package containing `test_init.py`, so the module names
  collide. Pre-existing, unrelated to this work, but the old command was wrong.

## Success criterion

`/api/analysis/status` on 8034 returns 200, with the stack still 58 healthy and the
contract gate green. `/api/v1/memories` already meets its half.

## Carry-forward gotchas

1. The `--no-deps`-until-swap caution is **retired** — the swap is done. Postgres was
   brought up with `docker compose --env-file .env -f domains/core-platform/compose.yml
   up -d --no-deps postgres`; the `--env-file .env` is required or the host port and
   credentials resolve to their committed defaults.
2. Host ports: dashboard **13000**, admin-api **18004**, websocket **18001**,
   postgres **15432**, ai-pattern-service **8034**.
3. Test runner is `.venv/bin/python -m pytest`; system `python3` has no pytest.
   `.venv` has no `pip` — use `uv pip`. `ruff` is at `~/.local/bin/ruff`.
4. Don't lower `CONTRACT_PACE` — admin-api rate-limits at 60/min burst 20.
   `CONTRACT_TIMEOUT` is 15 because `/api/v1/real-time-metrics` answers at ~10s.
5. Never use `git stash` for a quality-gate baseline; use `git worktree` or
   `git show HEAD:path`. Quality scores are location-sensitive.
6. The committed `POSTGRES_PASSWORD:-homeiq-secure-2026` default is **not** live —
   `.env` overrides it.
7. `depends_on` cannot cross compose projects here; dependency resilience must be
   application-side.
8. **`libs/homeiq-memory/alembic/versions/` is the schema source of truth**, but
   nothing runs alembic — `MemoryClient.initialize()` defaults to
   `create_tables=False`. The two SQL paths are hand-mirrored from it, which is
   exactly how they fell three revisions behind. When a revision 005 lands, mirror
   it into `init-schemas.sql` *and* `002-memory-schema.sql`, and add a guarded
   corrective step to `003-memory-schema-align-alembic.sql`.
9. `ALTER DATABASE ... REFRESH COLLATION VERSION` fails with "invalid collation
   version change" on these databases: `datcollversion` is NULL because the cluster
   was initialised under musl, which records no version. Harmless — the REINDEX did
   the real work. It only means Postgres won't warn on a *future* libc change.
