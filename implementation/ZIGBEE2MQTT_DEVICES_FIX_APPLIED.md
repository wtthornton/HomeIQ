# Zigbee2MQTT Devices Fix - Applied

**Date:** January 14, 2026  
**Issue:** Zigbee2MQTT devices not appearing in HomeIQ Dashboard  
**Status:** Fix Applied - Service Restart Required

## Root Cause Analysis

1. **Integration field was null**: All devices had `integration: null` because:
   - Config entries discovery requires websocket, but `discover_all()` may run without it
   - Integration resolution from config entries wasn't working

2. **Zigbee identification logic flaw**: The code only checked devices with `integration == "mqtt"` (line 714), but since integration was null, Zigbee devices were never identified.

3. **No HTTP API fallback**: Device discovery required websocket, and if unavailable, returned 0 devices.

## Fixes Applied

### 1. Fixed Zigbee Device Identification Logic
**File:** `services/websocket-ingestion/src/discovery_service.py`

**Changes:**
- Reordered identification methods to check device identifiers FIRST (works even when integration is null)
- Added support for identifying Zigbee devices by:
  1. **IEEE address patterns** in identifiers (0x followed by hex digits)
  2. **Zigbee/IEEE keywords** in identifiers
  3. **Config entry sharing** with Zigbee bridge (if available)
  4. **Via device relationship** to Zigbee bridge (if integration already resolved)

**Key Change:**
```python
# BEFORE: Only checked devices with integration == "mqtt"
if integration != "mqtt":
    continue

# AFTER: Check identifiers first, even if integration is null
identifiers = device.get("identifiers", [])
for identifier in identifiers:
    # Check for IEEE address patterns, zigbee keywords, etc.
    if is_zigbee_pattern(identifier):
        device["integration"] = "zigbee2mqtt"
```

### 2. Added HTTP API Fallback for Device Discovery
**File:** `services/websocket-ingestion/src/discovery_service.py`

**Changes:**
- Added `_discover_devices_http()` method that uses `/api/config/device_registry/list` endpoint
- Updated `discover_devices()` to try WebSocket first, then fall back to HTTP API
- Ensures device discovery works even when websocket isn't available

**Key Change:**
```python
# Try WebSocket first (preferred)
if websocket:
    devices = await self._discover_devices_websocket(websocket)
    if devices:
        return devices

# Fallback to HTTP API
devices = await self._discover_devices_http()
return devices
```

## Next Steps

### 1. Restart websocket-ingestion Service
The service needs to be restarted for the code changes to take effect:

```powershell
# If using Docker Compose
docker-compose restart websocket-ingestion

# Or if running directly
# Restart the service process
```

### 2. Trigger Device Discovery
After restart, trigger discovery to update devices:

```powershell
Invoke-RestMethod -Uri "http://localhost:8001/api/v1/discovery/trigger" -Method Post
```

### 3. Verify Zigbee Devices
Check if Zigbee devices are now identified:

```powershell
# Check for Zigbee2MQTT devices
$response = Invoke-RestMethod -Uri "http://localhost:8006/api/devices?limit=1000"
$zigbeeDevices = $response.devices | Where-Object { $_.integration -eq "zigbee2mqtt" }
Write-Host "Zigbee2MQTT devices: $($zigbeeDevices.Count)"
```

### 4. Verify in UI
1. Navigate to `http://localhost:3000/#devices`
2. Check if Zigbee devices appear
3. Filter by platform "zigbee2mqtt" (if available)
4. Filter by manufacturer containing "Zigbee" or device names

## Expected Results

After restart and discovery:
- ✅ Devices should have `integration: "zigbee2mqtt"` field populated
- ✅ Zigbee devices identified by IEEE addresses should be marked as Zigbee2MQTT
- ✅ Devices should appear in UI with correct integration/platform
- ✅ Platform filter should work for Zigbee2MQTT devices

## Testing Checklist

- [ ] Service restarted successfully
- [ ] Discovery triggered successfully (devices_discovered > 0)
- [ ] Zigbee devices have integration="zigbee2mqtt" in API
- [ ] Zigbee devices appear in UI
- [ ] Platform filter works for Zigbee2MQTT
- [ ] Device details show correct integration

## Related Files

- `services/websocket-ingestion/src/discovery_service.py` - Main fix location
- `services/websocket-ingestion/src/api/routers/discovery.py` - Discovery trigger endpoint
- `services/data-api/src/devices_endpoints.py` - Device query endpoint
- `services/health-dashboard/src/components/tabs/DevicesTab.tsx` - UI device display

## Notes

- The fix works even when config entries aren't discovered (identifies by identifiers)
- HTTP API fallback ensures discovery works without websocket
- Existing devices in database will be updated on next discovery
- New devices will be automatically identified as Zigbee if they match patterns
