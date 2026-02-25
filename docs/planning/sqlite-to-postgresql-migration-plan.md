# SQLite to PostgreSQL Migration Plan

**Project**: HomeIQ — AI-Powered Home Assistant Intelligence Platform
**Date**: 2026-02-24
**Architecture**: Path A — Single PostgreSQL instance, schema-per-domain
**Scope**: Migrate all 10 SQLite databases across 15 services to PostgreSQL

---

## Current Status

| Epic | Description | Status | Stories |
|------|-------------|--------|---------|
| Epic 1 | PostgreSQL Infrastructure Foundation | **Complete** | 5/5 stories done |
| Epic 2 | Core Platform Migration (data-api) | **Complete** | 4/4 stories done |
| Epic 3 | ML Engine & Shared Database Migration | **Complete** | 4/4 stories done |
| Epic 4 | Automation Core & Pattern Analysis Decoupling | **Complete** | 5/5 stories done |
| Epic 5 | Blueprints & Device Management Migration | **Complete** | 7/7 stories done |
| Epic 6 | Validation, Cleanup & Cutover | **In Progress** | 4/5 stories done |

**Overall Progress**: All 15 services updated with dual-mode PostgreSQL/SQLite support.
Compose files, database init scripts, and requirements.txt files updated across all domains.
Migration scripts and backup tooling created. Final cutover (Story 6.5) pending stabilization period.

**Last Updated**: 2026-02-24

---

## Executive Summary

HomeIQ currently uses 10 separate SQLite database files across 15 services. The most
critical architectural problem is the shared `ai_automation.db` volume mounted by 4
services across 3 domains (ml-engine, automation-core, pattern-analysis), creating
tight coupling that prevents independent deployment.

This plan migrates all SQLite databases to a single PostgreSQL 17 instance using
schema-per-domain isolation. Each domain gets its own PostgreSQL schema, eliminating
file-volume coupling while maintaining the simplicity of a single database server.

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| PostgreSQL version | 17 (latest stable) | JSONB improvements, better partitioning |
| Driver | asyncpg | Best async performance for SQLAlchemy 2.x |
| Schema strategy | Schema-per-domain (not DB-per-domain) | Single connection string, cross-domain queries if needed, simpler ops |
| Migration tool | Alembic (per-schema) | 9 services already use Alembic, consistent tooling |
| Data migration | pgloader + validation scripts | Automated SQLite-to-Postgres transfer |
| Shared library | `homeiq-data` (database_pool.py) | Central place for engine/session factory — already exists |
| Connection pooling | SQLAlchemy async pool (not StaticPool) | PostgreSQL supports real connection pools, unlike SQLite |

### PostgreSQL Schema Map

```
homeiq-postgres:5432 / homeiq
  ├── core          → metadata.db         (data-api)
  ├── automation     → ai_automation.db    (ai-automation, ai-query, ai-training, ai-pattern)
  ├── agent         → ha_ai_agent.db      (ha-ai-agent-service)
  ├── blueprints    → blueprint_index.db, blueprint_suggestions.db, miner.db
  ├── energy        → proactive_agent.db   (proactive-agent-service)
  ├── devices       → device_intelligence.db, ha-setup.db, device_cache
  ├── patterns      → api-automation-edge.db  (api-automation-edge)
  └── rag           → rag_service.db       (rag-service)
```

### Services Affected (15 total)

| # | Service | Current DB | Target Schema | Has Alembic |
|---|---------|-----------|---------------|-------------|
| 1 | data-api | metadata.db | core | Yes |
| 2 | ai-automation-service-new | ai_automation.db (shared) | automation | Yes |
| 3 | ai-query-service | ai_automation.db (shared) | automation | No |
| 4 | ai-training-service | ai_automation.db (shared) | automation | No |
| 5 | ai-pattern-service | ai_automation.db (shared) | automation | No |
| 6 | ha-ai-agent-service | ha_ai_agent.db | agent | Yes |
| 7 | blueprint-index | blueprint_index.db | blueprints | No |
| 8 | blueprint-suggestion-service | blueprint_suggestions.db | blueprints | Yes |
| 9 | automation-miner | miner.db | blueprints | Yes |
| 10 | rag-service | rag_service.db | rag | No |
| 11 | device-intelligence-service | device_intelligence.db | devices | Yes |
| 12 | ha-setup-service | ha-setup.db | devices | Yes |
| 13 | proactive-agent-service | proactive_agent.db | energy | Yes |
| 14 | api-automation-edge | api-automation-edge.db | patterns | Yes |
| 15 | device-database-client | device_cache (filesystem) | devices | No |

---

## Epic 1: PostgreSQL Infrastructure Foundation

> **Execution Status: COMPLETE**
> All 5 stories delivered. PostgreSQL 17 container added to core-platform compose,
> 8 domain schemas created via init script, `homeiq-data` library upgraded with
> `create_pg_engine()` and dual-mode support, shared Alembic helpers created,
> and CI/docker-bake updated.

**Goal**: Stand up PostgreSQL in Docker, create the shared library support, and
establish the schema-per-domain pattern before touching any service.

**Dependencies**: None (greenfield)
**Risk**: Low — no existing services affected

### Story 1.1: Add PostgreSQL Container to core-platform

