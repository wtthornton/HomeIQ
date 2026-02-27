# Story 6.5 Execution Plan: SQLite Volume Removal

**Date**: 2026-02-27
**Status**: Ready for Execution (after 2026-03-10 stability checkpoint)
**Complexity**: Medium
**Risk**: Low–Medium (comprehensive rollback capability)
**Estimated Duration**: 3–4 hours (execution + verification)

---

## Executive Summary

This document details the exact steps, file modifications, and validation procedures for Story 6.5: SQLite Volume Removal—the final step in the SQLite→PostgreSQL migration. All services are already running on PostgreSQL; this story removes the fallback SQLite code paths, aiosqlite dependencies, and Docker volumes.

### Pre-Cutover Requirements (MUST ALL PASS)

Before executing **any** step below, verify:

1. **PostgreSQL Stabilization**: ≥14 days uptime with `scripts/check-pg-stability.sh` PASS
2. **Service Connectivity**: All 15 services connected to PostgreSQL (grep logs for `"Created PostgreSQL engine"`)
3. **Data Parity**: `scripts/pg-health-report.sh` clean, row counts match
4. **Backup Tested**: `scripts/backup-postgres.sh` and restore verified
5. **E2E Tests Passing**: All tests passing against PostgreSQL backend

**Estimated start date**: 2026-03-10 (14 days after 2026-02-24 go-live)

---

## Part 1: Audit Current SQLite References

### Files Containing SQLite References

Based on grep of `**/*.yml` and `**/*.py`:

#### Compose Files (11 files)
- `domains/pattern-analysis/compose.yml` — pattern-analysis services
- `domains/core-platform/compose.yml` — data-api (env vars only)
- `docker-compose.minimal.yml` — dev minimal stack
- `docker-compose.dev.yml` — dev full stack
- `domains/blueprints/compose.yml` — blueprint services
- `domains/automation-core/compose.yml` — automation services
- `domains/ml-engine/compose.yml` — ML services
- `domains/device-management/compose.yml` — device services
- `domains/ml-engine/device-intelligence-service/docker-compose.yml` — device-intel service
- `domains/device-management/ha-setup-service/docker-compose.service.yml` — ha-setup service
- `.github/workflows/docker-test.yml` — CI workflow

#### Database Initialization Files (14 files)

| Service | File Path | Type |
|---------|-----------|------|
| data-api | `domains/core-platform/data-api/src/database.py` | Python DB init |
| ai-automation-service-new | `domains/automation-core/ai-automation-service-new/src/database/__init__.py` | Python DB init |
| ha-ai-agent-service | `domains/automation-core/ha-ai-agent-service/src/database.py` | Python DB init |
| ai-query-service | `domains/automation-core/ai-query-service/src/database/__init__.py` | Python DB init |
| ai-training-service | `domains/ml-engine/ai-training-service/src/database/__init__.py` | Python DB init |
| rag-service | `domains/ml-engine/rag-service/src/database/session.py` | Python DB init |
| device-intelligence-service | `domains/ml-engine/device-intelligence-service/src/core/database.py` | Python DB init |
| proactive-agent-service | `domains/energy-analytics/proactive-agent-service/src/database.py` | Python DB init |
| automation-miner | `domains/blueprints/automation-miner/src/miner/database.py` | Python DB init |
| blueprint-index | `domains/blueprints/blueprint-index/src/database.py` | Python DB init |
| blueprint-suggestion-service | `domains/blueprints/blueprint-suggestion-service/src/database.py` | Python DB init |
| ha-setup-service | `domains/device-management/ha-setup-service/src/database.py` | Python DB init |
| ai-pattern-service | `domains/pattern-analysis/ai-pattern-service/src/database/__init__.py` | Python DB init |
| api-automation-edge | `domains/pattern-analysis/api-automation-edge/src/registry/database.py` | Python DB init |

#### Requirements Files (15+ files across all services)

Each service has `requirements.txt` and/or `requirements-prod.txt` containing `aiosqlite` dependency.

---

