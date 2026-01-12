# Zigbee2MQTT Devices Fix - Phase 2 MQTT Investigation

**Date:** 2026-01-12  
**Phase:** 2 - Fix device-intelligence-service  
**Status:** Investigating MQTT Message Reception

## Issue

- ✅ Database schema fixed
- ✅ Service running and storing devices
- ✅ MQTT connection shows as "connected"
- ❌ No Zigbee2MQTT devices being stored (0 devices with source='zigbee2mqtt')
- ❌ No logs showing "📱 Received X devices from Zigbee2MQTT bridge"

## Analysis

### Code Flow
1. Service subscribes to `zigbee2mqtt/bridge/devices` (retained topic)
2. Service subscribes to `zigbee2mqtt/bridge/response/device/list` (response topic)
3. On discovery refresh, service publishes to `zigbee2mqtt/bridge/request/device/list`
4. Zigbee2MQTT should publish device list to response topic
5. Service should receive messages and call `_on_zigbee_devices_update()`

### Expected Logs (Missing)
- "📡 Subscribed to zigbee2mqtt/bridge/devices"
- "📡 Requested Zigbee2MQTT device list refresh"
- "📱 Received X devices from Zigbee2MQTT bridge"
- "📱 Zigbee2MQTT devices updated: X devices"

## Next Steps

1. Verify MQTT subscription logs exist
2. Verify base_topic configuration (should be "zigbee2mqtt")
3. Check if Zigbee2MQTT is publishing to the expected topics
4. Manually test MQTT message reception
5. Verify topic names match between service and Zigbee2MQTT

## Configuration

- **Base Topic**: `ZIGBEE2MQTT_BASE_TOPIC` (default: "zigbee2mqtt")
- **MQTT Broker**: `MQTT_BROKER` (default: mqtt://192.168.1.86:1883)
- **Expected Topics**:
  - `zigbee2mqtt/bridge/devices` (retained)
  - `zigbee2mqtt/bridge/response/device/list` (response)
  - `zigbee2mqtt/bridge/request/device/list` (request)