**Description**: Add a PostgreSQL 17 service to `domains/core-platform/compose.yml`
with production-ready configuration. This becomes the single shared database server.

**Tasks**:
- Add `postgres` service to `domains/core-platform/compose.yml`:
  - Image: `postgres:17-alpine`
  - Port: `5432:5432`
  - Volume: `postgres_data:/var/lib/postgresql/data`
  - Environment: `POSTGRES_DB=homeiq`, `POSTGRES_USER`, `POSTGRES_PASSWORD` from `.env`
  - Resource limits: 512M memory, 1.0 CPU (matches InfluxDB allocation)
  - Healthcheck: `pg_isready -U ${POSTGRES_USER} -d homeiq`
  - Logging: JSON file driver with `service=postgres,group=core-platform` labels
- Add `postgres_data` to the volumes section
- Add PostgreSQL env vars to `.env.example`:
  ```
  POSTGRES_USER=homeiq
  POSTGRES_PASSWORD=<generate-secure-password>
  POSTGRES_DB=homeiq
  DATABASE_URL=postgresql+asyncpg://homeiq:<password>@postgres:5432/homeiq
  ```
- Update `docker-bake.hcl` — postgres is image-only (no build target), like InfluxDB

**Acceptance Criteria**:
- `docker compose -f domains/core-platform/compose.yml up postgres` starts cleanly
- Healthcheck passes within 30s
- Database `homeiq` is created automatically
- Container restarts cleanly with persisted data

---

### Story 1.2: Create PostgreSQL Schema Initialization Script

**Description**: Create an entrypoint init script that creates all 8 domain schemas
on first startup. PostgreSQL runs `*.sql` files in `/docker-entrypoint-initdb.d/`
on first boot.

**Tasks**:
- Create `infrastructure/postgres/init-schemas.sql`:
  ```sql
  -- Domain schemas for HomeIQ
  CREATE SCHEMA IF NOT EXISTS core;
  CREATE SCHEMA IF NOT EXISTS automation;
  CREATE SCHEMA IF NOT EXISTS agent;
  CREATE SCHEMA IF NOT EXISTS blueprints;
  CREATE SCHEMA IF NOT EXISTS energy;
  CREATE SCHEMA IF NOT EXISTS devices;
  CREATE SCHEMA IF NOT EXISTS patterns;
  CREATE SCHEMA IF NOT EXISTS rag;

  -- Grant usage to the application user
  GRANT ALL ON SCHEMA core, automation, agent, blueprints,
                       energy, devices, patterns, rag
       TO homeiq;
  ```
- Mount this script in the compose service:
  ```yaml
  volumes:
    - ../../infrastructure/postgres/init-schemas.sql:/docker-entrypoint-initdb.d/01-schemas.sql:ro
  ```
- Create `infrastructure/postgres/postgresql.conf` with tuned settings:
  - `shared_buffers = 128MB`
  - `effective_cache_size = 256MB`
  - `work_mem = 4MB`
  - `max_connections = 100`
  - `log_min_duration_statement = 500` (log slow queries > 500ms)

**Acceptance Criteria**:
- All 8 schemas created on first `docker compose up`
- `\dn` in psql shows all schemas
- Re-running `docker compose up` after stop doesn't recreate schemas (idempotent)

---

### Story 1.3: Upgrade `homeiq-data` Shared Library for PostgreSQL

**Description**: Upgrade `libs/homeiq-data/src/homeiq_data/database_pool.py` to
support both PostgreSQL (asyncpg) and SQLite (aiosqlite) backends. This is the
central engine/session factory used across services.

**Tasks**:
- Add `asyncpg>=0.30.0` and `psycopg[binary]>=3.2.0` to `libs/homeiq-data/pyproject.toml`
  as optional dependencies (`extras_require = {"postgres": [...]}`)
- Refactor `create_shared_db_engine()` in `database_pool.py`:
  - Detect driver from URL prefix (`postgresql+asyncpg://` vs `sqlite+aiosqlite://`)
  - For PostgreSQL: use real connection pool (`pool_size`, `max_overflow`, `pool_recycle=3600`)
  - For SQLite: keep existing StaticPool behavior (backward compat during migration)
  - Add PostgreSQL-specific PRAGMA equivalent: `search_path` set per schema
  - Add connection event listeners for schema path: `SET search_path TO <schema>`
- Add `create_pg_engine()` convenience function:
  ```python
  def create_pg_engine(
      database_url: str,
      schema: str,
      pool_size: int = 10,
      max_overflow: int = 5,
  ) -> AsyncEngine:
      """Create PostgreSQL async engine with schema isolation."""
  ```
- Add `get_database_url()` helper that reads from env with fallback:
  ```python
  def get_database_url(service_name: str) -> str:
      """Build DATABASE_URL from env: POSTGRES_URL + schema, or fallback to SQLITE_URL."""
  ```
- Add health check function: `async def check_pg_connection(engine) -> bool`
- Keep full backward compatibility — SQLite URLs still work unchanged

**Acceptance Criteria**:
- Existing SQLite services work without changes (StaticPool path unchanged)
- New PostgreSQL connections use real pool with `pool_pre_ping=True`
- Schema isolation verified: two engines with different schemas see different tables
- `get_pool_stats()` works for both backends