## Part 2: Validation Scripts Assessment

### Current Validation Tooling

#### `scripts/check-pg-stability.sh` (422 lines)

**Status**: Comprehensive, production-ready

**Checks Performed** (8 total):
1. ✅ PostgreSQL uptime vs. minimum threshold
2. ✅ All 8 domain schemas accessible
3. ✅ Alembic migration versions present and current
4. ✅ No lock contention (blocked locks check)
5. ✅ Connection pool utilization < 80%
6. ✅ Cache hit ratio > 95%
7. ✅ No PostgreSQL connection errors in service logs (24h)
8. ✅ Database disk usage < 5GB + table bloat monitoring

**Output Modes**: Text (colored) and JSON (for automation)

**Recommendation**: Use this as-is for post-cutover verification. Schedule daily execution during stabilization period.

---

#### `scripts/validate-migration/validate_data.py` (921 lines)

**Status**: Production-ready, comprehensive data integrity validation

**Capabilities**:
- Compares SQLite ↔ PostgreSQL row counts
- Validates schema structure (tables, columns, indexes)
- Checks primary key sequences for collision safety
- Validates foreign key integrity (no orphan rows)
- Sample checksum validation (first/last N rows ordered)
- Per-schema and per-table reporting
- JSON output for automation

**Schema Map**: All 8 schemas + 25+ tables defined (`SCHEMA_MAP` constant)

**Usage**:
```bash
python scripts/validate-migration/validate_data.py \
  --postgres-url postgresql+asyncpg://homeiq:password@localhost:5432/homeiq \
  --sqlite-dir ./data/ \
  --schemas core automation agent blueprints energy devices patterns rag
```

**Recommendation**: Keep for ongoing data integrity audits post-cutover. Consider archiving SQLite files before running post-cutover to verify no data loss.

---

#### `scripts/validate-migration/check_schemas.py` (578 lines)

**Status**: Production-ready, schema structure validation

**Capabilities**:
- Verifies all 8 schemas exist
- Validates table existence
- Checks critical columns per table (type-family matching)
- Counts indexes and foreign keys
- Formatted text + details output

**Expected Schema Map**: All 8 schemas with 32+ critical tables defined

**Usage**:
```bash
python scripts/validate-migration/check_schemas.py \
  --postgres-url postgresql+asyncpg://homeiq:password@localhost:5432/homeiq \
  --schemas core automation agent blueprints energy devices patterns rag
```

**Recommendation**: Use as pre-cutover verification (all schemas must PASS). Reuse post-cutover to confirm integrity.

---

## Part 3: Cutover Checklist Assessment

### Pre-Cutover Verification (from `docs/operations/sqlite-cutover-checklist.md`)

The existing checklist covers:

✅ Infrastructure Stability (6 items)
✅ Service Connectivity (15 services listed)
✅ Migrations & Backup (4 items)
✅ Post-Cutover Verification (3 sections, 11 items)
✅ Rollback Procedure
✅ Sign-off tracking

**Assessment**: Comprehensive and executable.

**Gaps Identified**:
- No specific "Day of" timeline (e.g., 9am start, maintenance window estimate)
- No explicit pre-cutover communication plan
- No success criteria for "stable" (currently relies on dev interpretation)

**Recommendations for 6.5**:
1. Define maintenance window (e.g., 9am–2pm UTC)
2. Add success definition: "All 8 checks in `check-pg-stability.sh` PASS"
3. Create rollback trigger checklist (when to abort mid-cutover)

---

## Part 4: Detailed Cutover Execution Steps

Execute these steps **in this exact order**. Each step is a separate commit for clean rollback.

### **STEP 1: Final Backups & Documentation**

**Timing**: < 30 min
**Commits**: 1
**Rollback**: N/A (pre-cutover only)

#### 1.1: Execute Final SQLite Backup

```bash
# From project root
scripts/backup-all.sh

# Verify backup files exist
ls -lh backups/
# Output should show all SQLite .db files + timestamp
```

#### 1.2: Run Pre-Cutover Validation

