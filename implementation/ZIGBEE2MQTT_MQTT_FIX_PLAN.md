# Zigbee2MQTT MQTT Fix Plan

**Date:** 2026-01-12  
**Issue:** Service subscribes to topics but receives 0 devices

## Findings

1. ✅ **Subscriptions Working**: Service successfully subscribes to all Zigbee2MQTT topics
2. ✅ **MQTT Connected**: Service shows "Connected to MQTT broker"
3. ✅ **Topics Correct**: Using `zigbee2mqtt/bridge/devices` (retained) and `zigbee2mqtt/bridge/response/device/list`
4. ❌ **No Messages Received**: No logs showing "📱 Received X devices from Zigbee2MQTT bridge"

## Analysis

Zigbee2MQTT publishes device list to `zigbee2mqtt/bridge/devices` as a **retained message**. When a client subscribes to a retained topic, it should receive the last retained message immediately.

### Possible Issues

1. **Retained message not received**: Service might subscribe before Zigbee2MQTT publishes, or retained message might be empty
2. **MQTT loop not running**: The paho-mqtt client needs `loop_start()` or `loop_forever()` to process incoming messages
3. **Message handler not called**: Messages received but handler callback not triggered

## Next Steps

1. Verify MQTT client loop is running (`loop_start()` or `loop_forever()`)
2. Check if messages are being received but not logged (add debug logging)
3. Test with direct MQTT client to verify Zigbee2MQTT is publishing
4. Check Zigbee2MQTT logs to see if requests are being processed