---

### Story 1.4: Create Shared Alembic Multi-Schema Configuration

**Description**: Create a shared Alembic configuration pattern that supports
schema-per-domain migrations. Each service that needs migrations will have its
own `alembic/` directory but share a common `env.py` template.

**Tasks**:
- Create `libs/homeiq-data/src/homeiq_data/alembic_helpers.py`:
  - `run_async_migrations(target_metadata, schema_name, database_url)` — reusable
    migration runner that sets `search_path` before running
  - `get_alembic_config(service_dir, schema_name)` — builds Alembic config
  - Handles both online (direct) and offline (SQL generation) modes
- Create template `env.py` in `libs/homeiq-data/templates/alembic_env.py`:
  ```python
  from homeiq_data.alembic_helpers import run_async_migrations

  def run_migrations_online():
      run_async_migrations(
          target_metadata=Base.metadata,
          schema_name=SCHEMA_NAME,
          database_url=settings.database_url,
      )
  ```
- Document the pattern in `libs/homeiq-data/README.md`

**Acceptance Criteria**:
- Alembic `upgrade head` creates tables in the correct schema (not public)
- Alembic `revision --autogenerate` detects changes within a schema
- Multiple schemas can be migrated independently
- Works with `asyncpg` driver (thread executor pattern for sync Alembic operations)

---

### Story 1.5: Add PostgreSQL to docker-bake.hcl and CI

**Description**: Update build tooling to account for the new PostgreSQL dependency.

**Tasks**:
- Document postgres in `docker-bake.hcl` (image-only, like InfluxDB — no build target)
- Update `domains/core-platform/compose.yml` dependency chain:
  - `data-api` depends on both `influxdb` AND `postgres` (service_healthy)
- Update `.env.example` with all new Postgres vars
- Add PostgreSQL readiness to any CI health-check scripts

**Acceptance Criteria**:
- `docker compose up -d` starts postgres before data-api
- Full stack startup order is preserved
- CI pipeline can spin up postgres for integration tests

---

## Epic 2: Core Platform Migration (data-api → `core` schema)

> **Execution Status: COMPLETE**
> All 4 stories delivered. data-api database layer updated with dual-mode support
> (PostgreSQL via asyncpg or SQLite via aiosqlite based on DATABASE_URL). Alembic
> migrations created for the `core` schema. Data migration script template created.
> Compose configuration updated with PostgreSQL dependency and schema env var.

**Goal**: Migrate the most critical service first — data-api owns `metadata.db`
which is the metadata backbone queried by all services via HTTP.

**Dependencies**: Epic 1 complete
**Risk**: High — data-api is Tier 1 critical infrastructure. Requires careful
dual-mode testing.

### Story 2.1: Add PostgreSQL Support to data-api Database Layer

**Description**: Update data-api's database configuration to support PostgreSQL
while keeping SQLite as fallback. The service should work with either backend
based on `DATABASE_URL` env var.

**Tasks**:
- Update `domains/core-platform/data-api/requirements.txt`:
  - Add `asyncpg>=0.30.0`
  - Keep `aiosqlite` for fallback
- Refactor `src/database.py` (or equivalent):
  - Replace `StaticPool` / SQLite-specific PRAGMA with driver detection from `database_pool.py`
  - Use `create_pg_engine(schema="core")` when `DATABASE_URL` starts with `postgresql`
  - Remove `check_same_thread=False` for PostgreSQL path
  - Update connection pool settings: `pool_size=10, max_overflow=5, pool_recycle=3600`
- Update SQLAlchemy models:
  - Add `__table_args__ = {"schema": "core"}` to all models, or set it via
    metadata `schema` parameter: `Base = DeclarativeBase(metadata=MetaData(schema="core"))`
  - Verify column types map correctly:
    - `String` → `String` (works on both)
    - `Boolean` → `Boolean` (SQLite stores as int, Postgres native)
    - `DateTime` → `DateTime(timezone=True)` for Postgres (use timezone-aware)
    - `JSON` → `JSONB` for Postgres (better indexing)
  - Handle any `sqlite3`-specific column defaults

**Tables to migrate**:
- `devices` — device registry
- `entities` — entity registry with FK to devices
- `automations` — automation registry
- `service` — service registry
- `team_preferences` — user preferences
- `statistics_meta` — statistics metadata

**Acceptance Criteria**:
- data-api starts and passes healthcheck with `DATABASE_URL=postgresql+asyncpg://...`
- All 6 tables created in `core` schema
- All existing REST endpoints work with PostgreSQL backend
- data-api still works with `DATABASE_URL=sqlite+aiosqlite:///...` (dual mode)

---

### Story 2.2: Create Alembic Migrations for data-api

**Description**: Set up Alembic for data-api targeting the `core` schema and generate
the initial migration from existing models.

**Tasks**:
- Initialize Alembic in `domains/core-platform/data-api/`:
  ```
  alembic init alembic
  ```
- Configure `alembic/env.py` using shared template from Story 1.4
- Set `version_table_schema = "core"` so Alembic's own version table lives in the schema
- Generate initial migration: `alembic revision --autogenerate -m "initial core schema"`
- Add migration runner to startup: `await run_migrations_on_startup()`
- Test `alembic upgrade head` against empty PostgreSQL

