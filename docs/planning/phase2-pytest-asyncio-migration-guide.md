# Phase 2: pytest-asyncio 1.3.0 Migration Guide

**Story:** PHASE2-002
**Status:** ✅ Complete
**Created:** February 5, 2026

---

## Overview

Automated migration tool for updating services from pytest-asyncio 0.23.x to 1.3.0.

### Breaking Changes in pytest-asyncio 1.3.0

1. **`asyncio_mode = "auto"` is now the default** - Remove from pytest.ini
2. **All async test functions MUST have `@pytest.mark.asyncio` decorator**
3. **Async fixtures no longer auto-detected** - Explicit markers required

---

## Migration Script

**Location:** `scripts/phase2-migrate-pytest-asyncio.py`

### Features

✅ **Automated Detection**
- Finds async test functions without `@pytest.mark.asyncio` markers
- Identifies pytest.ini with `asyncio_mode = auto`
- Skips fixtures (only marks actual test functions)

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
python scripts/phase2-migrate-pytest-asyncio.py automation-miner --dry-run

# Apply migration
python scripts/phase2-migrate-pytest-asyncio.py automation-miner
```

### Batch Migration

```bash
# Migrate multiple services
python scripts/phase2-migrate-pytest-asyncio.py \
  --batch automation-miner blueprint-index ha-setup-service ha-simulator
```

### From Service Directory

```bash
# Use relative or absolute path
python scripts/phase2-migrate-pytest-asyncio.py services/automation-miner
```

---

## What the Script Does

### Step 1: Validate Service Structure

Checks for:
- Service directory exists
- `tests/` directory exists
- `requirements.txt` exists

### Step 2: Create Backup

Creates `.migration_backup_YYYYMMDD_HHMMSS/` with:
- `pytest.ini`
- `requirements.txt`
- `tests/` directory (full copy)

### Step 3: Migrate pytest.ini

**Before:**
```ini
[pytest]
# Asyncio configuration
asyncio_mode = auto
```

**After:**
```ini
[pytest]
# (removed - asyncio_mode = auto is now default)
```

### Step 4: Scan and Update Test Files

**Before:**
```python
async def test_my_feature():
    result = await some_async_function()
    assert result is not None
```

**After:**
```python
@pytest.mark.asyncio
async def test_my_feature():
    result = await some_async_function()
    assert result is not None
```

**Skips Fixtures:**
```python
@pytest.fixture  # ← Script detects this and skips
async def test_db():
    ...
```

### Step 5: Update requirements.txt

**Before:**
```
pytest-asyncio>=0.23.0
```

**After:**
```
pytest-asyncio==1.3.0  # Phase 2 upgrade - BREAKING: new async patterns
```

### Step 6: Run Tests

Validates migration with:
```bash
pytest tests/ -v --tb=short
```

If tests fail, creates rollback script and exits.

### Step 7: Create Rollback Script

Generates `rollback_pytest_asyncio_YYYYMMDD_HHMMSS.sh`:

```bash
#!/bin/bash
# Rollback script for pytest-asyncio migration

# Restore pytest.ini
cp .migration_backup_*/pytest.ini ./pytest.ini

# Restore requirements.txt
cp .migration_backup_*/requirements.txt ./requirements.txt

# Restore tests directory
rm -rf tests
cp -r .migration_backup_*/tests ./tests

echo "✅ Rollback complete"
```

---

## Affected Services (20 total)

From `phase2-dependency-analysis.md`:

### CRITICAL Priority (2 services)
- ✅ `data-api` (also has influxdb)
- ✅ `websocket-ingestion` (also has asyncio-mqtt, influxdb)

### HIGH Priority (4 services)
- ✅ `admin-api` (also has influxdb)
- ✅ `ai-core-service` (also has tenacity)
- ✅ `ml-service` (also has tenacity)
- ✅ `data-retention` (also has asyncio-mqtt, influxdb)

### MEDIUM Priority (8 services)
- ✅ `ai-pattern-service` (also has tenacity)
- ✅ `ai-query-service`
- ✅ `ai-training-service`
- ✅ `device-intelligence-service` (also has tenacity)
- ✅ `ha-ai-agent-service` (also has tenacity)
- ✅ `openvino-service` (also has tenacity)
- ✅ `proactive-agent-service` (also has tenacity)
- ✅ `blueprint-suggestion-service`

### LOW Priority (6 services)
- ✅ `automation-miner`
- ✅ `blueprint-index`
- ✅ `ha-setup-service`
- ✅ `ha-simulator` (also has asyncio-mqtt)
- ✅ `sports-api` (also has influxdb)
- ✅ `weather-api` (also has influxdb)

---

## Migration Strategy

### Phase A: Low-Risk Test (4 services)

**Purpose:** Validate migration script on non-critical services

```bash
python scripts/phase2-migrate-pytest-asyncio.py \
  --batch automation-miner blueprint-index ha-setup-service ha-simulator
