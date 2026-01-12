# Zigbee2MQTT Devices Fix - Phase 2 Status Summary

**Date:** 2026-01-12  
**Phase:** 2 - Fix device-intelligence-service  
**Status:** ⚠️ Container Restart Loop After Database Deletion

## Summary

Phase 2 attempted to fix the database schema by deleting the old database file so the service would recreate it with the correct schema. However, deleting the database file caused the container to enter a restart loop because it cannot create/open the database file on startup.

## Progress Made

1. ✅ **Identified Root Cause**: Database schema missing Zigbee columns
2. ✅ **Found Solution**: SQLAlchemy models already include Zigbee columns (lines 47-56 in database.py)
3. ✅ **Attempted Fix**: Deleted database file to force recreation with correct schema
4. ❌ **New Issue**: Container enters restart loop - "unable to open database file"

## Current Blocker

**Container Restart Loop**: After deleting the database file, the container cannot start because:
- Error: `sqlite3.OperationalError: unable to open database file`
- Container status: "Restarting (3)" - crashes immediately on startup
- Cannot access container to create data directory (container is stopped/crashing)

## Analysis

The database initialization code in `database.py` should create the data directory automatically:
```python
db_dir = os.path.dirname(db_path)
if db_dir:
    os.makedirs(db_dir, exist_ok=True)
```

However, the service is crashing before it can create the directory, suggesting:
1. The data directory might have been deleted along with the database file
2. There may be a permissions issue preventing directory creation
3. The container might need the directory to exist before startup

## Recommended Next Steps

1. **Restore Original Database**: Since we can't easily fix the restart loop, consider:
   - Restore the database file from backup if available
   - OR manually create the database with correct schema using migration script
   
2. **Alternative Approach**: Instead of deleting the database:
   - Use ALTER TABLE commands to add missing columns
   - Run migration script with proper permissions
   - Use recreate-tables endpoint (if it can be fixed)

3. **Fix Container Startup**: 
   - Check if data directory is a volume mount
   - Create data directory with correct permissions
   - Ensure container can create database file on startup

## Key Learnings

- SQLAlchemy models already include Zigbee columns (code is correct)
- Database file had old schema (mismatch between code and database)
- Deleting database file caused container restart loop
- Need better approach to schema migration

## Related Files

- `services/device-intelligence-service/src/models/database.py` - Models with Zigbee columns
- `services/device-intelligence-service/src/core/database.py` - Database initialization
- `services/device-intelligence-service/scripts/migrate_add_zigbee_fields.py` - Migration script