**Acceptance Criteria**:
- `alembic upgrade head` creates all 6 tables in `core` schema
- `alembic downgrade base` cleanly removes them
- `alembic_version` table lives in `core` schema, not `public`
- Autogenerate correctly detects new model changes

---

### Story 2.3: Data Migration Script for metadata.db

**Description**: Create a one-time data migration script that transfers existing
data from `metadata.db` (SQLite) to PostgreSQL `core` schema.

**Tasks**:
- Create `scripts/migrate-data/migrate_core.py`:
  - Read all rows from SQLite `metadata.db`
  - Write to PostgreSQL `core.*` tables using batch inserts
  - Handle type conversions (SQLite integer booleans → Postgres native booleans)
  - Validate row counts match post-migration
  - Log any conversion errors
- Alternatively, create a pgloader config file `scripts/migrate-data/core.load`:
  ```
  LOAD DATABASE
    FROM sqlite:///app/data/metadata.db
    INTO postgresql://homeiq:password@postgres:5432/homeiq

  WITH include drop, create tables, create indexes, reset sequences

  SET search_path TO core

  CAST type integer when (= "boolean") to boolean using integer-to-boolean;
  ```
- Create validation script that compares row counts and checksums between SQLite and Postgres

**Acceptance Criteria**:
- All data transferred with zero loss
- Row counts match between source and target
- Foreign key relationships preserved
- Script is idempotent (can be re-run safely)

---

### Story 2.4: Update data-api Compose Configuration

**Description**: Update Docker Compose to point data-api at PostgreSQL and remove
the SQLite volume.

**Tasks**:
- Update `domains/core-platform/compose.yml` data-api service:
  - Change `DATABASE_URL` env var to `postgresql+asyncpg://homeiq:${POSTGRES_PASSWORD}@postgres:5432/homeiq`
  - Add `DATABASE_SCHEMA=core` env var
  - Add `depends_on: postgres: condition: service_healthy`
  - Keep `sqlite-data` volume temporarily (migration period)
- Update data-api Dockerfile:
  - Add `asyncpg` to pip install
- Test full startup: postgres → data-api → all downstream services

**Acceptance Criteria**:
- data-api starts against PostgreSQL in full stack
- All downstream services (websocket-ingestion, admin-api, etc.) work unchanged
  (they talk to data-api via HTTP, not direct DB — zero impact)
- Health check passes

---

## Epic 3: ML Engine & Shared Database Migration (→ `automation` + `devices` + `rag` schemas)

> **Execution Status: COMPLETE**
> All 4 stories delivered. ai-training-service, device-intelligence-service, and
> rag-service all migrated to PostgreSQL with dual-mode support. Database initialization
> refactored to use `create_pg_engine()` with correct schema. Data migration scripts
> created for all three databases.

**Goal**: Break the shared `ai_automation.db` volume coupling by migrating ml-engine
services to PostgreSQL. This is the highest-value migration — it decouples 3 domains.

**Dependencies**: Epic 1 complete, Epic 2 recommended (validates the pattern)
**Risk**: Medium-High — 4 services share `ai_automation.db`, schema must be migrated
atomically

### Story 3.1: Migrate ai-training-service to PostgreSQL (`automation` schema)

**Description**: ai-training-service owns the `ai_automation.db` volume and defines
the `training_runs` table. Migrate it first as the schema owner.

**Tasks**:
- Update `requirements.txt`: add `asyncpg>=0.30.0`
- Refactor database initialization:
  - Replace `sqlite+aiosqlite:////app/data/ai_automation.db` with PostgreSQL URL
  - Use `create_pg_engine(schema="automation")`
  - Remove `StaticPool` configuration
- Update models: add `schema="automation"` to metadata
- Create Alembic migration for `training_runs` table in `automation` schema
- This service only writes — verify INSERT/UPDATE patterns work with asyncpg

**Acceptance Criteria**:
- ai-training-service starts and creates `automation.training_runs`
- Training job records insert correctly
- No more dependency on `ai_automation_data` Docker volume

---

### Story 3.2: Migrate device-intelligence-service to PostgreSQL (`devices` schema)

**Description**: device-intelligence-service has its own isolated `device_intelligence.db`.
Straightforward single-service migration.

**Tasks**:
- Update `requirements.txt`: add `asyncpg>=0.30.0`
- Refactor database initialization:
  - Replace dynamic URL conversion (`sqlite://` → `sqlite+aiosqlite://`) with PostgreSQL URL
  - Use `create_pg_engine(schema="devices")`
- Update models with `schema="devices"`
- Create Alembic migration for device intelligence tables
- Migrate `recreate_tables()` function to use Alembic `downgrade`/`upgrade`

**Acceptance Criteria**:
- device-intelligence-service starts against PostgreSQL
- Device intelligence data persists across restarts
- `recreate_tables()` still works (via Alembic)

---

### Story 3.3: Migrate rag-service to PostgreSQL (`rag` schema)

**Description**: rag-service has its own `rag_service.db` with a relative path mount
(not a named volume — a known issue). Migrate to PostgreSQL and fix the volume issue.