```

**Expected Results:**
- 4/4 services migrate successfully
- All tests pass
- Rollback scripts created

### Phase B: Medium-Risk (8 services)

**Purpose:** Migrate medium-priority services

```bash
python scripts/phase2-migrate-pytest-asyncio.py \
  --batch ai-pattern-service ai-query-service ai-training-service \
          device-intelligence-service ha-ai-agent-service openvino-service \
          proactive-agent-service blueprint-suggestion-service
```

### Phase C: High-Risk (4 services)

**Purpose:** Migrate high-priority services

```bash
python scripts/phase2-migrate-pytest-asyncio.py \
  --batch ai-core-service ml-service admin-api data-retention
```

### Phase D: Critical Services (2 services, SEQUENTIAL)

**Purpose:** Migrate critical path services with blue-green deployment

```bash
# Migrate data-api first
python scripts/phase2-migrate-pytest-asyncio.py data-api

# Wait for validation, then migrate websocket-ingestion
python scripts/phase2-migrate-pytest-asyncio.py websocket-ingestion
```

---

## Validation

### Post-Migration Checklist

For each service:

- [ ] ✅ pytest.ini no longer has `asyncio_mode = auto`
- [ ] ✅ All async test functions have `@pytest.mark.asyncio`
- [ ] ✅ Fixtures are NOT marked with `@pytest.mark.asyncio`
- [ ] ✅ requirements.txt has `pytest-asyncio==1.3.0`
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
./rollback_pytest_asyncio_YYYYMMDD_HHMMSS.sh

# Option 2: Manual rollback
cd services/<service-name>
cp .migration_backup_*/pytest.ini ./pytest.ini
cp .migration_backup_*/requirements.txt ./requirements.txt
rm -rf tests
cp -r .migration_backup_*/tests ./tests

# Rebuild service with old versions
docker-compose build <service-name>
docker-compose up -d <service-name>
```

---

## Common Issues

### Issue 1: Tests Still Failing After Migration

**Symptom:** Tests pass before migration, fail after

**Possible Causes:**
1. Async fixture scope issues
2. Event loop conflicts

**Solution:**
```python
# Check conftest.py for event loop fixtures
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
```

### Issue 2: Marker Not Applied to Test

**Symptom:** `PytestUnraisableExceptionWarning` or similar

**Cause:** Test function is async but missing marker

**Solution:**
```python
# Manually add marker
@pytest.mark.asyncio
async def test_my_feature():
    ...
```

### Issue 3: Fixture Incorrectly Marked

**Symptom:** `ScopeMismatch` error

**Cause:** Fixture has `@pytest.mark.asyncio` (should only be on tests)

**Solution:**
```python
# Remove marker from fixture
@pytest.fixture  # ← No @pytest.mark.asyncio
async def my_fixture():
    ...
```

---

## Script Output Example

### Dry Run

```
============================================================
pytest-asyncio Migration Summary: automation-miner
============================================================
[DRY RUN] - No changes made

Changes (5):
  [OK] pytest.ini: Removed 'asyncio_mode = auto' (now default in pytest-asyncio 1.3.0)
  [OK] test_main.py: Added @pytest.mark.asyncio to test_lifespan_startup
  [OK] test_main.py: Added @pytest.mark.asyncio to test_health_check
  [OK] test_api.py: Added @pytest.mark.asyncio to test_search_endpoint
  [OK] requirements.txt: Updated pytest-asyncio to 1.3.0
============================================================
```

### Actual Migration

```
============================================================
pytest-asyncio Migration Summary: automation-miner
============================================================

Changes (5):
  [OK] pytest.ini: Removed 'asyncio_mode = auto' (now default in pytest-asyncio 1.3.0)
  [OK] test_main.py: Added @pytest.mark.asyncio to test_lifespan_startup
  [OK] test_main.py: Added @pytest.mark.asyncio to test_health_check
  [OK] test_api.py: Added @pytest.mark.asyncio to test_search_endpoint
  [OK] requirements.txt: Updated pytest-asyncio to 1.3.0

Backup: services/automation-miner/.migration_backup_20260205_121530
Rollback Script: services/automation-miner/rollback_pytest_asyncio_20260205_121530.sh

Running tests...
[OK] All tests passed (42 tests, 2.3s)
============================================================
```

---

## Next Steps

After completing pytest-asyncio migration:

1. ✅ Mark Story 2 as complete
2. 📋 Begin Story 3: tenacity 9.1.2 Migration Script
3. 📋 Continue with remaining Phase 2 stories

---

## References

- **Breaking Changes:** [pytest-asyncio 1.3.0 changelog](https://github.com/pytest-dev/pytest-asyncio/releases/tag/v1.3.0)
- **Phase 2 Plan:** [phase2-implementation-plan.md](phase2-implementation-plan.md)
- **Service Dependencies:** [phase2-dependency-analysis.md](phase2-dependency-analysis.md)

---

**Status:** ✅ Migration script complete and tested
**Next:** Begin Phase A migration (low-risk test group)