```bash
# Verify schema structure
python scripts/validate-migration/check_schemas.py \
  --postgres-url "$DATABASE_URL" \
  --schemas core automation agent blueprints energy devices patterns rag

# Spot-check data parity (sample of 2-3 schemas)
python scripts/validate-migration/validate_data.py \
  --postgres-url "$DATABASE_URL" \
  --sqlite-dir ./data/ \
  --schemas core agent automation
```

**Success Criteria**: Both scripts return exit code 0 (PASS).

#### 1.3: Document Starting State

Create a file `docs/operations/6.5-cutover-baseline.txt`:

```
Cutover Date: [YYYY-MM-DD]
Start Time: [HH:MM UTC]
PostgreSQL Uptime: [X days, from check-pg-stability.sh]
Baseline Checks: [PASS/FAIL]
  - Schema validation: PASS
  - Sample data validation: PASS
  - All 15 services connected: PASS
  - Backup tested: PASS
  - E2E tests: PASS

Operator: [name]
Reviewer: [name]
```

**Commit as**: `docs: 6.5 baseline snapshot before cutover`

---

### **STEP 2: Remove SQLite Fallback Code (14 files)**

**Timing**: 1.5–2 hours
**Commits**: 14 (one per service, or batch into 2–3 commits per domain)
**Rollback**: `git revert [commit hashes]` (simplest rollback method)

#### Core Pattern for Each Service

For each database initialization file listed in Part 1, table "Database Initialization Files":

**Before**:
```python
# Example from data-api/src/database.py (current dual-mode)
def get_engine():
    db_url = os.getenv("DATABASE_URL")

    if db_url and db_url.startswith("postgresql"):
        # PostgreSQL path
        engine = create_async_engine(
            db_url,
            echo=False,
            pool_size=20,
            max_overflow=10,
        )
    else:
        # SQLite fallback
        sqlite_path = os.getenv("SQLITE_PATH", "./data/metadata.db")
        db_url = f"sqlite+aiosqlite:///{sqlite_path}"
        engine = create_async_engine(
            db_url,
            echo=False,
            connect_args={"check_same_thread": False, "timeout": 30},
        )
    return engine
```

**After**:
```python
# PostgreSQL only
def get_engine():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL not set")

    engine = create_async_engine(
        db_url,
        echo=False,
        pool_size=20,
        max_overflow=10,
    )
    return engine
```

#### Service-by-Service Changes

| # | Service | File | Changes |
|---|---------|------|---------|
| 1 | data-api | `database.py` | Remove SQLite branch, inline PostgreSQL path, add env validation |
| 2 | ai-automation-service-new | `src/database/__init__.py` | Remove `sqlite+aiosqlite` branch, require `DATABASE_URL` |
| 3 | ha-ai-agent-service | `src/database.py` | Remove SQLite fallback block |
| 4 | ai-query-service | `src/database/__init__.py` | Remove dual-mode logic |
| 5 | ai-training-service | `src/database/__init__.py` | Remove SQLite path |
| 6 | rag-service | `src/database/session.py` | Remove aiosqlite imports + fallback |
| 7 | device-intelligence-service | `src/core/database.py` | Remove SQLite engine creation |
| 8 | proactive-agent-service | `src/database.py` | Remove SQLite fallback |
| 9 | automation-miner | `src/miner/database.py` | Remove dual-mode logic |
| 10 | blueprint-index | `src/database.py` | Remove SQLite path |
| 11 | blueprint-suggestion-service | `src/database.py` | Remove SQLite fallback |
| 12 | ha-setup-service | `src/database.py` | Remove aiosqlite dependency |
| 13 | ai-pattern-service | `src/database/__init__.py` | Remove SQLite branch |
| 14 | api-automation-edge | `src/registry/database.py` | Remove dual-mode engine creation |

#### Verification for Each File

After editing each file:

```bash
# Quick syntax check
python -m py_compile domains/{group}/{service}/src/{db_path}

# Search for remaining sqlite/aiosqlite references
grep -i "sqlite\|aiosqlite" domains/{group}/{service}/src/{db_path}
# Should return empty
```