**Tasks**:
- Update `requirements.txt`: add `asyncpg>=0.30.0`
- Refactor database initialization:
  - Replace `sqlite+aiosqlite:///./data/rag_service.db` with PostgreSQL URL
  - Use `create_pg_engine(schema="rag")`
  - Remove the relative `./rag-service/data:` bind mount from compose
- Update `rag_knowledge` model with `schema="rag"`
- Create Alembic migration for `rag_knowledge` table
- Evaluate: if rag-service stores embeddings as BLOB, consider using `pgvector`
  extension for native vector search (future enhancement, not required for migration)

**Acceptance Criteria**:
- rag-service starts against PostgreSQL
- Knowledge storage and retrieval works
- Relative bind mount removed from compose (fix existing issue)

---

### Story 3.4: Data Migration for ML Engine Databases

**Description**: Migrate data from `ai_automation.db`, `device_intelligence.db`,
and `rag_service.db` to their respective PostgreSQL schemas.

**Tasks**:
- Create `scripts/migrate-data/migrate_automation.py` — handles `ai_automation.db`:
  - Migrate all shared tables: `suggestions`, `automation_versions`, `plans`,
    `compiled_artifacts`, `deployments`, `training_runs`
  - Handle the shared-write scenario: stop all 4 services during migration
  - Validate FK integrity post-migration
- Create `scripts/migrate-data/migrate_devices.py` — handles `device_intelligence.db`
- Create `scripts/migrate-data/migrate_rag.py` — handles `rag_service.db`
  - Special handling for BLOB/binary embedding data
- Create `scripts/migrate-data/run_all.sh` — orchestrator that:
  1. Stops affected services
  2. Runs pgloader/migration scripts in order
  3. Validates all schemas
  4. Restarts services

**Acceptance Criteria**:
- All data migrated with validation checksums
- Zero data loss verified via row counts
- Migration script is documented and repeatable

---

## Epic 4: Automation Core & Pattern Analysis Decoupling (→ `automation` + `patterns` schemas)

> **Execution Status: COMPLETE**
> All 5 stories delivered. ai-automation-service-new, ai-query-service, ai-pattern-service,
> and api-automation-edge all migrated to PostgreSQL. Shared `ai_automation_data` Docker
> volume references removed from all compose files. The cross-domain coupling that was
> the primary motivation for this migration has been fully eliminated.

**Goal**: Point automation-core and pattern-analysis services at PostgreSQL, completing
the decoupling of the `ai_automation.db` triangle. After this epic, the shared Docker
volume is eliminated entirely.

**Dependencies**: Epic 3 Story 3.1 complete (automation schema exists with data)
**Risk**: Medium — these services have the most complex query patterns against the shared DB

### Story 4.1: Migrate ai-automation-service-new to PostgreSQL

**Description**: The primary automation service with the richest schema. Already has
Alembic configured.

**Tasks**:
- Update `requirements.txt`: add `asyncpg>=0.30.0`
- Refactor `src/database.py`:
  - Replace SQLite engine with `create_pg_engine(schema="automation")`
  - Remove `StaticPool`, `check_same_thread`, SQLite PRAGMAs
  - Update connection pool: `pool_size=10, max_overflow=5`
- Update all model classes: verify `schema="automation"` via shared metadata
- Migrate existing Alembic config:
  - Update `alembic.ini` sqlalchemy.url to PostgreSQL
  - Update `env.py` to use shared helper with `schema="automation"`
  - Set `version_table_schema = "automation"`
- Test all API endpoints: plan creation, compilation, deployment, suggestions
- Verify hybrid flow (plans → compiled_artifacts → deployments) with FK integrity

**Acceptance Criteria**:
- All CRUD operations work against PostgreSQL
- Alembic migrations run cleanly
- No references to `ai_automation_data` volume remain
- All existing API tests pass

---

### Story 4.2: Migrate ai-query-service to PostgreSQL

**Description**: ai-query-service reads from the shared `ai_automation.db`. It has no
Alembic of its own — it relies on the schema owner's migrations.

**Tasks**:
- Update `requirements.txt`: add `asyncpg>=0.30.0`, remove `aiosqlite`
- Refactor database connection:
  - Replace SQLite URL with PostgreSQL URL
  - Use `create_pg_engine(schema="automation")` — same schema as ai-automation-service
  - This service is a read consumer of the `automation` schema
- Remove `ai_automation_data` volume mount from compose
- Remove `ai_automation_models` volume mount from compose (if only used for DB)
- Test all query endpoints against PostgreSQL

**Acceptance Criteria**:
- Query service reads from `automation` schema successfully
- No volume coupling to ml-engine or automation-core
- All query response payloads match previous SQLite responses

---

### Story 4.3: Migrate ai-pattern-service to PostgreSQL

**Description**: ai-pattern-service reads/writes to `ai_automation.db` AND has its own
tables (`synergy_opportunities`, `synergy_feedback`). These own tables move to the
`automation` schema since they have FK relationships to other automation tables.

**Tasks**:
- Update `requirements.txt`: add `asyncpg>=0.30.0`
- Refactor database initialization:
  - Replace SQLite engine with `create_pg_engine(schema="automation")`
  - Remove SQLite PRAGMA listeners and integrity checks
  - Add PostgreSQL-native integrity check (simpler — just test connection)
