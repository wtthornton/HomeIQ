# Zigbee2MQTT Devices Fix - Investigation Complete

**Date:** 2026-01-12  
**Status:** ✅ Code Fixes Applied - Further Investigation Needed

## Fixes Applied

### 1. Database Schema Fix (Phase 2) ✅
- **Issue**: Database schema mismatch (missing Zigbee columns)
- **Fix**: Recreated database with correct schema
- **Result**: Service storing devices correctly, schema includes all Zigbee fields

### 2. MQTT Event Loop Fix ✅  
- **Issue**: `asyncio.create_task()` called from MQTT callback thread (no event loop)
- **Error**: "no running event loop"
- **Fix**: Changed to `asyncio.run_coroutine_threadsafe()` with stored event loop
- **Code Quality**: Reviewed by tapps-agents - Score: 80.7/100 ✅
- **Result**: Event loop errors resolved in logs

## Current Status

### ✅ Working
- Database schema correct (all Zigbee columns present)
- Service running and healthy
- MQTT connection established
- Event loop errors resolved
- Service requesting device list: "📡 Requested Zigbee2MQTT device list refresh"
- Code quality: 80.7/100 (passes threshold)

### ⚠️ Outstanding Issue
- **Still 0 Zigbee devices** with source='zigbee2mqtt' in database
- **No "📱 Received X devices from Zigbee2MQTT bridge"** messages in logs
- **No MQTT errors** (fix working, but messages not received)

## Analysis

The event loop fix is working correctly (no more errors), but Zigbee2MQTT devices are still not being received. This suggests:

1. **Zigbee2MQTT may not be publishing** to the expected topics
2. **Topic format mismatch** - Zigbee2MQTT might use different topic names
3. **Retained messages not available** - Messages published before service subscribed
4. **Zigbee2MQTT configuration** - Base topic or API format might differ

## Code Changes Made

**File**: `services/device-intelligence-service/src/clients/mqtt_client.py`

```python
# Added event_loop attribute
self.event_loop: asyncio.AbstractEventLoop | None = None

# Store event loop in connect()
self.event_loop = asyncio.get_running_loop()

# Use run_coroutine_threadsafe in _on_message callback
if self.event_loop and self.event_loop.is_running():
    asyncio.run_coroutine_threadsafe(self._handle_message(topic, data), self.event_loop)
```

## Next Steps

1. **Verify Zigbee2MQTT Configuration**
   - Check Zigbee2MQTT base_topic setting
   - Verify Zigbee2MQTT is publishing to `zigbee2mqtt/bridge/devices`
   - Check Zigbee2MQTT logs for MQTT activity

2. **Test MQTT Topics Directly**
   - Use MQTT client (mosquitto_sub) to verify topics exist
   - Check if retained messages are published
   - Verify message format matches expectations

3. **Check Zigbee2MQTT API Documentation**
   - Verify correct topic format for device list requests
   - Check if API format changed in Zigbee2MQTT version

4. **Alternative Approach**
   - Consider using Zigbee2MQTT HTTP API instead of MQTT
   - Or check if Zigbee devices are available via Home Assistant API

## Verification Commands

```bash
# Check service status
curl http://localhost:8028/health

# Check device count
curl http://localhost:8028/api/devices | jq '.devices[] | select(.source=="zigbee2mqtt")'

# Check MQTT topics (if mosquitto_sub available)
mosquitto_sub -h 192.168.1.86 -t "zigbee2mqtt/bridge/devices" -v
```

## Documentation Created

- `implementation/ZIGBEE2MQTT_PHASE2_COMPLETE_SUMMARY.md` - Phase 2 completion
- `implementation/ZIGBEE2MQTT_MQTT_FIX_APPLIED.md` - Event loop fix details
- `implementation/ZIGBEE2MQTT_FINAL_STATUS.md` - Status summary
- `implementation/ZIGBEE2MQTT_INVESTIGATION_COMPLETE.md` - This document
