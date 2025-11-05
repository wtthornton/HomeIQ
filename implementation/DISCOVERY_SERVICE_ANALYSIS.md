# Discovery Service Analysis - Device Count Issue

**Date:** November 5, 2025  
**Status:** Discovery Working, Storage Issues Identified

## Executive Summary

The discovery service **IS working correctly** and has discovered:
- ✅ **96 devices** from Home Assistant
- ✅ **17 areas** from Home Assistant
- ❌ **0 Zigbee devices** from Zigbee2MQTT (MQTT topic issue)

## Current Status

### Discovery Status (Latest)
```json
{
  "service_running": true,
  "ha_connected": true,
  "mqtt_connected": true,
  "devices_count": 96,
  "areas_count": 17,
  "last_discovery": null,
  "errors": ["Database schema error: missing device_class column"]
}
```

## Issues Identified

### 1. Database Schema Issue ⚠️ CRITICAL

**Problem:** Missing `device_class` column in database schema

**Error:**
```
sqlite3.OperationalError: no such column: devices.device_class
```

**Impact:** Devices are discovered but cannot be stored in database

**Solution:** 
- Run database migration to add missing column
- Or recreate database with updated schema
- See: `services/device-intelligence-service/DATABASE_UPDATES_GUIDE.md`

**Fix:**
```bash
curl -X POST http://localhost:8028/api/admin/database/recreate-tables
```

### 2. Zigbee2MQTT MQTT Topic Issues ⚠️

**Problem:** Not receiving Zigbee device messages from MQTT

**Issues Found:**

1. **Hardcoded Topics:** Code uses hardcoded `"zigbee2mqtt/bridge/devices"` instead of configurable `ZIGBEE2MQTT_BASE_TOPIC`
   - Location: `services/device-intelligence-service/src/clients/mqtt_client.py:177-184`
   - Should use: `settings.ZIGBEE2MQTT_BASE_TOPIC` (default: `"zigbee2mqtt"`)

2. **Missing Response Topic Subscription:**
   - When requesting device list: `zigbee2mqtt/bridge/request/device/list`
   - Response comes on: `zigbee2mqtt/bridge/response/device/list` (NOT `zigbee2mqtt/bridge/devices`)
   - Code only subscribes to `zigbee2mqtt/bridge/devices` which is published on startup, not on demand

3. **No Subscription Logs:** Recent logs don't show "Subscribed to" messages, suggesting subscriptions may not have occurred

**Solution:**
1. Update `MQTTClient` to use configurable base topic
2. Subscribe to response topics: `{base_topic}/bridge/response/device/list`
3. Also subscribe to retained device list: `{base_topic}/bridge/devices` (published on startup)

## How Discovery Works

### Home Assistant Discovery ✅
1. Service connects to HA WebSocket API
2. Calls `config/device_registry/list` → Gets devices
3. Calls `config/entity_registry/list` → Gets entities  
4. Calls `config/area_registry/list` → Gets areas
5. **Result:** 96 devices, 668 entities, 17 areas discovered

### Zigbee2MQTT Discovery ❌
1. Service connects to MQTT broker
2. Subscribes to topics (hardcoded, not using config)
3. Publishes request: `zigbee2mqtt/bridge/request/device/list`
4. **Issue:** Not subscribed to response topic
5. **Result:** 0 Zigbee devices received

## MQTT Topics Reference (Zigbee2MQTT)

### Published Topics (Zigbee2MQTT → Service)
- `zigbee2mqtt/bridge/devices` - Device list (published on startup, retained)
- `zigbee2mqtt/bridge/groups` - Group list
- `zigbee2mqtt/bridge/info` - Bridge information
- `zigbee2mqtt/bridge/response/device/list` - Response to device list request
- `zigbee2mqtt/bridge/response/group/list` - Response to group list request

### Request Topics (Service → Zigbee2MQTT)
- `zigbee2mqtt/bridge/request/device/list` - Request device list
- `zigbee2mqtt/bridge/request/group/list` - Request group list

## Recommended Fixes

### Priority 1: Fix Database Schema
```bash
# Recreate database with updated schema
curl -X POST http://localhost:8028/api/admin/database/recreate-tables

# Then trigger discovery refresh
curl -X POST http://localhost:8028/api/discovery/refresh
```

### Priority 2: Fix MQTT Client to Use Configurable Topics

**File:** `services/device-intelligence-service/src/clients/mqtt_client.py`

**Changes Needed:**
1. Accept `base_topic` parameter in `__init__`
2. Use `base_topic` to construct all topic strings
3. Subscribe to both retained topics AND response topics
4. Handle responses from `bridge/response/device/list`

### Priority 3: Verify MQTT Subscriptions

**Check if subscriptions are working:**
```bash
# Check logs for subscription messages
docker logs homeiq-device-intelligence | grep "Subscribed"

# Manually trigger MQTT device list request
# (via API or direct MQTT publish)
```

## Testing After Fixes

1. **Verify Database:**
   ```bash
   curl http://localhost:8028/api/discovery/status
   # Should show devices_count > 0 AND no database errors
   ```

2. **Verify MQTT:**
   ```bash
   # Check logs for Zigbee device messages
   docker logs homeiq-device-intelligence | grep "Received.*devices from Zigbee2MQTT"
   ```

3. **Trigger Manual Discovery:**
   ```bash
   curl -X POST http://localhost:8028/api/discovery/refresh
   ```

## Conclusion

Discovery is **working for Home Assistant** (96 devices found). The "0 devices" issue is actually:
1. **Database storage failing** due to schema mismatch
2. **Zigbee2MQTT not connected** due to MQTT topic configuration issues

Both issues are fixable without architectural changes.

