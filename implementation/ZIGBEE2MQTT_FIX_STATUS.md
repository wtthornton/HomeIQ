# Zigbee2MQTT Devices Fix - Status Update

**Date:** January 14, 2026  
**Status:** Code Changes Applied - Service Rebuild Required

## Current Status

✅ **Code fixes applied** to `services/websocket-ingestion/src/discovery_service.py`:
1. Fixed Zigbee device identification to check identifiers first
2. Added HTTP API fallback for device discovery

⚠️ **Service needs rebuild** - Docker container is running old code

## Issue

The service was restarted but Docker is using the old image. The code changes are in the source files but haven't been built into a new Docker image.

## Next Steps

### Option 1: Rebuild Docker Image (Recommended)
```powershell
# Rebuild the websocket-ingestion service
docker-compose build websocket-ingestion

# Restart with new image
docker-compose up -d websocket-ingestion
```

### Option 2: If using volume mounts (code changes should be live)
```powershell
# Just restart to pick up code changes
docker-compose restart websocket-ingestion

# Wait for service to start
Start-Sleep -Seconds 10

# Trigger discovery
Invoke-RestMethod -Uri "http://localhost:8001/api/v1/discovery/trigger" -Method Post
```

## Verification After Rebuild

1. **Check logs for HTTP API fallback:**
   ```powershell
   docker logs homeiq-websocket --tail 50 | Select-String -Pattern "HTTP API|Fetching devices|Retrieved.*devices"
   ```

2. **Trigger discovery:**
   ```powershell
   Invoke-RestMethod -Uri "http://localhost:8001/api/v1/discovery/trigger" -Method Post
   ```

3. **Verify Zigbee devices:**
   ```powershell
   $response = Invoke-RestMethod -Uri "http://localhost:8006/api/devices?limit=1000"
   $zigbeeDevices = $response.devices | Where-Object { $_.integration -eq "zigbee2mqtt" }
   Write-Host "Zigbee2MQTT devices: $($zigbeeDevices.Count)"
   ```

## Expected Log Messages After Fix

After rebuild, you should see:
- `"Attempting HTTP API for device discovery (fallback)"`
- `"🔗 Fetching devices from HTTP API: http://.../api/config/device_registry/list"`
- `"✅ Retrieved X devices via HTTP API"`
- `"✅ Identified Zigbee device: ..."` (for Zigbee devices)

## Current Logs Show

- `"⚠️  No WebSocket provided - skipping device discovery"` - This is expected
- **Missing:** HTTP API fallback messages - This indicates old code is running

## Code Changes Summary

1. **Zigbee Identification Fix** (lines ~708-757):
   - Now checks device identifiers FIRST (works even when integration is null)
   - Identifies Zigbee devices by IEEE address patterns, Zigbee keywords, config_entry sharing

2. **HTTP API Fallback** (lines ~83-135):
   - Added `_discover_devices_http()` method
   - Updated `discover_devices()` to try WebSocket first, then HTTP API
   - Uses `/api/config/device_registry/list` endpoint

## Files Modified

- `services/websocket-ingestion/src/discovery_service.py`
  - Added HTTP API fallback method
  - Fixed Zigbee identification logic order
