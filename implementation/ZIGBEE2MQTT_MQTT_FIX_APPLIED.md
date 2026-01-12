# Zigbee2MQTT MQTT Fix Applied

**Date:** 2026-01-12  
**Issue:** MQTT messages not being processed  
**Root Cause:** Event loop error in MQTT callback  
**Status:** ✅ Fix Applied

## Root Cause Identified

Error in logs:
```
❌ Error handling MQTT message: no running event loop
```

### Problem
The `_on_message` callback runs in the MQTT client thread (paho-mqtt library thread), but was trying to use `asyncio.create_task()` which requires the async event loop. Since the callback runs in a different thread, there's no event loop available.

## Fix Applied

Changed `_on_message` callback in `services/device-intelligence-service/src/clients/mqtt_client.py`:

### Before:
```python
# Handle message based on topic
asyncio.create_task(self._handle_message(topic, data))
```

### After:
```python
# Store event loop in connect() method
self.event_loop = asyncio.get_event_loop()

# In _on_message callback:
if self.event_loop and self.event_loop.is_running():
    asyncio.run_coroutine_threadsafe(self._handle_message(topic, data), self.event_loop)
```

## Changes Made

1. Added `event_loop` attribute to store the event loop reference
2. Store event loop in `connect()` method
3. Use `asyncio.run_coroutine_threadsafe()` instead of `asyncio.create_task()`
4. Added error handling if event loop not available

## Expected Result

- MQTT messages should now be processed correctly
- Zigbee2MQTT devices should be received and stored
- "📱 Received X devices from Zigbee2MQTT bridge" logs should appear
- Devices with `source='zigbee2mqtt'` should appear in database