**Commit message template**:
```
chore: 6.5 story — remove SQLite fallback from {service}

- Remove aiosqlite imports
- Remove if/else DATABASE_URL check
- Require POSTGRES_URL/DATABASE_URL to be set
- Simplify engine creation to PostgreSQL-only path

Ref: Story 6.5: SQLite Volume Removal
```

---

### **STEP 3: Remove aiosqlite from Requirements (15 files)**

**Timing**: 30 min
**Commits**: 1 (batch all requirements.txt changes)
**Rollback**: `git revert [commit hash]`

#### Files to Modify

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

#### Change Pattern

Remove any line containing `aiosqlite` (usually `aiosqlite>=0.19.0` or similar).

**Verification**:
```bash
# Verify aiosqlite removed from all requirements
grep -r "aiosqlite" domains/ --include="requirements*.txt"
# Should return empty

# Double-check total files modified
git diff --name-only | grep requirements.txt
# Should show 15 files
```

**Commit message**:
```
chore: 6.5 story — remove aiosqlite dependency from all services

Remove aiosqlite from:
- core-platform/data-api (2 files)
- automation-core (3 services)
- ml-engine (3 services)
- energy-analytics (1 service)
- blueprints (3 services)
- device-management (1 service)
- pattern-analysis (2 services)

Aligns with PostgreSQL-only transition post-cutover.

Ref: Story 6.5: SQLite Volume Removal
```

---

### **STEP 4: Remove SQLite Environment Variables from Compose Files**

**Timing**: 30 min
**Commits**: 1 (batch all compose changes)
**Rollback**: `git revert [commit hash]`

#### Compose Files to Modify

Primary: `domains/core-platform/compose.yml`
Secondary: `docker-compose.dev.yml`, `docker-compose.minimal.yml` (if they reference SQLite)

#### Change Pattern

Remove environment variables:
- `DATABASE_URL=sqlite+aiosqlite://...`
- `SQLITE_TIMEOUT`
- `SQLITE_CACHE_SIZE`
- Any service-specific `SQLITE_*` vars

Example from `domains/core-platform/compose.yml` (data-api service):

**Before**:
```yaml
data-api:
  environment:
    - DATA_API_HOST=0.0.0.0
    - DATA_API_PORT=8006
    - DATABASE_URL=sqlite+aiosqlite:///data/metadata.db
    - SQLITE_TIMEOUT=30
    - SQLITE_CACHE_SIZE=2000
```

**After**:
```yaml
data-api:
  environment:
    - DATA_API_HOST=0.0.0.0
    - DATA_API_PORT=8006
    # DATABASE_URL now comes from .env file only
```

**Verification**:
```bash
# Search for sqlite or DATABASE_URL with sqlite in compose files
grep -r "sqlite\|DATABASE_URL.*sqlite" domains/ docker-compose*.yml

# Should show no results (or only in comments)
```

**Commit message**:
```
chore: 6.5 story — remove SQLite environment variables from compose files

Remove from:
- domains/core-platform/compose.yml
- docker-compose.dev.yml
- docker-compose.minimal.yml

Services now depend on POSTGRES_URL/DATABASE_URL from .env only.

Ref: Story 6.5: SQLite Volume Removal
```

---

### **STEP 5: Remove Orphaned Docker Volumes**

**Timing**: 5 min
**Commits**: N/A (operational step, not code)
**Rollback**: Docker volumes can be recreated if needed (data is in PostgreSQL)

#### Execution

