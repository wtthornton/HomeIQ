# Phase 2: tenacity 9.1.2 Migration Guide

**Story:** PHASE2-003
**Status:** ✅ Complete
**Created:** February 5, 2026

---

## Overview

Automated migration tool for updating services from tenacity 8.x to 9.1.2.

### Breaking Changes in tenacity 9.0+

1. **`reraise` parameter default changed from `True` to `False`**
   - Impact: Exceptions may be silently swallowed instead of re-raised
   - Fix: Explicitly add `reraise=True` to maintain 8.x behavior

2. **Wait strategy parameter updates**
   - Minor typing improvements (non-breaking)

---

## Migration Script

**Location:** `scripts/phase2-migrate-tenacity.py`

### Features

✅ **Automated Detection**
- Finds `@retry` decorators without explicit `reraise` parameter
- Updates requirements.txt to 9.1.2
- Validates retry patterns still work

✅ **Safe Migration**
- Creates backups before making changes
- Dry-run mode to preview changes
- Rollback script generation
- Post-migration test validation

✅ **Batch Processing**
- Migrate multiple services in one command
- Parallel-safe (each service isolated)

---

## Usage

### Single Service

```bash
# Dry run (preview changes)
python scripts/phase2-migrate-tenacity.py api-automation-edge --dry-run

# Apply migration
python scripts/phase2-migrate-tenacity.py api-automation-edge
```

### Batch Migration

```bash
# Migrate multiple services
python scripts/phase2-migrate-tenacity.py \
  --batch api-automation-edge ai-automation-service-new rag-service
```

---

## What the Script Does

### Step 1: Validate Service Structure

Checks for:
- Service directory exists
- `requirements.txt` exists

### Step 2: Check if Migration Needed

Skips if:
- Already has tenacity==9.1.2
- Does not use tenacity at all

### Step 3: Create Backup

Creates `.migration_backup_tenacity_YYYYMMDD_HHMMSS/` with:
- `requirements.txt`
- `src/` directory (full copy)

### Step 4: Find Retry Usage

Scans `src/**/*.py` for:
- `@retry` decorators
- `from tenacity import` statements
- `import tenacity` statements

### Step 5: Migrate Retry Decorators

**Before (tenacity 8.x):**
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.HTTPError,))
)
async def call_api():
    ...
```

**After (tenacity 9.1.2):**
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.HTTPError,)),
    reraise=True  # ← Added to maintain 8.x behavior
)
async def call_api():
    ...
```

**Already Compatible:**
If code already has `reraise=True`, no changes needed:
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.HTTPError,)),
    reraise=True  # ← Already has it
)
```

### Step 6: Update requirements.txt

**Before:**
```
tenacity>=8.2.0,<9.0.0
```

**After:**
```
tenacity==9.1.2  # Phase 2 upgrade - MAJOR version
```

### Step 7: Run Tests

Validates migration with:
```bash
pytest tests/ -v --tb=short
```

If tests fail, creates rollback script and exits.

### Step 8: Create Rollback Script

Generates `rollback_tenacity_YYYYMMDD_HHMMSS.sh`

---

## Affected Services (10 total)

From `phase2-dependency-analysis.md`:

### CRITICAL Priority (1 service)
- ✅ `api-automation-edge` (also has influxdb)

### HIGH Priority (3 services)
- ✅ `ai-automation-service-new`
- ✅ `ai-core-service` (also has pytest-asyncio)
- ✅ `ml-service` (also has pytest-asyncio)

### MEDIUM Priority (6 services)
- ✅ `ai-pattern-service` (also has pytest-asyncio)
- ✅ `device-intelligence-service` (also has pytest-asyncio)
- ✅ `ha-ai-agent-service` (also has pytest-asyncio)
- ✅ `openvino-service` (also has pytest-asyncio)
- ✅ `proactive-agent-service` (also has pytest-asyncio)
- ✅ `rag-service`

---

## Migration Strategy

### Phase A: Low-Risk Test (2 services)

**Purpose:** Validate migration script on non-critical services

```bash
python scripts/phase2-migrate-tenacity.py \
  --batch rag-service ai-automation-service-new
```

### Phase B: Medium-Risk (6 services)

**Purpose:** Migrate medium-priority services

```bash
python scripts/phase2-migrate-tenacity.py \
  --batch ai-pattern-service device-intelligence-service \
          ha-ai-agent-service openvino-service \
          proactive-agent-service
