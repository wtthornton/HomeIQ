# Zigbee2MQTT Devices Fix - Phase 2 Final Summary

**Date:** 2026-01-12  
**Phase:** 2 - Fix device-intelligence-service  
**Status:** ⚠️ BLOCKED - Container Restart Loop

## Executive Summary

Phase 2 identified the root cause (database schema mismatch) but hit a blocker when attempting to fix it. Deleting the database file caused the container to enter a restart loop, preventing the service from starting.

## Key Findings

### ✅ Root Cause Identified
- **Problem**: Database schema missing Zigbee columns (`lqi`, `source`, `battery_level`, etc.)
- **Code Status**: SQLAlchemy models **already include** Zigbee columns (lines 47-56 in `database.py`)
- **Issue**: Database file has old schema, code expects new schema

### ✅ Discovery Working
- Service successfully discovers 101 devices
- MQTT and HA connections working
- All dependencies healthy

### ❌ Storage Blocked
- Cannot store devices due to schema mismatch
- Error: `table devices has no column named lqi`
- 0 devices stored despite successful discovery

## Attempted Solutions

1. **Migration Script**: Script exists but not available in container
2. **Direct SQL**: Database file read-only (permission issues)
3. **Recreate-Tables API**: Returns 500 error
4. **Delete Database**: Caused container restart loop

## Current Blocker

**Container Restart Loop**: After deleting database file
- Error: `unable to open database file`
- Container crashes immediately on startup
- Status: "Restarting (3)"
- Volume: `homeiq_device_intelligence_data` at `/app/data`

## Recommended Next Steps

### Option 1: Restore and Use Migration Script (Recommended)
1. Restore original database file from volume backup
2. Copy migration script into container
3. Run migration script as appuser
4. Restart service

### Option 2: Fix Container Startup
1. Access Docker volume directly
2. Create database file with correct schema manually
3. Set correct permissions
4. Restart container

### Option 3: Use Recreate-Tables Endpoint
1. Fix the `/api/database/recreate-tables` endpoint (500 error)
2. Use endpoint to recreate tables with correct schema
3. Trigger discovery refresh

### Option 4: Rebuild Container
1. Ensure latest code with Zigbee columns is in container
2. Rebuild container image
3. Start fresh with correct schema from initialization

## Technical Details

### Database Configuration
- **Volume**: `homeiq_device_intelligence_data` → `/app/data`
- **Database File**: `./data/device_intelligence.db`
- **Service User**: `appuser` (uid 1001)
- **File Owner**: Was `root:root` (caused permission issues)

### SQLAlchemy Models
The models in `services/device-intelligence-service/src/models/database.py` include:
- ✅ `lqi`, `lqi_updated_at`
- ✅ `availability_status`, `availability_updated_at`
- ✅ `battery_level`, `battery_low`, `battery_updated_at`
- ✅ `device_type`, `source`

### Database Initialization
The `initialize_database()` function in `database.py` should:
1. Create data directory if missing
2. Create tables using `Base.metadata.create_all`
3. This should create tables with correct schema from models

## Lessons Learned

1. **Code is correct**: Models already include Zigbee columns
2. **Schema mismatch**: Database file has old schema
3. **Permission issues**: Database file owned by root, service runs as appuser
4. **Restart loop**: Deleting database file prevents container startup
5. **Migration needed**: Need safe way to update schema without breaking service

## Related Files

- `services/device-intelligence-service/src/models/database.py` - SQLAlchemy models (lines 47-56)
- `services/device-intelligence-service/src/core/database.py` - Database initialization
- `services/device-intelligence-service/scripts/migrate_add_zigbee_fields.py` - Migration script
- `implementation/analysis/ZIGBEE2MQTT_DEVICES_REVIEW_AND_PLAN.md` - Original plan