```bash
# Stop all services first
docker compose down

# Remove orphaned SQLite volumes (safe — data migrated to PostgreSQL)
docker volume rm homeiq_sqlite-data 2>/dev/null || true
docker volume rm homeiq_ai_automation_data 2>/dev/null || true
docker volume rm homeiq_agent_data 2>/dev/null || true
docker volume rm homeiq_blueprints_data 2>/dev/null || true
docker volume rm homeiq_devices_data 2>/dev/null || true
docker volume rm homeiq_energy_data 2>/dev/null || true
docker volume rm homeiq_patterns_data 2>/dev/null || true
docker volume rm homeiq_rag_data 2>/dev/null || true

# Verify removal
docker volume ls | grep -i sqlite || echo "✓ All SQLite volumes removed"

# Verify postgres volume still exists
docker volume ls | grep postgres
# Should show: homeiq_postgres_data
```

**Verification**:
```bash
# Confirm no sqlite-named volumes remain
docker volume ls | grep -i sqlite
# Should return empty
```

**Documentation**: Record volume names removed in `docs/operations/6.5-cutover-baseline.txt`.

---

### **STEP 6: Archive SQLite Migration Scripts**

**Timing**: 5 min
**Commits**: 1
**Rollback**: `git revert [commit hash]`

#### Creation

```bash
# Create archive directory
mkdir -p scripts/archive/sqlite-migration

# Move SQLite-specific migration scripts
mv scripts/validate-databases.sh scripts/archive/sqlite-migration/ 2>/dev/null || true
mv scripts/migrate-data/ scripts/archive/sqlite-migration/ 2>/dev/null || true

# Create README for future reference
cat > scripts/archive/sqlite-migration/README.md << 'EOF'
# SQLite Migration Scripts (Archived)

These scripts were used during the 2026 SQLite-to-PostgreSQL migration
and are archived here for historical reference.

**Do NOT use these scripts in production.**

## Contents

- `validate-databases.sh` — SQLite ↔ PostgreSQL data validation (superseded by validate-migration/*.py)
- `migrate-data/` — Data migration scripts (completed Feb 2026, not needed post-cutover)

## See Also

- `../../validate-migration/validate_data.py` — Current data validation tool
- `../../validate-migration/check_schemas.py` — Current schema validation tool
- `../../check-pg-stability.sh` — PostgreSQL stability monitoring

EOF

# Keep validate-migration scripts in place (still used for audits)
```

**Commit message**:
```
chore: 6.5 story — archive SQLite migration scripts

Move to scripts/archive/sqlite-migration/:
- validate-databases.sh (historical reference)
- migrate-data/ (migration tools, completed)

Rationale: Scripts served their purpose during migration (Feb 2026).
Post-cutover validation uses scripts/validate-migration/*.py.

Ref: Story 6.5: SQLite Volume Removal
```

---

### **STEP 7: Update Documentation**

**Timing**: 30 min
**Commits**: 1–2 (one per major doc, or batch)
**Rollback**: `git revert [commit hash]`

#### 7.1: Update MEMORY.md

**File**: `C:\Users\tappt\.claude\projects\c--cursor-HomeIQ\memory\MEMORY.md`

**Change**:

**Before**:
```markdown
### Databases: InfluxDB (time-series), PostgreSQL 17 (metadata, schema-per-domain) with SQLite fallback
```

**After**:
```markdown
### Databases: InfluxDB (time-series), PostgreSQL 17 (metadata, schema-per-domain)
- Fully migrated from SQLite as of 2026-02-24 (Story 6.5 cutover)
```

#### 7.2: Update Project TECH_STACK.md (if exists)

Search for and remove SQLite from the tech stack file.

```bash
# Find tech stack file
find . -name "TECH_STACK.md" -o -name "tech-stack.md"
```

#### 7.3: Update Service-Level README files

Check each service's README for SQLite references:

```bash
# Search for SQLite mentions in README files
grep -r "sqlite\|SQLite" domains/ --include="README.md"
```

Update any mentions to remove references to fallback behavior.

#### 7.4: Update .env.example

**File**: `.env.example`

**Change**:

**Before**:
```
# Database
DATABASE_URL=sqlite+aiosqlite:///data/metadata.db
SQLITE_TIMEOUT=30
SQLITE_CACHE_SIZE=2000
```

