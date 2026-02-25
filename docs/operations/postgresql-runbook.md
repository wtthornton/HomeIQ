# PostgreSQL Operations Runbook

**Version:** 1.0
**Last Updated:** 2026-02-24
**Maintainer:** HomeIQ Platform Team

---

## Overview

HomeIQ uses PostgreSQL 17 as the primary metadata store, replacing the original per-service SQLite databases. The database uses a **schema-per-domain** pattern with 8 schemas: `core`, `automation`, `agent`, `blueprints`, `energy`, `devices`, `patterns`, `rag`.

### Architecture

```
                        PostgreSQL (port 5432)
                        Database: homeiq
                        ┌────────────────────────────────────┐
                        │  Schema: core       (data-api)     │
                        │  Schema: automation (ai-automation) │
                        │  Schema: agent      (ha-ai-agent)  │
                        │  Schema: blueprints (blueprint-*)   │
                        │  Schema: energy     (energy-*)      │
                        │  Schema: devices    (device-*)      │
                        │  Schema: patterns   (ai-pattern)    │
                        │  Schema: rag        (rag-service)   │
                        └────────────────────────────────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              │                        │                        │
         data-api (8006)     ai-automation (8025)     ha-ai-agent (8030)
              │                        │                        │
         admin-api (8004)    blueprint-* services    device-* services
              │
     health-dashboard (3000)
```

---

## Connection Troubleshooting

### Common Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `FATAL: password authentication failed` | Wrong credentials | Verify `POSTGRES_PASSWORD` in `.env` matches container config |
| `could not connect to server: Connection refused` | PostgreSQL not running | `docker compose up -d postgres` |
| `FATAL: database "homeiq" does not exist` | First boot, DB not created | Container auto-creates on first run; check `POSTGRES_DB` env var |
| `FATAL: too many connections for role` | Connection pool exhaustion | See "Connection Pool Exhaustion" section below |
| `ERROR: schema "core" does not exist` | Init script did not run | Run `infrastructure/postgres/init-schemas.sql` manually |
| `SSL connection required` | SSL mismatch | Add `?sslmode=disable` for local dev |

### Verifying Connectivity

```bash
# From host machine
psql -h localhost -p 5432 -U homeiq -d homeiq -c "SELECT 1;"

# From inside a service container
docker exec homeiq-data-api python -c "
import asyncpg, asyncio
async def check():
    conn = await asyncpg.connect('postgresql://homeiq:homeiq@homeiq-postgres:5432/homeiq')
    print(await conn.fetchval('SELECT version()'))
    await conn.close()
asyncio.run(check())
"

# From the PostgreSQL container
docker exec homeiq-postgres psql -U homeiq -d homeiq -c "SELECT current_database(), current_user, version();"
```

### Connection Pool Exhaustion

**Symptoms:** Services fail to connect; `pg_stat_activity` shows many idle connections.

```bash
# Check current connections
docker exec homeiq-postgres psql -U homeiq -d homeiq -c "
SELECT usename, application_name, state, COUNT(*)
FROM pg_stat_activity
WHERE datname = 'homeiq'
GROUP BY usename, application_name, state
ORDER BY COUNT(*) DESC;
"

# Kill idle connections older than 5 minutes
docker exec homeiq-postgres psql -U homeiq -d homeiq -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'homeiq'
  AND state = 'idle'
  AND state_change < NOW() - INTERVAL '5 minutes'
  AND pid <> pg_backend_pid();
"
```

**Prevention:** Set `idle_in_transaction_session_timeout` and use connection pooling (PgBouncer or application-level pools with `asyncpg.create_pool()`).

---

## Schema Management

### Listing Schemas

```bash
docker exec homeiq-postgres psql -U homeiq -d homeiq -c "\dn"
```

### Adding a New Schema

1. Add the schema to `infrastructure/postgres/init-schemas.sql`:

```sql
CREATE SCHEMA IF NOT EXISTS newdomain;
```

2. Grant permissions:

```sql
GRANT ALL ON SCHEMA newdomain TO homeiq;
```

3. Update the search path:

```sql
ALTER DATABASE homeiq SET search_path TO public, core, automation, agent, blueprints, energy, devices, patterns, rag, newdomain;
```

4. Update `scripts/backup-postgres.sh` to include the new schema in the `SCHEMAS` array.

5. Update `scripts/restore-postgres.sh` similarly.

### Checking Schema Contents

