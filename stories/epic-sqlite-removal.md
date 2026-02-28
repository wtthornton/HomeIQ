---
epic: sqlite-removal
priority: critical
status: complete
estimated_duration: 3-5 days
risk_level: high
source: Story 6.5 (deferred), full codebase audit (2026-02-27)
---

# Epic: Complete SQLite Removal — COMPLETED

**Status:** Open — EXECUTE IMMEDIATELY
**Priority:** Critical (P0)
**Duration:** 3-5 days
**Risk Level:** High — 356 files across 12 categories; runtime breakage if incomplete
**Predecessor:** None — PostgreSQL has been stable for 2+ weeks
**Affects:** 15 services, 19 requirements files, 11 compose files, 13 Alembic configs, 12 test suites, 103 docs, 14+ scripts

## Context

The SQLite-to-PostgreSQL migration (Epics 1-5) is complete and PostgreSQL has been
running stably for over 2 weeks. The dual-mode SQLite fallback code was preserved
during migration for safety. That stabilization window has passed. It's time to
remove ALL SQLite references — code, configs, dependencies, scripts, and documentation.

**Audit found 356 files with SQLite references across 12 categories.**

## Stories

### Story 1: Remove SQLite from Compose Files (11 files)

**Priority:** Critical | **Estimate:** 2h | **Risk:** Medium

**Problem:** 11 compose files still have `DATABASE_URL=sqlite+aiosqlite:///...` env vars
and SQLite named volumes. These are the actual runtime defaults — if `POSTGRES_URL` isn't
set, services fall back to SQLite.

**Files:**
- `domains/core-platform/compose.yml` — env var line 105, volume mount line 116, named volume line 647
- `domains/blueprints/compose.yml` — lines 21, 63
- `domains/automation-core/compose.yml` — lines 82, 128
- `domains/device-management/compose.yml` — line 320
- `domains/pattern-analysis/compose.yml` — lines 15, 65
- `domains/ml-engine/compose.yml` — lines 242, 295
- `docker-compose.dev.yml` — line 91, volume line 99, named volume line 269
- `docker-compose.minimal.yml` — line 33, volume line 36, named volume line 104
- `domains/device-management/ha-setup-service/docker-compose.service.yml` — line 20
- `domains/ml-engine/device-intelligence-service/docker-compose.yml` — line 12

**Acceptance Criteria:**
- [ ] Zero `sqlite` strings in any compose file (`grep -ri sqlite **/compose*.yml` returns 0)
- [ ] All `DATABASE_URL` defaults point to PostgreSQL connection string
- [ ] All SQLite named volumes removed
- [ ] All SQLite volume mounts removed
- [ ] `docker compose config` validates without errors for all compose files
- [ ] `SQLITE_DATABASE_URL` env vars removed

---

### Story 2: Remove SQLite Fallback from Database Init Files (12 files)

**Priority:** Critical | **Estimate:** 4h | **Risk:** High

**Problem:** 12 database init files have `if _is_postgres: ... else: sqlite_engine` dual-mode
logic. The entire `else` branch (SQLite engine creation, PRAGMA event listeners,
WAL mode configuration) must be removed.

**Files:**
- `domains/core-platform/data-api/src/database.py` — also remove `SQLITE_TIMEOUT`, `SQLITE_CACHE_SIZE` env reads
- `domains/automation-core/ai-automation-service-new/src/database/__init__.py`
- `domains/automation-core/ha-ai-agent-service/src/database.py` — most complex: has SQLite permission fixing + inline `ALTER TABLE` migrations
- `domains/automation-core/ai-query-service/src/database/__init__.py`
- `domains/pattern-analysis/ai-pattern-service/src/database/__init__.py`
- `domains/pattern-analysis/api-automation-edge/src/registry/spec_registry.py` — sync SQLAlchemy; also fix `String` → `Boolean` column type
- `domains/ml-engine/rag-service/src/database/session.py`
- `domains/ml-engine/device-intelligence-service/src/core/database.py`
- `domains/ml-engine/ai-training-service/src/database/__init__.py`
- `domains/energy-analytics/proactive-agent-service/src/database.py`
- `domains/device-management/ha-setup-service/src/database.py`
- `domains/blueprints/blueprint-suggestion-service/src/database.py`
- `domains/blueprints/blueprint-index/src/database.py`
- `domains/blueprints/automation-miner/src/miner/database.py`