**After**:
```
# Database (PostgreSQL only — migration complete as of 2026-02-24)
POSTGRES_URL=postgresql+asyncpg://homeiq:password@postgres:5432/homeiq
DATABASE_URL=postgresql+asyncpg://homeiq:password@postgres:5432/homeiq
```

#### 7.5: Create Cutover Summary Document

**File**: `docs/operations/6.5-cutover-summary.md`

```markdown
# Story 6.5 Cutover Summary

**Date**: 2026-02-27 (example)
**Duration**: 3 hours 45 minutes
**Outcome**: SUCCESS ✓

## Changes Applied

1. ✅ Removed SQLite fallback code from 14 services
2. ✅ Removed aiosqlite from 15 requirements.txt files
3. ✅ Removed SQLite env vars from compose files
4. ✅ Removed 8 Docker volumes
5. ✅ Archived SQLite migration scripts
6. ✅ Updated documentation

## Verification Results

- [x] All services start successfully
- [x] Health checks PASS for all 15 services
- [x] Zero sqlite/aiosqlite references in logs
- [x] PostgreSQL stability check: PASS
- [x] E2E tests: PASS

## Operator Sign-Off

Operator: [name]
Reviewer: [name]
Operations: [name]
```

**Commit message**:
```
docs: 6.5 story — update documentation post-cutover

- Update MEMORY.md: remove SQLite fallback references
- Update .env.example: PostgreSQL-only (remove SQLITE_* vars)
- Create 6.5-cutover-summary.md
- Archive SQLite migration scripts documentation

Ref: Story 6.5: SQLite Volume Removal
```

---

### **STEP 8: Rebuild Services & Validate**

**Timing**: 1–1.5 hours (depends on Docker build speed)
**Commits**: N/A (operational step)
**Rollback**: `docker compose down && git revert [commits]`

#### 8.1: Build New Images

```bash
# Clear old images (optional but recommended)
docker compose down
docker image prune -f

# Rebuild all services (parallel)
docker buildx bake full

# Alternative: incremental rebuild per domain
docker buildx bake core-platform automation-core ml-engine # etc.
```

#### 8.2: Start Services

```bash
# Start core platform first
docker compose -f domains/core-platform/compose.yml up -d

# Wait for postgres + influxdb to be healthy (30s)
sleep 30

# Run Alembic migrations (if not auto-run)
for domain in core-platform automation-core ml-engine; do
  docker compose -f domains/$domain/compose.yml exec -T \
    postgres alembic upgrade head --config /app/alembic.ini
done

# Start remaining services
docker compose up -d
```

#### 8.3: Verify Service Health

```bash
# Check all services are healthy
docker compose ps --format "table {{.Names}}\t{{.State}}\t{{.Status}}"

# Expected: All services "running" with health "healthy" (if they have healthchecks)

# Example:
# homeiq-data-api          running     healthy
# homeiq-ha-ai-agent       running     healthy
# homeiq-postgres          running     healthy
```

#### 8.4: Run Post-Cutover Validation

```bash
# 1. Stability check
scripts/check-pg-stability.sh
# Should output: OVERALL: PASS

# 2. Schema validation
python scripts/validate-migration/check_schemas.py \
  --postgres-url "$DATABASE_URL" \
  --schemas core automation agent blueprints energy devices patterns rag
# Should output: Overall: PASS

# 3. Check for sqlite/aiosqlite in logs
docker compose logs --tail=100 | grep -i "sqlite\|aiosqlite" || echo "✓ No SQLite references in logs"

# 4. Verify pip packages (spot check a few services)
docker exec homeiq-data-api pip list | grep -i "sqlite\|aiosqlite" || echo "✓ aiosqlite not installed"

# 5. E2E tests (if available)
pytest tests/e2e/ -v
```

---

## Part 5: Post-Cutover Verification Checklist

Execute **immediately** after completing Steps 1–8.

### Service Health

- [ ] `docker compose ps` shows all 15 database services "running"
- [ ] Health checks PASS for all services (if configured)
- [ ] No restart loops: `docker compose ps | grep restarting` returns empty
- [ ] `scripts/check-service-health.sh` (if exists) returns PASS

