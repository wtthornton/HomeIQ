# Zigbee2MQTT Fix - Final Status

**Date:** 2026-01-12  
**Issue:** Zigbee2MQTT devices not appearing in device list  
**Status:** ✅ Fix Applied - Verifying Results

## Fixes Applied

### 1. Database Schema (Phase 2) ✅
- Fixed database schema mismatch
- All Zigbee columns present
- Service storing devices correctly

### 2. MQTT Event Loop Fix ✅
- **Problem**: `asyncio.create_task()` called from MQTT callback thread (no event loop)
- **Error**: "no running event loop"
- **Fix**: Use `asyncio.run_coroutine_threadsafe()` with stored event loop
- **Change**: Store event loop using `asyncio.get_running_loop()` in `connect()` method

## Code Changes

**File**: `services/device-intelligence-service/src/clients/mqtt_client.py`

1. Added `event_loop` attribute to store event loop reference
2. Store event loop in `connect()` using `asyncio.get_running_loop()`
3. Changed `_on_message` callback to use `asyncio.run_coroutine_threadsafe()`

## Verification Steps

1. ✅ Service restarted
2. ⏳ Check logs for "📱 Received X devices from Zigbee2MQTT bridge"
3. ⏳ Verify Zigbee devices in database (source='zigbee2mqtt')
4. ⏳ Check dashboard for Zigbee devices

## Expected Outcome

- MQTT messages should now be processed
- Zigbee2MQTT devices should be received and stored
- Devices should appear in dashboard with source='zigbee2mqtt'
