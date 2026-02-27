---
epic: sqlite-to-postgresql-migration
priority: critical
status: in-progress
estimated_duration: 3-4 weeks
risk_level: high
source: docs/planning/sqlite-to-postgresql-migration-plan.md
---

# Epic: SQLite to PostgreSQL Migration

**Status:** In Progress (29/30 stories complete)
**Priority:** Critical
**Duration:** 3-4 weeks
**Risk Level:** High
**Source:** [Migration Plan](../docs/planning/sqlite-to-postgresql-migration-plan.md)

## Summary

Migrate all 10 SQLite databases across 15 services to a single PostgreSQL 17 instance using schema-per-domain isolation. Eliminates the shared `ai_automation.db` Docker volume that coupled 4 services across 3 domains.

### Architecture

- **Pattern:** Single PostgreSQL 17 instance, 8 domain schemas
- **Driver:** asyncpg (async) + psycopg (sync Alembic)
- **Migration tool:** Alembic (per-schema)
- **Shared library:** `homeiq-data` (`database_pool.py` — `create_pg_engine()`, `get_database_url()`)
- **Dual-mode:** All 15 services detect `postgresql` vs `sqlite` URL prefix automatically

### PostgreSQL Schema Map

| Schema | Source DB | Services |
|--------|----------|----------|
| core | metadata.db | data-api |
| automation | ai_automation.db (shared) | ai-automation, ai-query, ai-training, ai-pattern |
| agent | ha_ai_agent.db | ha-ai-agent-service |
| blueprints | blueprint_index.db, blueprint_suggestions.db, miner.db | blueprint-index, blueprint-suggestion, automation-miner |
| energy | proactive_agent.db | proactive-agent-service |
| devices | device_intelligence.db, ha-setup.db, device_cache | device-intelligence, ha-setup, device-database-client |
| patterns | api-automation-edge.db | api-automation-edge |
| rag | rag_service.db | rag-service |

---

## Implementation Status

### Epic 1: PostgreSQL Infrastructure Foundation — Complete

- **Story 1.1** (Add PostgreSQL Container): Complete — PostgreSQL 17 container in `domains/core-platform/compose.yml` with healthcheck, resource limits, JSON logging
- **Story 1.2** (Schema Initialization): Complete — `infrastructure/postgres/init-schemas.sql` creates all 8 schemas on first boot
- **Story 1.3** (Upgrade homeiq-data Library): Complete — `create_pg_engine()` with search_path isolation, `get_database_url()`, `check_pg_connection()`, dual-mode support
- **Story 1.4** (Shared Alembic Configuration): Complete — `homeiq_data.alembic_helpers` with `run_async_migrations()`, template `env.py`
- **Story 1.5** (CI and docker-bake): Complete — PostgreSQL dependency chain in compose, CI pipeline support

### Epic 2: Core Platform Migration (data-api → `core` schema) — Complete

- **Story 2.1** (PostgreSQL Support in data-api): Complete — Dual-mode engine creation, asyncpg connection pool, schema-aware metadata
- **Story 2.2** (Alembic Migrations): Complete — `domains/core-platform/data-api/alembic/` with `core` schema targeting
- **Story 2.3** (Data Migration Script): Complete — `scripts/migrate-data/migrate_template.py` with batch inserts and validation
- **Story 2.4** (Compose Configuration): Complete — `DATABASE_URL`, `DATABASE_SCHEMA=core`, depends_on postgres

### Epic 3: ML Engine & Shared Database Migration — Complete

- **Story 3.1** (ai-training-service → `automation`): Complete — Dual-mode engine, removed StaticPool, asyncpg in requirements
- **Story 3.2** (device-intelligence-service → `devices`): Complete — `create_pg_engine(schema="devices")`, Alembic migration scaffolding
- **Story 3.3** (rag-service → `rag`): Complete — PostgreSQL support, removed relative bind mount
- **Story 3.4** (Data Migration Scripts): Complete — `scripts/migrate-data/run_all.sh` orchestrator

### Epic 4: Automation Core & Pattern Analysis Decoupling — Complete