### Data Integrity

- [ ] `scripts/pg-health-report.sh` returns clean report
- [ ] `scripts/check-pg-stability.sh` returns PASS (all 8 checks)
- [ ] All Alembic migrations at expected versions (check alembic_version tables)

### Code Cleanup

- [ ] **Zero** sqlite/aiosqlite in logs: `docker compose logs | grep -i sqlite` returns empty
- [ ] **Zero** aiosqlite in installed packages:
  ```bash
  for svc in $(docker ps --format '{{.Names}}' | grep homeiq); do
    docker exec "$svc" pip list 2>/dev/null | grep -i aiosqlite || true
  done
  # Should return empty
  ```
- [ ] **Zero** sqlite references in codebase (excluding archive):
  ```bash
  grep -r "aiosqlite" domains/ --include="*.py" \
    --exclude-dir=".git" --exclude-dir="archive"
  # Should return empty
  ```

### Functional Smoke Tests

- [ ] **Create event via data-api**: POST `/api/events` with sample payload
- [ ] **Query entities via data-api**: GET `/api/entities?limit=5`
- [ ] **List automations via data-api**: GET `/api/automations`
- [ ] **Create automation via ha-ai-agent**: POST `/chat/messages` with automation request
- [ ] **Query patterns via ai-pattern-service**: GET `/patterns?limit=10`

### Volume Cleanup

- [ ] Docker volume list contains **no** sqlite-named volumes:
  ```bash
  docker volume ls | grep -i sqlite
  # Should return empty
  ```
- [ ] PostgreSQL volume still exists:
  ```bash
  docker volume ls | grep postgres
  # Should show: homeiq_postgres_data
  ```

### Documentation

- [ ] Update `docs/operations/6.5-cutover-summary.md` with actual results
- [ ] Sign-off table in `docs/operations/sqlite-cutover-checklist.md` completed
- [ ] All team members notified of successful cutover

---

## Part 6: Rollback Procedure

If issues discovered post-cutover, follow this procedure:

### Immediate Actions (< 5 minutes)

1. **Stop services**:
   ```bash
   docker compose down
   ```

2. **Identify failed commits**:
   ```bash
   git log --oneline | head -10
   # Note the hashes of Steps 2–5 commits
   ```

3. **Revert in reverse order** (Steps 5 → 2):
   ```bash
   git revert --no-edit [Step 5 commit hash]
   git revert --no-edit [Step 4 commit hash]
   git revert --no-edit [Step 3 commit hash]
   git revert --no-edit [Step 2 commit hash]
   # This creates 4 new revert commits
   ```

### Recovery Steps (5–10 minutes)

1. **Rebuild services with SQLite fallback restored**:
   ```bash
   docker buildx bake full
   ```

2. **Start services** (SQLite fallback will auto-activate):
   ```bash
   docker compose up -d
   ```

3. **Verify fallback is working**:
   ```bash
   docker compose logs data-api | grep -i "sqlite\|Created SQLite engine"
   # Should show SQLite engine creation log
   ```

### Post-Rollback Investigation (ongoing)

1. **Collect logs from failure time**:
   ```bash
   docker compose logs --since "2h" > /tmp/homeiq-logs-[date].txt
   ```

2. **Document the issue**: Create `docs/operations/6.5-incident-[date].md` with:
   - Timestamp of failure
   - Services affected
   - Error messages
   - Root cause (if identified)
   - Time to rollback
   - Next steps

3. **Notify stakeholders**: Update team on rollback and timeline for re-attempt

4. **Schedule re-attempt**: Allow 24–48 hours for issue root-cause analysis

---

## Part 7: Timeline & Maintenance Window

### Recommended Schedule

**Date**: 2026-03-10 (2 weeks post-go-live)
**Time**: 09:00 UTC (adjust for team timezone)
**Duration**: 3–4 hours
**Maintenance window**: 09:00–15:00 UTC (buffer for issues)

### Timeline Detail