```bash
# List all tables in a schema
docker exec homeiq-postgres psql -U homeiq -d homeiq -c "
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename))
FROM pg_tables
WHERE schemaname IN ('core','automation','agent','blueprints','energy','devices','patterns','rag')
ORDER BY schemaname, tablename;
"
```

---

## Performance Tuning

### Enable pg_stat_statements

Add to `postgresql.conf` (or via Docker env):

```
shared_preload_libraries = 'pg_stat_statements'
pg_stat_statements.track = all
```

Then activate:

```sql
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
```

### Top Slow Queries

```sql
SELECT
    round(total_exec_time::numeric, 2) AS total_ms,
    calls,
    round(mean_exec_time::numeric, 2) AS avg_ms,
    round((100 * total_exec_time / sum(total_exec_time) OVER ())::numeric, 2) AS pct,
    LEFT(query, 120) AS query_preview
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 20;
```

### Using EXPLAIN ANALYZE

```sql
-- Always use EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) for production queries
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT * FROM core.services WHERE status = 'active';
```

**Key things to look for:**

- `Seq Scan` on large tables -- add an index
- `Sort` with high cost -- add an index on the sort column
- `Nested Loop` with large row counts -- may need a different join strategy
- `Buffers: shared hit` vs `shared read` -- high read count means data is not cached

### Index Recommendations

```sql
-- Find tables missing indexes on foreign keys
SELECT
    c.conrelid::regclass AS table_name,
    a.attname AS column_name,
    c.confrelid::regclass AS referenced_table
FROM pg_constraint c
JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
WHERE c.contype = 'f'
  AND NOT EXISTS (
      SELECT 1 FROM pg_index i
      WHERE i.indrelid = c.conrelid
        AND a.attnum = ANY(i.indkey)
  );
```

### Table Bloat Detection

```sql
SELECT
    schemaname || '.' || relname AS table_name,
    pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
    n_live_tup AS live_rows,
    n_dead_tup AS dead_rows,
    CASE WHEN n_live_tup > 0
         THEN round(100.0 * n_dead_tup / n_live_tup, 1)
         ELSE 0
    END AS dead_pct
FROM pg_stat_user_tables
WHERE schemaname IN ('core','automation','agent','blueprints','energy','devices','patterns','rag')
ORDER BY n_dead_tup DESC;
```

**Fix:** Run `VACUUM ANALYZE` on bloated tables. For severe bloat, use `VACUUM FULL` (requires exclusive lock -- schedule during maintenance windows).

---

## Backup and Restore Procedures

### Automated Backups

The backup scheduler runs in a Docker container (see `infrastructure/backup/`):

- **Daily at 02:00 UTC**: Per-schema backup via `scripts/backup-postgres.sh`
- **Weekly on Sunday 01:00 UTC**: Full database backup
- **Retention**: 30 days (configurable via `BACKUP_RETENTION_DAYS`)

### Manual Backup

```bash
# Full database backup
./scripts/backup-postgres.sh

# Override backup directory
BACKUP_DIR=./my-backups ./scripts/backup-postgres.sh
```

### Manual Restore

```bash
# List backup contents before restoring
./scripts/restore-postgres.sh backups/postgres/homeiq_full_20260224_020000.dump --list

# Restore full database (with confirmation prompt)
./scripts/restore-postgres.sh backups/postgres/homeiq_full_20260224_020000.dump

# Restore single schema
./scripts/restore-postgres.sh backups/postgres/homeiq_core_20260224_020000.dump --schema core

# Force restore (skip confirmation)
./scripts/restore-postgres.sh backups/postgres/homeiq_full_20260224_020000.dump --force
```

### Testing Backup/Restore

```bash
# Run the automated integration test
./scripts/test-backup-restore.sh
```

This script creates a throwaway PostgreSQL container, seeds data, backs up, wipes, restores, and validates row counts and data integrity.

---

## Monitoring Queries

### Active Connections

```sql
SELECT pid, usename, application_name, client_addr, state, query_start,
       NOW() - query_start AS duration, LEFT(query, 80) AS query_preview
FROM pg_stat_activity
WHERE datname = 'homeiq'
ORDER BY query_start ASC;
```

### Long-Running Queries (> 30 seconds)

```sql
SELECT pid, usename, state, NOW() - query_start AS duration,
       LEFT(query, 200) AS query
FROM pg_stat_activity
WHERE datname = 'homeiq'
  AND state = 'active'
  AND NOW() - query_start > INTERVAL '30 seconds'
ORDER BY duration DESC;
```