**Pattern to apply:** Remove `else:` block, make PostgreSQL branch unconditional.
Remove `_is_postgres` / `_is_sqlite` detection variables. Remove PRAGMA event listeners.
Remove SQLite-specific imports (`import aiosqlite`, sqlite3).

**Acceptance Criteria:**
- [ ] Zero `sqlite` references in any database init file
- [ ] PostgreSQL engine creation is unconditional (no `if` guard)
- [ ] All PRAGMA event listeners removed
- [ ] All SQLite-specific imports removed
- [ ] `api-automation-edge/spec_registry.py` Boolean column type fixed
- [ ] Each service starts successfully with PostgreSQL

---

### Story 3: Remove SQLite from Config Files (11 files)

**Priority:** High | **Estimate:** 1h | **Risk:** Low

**Problem:** 11 config/settings files have SQLite connection strings as defaults.

**Files:**
- `domains/automation-core/ha-ai-agent-service/src/config.py` — line 135
- `domains/automation-core/ai-automation-service-new/src/config.py` — line 12
- `domains/automation-core/ai-query-service/src/config.py` — line 12
- `domains/pattern-analysis/ai-pattern-service/src/config.py` — line 12
- `domains/pattern-analysis/api-automation-edge/src/config.py` — lines 29-31
- `domains/ml-engine/ai-training-service/src/config.py` — line 12
- `domains/ml-engine/device-intelligence-service/src/config.py`
- `domains/blueprints/blueprint-suggestion-service/src/config.py` — line 12
- `domains/blueprints/blueprint-index/src/config.py` — line 11
- `domains/device-management/ha-setup-service/src/config.py` — line 24
- `domains/energy-analytics/proactive-agent-service/src/config.py`

**Change:** Replace SQLite default with empty string or PostgreSQL default URL.
Services must require `POSTGRES_URL` / `DATABASE_URL` to be set.

**Acceptance Criteria:**
- [ ] Zero SQLite connection strings in any config file
- [ ] Default is either PostgreSQL URL or empty (requiring env var)
- [ ] `.env.template` / `env.template` files updated with PostgreSQL examples

---

### Story 4: Remove aiosqlite from Requirements Files (19 files)

**Priority:** High | **Estimate:** 30min | **Risk:** Low

**Files:** All 19 requirements files listed in audit:
- `requirements-base.txt` (root shared file)
- `requirements-test.txt`
- 15 service-level `requirements.txt`
- 2 service-level `requirements-prod.txt`

**Acceptance Criteria:**
- [ ] `aiosqlite` not present in any requirements file
- [ ] `grep -ri aiosqlite **/requirements*.txt` returns 0

---

### Story 5: Update Alembic Configs (13 .ini + 13 env.py)

**Priority:** High | **Estimate:** 2h | **Risk:** Medium

**Problem:**
- 13 `alembic.ini` files have `sqlalchemy.url = sqlite+aiosqlite:///...` as default
- 2 `env.py` files lack the `_is_postgres` guard and use SQLite directly
- 1 `env.py` has `sqlite:///` → `sqlite+aiosqlite:///` conversion code to remove

**Acceptance Criteria:**
- [ ] All `alembic.ini` default URLs point to PostgreSQL (or placeholder requiring env var)
- [ ] `blueprint-suggestion-service/alembic/env.py` uses `POSTGRES_URL`
- [ ] `ai-automation-service-new/alembic/env.py` uses `POSTGRES_URL`
- [ ] `device-intelligence-service/alembic/env.py` sqlite conversion code removed
- [ ] `alembic upgrade head` works for all 13 services against PostgreSQL
- [ ] `alembic downgrade -1` works for all 13 services