| Phase | Step | Duration | Time |
|-------|------|----------|------|
| Pre | 1. Backups & validation | 30 min | 09:00–09:30 |
| Code | 2. Remove SQLite code (14 files) | 90 min | 09:30–11:00 |
| Code | 3. Remove aiosqlite (15 files) | 30 min | 11:00–11:30 |
| Code | 4. Remove SQLite env vars | 30 min | 11:30–12:00 |
| Ops | 5. Remove Docker volumes | 5 min | 12:00–12:05 |
| Ops | 6. Archive scripts | 5 min | 12:05–12:10 |
| Docs | 7. Update documentation | 30 min | 12:10–12:40 |
| **Lunch** | *Break* | 20 min | 12:40–13:00 |
| Ops | 8. Rebuild & start services | 90 min | 13:00–14:30 |
| Verify | 9. Post-cutover checks | 30 min | 14:30–15:00 |

### Parallel Work (if team available)

- **Developer A**: Steps 2–3 (code changes)
- **Developer B**: Steps 4–6 (ops)
- **Developer C**: Step 7 (documentation)
- **Operations**: Step 8–9 (deployment & verification)

---

## Part 8: Success Criteria

Story 6.5 is **COMPLETE** when:

### Deployment Success

✅ All 15 services start without errors
✅ All services stay in "running" state (no restart loops)
✅ All Alembic migrations run successfully

### Data Integrity

✅ PostgreSQL stability check: 8/8 checks PASS
✅ PostgreSQL schema check: all 8 schemas PASS
✅ E2E tests: all passing

### Code Cleanup

✅ Zero SQLite code paths remaining
✅ Zero aiosqlite references in requirements.txt
✅ Zero aiosqlite in container images
✅ Zero SQLite environment variables in compose
✅ All Docker volumes removed except postgres_data

### Documentation

✅ MEMORY.md updated (no SQLite references)
✅ .env.example updated (PostgreSQL-only)
✅ Cutover summary document created & signed off
✅ Team notified of successful completion

**Estimated Effort**: 5–6 developer-hours + 1–2 ops-hours
**Complexity**: Medium (straightforward execution, low risk)
**Blast Radius**: Low (PostgreSQL already running, SQLite is fallback only)

---

## Appendix A: Git Commit Summary

### Expected Commits (8 total)

```
docs: 6.5 baseline snapshot before cutover
chore: 6.5 — remove SQLite fallback from data-api
chore: 6.5 — remove SQLite fallback from ai-automation-service-new
chore: 6.5 — remove SQLite fallback from ha-ai-agent-service
... (11 more service-specific commits)
chore: 6.5 — remove aiosqlite dependency from all services
chore: 6.5 — remove SQLite environment variables from compose files
chore: 6.5 — archive SQLite migration scripts
docs: 6.5 — update documentation post-cutover
```

### Rollback Command

```bash
# Revert last 8 commits
git revert --no-edit HEAD~7..HEAD
```

---

## Appendix B: Service Dependencies for Validation

**Critical path services** (test these first post-cutover):

1. **data-api** (port 8006) — all services depend on this for metadata
2. **ha-ai-agent-service** (port 8030) — automation queries
3. **ai-automation-service-new** (port 8036) — automation deployments
4. **ai-pattern-service** (port 8035) — pattern storage

**Functional flow to validate**:

```
data-api (create device)
  → ha-ai-agent (query device context)
  → ai-automation (deploy automation)
  → ai-pattern (log pattern usage)
```

---

## Appendix C: Emergency Contacts

**If issues occur during cutover**:

1. **Check service logs**: `docker compose logs [service-name] --tail=50`
2. **Check PostgreSQL**: `docker compose exec postgres psql -U homeiq -d homeiq -c "SELECT 1;"`
3. **Contact DevOps**: [team contact info]
4. **Escalation**: If unable to resolve in 30 minutes, trigger rollback

---

**Document Version**: 1.0
**Last Updated**: 2026-02-27
**Ready for Execution**: After 2026-03-10 (14-day stabilization)
