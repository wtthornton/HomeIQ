# Missing Entity Attributes Fix

**Date:** January 15, 2026  
**Issue:** Missing all the attributes from Home Assistant entity state_changed events  
**Status:** ✅ Fixed

## Problem Summary

Entity attributes (like `friendly_name`, `device_class`, `unit_of_measurement`, etc.) were not being stored in InfluxDB when processing `state_changed` events from Home Assistant.

## Root Cause

In `services/websocket-ingestion/src/influxdb_schema.py`, the code was looking for attributes at the top level of `event_data`:
```python
attributes = event_data.get("attributes", {})  # ❌ Wrong - attributes aren't here
```

However, in Home Assistant events, attributes are nested inside the state objects:
```python
event_data = {
    "new_state": {
        "state": "on",
        "attributes": {  # ✅ Attributes are here
            "friendly_name": "Living Room Light",
            "device_class": "light",
            ...
        }
    }
}
```

This affected three methods:
1. `_add_event_tags()` - Couldn't extract `device_class` for tagging
2. `_add_event_fields()` - Couldn't extract attributes to store in InfluxDB
3. `_categorize_event()` - Couldn't extract `device_class` for event categorization

## Solution

Added a new helper method `_extract_attributes()` that correctly extracts attributes from the nested state structure:

```python
def _extract_attributes(self, event_data: dict[str, Any]) -> dict[str, Any]:
    """
    Extract attributes from event data.
    
    Attributes are nested inside new_state.attributes (or old_state.attributes as fallback).
    """
    # First try to get attributes from top level (for backwards compatibility)
    attributes = event_data.get("attributes", {})
    
    # If not at top level, extract from new_state.attributes (preferred)
    new_state = event_data.get("new_state")
    if isinstance(new_state, dict) and "attributes" in new_state:
        attributes = new_state.get("attributes", {})
    # Fallback to old_state.attributes if new_state doesn't have attributes
    elif not attributes:
        old_state = event_data.get("old_state")
        if isinstance(old_state, dict) and "attributes" in old_state:
            attributes = old_state.get("attributes", {})
    
    return attributes if isinstance(attributes, dict) else {}
```

Updated all three methods to use this helper:
- `_add_event_tags()` - Now correctly extracts `device_class` from `new_state.attributes`
- `_add_event_fields()` - Now correctly stores attributes JSON in InfluxDB
- `_categorize_event()` - Now correctly categorizes events based on device_class

## Files Changed

1. **services/websocket-ingestion/src/influxdb_schema.py**
   - Added `_extract_attributes()` helper method
   - Updated `_add_event_tags()` to use the helper
   - Updated `_add_event_fields()` to use the helper
   - Updated `_categorize_event()` to use the helper
   - Removed duplicate `import json` statement at end of file

## Testing

### Manual Verification Steps

1. **Restart websocket-ingestion service** to apply the fix:
   ```powershell
   docker compose restart websocket-ingestion
   ```

2. **Wait for new events** - Attributes will only be stored for new `state_changed` events after the fix is applied

3. **Verify attributes in InfluxDB**:
   ```powershell
   # Query InfluxDB to check if attributes field contains data
   # Use InfluxDB UI at http://localhost:8086
   # Query: SELECT attributes FROM home_assistant_events WHERE time > now() - 1h LIMIT 10
   ```

4. **Check dashboard** - New events should show attributes when viewing devices

### Expected Behavior After Fix

- ✅ Attributes from `state_changed` events are extracted from `new_state.attributes`
- ✅ Attributes are stored as JSON string in InfluxDB `attributes` field
- ✅ `device_class` is correctly extracted and used as a tag
- ✅ Event categorization works correctly based on device_class

### Limitations

- **Historical data**: Events ingested before this fix will not have attributes. Only new events after the fix is applied will have attributes.
- **Entity Registry attributes**: This fix only affects attributes from `state_changed` events. Entity registry attributes (stored in SQLite) are handled separately and are not affected by this fix.

## Impact

### What This Fixes

- Entity attributes are now properly stored in InfluxDB
- Device classification works correctly (lighting, climate, security, etc.)
- Event categorization works based on device_class
- Future analytics on entity attributes will have data

### What This Doesn't Fix

- Historical events (before fix) still won't have attributes
- Entity registry metadata (stored in SQLite) is separate from this fix
- Dashboard display of attributes depends on how data-api queries InfluxDB (separate concern)

## Related Issues

- The dashboard queries entities from SQLite (entity registry), not InfluxDB (state events)
- For full attribute display, the dashboard would need to:
  1. Query entity registry from SQLite (basic entity info)
  2. Query latest state from InfluxDB (for current attributes)
  3. Merge the data for display

This fix ensures attributes are available in InfluxDB for step 2.

## Next Steps

1. ✅ **Fix Applied** - Attributes extraction corrected
2. ⏳ **Deploy** - Restart websocket-ingestion service
3. ⏳ **Monitor** - Verify new events have attributes in InfluxDB
4. 🔮 **Future Enhancement** - Dashboard could query latest attributes from InfluxDB to enrich entity display