---

### Story 6: Update Test Fixtures to PostgreSQL (12 files)

**Priority:** High | **Estimate:** 4h | **Risk:** High

**Problem:** 9 `conftest.py` files use `sqlite+aiosqlite:///:memory:` for test databases.
3 additional test files have direct SQLite usage. All tests will break when aiosqlite
is removed unless they switch to PostgreSQL test fixtures.

**Strategy options:**
1. Use `pytest-postgresql` with ephemeral PostgreSQL instances
2. Use the CI PostgreSQL service container (already in `reusable-group-ci.yml`)
3. Use `testcontainers-python` for PostgreSQL

**Files:**
- `domains/core-platform/data-api/tests/conftest.py`
- `domains/automation-core/ai-automation-service-new/tests/conftest.py`
- `domains/automation-core/ai-query-service/tests/conftest.py`
- `domains/pattern-analysis/ai-pattern-service/tests/conftest.py`
- `domains/blueprints/blueprint-index/tests/conftest.py`
- `domains/blueprints/automation-miner/tests/conftest.py`
- `domains/ml-engine/ai-training-service/tests/conftest.py`
- `domains/energy-analytics/proactive-agent-service/tests/conftest.py`
- `domains/pattern-analysis/api-automation-edge/tests/conftest.py`
- `domains/core-platform/data-api/tests/test_database.py`
- `domains/energy-analytics/proactive-agent-service/tests/test_database.py`
- `domains/automation-core/ai-automation-service-new/tests/test_database_init.py`

**Acceptance Criteria:**
- [ ] All test conftest files use PostgreSQL (not SQLite in-memory)
- [ ] Test fixture provides isolated database per test session (schema cleanup between tests)
- [ ] All 704+ tests pass against PostgreSQL
- [ ] CI pipeline uses PostgreSQL service container for all test jobs
- [ ] `StaticPool` SQLAlchemy pool class removed (SQLite-specific)

---

### Story 7: Delete SQLite-Specific Scripts & Tools (14+ files)

**Priority:** Medium | **Estimate:** 1h | **Risk:** Low

**Files to delete:**
- `tools/cli/check_sqlite.py`
- `tools/cli/populate_sqlite.py`
- `tools/cli/simple_populate_sqlite.py`
- `scripts/quality_checks/sqlite_checks.py`
- `scripts/sqlite_maintenance.py`
- `scripts/check_databases.py`
- `scripts/review_databases.py`
- `scripts/clear-devices-db.py`
- `scripts/sqlite-cutover.sh`
- `scripts/sqlite-cutover.ps1`
- `domains/pattern-analysis/ai-pattern-service/scripts/repair_database.py`
- `domains/pattern-analysis/ai-pattern-service/scripts/add_2025_synergy_fields.py`
- `domains/pattern-analysis/ai-pattern-service/scripts/add_quality_columns.py`
- `domains/automation-core/ha-ai-agent-service/scripts/add_pending_preview_column.py`
- `domains/automation-core/ha-ai-agent-service/check_conversation.py`
- `domains/ml-engine/device-intelligence-service/scripts/migrate_add_zigbee_fields.py`

**Also archive (move to `scripts/archive/`):**
- `scripts/migrate-data/` directory (migration tools — historical value)
- `scripts/validate-migration/` directory (validation tools — historical value)

**Acceptance Criteria:**
- [ ] All SQLite-specific scripts deleted
- [ ] Migration/validation scripts archived
- [ ] No broken references to deleted scripts in docs or CI

---

### Story 8: Update CI Workflow

**Priority:** High | **Estimate:** 30min | **Risk:** Low

**File:** `.github/workflows/docker-test.yml`

**Problem:** Line 39 references `sqlite-data` service: `docker compose up -d influxdb sqlite-data`

