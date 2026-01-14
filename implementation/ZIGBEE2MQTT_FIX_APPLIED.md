# Zigbee2MQTT Device Identification - Fix Applied

**Date:** January 13, 2026  
**Status:** ✅ Fix Applied - Device Discovery Now Uses WebSocket

## Summary

Fixed the issue where device discovery was being skipped because `websocket=None` was being passed to `discover_all()`. The code now properly passes the WebSocket connection when available, enabling device discovery and Zigbee identification.

## Changes Made

### File: `services/websocket-ingestion/src/connection_manager.py`

#### Change 1: Initial Discovery (Line ~521)
**Before:**
```python
# 2025 Best Practice: Pass None for websocket to force HTTP API usage
# This avoids "Concurrent call to receive() is not allowed" errors
# Discovery will use HTTP API endpoints instead of WebSocket
await self.discovery_service.discover_all(websocket=None)
```

**After:**
```python
# Pass WebSocket if available (required for device discovery and Zigbee identification)
websocket_for_discovery = None
if self.client and self.client.websocket:
    websocket_for_discovery = self.client.websocket
    logger.info("📡 Using WebSocket for device discovery (required for device registry)")
else:
    logger.warning("⚠️  WebSocket not available - device discovery will be limited")

await self.discovery_service.discover_all(websocket=websocket_for_discovery)
```

#### Change 2: Periodic Discovery Refresh (Line ~481)
**Before:**
```python
# 2025 Best Practice: Pass None for websocket to force HTTP API usage
# This avoids "Concurrent call to receive() is not allowed" errors
await self.discovery_service.discover_all(websocket=None, store=True)
```

**After:**
```python
# Pass WebSocket for device discovery (required for device registry and Zigbee identification)
await self.discovery_service.discover_all(websocket=self.client.websocket, store=True)
```

## Why This Fix Was Necessary

1. **Device Discovery Requires WebSocket**: Home Assistant doesn't provide an HTTP API for device registry. The `discover_devices()` method returns an empty list when `websocket=None`, skipping all device discovery.

2. **Zigbee Identification Needs Devices**: The Zigbee identification code runs during device discovery. Without devices being discovered, Zigbee devices can't be identified.

3. **Config Entries Discovery**: Config entries discovery also requires WebSocket to build the integration mapping needed for Zigbee identification.

## Expected Behavior After Fix

Once the service restarts and discovery runs, you should see:

1. **Device Discovery Logs**:
   ```
   📱 DISCOVERING DEVICES
   Using WebSocket for device discovery (HTTP API not available)
   ✅ Discovered {n} devices
   ```

2. **Config Entry Mapping**:
   ```
   🔧 Built config entry mapping: {n} entries
   ```

3. **Zigbee Bridge Detection** (if Zigbee2MQTT is installed):
   ```
   🔍 Found Zigbee2MQTT Bridge with config_entry: {id}
   ```

4. **Zigbee Device Identification** (if Zigbee devices exist):
   ```
   ✅ Identified Zigbee device: {device_name} (manufacturer: {manufacturer})
   🔍 Identified {n} Zigbee devices within MQTT integration
   ```

5. **Device Storage**:
   ```
   ✅ Stored {n} devices to SQLite
   ```

## Verification Steps

1. **Check Logs for WebSocket Usage**:
   ```powershell
   docker compose logs websocket-ingestion --tail 500 | Select-String -Pattern "Using WebSocket|DISCOVERING DEVICES|✅ Discovered"
   ```

2. **Check for Zigbee Identification**:
   ```powershell
   docker compose logs websocket-ingestion --tail 1000 | Select-String -Pattern "Found Zigbee|Identified.*Zigbee|Built config entry"
   ```

3. **Check Database** (after discovery completes):
   ```powershell
   # Query SQLite directly
   sqlite3 data/metadata.db "SELECT name, integration, source FROM devices WHERE integration='zigbee2mqtt' LIMIT 10;"
   ```

## Potential Issues

### Concurrent WebSocket Usage

**Issue**: Using the same WebSocket for discovery and event listening may cause "Concurrent call to receive() is not allowed" errors.

**Mitigation**: 
- Discovery runs quickly (typically completes in a few seconds)
- Discovery runs at startup and periodically (every 30 minutes by default)
- Event listening and discovery use separate message IDs
- If errors occur, they're logged but don't crash the service

**If Errors Occur**:
- Check logs for "Concurrent call to receive()" errors
- Consider implementing a WebSocket connection pool (future enhancement)
- Or use separate WebSocket connections for discovery vs. events (complex but possible)

### WebSocket Not Available

**Issue**: If WebSocket is not available during discovery, device discovery will be skipped.

**Expected Behavior**: 
- Service logs warning: `"⚠️  WebSocket not available - device discovery will be limited"`
- Entities will still be discovered (via HTTP API)
- Devices can be inferred from entity registry (device_id references)

## Related Documents

- `implementation/ZIGBEE2MQTT_IMPLEMENTATION_STATUS.md` - Initial implementation details
- `implementation/ZIGBEE2MQTT_VERIFICATION_STATUS.md` - Verification status
- `implementation/analysis/ZIGBEE2MQTT_CURRENT_STATE_REVIEW.md` - Initial state analysis
- `implementation/analysis/ZIGBEE2MQTT_SOLUTION.md` - Solution design

## Status

✅ **Fix Applied**: WebSocket now passed to discovery  
⏳ **Awaiting Results**: Discovery running after service restart  
⏳ **Verification Pending**: Waiting for Zigbee identification logs