### Table Sizes

```sql
SELECT
    schemaname || '.' || relname AS table_name,
    pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
    pg_size_pretty(pg_relation_size(relid)) AS data_size,
    pg_size_pretty(pg_indexes_size(relid)) AS index_size,
    n_live_tup AS rows
FROM pg_stat_user_tables
WHERE schemaname IN ('core','automation','agent','blueprints','energy','devices','patterns','rag')
ORDER BY pg_total_relation_size(relid) DESC;
```

### Database Size

```sql
SELECT pg_size_pretty(pg_database_size('homeiq')) AS db_size;
```

### Lock Monitoring

```sql
SELECT
    blocked_locks.pid AS blocked_pid,
    blocked_activity.usename AS blocked_user,
    blocking_locks.pid AS blocking_pid,
    blocking_activity.usename AS blocking_user,
    blocked_activity.query AS blocked_query,
    blocking_activity.query AS blocking_query
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks
    ON blocking_locks.locktype = blocked_locks.locktype
    AND blocking_locks.relation = blocked_locks.relation
    AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
```

---

## Emergency Procedures

### Kill a Runaway Query

```bash
# Find the PID
docker exec homeiq-postgres psql -U homeiq -d homeiq -c "
SELECT pid, NOW() - query_start AS duration, LEFT(query, 100)
FROM pg_stat_activity
WHERE state = 'active' AND datname = 'homeiq'
ORDER BY duration DESC LIMIT 5;
"

# Cancel the query (graceful)
docker exec homeiq-postgres psql -U homeiq -d homeiq -c "SELECT pg_cancel_backend(<PID>);"

# Terminate the connection (forceful -- use if cancel does not work)
docker exec homeiq-postgres psql -U homeiq -d homeiq -c "SELECT pg_terminate_backend(<PID>);"
```

### Reset All Connections

```bash
docker exec homeiq-postgres psql -U homeiq -d homeiq -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'homeiq' AND pid <> pg_backend_pid();
"
```

### Emergency Restart

```bash
# Graceful restart (allows connections to finish)
docker compose restart postgres

# Hard restart (if graceful fails)
docker compose stop postgres && docker compose up -d postgres
```

### Recover from Corrupted Data

1. Stop all services: `docker compose down`
2. Check PostgreSQL logs: `docker logs homeiq-postgres --tail 200`
3. If data is recoverable, restart and run `REINDEX DATABASE homeiq;`
4. If data is corrupted, restore from backup (see Backup and Restore section)

---

## Alembic Migration Guide

### Creating a New Migration

```bash
# From the service directory that owns the schema
cd domains/core-platform/data-api

# Auto-generate migration from model changes
alembic revision --autogenerate -m "add_new_column_to_services"

# Create empty migration for manual SQL
alembic revision -m "custom_migration_name"
```

### Applying Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Apply specific migration
alembic upgrade <revision_id>

# Show current state
alembic current

# Show migration history
alembic history --verbose
```

### Rolling Back Migrations

```bash
# Roll back one step
alembic downgrade -1

# Roll back to specific revision
alembic downgrade <revision_id>

# Roll back all (DANGEROUS)
alembic downgrade base
```

### Troubleshooting Migrations

| Problem | Solution |
|---------|----------|
| `Target database is not up to date` | Run `alembic upgrade head` first |
| `Can't locate revision` | Check `alembic/versions/` directory; may need to regenerate |
| `Duplicate column/table` | Migration already partially applied; check DB state manually |
| `Permission denied on schema` | Run GRANT command from "Adding a New Schema" section |
| `Migration hangs` | Check for locks (see Lock Monitoring above); another connection may hold a lock |

### Best Practices

- Always review auto-generated migrations before applying
- Test migrations against a copy of production data
- Never modify a migration after it has been applied in any environment
- Include both `upgrade()` and `downgrade()` functions
- Use `op.execute()` for raw SQL when the ORM abstractions are insufficient
- Run `./scripts/test-backup-restore.sh` after major schema changes

---

## Related Documentation

- [Disaster Recovery Procedures](disaster-recovery.md)
- [Monitoring Setup](monitoring-setup.md)
- [Service Health Checks](service-health-checks.md)
- [SQLite to PostgreSQL Migration Plan](../planning/sqlite-to-postgresql-migration-plan.md)
- [Init Schemas SQL](../../infrastructure/postgres/init-schemas.sql)
