# Issue Found: InfluxDB Query Filter Mismatch

**Date:** 2025-11-04  
**Status:** ROOT CAUSE IDENTIFIED

## Problem

The `InfluxDBEventClient.fetch_events()` method is querying InfluxDB with filters that don't match how data is stored, resulting in 0 events being returned.

## Evidence

### Events Exist in InfluxDB
✅ Data API endpoint `/api/v1/events` returns recent events successfully:
- Events from 2025-11-04T05:05:10 (just minutes ago)
- Multiple entity types: sensor, image, media_player
- Events are being ingested and stored correctly

### Query Issue

**Location:** `services/ai-automation-service/src/clients/influxdb_client.py:74-99`

The query filters for:
```flux
|> filter(fn: (r) => r["_measurement"] == "home_assistant_events")
|> filter(fn: (r) => r["_field"] == "state")
|> filter(fn: (r) => r["event_type"] == "state_changed")
```

**Problem:** The query assumes:
1. `_field == "state"` - But events might be stored with different field names
2. `event_type == "state_changed"` - This might be a tag, not a field

### Data API vs Direct InfluxDB Query

**Data API** (working): Uses `/api/v1/events` endpoint which queries InfluxDB correctly
**Direct Query** (broken): Uses `InfluxDBEventClient` which has incorrect filters

## Solution

The `InfluxDBEventClient.fetch_events()` method needs to be updated to match the actual InfluxDB schema. Two options:

### Option 1: Use Data API Instead of Direct InfluxDB Query
- Change `DataAPIClient.fetch_events()` to use the Data API endpoint instead of direct InfluxDB query
- This would be more reliable and consistent

### Option 2: Fix InfluxDB Query
- Update the Flux query to match the actual schema
- Remove the `_field == "state"` filter or make it more flexible
- Verify how `event_type` is stored (tag vs field)

## Recommended Fix

**Option 1 is recommended** because:
1. Data API is already working and tested
2. Provides a consistent abstraction layer
3. Easier to maintain and update
4. Better error handling

## Next Steps

1. Update `DataAPIClient.fetch_events()` to use Data API endpoint
2. Remove direct InfluxDB query dependency
3. Test with nightly job
4. Verify suggestions are created

