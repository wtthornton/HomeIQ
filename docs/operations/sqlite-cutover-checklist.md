# Story 6.5: Final SQLite Cutover Checklist

> **Status**: Deferred -- execute after 14+ days of PostgreSQL stabilization.
>
> **Target date**: Earliest 2026-03-10 (14 days after PostgreSQL go-live)
>
> **Owner**: TBD
>
> **Rollback plan**: Re-enable SQLite fallback by reverting the commits from this story.

---

## Pre-Cutover Verification (Must ALL pass)

Every item below must be verified before starting the cutover. If any item
fails, **stop and investigate** before proceeding.

### Infrastructure Stability

- [ ] PostgreSQL has been running stable for **14+ days** (check uptime via `scripts/pg-health-report.sh`)
- [ ] Zero data integrity issues reported in the last 14 days
- [ ] `scripts/check-pg-stability.sh` returns PASS on 3 consecutive daily runs
- [ ] Connection pool utilization stays below 80% under normal load
- [ ] Cache hit ratio > 95% (check via `monitoring.cache_stats` view)
- [ ] No unresolved lock contention incidents

### Service Connectivity

- [ ] All 15 services connecting to PostgreSQL (check logs for `"Created PostgreSQL engine"`)
- [ ] Services verified:
  - [ ] `core-platform/data-api`
  - [ ] `automation-core/ai-automation-service-new`
  - [ ] `automation-core/ha-ai-agent-service`
  - [ ] `automation-core/ai-query-service`
  - [ ] `ml-engine/ai-training-service`
  - [ ] `ml-engine/rag-service`
  - [ ] `ml-engine/device-intelligence-service`
  - [ ] `energy-analytics/proactive-agent-service`
  - [ ] `blueprints/automation-miner`
  - [ ] `blueprints/blueprint-index`
  - [ ] `blueprints/blueprint-suggestion-service`
  - [ ] `device-management/ha-setup-service`
  - [ ] `pattern-analysis/ai-pattern-service`
  - [ ] `pattern-analysis/api-automation-edge`
  - [ ] `automation-core/ai-code-executor` (if applicable)

### Migrations & Backup

- [ ] Alembic migrations running successfully on all schemas (check via `scripts/pg-health-report.sh` section 11)
- [ ] Backup tested: `scripts/backup-postgres.sh` completes without errors
- [ ] Restore tested: successfully restored a backup to a clean database
- [ ] All E2E tests passing against PostgreSQL backend

---

## Cutover Steps

Execute these steps **in order**. Each step should be committed separately for
clean rollback capability.

### Step 1: Final SQLite Backup

```bash
# Take final SQLite backup for archival
scripts/backup-all.sh

# Verify backup files exist
ls -la backups/
```

### Step 2: Verify PostgreSQL Data Parity

```bash
# Run the migration validation scripts
scripts/pg-health-report.sh

# Verify row counts match between SQLite and PostgreSQL for each service
# (manual spot-check at minimum)
```

### Step 3: Remove SQLite Fallback Code

Remove the SQLite fallback / dual-engine logic from each service's database
initialization module. The following files contain SQLite references that must
be updated:

**Database initialization files:**

| # | Service | File Path |
|---|---------|-----------|
| 1 | data-api | `domains/core-platform/data-api/src/database.py` |
| 2 | ai-automation-service-new | `domains/automation-core/ai-automation-service-new/src/database/__init__.py` |
| 3 | ha-ai-agent-service | `domains/automation-core/ha-ai-agent-service/src/database.py` |
| 4 | ai-query-service | `domains/automation-core/ai-query-service/src/database/__init__.py` |
| 5 | ai-training-service | `domains/ml-engine/ai-training-service/src/database/__init__.py` |
| 6 | rag-service | `domains/ml-engine/rag-service/src/database/session.py` |
| 7 | device-intelligence-service | `domains/ml-engine/device-intelligence-service/src/core/database.py` |
| 8 | proactive-agent-service | `domains/energy-analytics/proactive-agent-service/src/database.py` |
| 9 | automation-miner | `domains/blueprints/automation-miner/src/miner/database.py` |
| 10 | blueprint-index | `domains/blueprints/blueprint-index/src/database.py` |
| 11 | blueprint-suggestion-service | `domains/blueprints/blueprint-suggestion-service/src/database.py` |
| 12 | ha-setup-service | `domains/device-management/ha-setup-service/src/database.py` |
| 13 | ai-pattern-service | `domains/pattern-analysis/ai-pattern-service/src/database/__init__.py` |
| 14 | api-automation-edge | `domains/pattern-analysis/api-automation-edge/src/registry/database.py` |