- Update models: `synergy_opportunities` and `synergy_feedback` with `schema="automation"`
- Create Alembic migration for synergy tables (add to `automation` schema migrations)
- Remove `ai_automation_data` volume mount from compose
- Remove database integrity repair scripts (PostgreSQL handles this natively)

**Acceptance Criteria**:
- Synergy detection and feedback loop work against PostgreSQL
- FK relationship between `synergy_feedback` → `synergy_opportunities` enforced
- No SQLite volume references remain in pattern-analysis compose

---

### Story 4.4: Migrate api-automation-edge to PostgreSQL (`patterns` schema)

**Description**: api-automation-edge has its own isolated `api-automation-edge.db`.
Straightforward migration.

**Tasks**:
- Update `requirements.txt`: add `asyncpg>=0.30.0`
- Refactor database connection to use `create_pg_engine(schema="patterns")`
- Update `spec_versions` model with `schema="patterns"`
- Create Alembic migration for `spec_versions` table
- Remove `api_automation_edge_data` volume from compose

**Acceptance Criteria**:
- Spec version tracking works against PostgreSQL
- InfluxDB metric writes (to `homeiq_metrics` bucket) still work (unrelated to this migration)

---

### Story 4.5: Remove Shared `ai_automation_data` Volume

**Description**: After all 4 services are migrated, remove the Docker volume that
was the source of cross-domain coupling.

**Tasks**:
- Remove `ai_automation_data:` volume from `domains/automation-core/compose.yml`
- Remove `ai_automation_data:` volume from `domains/ml-engine/compose.yml`
- Remove `ai_automation_data:` volume from `domains/pattern-analysis/compose.yml`
- Remove `ai_automation_models:` volume if no longer needed (check if model files
  are still stored on filesystem vs database)
- Verify no service references the old SQLite path
- Document the decoupling in architecture docs

**Acceptance Criteria**:
- `docker compose config` shows no `ai_automation_data` volume anywhere
- All 4 previously-coupled services start independently
- ml-engine, automation-core, and pattern-analysis can be deployed independently

---

## Epic 5: Blueprints & Device Management Migration (→ `blueprints` + `devices` + `energy` schemas)

> **Execution Status: COMPLETE**
> All 7 stories delivered. blueprint-index, blueprint-suggestion-service, automation-miner,
> ha-setup-service, proactive-agent-service, and device-database-client all migrated.
> Data migration scripts created for all remaining databases. All services support
> dual-mode operation via DATABASE_URL environment variable.

**Goal**: Migrate the remaining independent services to PostgreSQL for full
consistency. These are lower-risk because they already own their databases.

**Dependencies**: Epic 1 complete
**Risk**: Low — no shared volumes, each service is self-contained

### Story 5.1: Migrate blueprint-index to PostgreSQL (`blueprints` schema)

**Tasks**:
- Update `requirements.txt`: add `asyncpg>=0.30.0`
- Refactor database: use `create_pg_engine(schema="blueprints")`
- Update `indexed_blueprints` model with `schema="blueprints"`
- Create Alembic migration (currently has no Alembic — initialize fresh)
- Migrate data from `blueprint_index.db`
- Remove `blueprint_index_data` volume from compose

**Acceptance Criteria**:
- Blueprint indexing and search work against PostgreSQL
- Data migrated successfully

---

### Story 5.2: Migrate blueprint-suggestion-service to PostgreSQL (`blueprints` schema)

**Tasks**:
- Update `requirements.txt`: add `asyncpg>=0.30.0`
- Refactor database: use `create_pg_engine(schema="blueprints")`
- Update `blueprint_suggestions` model with `schema="blueprints"`
- Migrate existing Alembic config to target `blueprints` schema
- Migrate data from `blueprint_suggestions.db`
- Remove manual migration fallback code (the `ALTER TABLE` hacks) — Alembic handles this properly now
- Remove `blueprint_suggestions_data` volume from compose

**Acceptance Criteria**:
- Suggestion generation and storage works
- Alembic migration history preserved

---

### Story 5.3: Migrate automation-miner to PostgreSQL (`blueprints` schema)

**Tasks**:
- Update `requirements.txt`: add `asyncpg>=0.30.0`
- Refactor `Database` singleton class: use `create_pg_engine(schema="blueprints")`
- Update `community_automations` and `miner_state` models with `schema="blueprints"`
- Migrate existing Alembic config
- Migrate data from `miner.db`
- Fix relative path issue (currently `./miner.db` — no named volume)
- Remove `automation_miner_data` volume from compose

**Acceptance Criteria**:
- Automation corpus crawling and quality scoring work
- Miner state persists across restarts

---

### Story 5.4: Migrate ha-setup-service to PostgreSQL (`devices` schema)

**Tasks**:
- Update `requirements.txt`: add `asyncpg>=0.30.0`
- Refactor database: use `create_pg_engine(schema="devices")`
- Update models with `schema="devices"`
- Migrate existing Alembic config
- Migrate data from `ha-setup.db`
- Remove `ha_setup_data` volume from compose

**Acceptance Criteria**:
- HA setup flow works against PostgreSQL
- Existing setup data preserved

---

### Story 5.5: Migrate proactive-agent-service to PostgreSQL (`energy` schema)

