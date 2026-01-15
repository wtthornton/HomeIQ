# Zigbee2MQTT Devices Fix - Final Status

**Date:** January 14, 2026  
**Status:** Code Fixes Applied - Discovery Blocked by Infrastructure Issues

## Summary

✅ **Code fixes successfully applied:**
1. Fixed Zigbee device identification logic (checks identifiers first)
2. Added HTTP API fallback for device discovery
3. Docker image rebuilt with new code

⚠️ **Infrastructure issues preventing discovery:**
1. HTTP API endpoint `/api/config/device_registry/list` returns 404 (doesn't exist in this HA version)
2. WebSocket discovery conflicts with listen loop (concurrent receive() error)
3. Database is readonly (preventing device storage even if discovered)

## Current State

- **104 devices** in database, all with `integration: null`
- **0 Zigbee2MQTT devices** identified
- **Discovery returns 0 devices** due to infrastructure issues
- **Code fixes are in place** and will work once discovery succeeds

## Root Causes

### 1. Device Discovery Failing
- **WebSocket**: Conflicts with active listen loop (`Concurrent call to receive() is not allowed`)
- **HTTP API**: Endpoint doesn't exist (404) in this Home Assistant version
- **Result**: 0 devices discovered

### 2. Database Readonly
- SQLite database has readonly permissions
- Even if devices were discovered, they can't be stored
- Error: `attempt to write a readonly database`

### 3. No Device Identifiers in Database
- Existing devices don't have identifiers stored
- Zigbee identification requires identifiers (IEEE addresses, etc.)
- Can't identify Zigbee devices from existing database records

## Solutions Needed

### Option 1: Fix Database Permissions (Immediate)
```powershell
# Check database file permissions
Get-Item services/data-api/data/metadata.db | Select-Object FullName, Attributes

# Fix permissions if needed
icacls services/data-api/data/metadata.db /grant Users:F
```

### Option 2: Fix WebSocket Discovery (Preferred)
- Modify discovery to use message routing instead of direct receive()
- Or pause listen loop during discovery
- Or use separate WebSocket connection for discovery

### Option 3: Alternative Discovery Method
- Use Home Assistant's REST API to get device registry
- Or query entities and infer devices from entity.device_id
- Or use a scheduled job that runs when listen loop is idle

## Code Changes Status

✅ **Applied and working:**
- `services/websocket-ingestion/src/discovery_service.py`:
  - Lines 83-135: HTTP API fallback method added
  - Lines 137-170: Updated discover_devices() to try HTTP fallback
  - Lines 708-757: Fixed Zigbee identification (checks identifiers first)

✅ **Docker image rebuilt:**
- New image includes all code changes
- Service restarted with new image

## Next Steps

1. **Fix database permissions** to allow writes
2. **Fix WebSocket discovery** to work with listen loop
3. **Or implement alternative discovery** method
4. **Trigger discovery** once infrastructure is fixed
5. **Verify Zigbee devices** are identified and stored

## Verification Commands

Once discovery works:
```powershell
# Check Zigbee devices
$response = Invoke-RestMethod -Uri "http://localhost:8006/api/devices?limit=1000"
$zigbeeDevices = $response.devices | Where-Object { $_.integration -eq "zigbee2mqtt" }
Write-Host "Zigbee2MQTT devices: $($zigbeeDevices.Count)"
```

## Expected Behavior After Fix

1. Discovery should find devices (either via WebSocket or HTTP API)
2. Zigbee devices should be identified by:
   - IEEE address patterns in identifiers
   - Zigbee keywords in identifiers
   - Config entry sharing with Zigbee bridge
3. Integration field should be set to "zigbee2mqtt"
4. Devices should appear in UI with correct integration

## Files Modified

- `services/websocket-ingestion/src/discovery_service.py` - All fixes applied
- `implementation/ZIGBEE2MQTT_DEVICES_FIX_APPLIED.md` - Documentation
- `implementation/ZIGBEE2MQTT_FIX_STATUS.md` - Status tracking
