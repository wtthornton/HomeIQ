# Zigbee2MQTT Settings Check Required

**Date:** 2026-01-12  
**Status:** Zigbee2MQTT Working - Need Settings Verification

## Confirmed from About Page

✅ **Zigbee2MQTT is working correctly:**
- Version: 2.7.2
- MQTT Broker: `mqtt://core-mosquitto:1883` (internal Docker network)
- Our service connects to: `mqtt://192.168.1.86:1883` (external IP) - Same broker ✅
- 6 devices connected and working
- System operational

## Critical Settings to Check

### 1. Base Topic Configuration

**In Zigbee2MQTT Settings page:**
- Navigate to: Settings → MQTT settings
- Find: **"Base topic"** setting
- **Expected**: `zigbee2mqtt`
- **Our service uses**: `zigbee2mqtt` (default)

**Action**: Verify base_topic matches `zigbee2mqtt`

### 2. Device List Publishing

**Check if Zigbee2MQTT publishes device list:**
- In Settings, look for options like:
  - "Publish device list"
  - "Bridge topics"
  - "Advanced settings"

### 3. Check Logs for Bridge Topics

**In Zigbee2MQTT Logs page:**
- Filter/search for: `bridge/devices`
- Or: `bridge/response/device/list`

**Key Question**: Does `zigbee2mqtt/bridge/devices` appear in the logs?

## Our Service Configuration

- **Base Topic**: `zigbee2mqtt` (from ZIGBEE2MQTT_BASE_TOPIC env var)
- **Subscribes to**:
  - `zigbee2mqtt/bridge/devices` (retained device list)
  - `zigbee2mqtt/bridge/response/device/list` (response to request)
- **Publishes to**:
  - `zigbee2mqtt/bridge/request/device/list` (request device list)

## Next Steps

1. **Check Zigbee2MQTT Settings page**:
   - Verify base_topic = `zigbee2mqtt`
   - Check for any device list publishing settings

2. **Check Logs for bridge/devices**:
   - Filter logs for "bridge/devices"
   - Check startup logs (when Zigbee2MQTT first started)

3. **Verify Topic Pattern**:
   - Our service expects: `zigbee2mqtt/bridge/devices`
   - Zigbee2MQTT should publish to: `{base_topic}/bridge/devices`
   - If base_topic differs, topics won't match!