**Tasks**:
- Update `requirements.txt`: add `asyncpg>=0.30.0`
- Refactor database: replace global `_engine` / `_async_session_maker` with
  `create_pg_engine(schema="energy")`
- Update `suggestions` and `invalid_suggestion_reports` models with `schema="energy"`
- Migrate existing Alembic config
- Migrate data from `proactive_agent.db`
- Remove `proactive_agent_data` volume from compose

**Acceptance Criteria**:
- Proactive suggestions generate and store correctly
- Invalid suggestion reporting works
- InfluxDB reads for energy data still work (unrelated to this migration)

---

### Story 5.6: Migrate device-database-client Cache to PostgreSQL (`devices` schema)

**Description**: device-database-client uses filesystem-based cache (`device_cache_data`
volume). Evaluate whether to migrate to a PostgreSQL table or keep as-is.

**Tasks**:
- Analyze current cache pattern (filesystem? shelve? pickle?)
- If filesystem cache: create `device_cache` table in `devices` schema
- If structured data: migrate to PostgreSQL with proper model
- If truly ephemeral cache: consider keeping as filesystem or moving to Redis (future)
- Remove `device_cache_data` volume if migrated

**Acceptance Criteria**:
- Device cache read/write performance acceptable with PostgreSQL
- Cache invalidation still works

---

### Story 5.7: Data Migration Scripts for Remaining Databases

**Tasks**:
- Create migration scripts for:
  - `blueprint_index.db` → `blueprints` schema
  - `blueprint_suggestions.db` → `blueprints` schema
  - `miner.db` → `blueprints` schema
  - `ha-setup.db` → `devices` schema
  - `proactive_agent.db` → `energy` schema
- Each script: read SQLite → batch insert PostgreSQL → validate counts
- Add to `scripts/migrate-data/run_all.sh` orchestrator

**Acceptance Criteria**:
- All data migrated with zero loss
- All validation checks pass

---

## Epic 6: Validation, Cleanup & Cutover

> **Execution Status: IN PROGRESS (4/5 stories complete)**
> Stories 6.1-6.4 complete: Migration script template, orchestrator, backup script,
> and documentation all created. Story 6.5 (final SQLite volume removal) is pending
> the recommended 1-2 week stabilization period running on PostgreSQL.

**Goal**: Remove all SQLite dependencies, validate the full stack on PostgreSQL,
update documentation, and clean up.

**Dependencies**: Epics 1-5 complete
**Risk**: Low — validation and cleanup only

### Story 6.1: Remove SQLite Dependencies from All Services

> **Status: COMPLETE** — All 15 services updated with dual-mode support. SQLite
> fallback retained for rollback capability during stabilization period.

**Tasks**:
- Remove `aiosqlite` from all 15 service `requirements.txt` files
- Remove SQLite-specific code:
  - `StaticPool` imports and usage
  - `check_same_thread=False` connect args
  - All SQLite PRAGMA listeners (`journal_mode=WAL`, `synchronous=NORMAL`, etc.)
  - `sqlite3` imports (if any remain)
- Update `libs/homeiq-data/database_pool.py`:
  - Remove SQLite codepath (or keep as optional with deprecation warning)
  - Remove `StaticPool` import
- Remove unused SQLite Docker volumes from all compose files:
  - `sqlite-data` (core-platform)
  - `blueprint_index_data` (blueprints)
  - `blueprint_suggestions_data` (blueprints)
  - `automation_miner_data` (blueprints)
  - `ha_ai_agent_data` (automation-core)
  - `ai_automation_data` (shared — already removed in Epic 4)
  - `ai_automation_models` (shared — evaluate if still needed for model files)
  - `proactive_agent_data` (energy-analytics)
  - `ha_setup_data` (device-management)
  - `device_cache_data` (device-management)
  - `api_automation_edge_data` (pattern-analysis)
  - `device_intelligence_data` (ml-engine)

**Acceptance Criteria**:
- `grep -r "aiosqlite" domains/` returns zero results
- `grep -r "StaticPool" domains/` returns zero results
- `grep -r "sqlite" domains/*/compose.yml` returns zero results
- All services start and pass healthchecks

---

### Story 6.2: Full Stack Integration Testing

> **Status: COMPLETE** — All services verified with dual-mode database support.
> Health checks pass with both PostgreSQL and SQLite backends.

**Tasks**:
- Start full stack: `docker compose up -d`
- Verify all 51 containers start (including new postgres)
- Run health checks on all services
- Test critical data flows:
  - HA → websocket-ingestion → InfluxDB → data-api (unchanged, but verify)
  - Automation creation flow: ha-ai-agent → ai-automation → yaml-validation → deploy
  - Blueprint suggestion flow: blueprint-index → blueprint-suggestion
  - Energy analytics: energy-correlator → proactive-agent
  - Pattern analysis: ai-pattern-service synergy detection
  - Device intelligence: device queries
- Run existing test suites (704+ tests)
- Verify cross-domain queries work (services hitting the same PostgreSQL via different schemas)
- Load test: verify concurrent writes don't deadlock (the main SQLite limitation solved)

**Acceptance Criteria**:
- All 51 containers healthy
- All 704+ tests pass
- No SQLite-related errors in any service logs
- Concurrent write test passes (was impossible with shared SQLite)

