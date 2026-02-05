# Phase 2: asyncio-mqtt -> aiomqtt 2.4.0 Migration Guide

**Story:** PHASE2-004
**Status:** ✅ Complete
**Created:** February 5, 2026

---

## Overview

Automated migration tool for replacing asyncio-mqtt with aiomqtt 2.4.0.

### Breaking Changes

1. **Complete library replacement** - asyncio-mqtt deprecated, replaced by aiomqtt
2. **Package renamed** - `asyncio_mqtt` -> `aiomqtt`
3. **Requires paho-mqtt 2.1.0** as additional dependency
4. **Client API changes** (if code uses MQTT client)

---

## Migration Script

**Location:** `scripts/phase2-migrate-mqtt.py`

### Features

✅ **Automated Detection**
- Finds asyncio-mqtt usage in code
- Updates requirements.txt
- Adds paho-mqtt dependency

✅ **Safe Migration**
- Creates backups before making changes
- Dry-run mode to preview changes
- Rollback script generation
- Post-migration test validation

✅ **Code Migration** (if MQTT client used)
- Replaces `import asyncio_mqtt` with `import aiomqtt`
- Replaces `from asyncio_mqtt import` with `from aiomqtt import`
- Replaces `asyncio_mqtt.` with `aiomqtt.`

---

## Usage

### Single Service

```bash
# Dry run (preview changes)
python scripts/phase2-migrate-mqtt.py websocket-ingestion --dry-run

# Apply migration
python scripts/phase2-migrate-mqtt.py websocket-ingestion
```

### Batch Migration

```bash
# Migrate multiple services
python scripts/phase2-migrate-mqtt.py \
  --batch websocket-ingestion data-retention
```

---

## What the Script Does

### Step 1: Validate Service Structure

Checks for:
- Service directory exists
- `requirements.txt` exists

### Step 2: Check if Migration Needed

Skips if:
- Already has aiomqtt==2.4.0
- Does not use asyncio-mqtt

### Step 3: Create Backup

Creates `.migration_backup_mqtt_YYYYMMDD_HHMMSS/` with:
- `requirements.txt`
- `src/` directory (full copy)

### Step 4: Find MQTT Usage

Scans `src/**/*.py` for:
- `import asyncio_mqtt`
- `from asyncio_mqtt import`
- `asyncio_mqtt.`

**Note:** For websocket-ingestion and data-retention, no actual MQTT client code found.

### Step 5: Migrate Code (if needed)

**Before:**
```python
import asyncio_mqtt

async def connect_mqtt():
    async with asyncio_mqtt.Client("mqtt://localhost") as client:
        await client.subscribe("home/#")
```

**After:**
```python
import aiomqtt

async def connect_mqtt():
    async with aiomqtt.Client("mqtt://localhost") as client:
        await client.subscribe("home/#")
```

### Step 6: Update requirements.txt

**Before:**
```
asyncio-mqtt>=0.16.1,<0.17.0
```

**After:**
```
aiomqtt==2.4.0  # Phase 2 upgrade - MIGRATION from asyncio-mqtt (package renamed)
paho-mqtt==2.1.0  # Phase 2 upgrade - required by aiomqtt
```

### Step 7: Run Tests

Validates migration with:
```bash
pytest tests/ -v --tb=short
```

### Step 8: Create Rollback Script

Generates `rollback_mqtt_YYYYMMDD_HHMMSS.sh`

---

## Affected Services (3 total)

From `phase2-dependency-analysis.md`:

### CRITICAL Priority (1 service)
- ✅ `websocket-ingestion` (also has pytest-asyncio, influxdb)

### HIGH Priority (1 service)
- ✅ `data-retention` (also has pytest-asyncio, influxdb)

### LOW Priority (1 service)
- ✅ `ha-simulator` - **Already migrated to aiomqtt 2.4.0**

**Special Note:** websocket-ingestion and data-retention have asyncio-mqtt in requirements.txt but don't use MQTT client in code. Migration only updates requirements.txt.

