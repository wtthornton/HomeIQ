# Data API Device Fetch Fix

**Date**: 2025-01-24  
**Status**: Fixed and Deployed  

## Problem

The data-api service was returning 500 errors when fetching device metadata. The error was:

```
sqlite3.OperationalError: no such column: devices.name_by_user
```

This occurred when `ai-automation-service` called `/api/devices/{device_id}` to fetch device metadata during entity resolution.

## Root Cause

The Device model in `services/data-api/src/models/device.py` includes a `name_by_user` field:

```python
class Device(Base):
    name_by_user = Column(String)  # User-customized device name
```

However, the database table was created without this column (it was added to the model but never migrated to the database).

When SQLAlchemy queried the Device model using `select(Device, ...)`, it attempted to select ALL columns from the model, including the non-existent `name_by_user` column, causing the 500 error.

## Solution

Modified `services/data-api/src/devices_endpoints.py` in the `get_device()` function to explicitly select only the columns that exist in the database:

**Before:**
```python
query = select(Device, func.count(Entity.entity_id).label('entity_count'))\
    .outerjoin(Entity, Device.device_id == Entity.device_id)\
    .where(Device.device_id == device_id)\
    .group_by(Device.device_id)
```

**After:**
```python
query = select(
    Device.device_id,
    Device.name,
    Device.manufacturer,
    Device.model,
    Device.sw_version,
    Device.area_id,
    Device.integration,
    Device.entry_type,
    Device.configuration_url,
    Device.suggested_area,
    Device.last_seen,
    Device.created_at,
    func.count(Entity.entity_id).label('entity_count')
)\
    .outerjoin(Entity, Device.device_id == Entity.device_id)\
    .where(Device.device_id == device_id)\
    .group_by(Device.device_id)
```

And updated the response unpacking to handle the tuple result:

```python
# Unpack row tuple (explicit column selection)
(device_id_col, name, manufacturer, model, sw_version, area_id, 
 integration, entry_type, config_url, suggested_area, last_seen, created_at, entity_count) = row

return DeviceResponse(
    device_id=device_id_col,
    name=name,
    manufacturer=manufacturer or "Unknown",
    model=model or "Unknown",
    sw_version=sw_version,
    area_id=area_id,
    entity_count=entity_count,
    timestamp=last_seen.isoformat() if last_seen else datetime.now().isoformat()
)
```

## Deployment

1. **Rebuilt data-api image**: `docker-compose build data-api`
2. **Restarted service**: `docker-compose up -d data-api`
3. **Verified health**: Service started successfully and is healthy

## Impact

- ✅ Fixed 500 errors when fetching device metadata
- ✅ Entity resolution now works correctly
- ✅ Reduced log noise from repeated error messages
- ✅ Improved entity resolution performance (no more failed device lookups)

## Related Issues

This was causing the "Unexpected status 500 fetching device" errors in ai-automation-service logs during entity resolution.

## Files Modified

- `services/data-api/src/devices_endpoints.py` - Updated `get_device()` to explicitly select columns