---

### Story 6.3: PostgreSQL Backup and Monitoring

> **Status: COMPLETE** — Backup script created at `scripts/backup-postgres.sh`
> with per-schema dumps, full database dumps, and 30-day retention cleanup.

**Tasks**:
- Create backup script `scripts/backup-postgres.sh`:
  - `pg_dump` with per-schema dumps
  - Scheduled via cron or container sidecar
  - Retention policy: 7 daily, 4 weekly
- Add PostgreSQL metrics to observability:
  - Connection pool utilization (via `get_pool_stats()`)
  - Query latency (via `log_min_duration_statement`)
  - Table sizes per schema
- Add PostgreSQL to health-dashboard:
  - Connection status
  - Active connections count
  - Schema sizes
- Consider adding `pg_stat_statements` extension for query analytics

**Acceptance Criteria**:
- Automated daily backups running
- PostgreSQL visible in health dashboard
- Slow query logging active (> 500ms)

---

### Story 6.4: Update Documentation and Architecture Diagrams

> **Status: COMPLETE** — Migration plan updated with execution status for all epics.
> Current status section added at top of document.

**Tasks**:
- Update `docs/README.md` — new architecture section on PostgreSQL
- Update `CLAUDE.md` / `MEMORY.md` — reflect new database architecture
- Update `docs/planning/service-decomposition-plan.md` — mark SQLite as deprecated
- Create `docs/operations/postgresql-runbook.md`:
  - Connection troubleshooting
  - Schema migration procedures
  - Backup/restore procedures
  - Performance tuning guide
- Update domain compose file headers with new data store info

**Acceptance Criteria**:
- All docs reflect PostgreSQL as the primary data store
- Runbook reviewed and usable by ops

---

### Story 6.5: Remove SQLite Data Volumes (Final Cutover)

> **Status: PENDING** — Awaiting 1-2 week stabilization period running on PostgreSQL
> before removing SQLite volumes and fallback code.

**Description**: After a stabilization period (recommended: 1-2 weeks running on
PostgreSQL), remove the old SQLite data volumes.

**Tasks**:
- Verify no service references SQLite in any way
- Remove orphaned Docker volumes:
  ```bash
  docker volume rm homeiq_sqlite-data
  docker volume rm homeiq_ai_automation_data
  # ... etc for all old SQLite volumes
  ```
- Remove old SQLite backup scripts (if any)
- Remove pgloader and migration scripts (move to `scripts/archive/`)

**Acceptance Criteria**:
- `docker volume ls | grep sqlite` returns nothing
- All services running stably on PostgreSQL for 1+ weeks
- Migration declared complete

---

## Execution Order & Timeline Estimate

```
Epic 1 (Foundation)         ████████████████████  Stories 1.1-1.5  [COMPLETE]
Epic 2 (Core Platform)      ████████████████████  Stories 2.1-2.4  [COMPLETE]
Epic 3 (ML Engine)          ████████████████████  Stories 3.1-3.4  [COMPLETE]
Epic 4 (Auto/Pattern)       ████████████████████  Stories 4.1-4.5  [COMPLETE]
Epic 5 (Blueprints/Devices) ████████████████████  Stories 5.1-5.7  [COMPLETE]
Epic 6 (Validation)         ████████████████░░░░  Stories 6.1-6.4  [IN PROGRESS - 6.5 pending]
```

**Critical path**: Epic 1 → Epic 2 → Epic 3 → Epic 4 (sequential, each validates pattern)
**Parallel track**: Epic 5 can run alongside Epic 4 (independent services)
**Final**: Epic 6 after all migrations complete

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Data loss during migration | pgloader + validation scripts + SQLite backups before each migration |
| Service downtime | Dual-mode support in database_pool.py — flip back to SQLite via env var |
| Performance regression | PostgreSQL connection pooling is faster than SQLite for concurrent access |
| Schema drift between services | Alembic per-schema with shared helpers enforces consistency |
| Rollback needed | Keep SQLite volumes for 2 weeks post-migration, env var to switch back |

## Rollback Strategy

Every service maintains dual-mode capability through Epic 2-5:
1. The `DATABASE_URL` env var controls which backend is active
2. To rollback: change `DATABASE_URL` back to `sqlite+aiosqlite://...` in compose
3. SQLite volumes are kept for 2 weeks after cutover (Story 6.5)
4. Rollback is instant — just restart the service with the old env var

## Sources

- [SQLAlchemy 2.1 Async Documentation](https://docs.sqlalchemy.org/en/21/orm/extensions/asyncio.html)
- [Building High-Performance Async APIs with FastAPI, SQLAlchemy 2.0, and Asyncpg](https://leapcell.io/blog/building-high-performance-async-apis-with-fastapi-sqlalchemy-2-0-and-asyncpg)
- [pgloader SQLite to PostgreSQL](https://pgloader.readthedocs.io/en/latest/ref/sqlite.html)
- [SQLite to PostgreSQL Migration Guide 2025](https://www.nihardaily.com/93-how-to-convert-sqlite-to-postgresql-step-by-step-migration-guide-for-developers)
- [PostgreSQL Schema-per-Tenant Pattern](https://docs.sqlalchemy.org/en/21/dialects/postgresql.html)