**Acceptance Criteria:**
- [ ] `sqlite-data` removed from all CI workflow commands
- [ ] CI pipeline passes end-to-end
- [ ] No SQLite references in any `.github/workflows/*.yml` file

---

### Story 9: Remove SQLite from Source Code References (Misc Python)

**Priority:** Medium | **Estimate:** 3h | **Risk:** Low

**Problem:** Various Python source files reference SQLite outside of database init —
health endpoints, API routers, library code, etc.

**Key files:**
- `domains/ml-engine/device-intelligence-service/src/api/health.py` — SQLite health check
- `domains/automation-core/ai-automation-service-new/src/api/suggestion_router.py`
- `domains/pattern-analysis/ai-pattern-service/src/crud/community_patterns.py`
- `domains/blueprints/rule-recommendation-ml/src/data/feedback_store.py`
- `libs/homeiq-patterns/src/homeiq_patterns/evaluation/session_tracer.py`
- `libs/homeiq-patterns/src/homeiq_patterns/evaluation/store.py`
- `libs/homeiq-patterns/src/homeiq_patterns/post_action_verifier.py`
- `libs/homeiq-data/src/homeiq_data/correlation_cache.py`
- `domains/pattern-analysis/api-automation-edge/src/task_queue/huey_config.py`
- `domains/pattern-analysis/api-automation-edge/src/task_queue/scheduler.py`
- `domains/pattern-analysis/api-automation-edge/src/registry/database.py`
- Various other service source files with SQLite comments or fallback references

**Acceptance Criteria:**
- [ ] Zero `sqlite` imports in any Python source file
- [ ] SQLite-specific health check branches removed
- [ ] SQLite-specific PRAGMA references removed
- [ ] `# SQLite compatibility` comments removed
- [ ] `api-automation-edge` huey/scheduler uses PostgreSQL backend

---

### Story 10: Update All Documentation (103 .md files)

**Priority:** Medium | **Estimate:** 4h | **Risk:** Low

**Problem:** 103 markdown files reference SQLite. Categories:

**Delete entirely:**
- `docs/operations/sqlite-cutover-checklist.md`
- `docs/planning/story-6.5-sqlite-cutover-plan.md`
- `docs/planning/story-6.5-quick-reference.md`

**Mark as historical/complete:**
- `stories/epic-sqlite-to-postgresql-migration.md` — mark Story 6.5 as COMPLETE
- `docs/planning/sqlite-to-postgresql-migration-plan.md` — add "COMPLETED" header

**Update tech stack descriptions:**
- `README.md` — PostgreSQL only, no SQLite mention
- `TECH_STACK.md` — PostgreSQL only
- `REBUILD_STATUS.md` — Story 6.5 complete
- `docs/planning/rebuild-status.md` — Story 6.5 complete

**Update operational docs:**
- `docs/operations/disaster-recovery.md` — remove SQLite backup/restore sections
- `docs/operations/postgresql-runbook.md` — remove SQLite comparison references
- `docs/architecture/database-schema.md` — PostgreSQL only
- `docs/architecture/service-groups.md` — remove SQLite references
- `docs/architecture/SERVICES_RANKED_BY_IMPORTANCE.md`
- `docs/architecture/README_ARCHITECTURE_QUICK_REF.md`

**Update service READMEs (20+ files):**
- All service-level `README.md` and `REVIEW_AND_FIXES.md` mentioning SQLite

**Update stories that reference SQLite:**
- `stories/epic-backend-completion.md` — remove Story 6.5 (done)
- `stories/OPEN-EPICS-INDEX.md` — remove Story 6.5 references

**Update MEMORY.md:**
- Remove SQLite migration references
- Update "Backward compat" notes

**Acceptance Criteria:**
- [ ] Cutover planning docs deleted
- [ ] Migration epic marked complete
- [ ] Tech stack docs say PostgreSQL only
- [ ] All service READMEs updated
- [ ] `grep -ri sqlite **/*.md` returns only historical context (migration plan marked complete)
- [ ] MEMORY.md updated