- **Story 4.1** (ai-automation-service-new → `automation`): Complete — Full dual-mode, all CRUD operations verified
- **Story 4.2** (ai-query-service → `automation`): Complete — Read consumer of automation schema, volume mount removed
- **Story 4.3** (ai-pattern-service → `automation`): Complete — synergy tables in automation schema, SQLite PRAGMAs removed
- **Story 4.4** (api-automation-edge → `patterns`): Complete — Isolated migration, spec_versions in patterns schema
- **Story 4.5** (Remove Shared Volume): Complete — `ai_automation_data` volume eliminated from all compose files

### Epic 5: Blueprints & Device Management Migration — Complete

- **Story 5.1** (blueprint-index → `blueprints`): Complete — Alembic initialized fresh
- **Story 5.2** (blueprint-suggestion-service → `blueprints`): Complete — Existing Alembic migrated to PostgreSQL
- **Story 5.3** (automation-miner → `blueprints`): Complete — Database singleton refactored
- **Story 5.4** (ha-setup-service → `devices`): Complete — Alembic config migrated
- **Story 5.5** (proactive-agent-service → `energy`): Complete — Global engine replaced with create_pg_engine
- **Story 5.6** (device-database-client → `devices`): Complete — Cache pattern evaluated and migrated
- **Story 5.7** (Data Migration Scripts): Complete — All remaining migration scripts in `scripts/migrate-data/`

### Epic 6: Validation, Cleanup & Cutover — In Progress (4/5)

- **Story 6.1** (Remove SQLite Dependencies): Complete — All 15 services have dual-mode support; SQLite fallback retained for rollback
- **Story 6.2** (Full Stack Integration Testing): Complete — Health checks pass with both backends
- **Story 6.3** (Backup and Monitoring): Complete — `scripts/backup-postgres.sh` with per-schema dumps, 30-day retention
- **Story 6.4** (Documentation): Complete — Migration plan updated, architecture docs reflect PostgreSQL
- **Story 6.5** (Final SQLite Volume Removal): **Pending** — Awaiting 1-2 week stabilization period before removing SQLite volumes and fallback code

---

## Key Files Created/Modified

| File | Purpose |
|------|---------|
| `infrastructure/postgres/init-schemas.sql` | Creates 8 domain schemas on first boot |
| `infrastructure/postgres/postgresql.conf` | Tuned settings (pg_stat_statements, slow query logging) |
| `libs/homeiq-data/src/homeiq_data/database_pool.py` | `create_pg_engine()` (with SQL injection guard), `get_database_url()`, dual-mode support, thread-safe engine creation |
| `libs/homeiq-data/src/homeiq_data/alembic_helpers.py` | Shared Alembic migration runners |
| `libs/homeiq-data/templates/alembic_env.py` | Template for service alembic/env.py |
| `scripts/migrate-data/migrate_template.py` | Data migration script template |
| `scripts/migrate-data/run_all.sh` | Migration orchestrator |
| `scripts/backup-postgres.sh` | Per-schema backup with retention |
| 15 service database init files | Dual-mode PostgreSQL/SQLite support |
| 7 compose files | POSTGRES_URL, DATABASE_SCHEMA env vars |
| 40+ requirements.txt | asyncpg, psycopg dependencies added |

## Rollback Strategy

Every service maintains dual-mode capability:
1. `DATABASE_URL` env var controls which backend is active
2. To rollback: change `DATABASE_URL` back to `sqlite+aiosqlite://...` in compose
3. SQLite volumes retained for 2 weeks after cutover (Story 6.5)
4. Rollback is instant — restart service with old env var

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-02-24 | Claude Code | Migration plan created (6 epics, 27 stories) |
| 2026-02-24 | Claude Code | Epics 1-5 complete, Epic 6 stories 6.1-6.4 complete |
| 2026-02-24 | Claude Code | Epic file created to track implementation status |
| 2026-02-27 | Claude Code | Security hardening: SQL injection guard on `create_pg_engine`, threading lock on engine singleton, `close_all_engines()` dispose fix |
| 2026-02-27 | Claude Code | Story 6.5 execution plan created: `docs/planning/story-6.5-sqlite-cutover-plan.md` |
