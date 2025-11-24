# Team Tracker Database Query Fix

**Date:** January 2025  
**Status:** ✅ Completed  
**Issue:** Team Tracker detection was querying wrong database

## Root Cause

The Team Tracker detection was querying the `device-intelligence-service` database's `DeviceEntity` table, but entities are actually stored in the `data-api` service's `Entity` table.

### Architecture

- **data-api** (Port 8006): Stores entities in SQLite `entities` table - this is where Home Assistant entities are actually stored
- **device-intelligence-service** (Port 8028): Has `DeviceEntity` table but it's not populated with all entities

## Solution

### 1. Created Data API Client

**File:** `services/device-intelligence-service/src/clients/data_api_client.py`

- Simple HTTP client to query data-api service
- Supports filtering by domain, platform, device_id, area_id
- Includes retry logic and error handling

### 2. Updated Detection Endpoint

**File:** `services/device-intelligence-service/src/api/team_tracker_router.py`

**Changes:**
- Now queries `data-api` service for entities instead of local database
- Falls back to local database if data-api is unavailable
- Handles both dict (from API) and object (from local DB) formats
- Improved error handling and logging

**Key Changes:**
```python
# Query entities from data-api (where they are actually stored)
data_api_client = DataAPIClient()
all_sensor_entities = await data_api_client.fetch_entities(
    domain="sensor",
    limit=10000
)

# Filter for Team Tracker entities using multiple strategies
team_sensors = []
for entity in all_sensor_entities:
    # Check platform and entity_id patterns
    ...
```

### 3. Updated Debug Endpoint

**File:** `services/device-intelligence-service/src/api/team_tracker_router.py`

- Now queries data-api for platform debug information
- Falls back to local database if data-api unavailable
- Returns source information in response

## Testing

1. **Test Detection:**
   ```bash
   curl -X POST http://localhost:8028/api/team-tracker/detect \
     -H "Authorization: Bearer $API_KEY"
   ```

2. **Test Debug Endpoint:**
   ```bash
   curl http://localhost:8028/api/team-tracker/debug/platforms \
     -H "Authorization: Bearer $API_KEY"
   ```

## Expected Results

- Detection should now find Team Tracker entities if they exist in Home Assistant
- Debug endpoint shows actual platform values from data-api
- Fallback to local database if data-api is unavailable
- Better error messages if data-api is unreachable

## Files Modified

1. `services/device-intelligence-service/src/clients/data_api_client.py` (NEW)
2. `services/device-intelligence-service/src/api/team_tracker_router.py` (UPDATED)

## Next Steps

1. Deploy and test with actual Home Assistant instance
2. Verify Team Tracker entities are detected
3. Monitor logs for any data-api connection issues

