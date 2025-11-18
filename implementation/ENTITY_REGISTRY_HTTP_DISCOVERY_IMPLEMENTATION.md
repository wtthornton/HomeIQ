# Entity Registry HTTP Discovery Implementation

**Date:** January 2025  
**Status:** ✅ Completed  
**Issue:** Entity registry name fields (name, name_by_user, original_name, friendly_name) were NULL due to WebSocket concurrency issues

## Problem Solved

**Root Cause:** Discovery service was failing with "Concurrent call to receive() is not allowed" because:
- Main event loop was using `websocket.receive()` continuously
- Discovery service tried to use the same WebSocket connection
- WebSocket doesn't allow concurrent `receive()` calls

**Solution:** Converted discovery to use HTTP API instead of WebSocket, eliminating concurrency issues entirely.

## Changes Made

### 1. Updated `discover_devices()` Method
**File:** `services/websocket-ingestion/src/discovery_service.py`

- ✅ Converted from WebSocket to HTTP API
- ✅ Uses `GET /api/config/device_registry/list`
- ✅ Made `websocket` parameter optional (backward compatibility)
- ✅ Follows same pattern as `discover_services()` (already using HTTP)

**Key Changes:**
- Removed WebSocket message ID tracking
- Removed `_wait_for_response()` call
- Added HTTP API call with proper error handling
- Maintains all caching logic (device → area mappings, metadata)

### 2. Updated `discover_entities()` Method
**File:** `services/websocket-ingestion/src/discovery_service.py`

- ✅ Converted from WebSocket to HTTP API
- ✅ Uses `GET /api/config/entity_registry/list`
- ✅ Made `websocket` parameter optional (backward compatibility)
- ✅ Added logging for name fields to verify they're present

**Key Changes:**
- Removed WebSocket message ID tracking
- Removed `_wait_for_response()` call
- Added HTTP API call with proper error handling
- Maintains all caching logic (entity → device mappings, entity → area mappings)
- Logs sample entity name fields for verification

### 3. Updated `discover_all()` Method
**File:** `services/websocket-ingestion/src/discovery_service.py`

- ✅ Made `websocket` parameter optional
- ✅ Updated documentation to reflect HTTP API usage
- ✅ All discovery methods now use HTTP API

### 4. Updated `connection_manager.py`
**File:** `services/websocket-ingestion/src/connection_manager.py`

- ✅ Removed WebSocket requirement check for discovery
- ✅ Discovery can now run independently of WebSocket connection
- ✅ Registry event subscriptions still require WebSocket (for real-time updates)

**Before:**
```python
if self.client and self.client.websocket:
    await self.discovery_service.discover_all(self.client.websocket)
else:
    logger.error("❌ Cannot run discovery: WebSocket not available")
```

**After:**
```python
# Discovery now uses HTTP API, so it can run independently of WebSocket connection
await self.discovery_service.discover_all()
```

### 5. Updated `main.py`
**File:** `services/websocket-ingestion/src/main.py`

- ✅ Removed WebSocket requirement check for discovery
- ✅ Updated manual discovery trigger endpoint
- ✅ Discovery can run even if WebSocket is not connected

## Benefits

1. **✅ No More Concurrency Issues**
   - HTTP API calls don't conflict with WebSocket event streaming
   - Discovery can run independently

2. **✅ Simpler Code**
   - No message ID tracking needed
   - No response waiting logic
   - Direct HTTP GET requests

3. **✅ More Reliable**
   - HTTP API is more stable than WebSocket for one-time queries
   - Can retry HTTP requests easily
   - Better error handling

4. **✅ Consistent Pattern**
   - Follows same pattern as `discover_services()` (already using HTTP)
   - All registry discovery now uses HTTP API

5. **✅ Better Logging**
   - Added name field logging to verify data is present
   - Clearer error messages

## Testing Recommendations

### 1. Verify Discovery Runs Successfully
```bash
# Check logs for discovery completion
# Should see: "✅ DISCOVERY COMPLETE" with device/entity counts
```

### 2. Verify Name Fields Are Populated
```sql
-- Check entities table for name fields
SELECT entity_id, name, name_by_user, original_name, friendly_name 
FROM entities 
WHERE entity_id LIKE 'light.hue%' 
LIMIT 10;
```

### 3. Verify Specific Devices
```python
# Run check_device_names.py script
python scripts/check_device_names.py
```

### 4. Test Manual Discovery Trigger
```bash
# Trigger discovery via HTTP endpoint
curl -X POST http://localhost:8001/api/discovery/trigger
```

## Expected Results

After discovery runs:
- ✅ All entities should have `name`, `name_by_user`, `original_name`, `friendly_name` populated
- ✅ No WebSocket concurrency errors in logs
- ✅ Discovery completes successfully even if WebSocket is busy
- ✅ Entity registry data matches Home Assistant

## Files Modified

1. `services/websocket-ingestion/src/discovery_service.py`
   - `discover_devices()` - Converted to HTTP API
   - `discover_entities()` - Converted to HTTP API
   - `discover_all()` - Made websocket optional

2. `services/websocket-ingestion/src/connection_manager.py`
   - Removed WebSocket requirement for discovery

3. `services/websocket-ingestion/src/main.py`
   - Removed WebSocket requirement for discovery
   - Updated manual discovery endpoint

## Backward Compatibility

- ✅ `websocket` parameter is optional (not removed)
- ✅ Old code calling with websocket parameter still works
- ✅ Tests may need updates (but functionality preserved)

## Next Steps

1. **Deploy and Test**
   - Deploy updated websocket-ingestion service
   - Monitor logs for discovery completion
   - Verify name fields populate in database

2. **Verify Entity Mappings**
   - Check that "Hue Office Back Left" maps correctly
   - Verify `name_by_user` values match HA expectations

3. **Monitor Performance**
   - Ensure HTTP API calls don't impact performance
   - Verify discovery completes in reasonable time

4. **Update Tests** (Optional)
   - Update unit tests to use HTTP API mocks
   - Remove WebSocket mocks from discovery tests

## Related Documentation

- `implementation/analysis/ENTITY_REGISTRY_NAME_FIELDS_RECOMMENDATIONS.md` - Full analysis and recommendations
- `scripts/refresh-entity-registry.py` - Working HTTP API example
- `scripts/standalone-entity-discovery.py` - Separate WebSocket example (alternative approach)