```

**Note:** Some of these services also need pytest-asyncio migration

### Phase C: High-Risk (2 services)

**Purpose:** Migrate high-priority services

```bash
python scripts/phase2-migrate-tenacity.py \
  --batch ai-core-service ml-service
```

**Note:** These services also need pytest-asyncio migration

### Phase D: Critical Service (1 service, SEQUENTIAL)

**Purpose:** Migrate critical path service with blue-green deployment

```bash
python scripts/phase2-migrate-tenacity.py api-automation-edge
```

**Note:** This service also needs influxdb migration

---

## Validation

### Post-Migration Checklist

For each service:

- [ ] ✅ requirements.txt has `tenacity==9.1.2`
- [ ] ✅ All `@retry` decorators have `reraise=True` (or explicit `reraise=False` if intended)
- [ ] ✅ All tests pass (`pytest tests/ -v`)
- [ ] ✅ Backup directory created
- [ ] ✅ Rollback script created

### Service Health Check

After migration, verify service is healthy:

```bash
# Build service with new dependencies
docker-compose build <service-name>

# Start service
docker-compose up -d <service-name>

# Check health
curl http://localhost:<port>/health

# Check logs
docker-compose logs <service-name>
```

---

## Rollback Procedure

If migration fails or tests fail:

```bash
# Option 1: Use rollback script
cd services/<service-name>
./rollback_tenacity_YYYYMMDD_HHMMSS.sh

# Option 2: Manual rollback
cd services/<service-name>
cp .migration_backup_tenacity_*/requirements.txt ./requirements.txt
rm -rf src
cp -r .migration_backup_tenacity_*/src ./src

# Rebuild service with old versions
docker-compose build <service-name>
docker-compose up -d <service-name>
```

---

## Common Issues

### Issue 1: Tests Failing After Migration

**Symptom:** Tests pass before migration, fail after

**Possible Causes:**
1. Exception now silently swallowed (missing `reraise=True`)
2. Retry behavior changed unexpectedly

**Solution:**
```python
# Ensure reraise=True is set
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True  # ← Add this
)
```

### Issue 2: Exceptions Not Being Raised

**Symptom:** Code fails silently, no exception raised

**Cause:** Default `reraise` changed from `True` to `False` in tenacity 9.0

**Solution:**
```python
# Explicitly set reraise=True
@retry(..., reraise=True)
```

---

## Script Output Example

### Dry Run

```
============================================================
tenacity Migration Summary: api-automation-edge
============================================================
[DRY RUN] - No changes made

Changes (1):
  [OK] requirements.txt: Updated tenacity to 9.1.2
============================================================
```

### Actual Migration (Code Already Compatible)

```
============================================================
tenacity Migration Summary: api-automation-edge
============================================================

Changes (1):
  [OK] requirements.txt: Updated tenacity to 9.1.2

Backup: services/api-automation-edge/.migration_backup_tenacity_20260205_122030
Rollback Script: services/api-automation-edge/rollback_tenacity_20260205_122030.sh

Running tests...
[OK] All tests passed (28 tests, 1.8s)
============================================================
```

### Migration with Code Changes

```
============================================================
tenacity Migration Summary: some-service
============================================================

Changes (3):
  [OK] src/api/client.py: Updated retry decorators
  [OK] src/utils/retry.py: Updated retry decorators
  [OK] requirements.txt: Updated tenacity to 9.1.2

Backup: services/some-service/.migration_backup_tenacity_20260205_122100

Running tests...
[OK] All tests passed (42 tests, 2.3s)
============================================================
```

---

## Next Steps

After completing tenacity migration:

1. ✅ Mark Story 3 as complete
2. 📋 Begin Story 4: asyncio-mqtt → aiomqtt 2.4.0 Migration Script
3. 📋 Continue with remaining Phase 2 stories

---

## References

- **Breaking Changes:** [tenacity 9.0 changelog](https://github.com/jd/tenacity/releases/tag/9.0.0)
- **Phase 2 Plan:** [phase2-implementation-plan.md](phase2-implementation-plan.md)
- **Service Dependencies:** [phase2-dependency-analysis.md](phase2-dependency-analysis.md)

---

**Status:** ✅ Migration script complete and tested
**Next:** Begin tenacity migration rollout
