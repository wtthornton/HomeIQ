# Database Migration Fix Complete

**Date:** December 2, 2025  
**Status:** ✅ Complete

---

## Problem

The websocket-ingestion service was failing to store devices and entities with errors:
- `no such column: devices.labels`
- `no such column: entities.original_icon`

## Root Cause

Migration 008 (`008_add_ha_2025_attributes.py`) existed but had not been applied to the database. The database was at migration 007, but the code expected columns from migration 008.

## Solution

Applied migration 008 to add the missing columns:

### Entity Table
- ✅ `aliases` (JSON array)
- ✅ `original_icon` (String)
- ✅ `labels` (JSON array)
- ✅ `options` (JSON object)
- ✅ Index: `idx_entity_name_by_user`

### Device Table
- ✅ `labels` (JSON array)
- ✅ `serial_number` (String)
- ✅ `model_id` (String)

## Migration Status

**Before:**
```
Current migration: 007
```

**After:**
```
Current migration: 008 (head)
```

## Verification

- ✅ Migration 008 applied successfully
- ✅ No more "no such column" errors in logs
- ✅ Websocket service is healthy
- ✅ Devices and entities can now be stored successfully

## Commands Used

```bash
# Check current migration
docker compose exec data-api alembic current

# Apply migration
docker compose exec data-api alembic upgrade head

# Restart websocket service
docker compose restart websocket-ingestion
```

---

**Last Updated:** December 2, 2025