**For each file:**
1. Remove the SQLite engine creation path (the `if/else` or fallback logic)
2. Remove `sqlite+aiosqlite://` connection string construction
3. Remove any `SQLITE_*` environment variable handling
4. Ensure only the `POSTGRES_URL` / `postgresql+asyncpg://` path remains
5. Run `tapps_quick_check` on each modified file

### Step 4: Remove aiosqlite from Requirements

Remove `aiosqlite` from `requirements.txt` in all 15 services:

```
domains/core-platform/data-api/requirements.txt
domains/core-platform/data-api/requirements-prod.txt
domains/automation-core/ai-automation-service-new/requirements.txt
domains/automation-core/ha-ai-agent-service/requirements.txt
domains/automation-core/ai-query-service/requirements.txt
domains/ml-engine/ai-training-service/requirements.txt
domains/ml-engine/rag-service/requirements.txt
domains/ml-engine/device-intelligence-service/requirements.txt
domains/ml-engine/device-intelligence-service/requirements-prod.txt
domains/energy-analytics/proactive-agent-service/requirements.txt
domains/blueprints/automation-miner/requirements.txt
domains/blueprints/blueprint-index/requirements.txt
domains/blueprints/blueprint-suggestion-service/requirements.txt
domains/device-management/ha-setup-service/requirements.txt
domains/pattern-analysis/ai-pattern-service/requirements.txt
domains/pattern-analysis/api-automation-edge/requirements.txt
```

### Step 5: Remove SQLite Environment Variables from Compose

Remove SQLite-related environment variables from `domains/core-platform/compose.yml`:
- `DATABASE_URL=sqlite+aiosqlite:///...`
- `SQLITE_TIMEOUT`
- `SQLITE_CACHE_SIZE`

And from any other domain compose files that reference SQLite.

### Step 6: Remove Orphaned Docker Volumes

```bash
# Stop all services first
docker compose down

# Remove orphaned SQLite volumes
docker volume rm homeiq_sqlite-data 2>/dev/null || true
docker volume rm homeiq_ai_automation_data 2>/dev/null || true

# Verify removal
docker volume ls | grep -i sqlite
```

### Step 7: Archive Migration Scripts

```bash
# Create archive directory
mkdir -p scripts/archive/sqlite-migration

# Move SQLite-specific migration and validation scripts
mv scripts/validate-databases.sh scripts/archive/sqlite-migration/ 2>/dev/null || true
# Move any other SQLite-specific scripts as identified
```

### Step 8: Update Documentation

- [ ] Update `MEMORY.md` — change "Databases" section to remove SQLite references
- [ ] Update `TECH_STACK.md` — remove SQLite from the stack
- [ ] Update any service-level README files that mention SQLite
- [ ] Update `.env.example` to remove `DATABASE_URL` SQLite defaults

---

## Post-Cutover Verification

Run these checks **immediately** after completing the cutover steps.

### Service Health

- [ ] All services start successfully: `scripts/check-service-health.sh`
- [ ] Health checks pass for all 15 database-backed services
- [ ] No `sqlite` or `aiosqlite` references in any service logs:
  ```bash
  docker compose logs --tail=100 | grep -i sqlite
  ```

### Data Integrity

- [ ] PostgreSQL health report clean: `scripts/pg-health-report.sh`
- [ ] Stability check passes: `scripts/check-pg-stability.sh`
- [ ] All Alembic migrations at expected versions

### Functional Tests

- [ ] E2E tests pass
- [ ] Manual smoke test: create/read/update/delete via data-api
- [ ] Manual smoke test: create automation via ha-ai-agent-service
- [ ] Manual smoke test: query patterns via ai-pattern-service

### Cleanup Verification

- [ ] No SQLite files remain in Docker volumes:
  ```bash
  docker volume ls | grep -i sqlite
  ```
- [ ] No `aiosqlite` in any installed Python packages:
  ```bash
  for svc in $(docker ps --format '{{.Names}}' | grep homeiq); do
    echo "--- $svc ---"
    docker exec "$svc" pip list 2>/dev/null | grep -i sqlite || echo "clean"
  done
  ```
- [ ] `grep -r "aiosqlite" domains/` returns no results (excluding archive)

---

## Rollback Procedure

If issues are discovered post-cutover:

1. **Immediate**: Revert the Git commits from Steps 3-5
2. **Rebuild**: `docker compose build && docker compose up -d`
3. **Verify**: Services will fall back to SQLite automatically
4. **Investigate**: Use `scripts/pg-health-report.sh` to diagnose PostgreSQL issues
5. **Re-attempt**: Fix root cause and re-execute the cutover checklist

---

## Sign-Off

| Role | Name | Date | Approved |
|------|------|------|----------|
| Developer | | | [ ] |
| Reviewer | | | [ ] |
| Operations | | | [ ] |
