# Discovery Testing Results

**Date:** January 2025  
**Status:** ⚠️ HTTP API Endpoints Not Available

## Test Results

### Entity Registry HTTP API
- **Endpoint:** `GET /api/config/entity_registry/list`
- **Result:** ❌ HTTP 404 - Not Found
- **Status:** Endpoint not available in this Home Assistant version

### Device Registry HTTP API  
- **Endpoint:** `GET /api/config/device_registry/list`
- **Result:** ❌ HTTP 404 - Not Found
- **Status:** Endpoint not available (expected - HA doesn't provide HTTP API for device registry)

## Findings

1. **Home Assistant Version Limitation**
   - The HTTP API endpoints for entity/device registry may not be available in all HA versions
   - These endpoints might require a newer HA version or specific configuration

2. **Current Implementation Status**
   - ✅ Code updated to use HTTP API for entities (when available)
   - ✅ Code falls back to WebSocket if HTTP API not available
   - ✅ Entity discovery can use WebSocket without concurrency issues if called before `listen()` loop starts

## Recommendations

### Option A: Use WebSocket Before Listen Loop (Recommended)
Since HTTP API isn't available, use WebSocket for discovery but call it **before** starting the `listen()` loop:

```python
# In connection_manager.py _on_connect():
# 1. Connect WebSocket
# 2. Authenticate
# 3. Run discovery (uses WebSocket, but no concurrency issue yet)
# 4. Start listen() loop (after discovery completes)
```

This avoids concurrency because discovery completes before the receive loop starts.

### Option B: Separate WebSocket Connection
Create a separate WebSocket connection just for discovery (like `standalone-entity-discovery.py` does).

### Option C: Check HA Version
Verify Home Assistant version and check if HTTP API endpoints are available in that version.

## Next Steps

1. **Verify HA Version**
   - Check what version of Home Assistant is running
   - Verify if HTTP API endpoints are available in that version

2. **Implement Option A**
   - Update `connection_manager.py` to run discovery before `listen()` loop
   - This should work without concurrency issues

3. **Test Discovery**
   - Verify discovery completes successfully
   - Check that name fields populate in database

## Current Code Status

- ✅ `discover_entities()` - Uses HTTP API, falls back to WebSocket
- ✅ `discover_devices()` - Uses WebSocket (no HTTP API available)
- ✅ `discover_all()` - Makes websocket optional
- ✅ `connection_manager.py` - Updated to call discovery without requiring websocket

The code is ready - we just need to ensure discovery runs before the listen loop starts, or use a separate WebSocket connection.