---

## Migration Strategy

### ha-simulator
**Status:** ✅ Already migrated to aiomqtt 2.4.0
- No action needed

### data-retention
**Risk:** MEDIUM (HIGH priority service)
**Action:** Update requirements.txt only (no code changes)

```bash
python scripts/phase2-migrate-mqtt.py data-retention
```

### websocket-ingestion
**Risk:** VERY HIGH (CRITICAL service with 3 breaking changes)
**Action:** Update requirements.txt only (no code changes)
**Deployment:** Blue-green deployment, off-peak hours

```bash
# Deploy during off-peak hours with blue-green strategy
python scripts/phase2-migrate-mqtt.py websocket-ingestion
```

---

## Validation

### Post-Migration Checklist

For each service:

- [ ] ✅ requirements.txt has `aiomqtt==2.4.0`
- [ ] ✅ requirements.txt has `paho-mqtt==2.1.0`
- [ ] ✅ No references to `asyncio_mqtt` in code (if migration included code changes)
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
./rollback_mqtt_YYYYMMDD_HHMMSS.sh

# Option 2: Manual rollback
cd services/<service-name>
cp .migration_backup_mqtt_*/requirements.txt ./requirements.txt
rm -rf src
cp -r .migration_backup_mqtt_*/src ./src

# Rebuild service with old versions
docker-compose build <service-name>
docker-compose up -d <service-name>
```

---

## Common Issues

### Issue 1: Missing paho-mqtt Dependency

**Symptom:** Import error when starting service

**Cause:** paho-mqtt not installed (required by aiomqtt)

**Solution:**
```bash
# Ensure paho-mqtt is in requirements.txt
pip install paho-mqtt==2.1.0
```

### Issue 2: Import Errors

**Symptom:** `ModuleNotFoundError: No module named 'asyncio_mqtt'`

**Cause:** Code still references asyncio_mqtt

**Solution:**
```python
# Replace all occurrences
import asyncio_mqtt  # <- Remove
import aiomqtt  # <- Add
```

---

## Script Output Example

### Dry Run (No Code Changes)

```
============================================================
MQTT Migration Summary: websocket-ingestion
============================================================
[DRY RUN] - No changes made

Changes (2):
  [OK] requirements.txt: Added paho-mqtt==2.1.0 (required by aiomqtt)
  [OK] requirements.txt: Updated asyncio-mqtt -> aiomqtt==2.4.0
============================================================
```

### Actual Migration (With Code Changes)

```
============================================================
MQTT Migration Summary: some-service
============================================================

Changes (3):
  [OK] src/mqtt/client.py: Updated MQTT imports
  [OK] requirements.txt: Added paho-mqtt==2.1.0 (required by aiomqtt)
  [OK] requirements.txt: Updated asyncio-mqtt -> aiomqtt==2.4.0

Backup: services/some-service/.migration_backup_mqtt_20260205_123000

Running tests...
[OK] All tests passed (28 tests, 1.8s)
============================================================
```

---

## Next Steps

After completing MQTT migration:

1. ✅ Mark Story 4 as complete
2. 📋 Begin Story 5: influxdb3-python 0.17.0 Migration Script
3. 📋 Continue with remaining Phase 2 stories

---

## References

- **aiomqtt Documentation:** [https://sbtinstruments.github.io/aiomqtt/](https://sbtinstruments.github.io/aiomqtt/)
- **Migration Guide:** [asyncio-mqtt -> aiomqtt migration](https://github.com/sbtinstruments/aiomqtt#migrating-from-asyncio-mqtt)
- **Phase 2 Plan:** [phase2-implementation-plan.md](phase2-implementation-plan.md)
- **Service Dependencies:** [phase2-dependency-analysis.md](phase2-dependency-analysis.md)

---

**Status:** ✅ Migration script complete and tested
**Next:** Begin MQTT migration rollout (only 2 services need migration, ha-simulator already done)
