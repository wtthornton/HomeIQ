# Zigbee2MQTT Devices Fix - Phase 2 Status

**Date:** 2026-01-12  
**Phase:** 2 - Fix device-intelligence-service  
**Status:** In Progress

## Summary

Phase 2 focuses on fixing the `device-intelligence-service` to properly store Zigbee2MQTT devices. The service discovery is working (finds 101 devices) but database schema mismatch prevents storage.

## Current Status

### ✅ Completed
1. **Service Health**: Service is healthy, all dependencies connected (MQTT, HA, SQLite, Redis)
2. **Discovery Working**: Discovery refresh successfully finds 101 devices
3. **API Endpoints**: Discovery API endpoints accessible (`/api/discovery/status`, `/api/discovery/refresh`)

### ❌ Blockers
1. **Database Schema Mismatch**: Service database still missing `lqi` column and other Zigbee fields
   - Error: `(sqlite3.OperationalError) table devices has no column named lqi`
   - Migration script exists but needs to run **inside the container**
   - Host database was migrated, but container uses separate database file

2. **No Devices Stored**: 0 devices in database despite discovery finding 101 devices
   - Discovery completes successfully
   - Storage fails due to schema mismatch

## Database Configuration

- **Database Path**: `./data/device_intelligence.db` (relative path in container)
- **Default Path**: `sqlite:///./data/device_intelligence.db`
- **Container Path**: `/app/data/device_intelligence.db` (per README)

## Migration Status

### Migration Script
- **Location**: `services/device-intelligence-service/scripts/migrate_add_zigbee_fields.py`
- **Status**: Script exists and works, but needs to run inside container
- **Columns to Add**: `lqi`, `lqi_updated_at`, `availability_status`, `availability_updated_at`, `battery_level`, `battery_low`, `battery_updated_at`, `device_type`, `source`

### Migration Execution
- **Host Database**: Migration completed (columns exist)
- **Container Database**: Migration not yet run (columns missing)
- **Action Required**: Run migration script inside container using `docker compose exec`

## Next Steps

1. ✅ Run migration script inside container: `docker compose exec device-intelligence-service python scripts/migrate_add_zigbee_fields.py`
2. ✅ Restart service after migration
3. ✅ Trigger discovery refresh
4. ⏳ Verify devices are stored (no schema errors)
5. ⏳ Verify Zigbee2MQTT devices appear in API response
6. ⏳ Check device count and integration field

## Discovery Status

- **Service Running**: True
- **HA Connected**: True
- **MQTT Connected**: True
- **Devices Discovered**: 101
- **Devices Stored**: 0 (blocked by schema error)
- **Errors**: 4 schema errors (all same: missing `lqi` column)

## Related Files

- `services/device-intelligence-service/scripts/migrate_add_zigbee_fields.py`
- `services/device-intelligence-service/src/core/database.py`
- `services/device-intelligence-service/src/models/database.py`
- `services/device-intelligence-service/src/core/discovery_service.py`
- `implementation/analysis/ZIGBEE2MQTT_DEVICES_REVIEW_AND_PLAN.md`
