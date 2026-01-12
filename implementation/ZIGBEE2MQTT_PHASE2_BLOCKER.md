# Zigbee2MQTT Devices Fix - Phase 2 Blocker

**Date:** 2026-01-12  
**Phase:** 2 - Fix device-intelligence-service  
**Status:** ⚠️ BLOCKED - Database Schema Migration Issue

## Summary

Phase 2 identified and attempted to fix the database schema mismatch blocking device storage. The migration cannot be completed due to database access/permission issues.

## Root Cause

The `device-intelligence-service` database schema is missing Zigbee2MQTT-specific columns that the code expects:
- `lqi`, `lqi_updated_at`
- `availability_status`, `availability_updated_at`
- `battery_level`, `battery_low`, `battery_updated_at`
- `device_type`, `source`

## Discovery Status

- ✅ **Service Healthy**: All dependencies connected (MQTT, HA, SQLite, Redis)
- ✅ **Discovery Working**: Successfully finds 101 devices
- ❌ **Storage Failing**: Cannot store devices due to schema mismatch
- ❌ **Error**: `(sqlite3.OperationalError) table devices has no column named lqi`

## Attempted Solutions

### 1. Migration Script (Failed)
- **Script**: `services/device-intelligence-service/scripts/migrate_add_zigbee_fields.py`
- **Issue**: Script not available in container (not copied during build)
- **Attempted**: Running script directly - script path not found

### 2. Direct SQL Migration (Failed)
- **Method**: SQL ALTER TABLE commands via Python sqlite3
- **Issue**: Database file is read-only when accessed via `docker exec`
- **Error**: `sqlite3.OperationalError: attempt to write a readonly database`
- **Attempted**: As root user and as appuser (uid 1001) - both failed

### 3. API Endpoint (Failed)
- **Endpoint**: `POST /api/database/recreate-tables`
- **Issue**: Endpoint returns 500 Internal Server Error
- **Status**: Cannot recreate tables via API

## Current Blocker

**Unable to modify database schema** due to:
1. Migration script not available in container
2. Database file permissions preventing direct SQL modifications
3. Recreate-tables API endpoint failing

## Recommended Next Steps

### Option 1: Fix Recreate-Tables Endpoint (Preferred)
1. Investigate why `/api/database/recreate-tables` returns 500 error
2. Check service logs for error details
3. Fix the endpoint or underlying `recreate_tables()` function
4. Use endpoint to recreate tables with correct schema

### Option 2: Manual Database Migration
1. Stop the service
2. Copy migration script into container or run externally
3. Run migration script with proper permissions
4. Restart service

### Option 3: Database File Access
1. Check database file permissions in container
2. Verify data directory mount/volume configuration
3. Fix permissions to allow schema modifications
4. Run migration script

### Option 4: Code Fix (If Schema Already Correct)
1. Verify SQLAlchemy models match actual database schema
2. If models have columns but database doesn't, check initialization
3. Ensure database initialization runs migrations automatically

## Verification Needed

1. Check service logs for recreate-tables endpoint error details
2. Verify database file location and permissions in container
3. Check if SQLAlchemy models include Zigbee columns
4. Verify database initialization/migration process

## Related Files

- `services/device-intelligence-service/scripts/migrate_add_zigbee_fields.py`
- `services/device-intelligence-service/src/core/database.py`
- `services/device-intelligence-service/src/models/database.py`
- `services/device-intelligence-service/src/api/database_management.py`
- `implementation/analysis/ZIGBEE2MQTT_DEVICES_REVIEW_AND_PLAN.md`
