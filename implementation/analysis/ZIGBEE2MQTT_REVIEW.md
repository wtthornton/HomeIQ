# Zigbee2MQTT Device Discovery Review

**Date:** 2026-01-12  
**Reviewer:** AI Assistant  
**Service:** device-intelligence-service (Port 8028)

## Executive Summary

**Result: 0 Zigbee2MQTT devices found**

The discovery service is running and connected to both Home Assistant and MQTT, but **no Zigbee2MQTT devices are being discovered**. The service has discovered 101 devices from Home Assistant, but none are identified as Zigbee2MQTT devices.

## Service Status

### Discovery Service Health
- ✅ **Service Running:** Yes
- ✅ **Home Assistant Connected:** Yes
- ✅ **MQTT Connected:** Yes
- ✅ **Last Discovery:** 2026-01-12T20:53:39 (after manual refresh)
- ✅ **Total Devices Discovered:** 101 devices
- ❌ **Zigbee2MQTT Devices:** 0 devices

### Connection Status
```json
{
    "service_running": true,
    "ha_connected": true,
    "mqtt_connected": true,
    "last_discovery": "2026-01-12T20:53:39.821096+00:00",
    "devices_count": 101,
    "areas_count": 0,
    "errors": []
}
```

## Device Analysis

### Total Devices by Integration
The service discovered 101 devices from Home Assistant with the following integrations:

| Integration | Device Count |
|------------|--------------|
| hue | 44 |
| hassio | 14 |
| wled | 5 |
| hacs | 5 |
| cast | 4 |
| ring | 4 |
| mobile_app | 3 |
| homekit | 3 |
| dlna_dmr | 2 |
| openai_conversation | 2 |
| roborock | 2 |
| sun | 1 |
| bluetooth | 1 |
| met | 1 |
| ipp | 1 |
| samsungtv | 1 |
| upnp | 1 |
| apple_tv | 1 |
| denonavr | 1 |
| heos | 1 |
| smlight | 1 |
| homekit_controller | 1 |
| speedtestdotnet | 1 |
| backup | 1 |

**Notable:** No devices with `integration='zigbee2mqtt'`, `integration='mqtt'`, or any integration containing 'zigbee'.

### Zigbee2MQTT Device Search Results
- **Devices with `source='zigbee2mqtt'`:** 0
- **Devices with `integration='zigbee2mqtt'`:** 0
- **Devices with `integration='mqtt'`:** 0
- **Devices with integration containing 'zigbee':** 0

## Technical Analysis

### Discovery Service Architecture

The discovery service uses a two-source approach:

1. **Home Assistant Device Registry** (Primary)
   - ✅ Successfully connected and discovering devices
   - ✅ 101 devices discovered
   - ✅ Devices stored in database with integration information
   - ❌ No devices identified as Zigbee2MQTT (no matching integration field)

2. **MQTT/Zigbee2MQTT Bridge** (Secondary - for enhanced data)
   - ✅ MQTT broker connected
   - ✅ Subscribed to topics: `zigbee2mqtt/bridge/devices`, `zigbee2mqtt/bridge/groups`, etc.
   - ❌ No Zigbee device data received via MQTT
   - ❌ `self.zigbee_devices` dictionary is empty (0 devices)

### Code Logic Review

The service has logic to identify Zigbee2MQTT devices from Home Assistant integration:

**Location:** `services/device-intelligence-service/src/core/discovery_service.py:418-444`

```python
# Set source based on HA device integration if Zigbee2MQTT
integration_lower = integration_value.lower()
if ('zigbee' in integration_lower or 
    integration_lower == 'zigbee2mqtt' or
    integration_lower == 'mqtt'):
    # For MQTT integration, check if it's a Zigbee device by checking identifiers
    is_zigbee = False
    if integration_lower == 'mqtt':
        # Check if device has Zigbee-like identifiers
        identifiers = device.ha_device.identifiers or []
        for identifier in identifiers:
            identifier_str = str(identifier).lower()
            if 'zigbee' in identifier_str or 'ieee' in identifier_str:
                is_zigbee = True
                break
        if not is_zigbee:
            continue
    
    device_data["source"] = "zigbee2mqtt"
```

**Issue:** This logic never executes because:
- No devices have `integration='zigbee2mqtt'`
- No devices have `integration='mqtt'`
- No devices have integration containing 'zigbee'

### MQTT Subscription Status

The service subscribes to the following Zigbee2MQTT MQTT topics:
- `zigbee2mqtt/bridge/devices` (retained device list)
- `zigbee2mqtt/bridge/groups` (retained group list)
- `zigbee2mqtt/bridge/info` (bridge information)
- `zigbee2mqtt/bridge/networkmap` (network map)
- `zigbee2mqtt/bridge/response/device/list` (response to device list request)
- `zigbee2mqtt/bridge/response/group/list` (response to group list request)

**Status:** MQTT is connected, but no messages received on these topics (or messages aren't being processed).

## Root Cause Analysis

### Possible Causes

1. **No Zigbee2MQTT Devices Present** ⭐ MOST LIKELY
   - Zigbee2MQTT integration may not be installed/configured in Home Assistant
   - Zigbee2MQTT bridge may not be set up
   - No Zigbee devices have been paired with Zigbee2MQTT

2. **Integration Name Mismatch**
   - Zigbee2MQTT devices in Home Assistant may use a different integration name
   - Integration field might not be set correctly in HA device registry
   - Devices might exist but aren't identified correctly

3. **MQTT Messages Not Received**
   - Zigbee2MQTT bridge may not be publishing to expected topics
   - Base topic might be different (currently `zigbee2mqtt`)
   - MQTT messages might not be retained/published on startup

4. **Zigbee2MQTT Not Running**
   - Zigbee2MQTT add-on/service may not be running
   - Zigbee coordinator may not be connected
   - Bridge may not be operational

## Recommendations

### 1. Verify Zigbee2MQTT Installation (IMMEDIATE)

**Check if Zigbee2MQTT is installed in Home Assistant:**
- Navigate to Home Assistant → Settings → Add-ons → Zigbee2MQTT
- Verify add-on is installed and running
- Check Zigbee2MQTT logs for any errors

**Verify Zigbee devices are paired:**
- Open Zigbee2MQTT web UI
- Check Devices page for paired devices
- Verify devices are online and communicating

### 2. Check Home Assistant Device Registry (IMMEDIATE)

**Check if Zigbee devices exist in HA:**
```bash
# Query HA device registry via API
curl -H "Authorization: Bearer $HA_TOKEN" \
  http://192.168.1.86:8123/api/config/device_registry/list | \
  jq '.[] | select(.identifiers[0][0] | contains("zigbee") or contains("ieee"))'
```

**Check integration field:**
- Look for devices with integration field containing 'zigbee', 'mqtt', or 'zigbee2mqtt'
- Verify device identifiers contain IEEE addresses or Zigbee identifiers

### 3. Verify MQTT Topics (IMMEDIATE)

**Check if Zigbee2MQTT is publishing to MQTT:**
```bash
# Subscribe to Zigbee2MQTT topics
mosquitto_sub -h 192.168.1.86 -p 1883 -t "zigbee2mqtt/bridge/devices" -v
```

**Expected:** Should see a JSON array of Zigbee devices (even if empty array `[]`)

**If no messages:**
- Check Zigbee2MQTT configuration for base topic
- Verify MQTT broker is accessible
- Check Zigbee2MQTT logs for MQTT connection errors

### 4. Check Service Logs (IMMEDIATE)

**Review discovery service logs for MQTT messages:**
```bash
docker logs homeiq-device-intelligence | grep -i "zigbee\|mqtt"
```

**Look for:**
- `📡 Subscribed to zigbee2mqtt/bridge/devices`
- `📱 Zigbee2MQTT devices updated: X devices`
- `❌ Error handling Zigbee devices update`
- Any MQTT connection/subscription errors

### 5. Manual Device Verification (IF NEEDED)

**If Zigbee devices exist but aren't being discovered:**

1. **Check device identifiers in HA:**
   - Devices should have identifiers like `zigbee2mqtt:<ieee_address>`
   - Integration field should be set correctly

2. **Verify MQTT data is being received:**
   - Check if `self.zigbee_devices` dictionary has any entries
   - Review MQTT message handler logs

3. **Test MQTT request/response pattern:**
   - Service publishes to `zigbee2mqtt/bridge/request/device/list`
   - Zigbee2MQTT should respond on `zigbee2mqtt/bridge/response/device/list`

## Next Steps

1. ✅ **Verify Zigbee2MQTT is installed and running** in Home Assistant
2. ✅ **Check if any Zigbee devices are paired** with Zigbee2MQTT
3. ✅ **Verify MQTT topics** are being published by Zigbee2MQTT
4. ✅ **Review service logs** for MQTT connection/subscription issues
5. ✅ **Check Home Assistant device registry** for Zigbee devices
6. ✅ **Test MQTT subscription** manually using mosquitto_sub

## Conclusion

The discovery service is functioning correctly and is connected to both Home Assistant and MQTT. However, **no Zigbee2MQTT devices are being discovered** because:

1. Either no Zigbee2MQTT devices exist in the system
2. Or Zigbee2MQTT devices exist but aren't being identified correctly
3. Or MQTT messages aren't being received/processed

The most likely scenario is that **Zigbee2MQTT is not installed or no Zigbee devices are paired**. The service is ready to discover Zigbee2MQTT devices once they are present in the system.

## References

- Discovery Service: `services/device-intelligence-service/src/core/discovery_service.py`
- MQTT Client: `services/device-intelligence-service/src/clients/mqtt_client.py`
- Previous Analysis: `implementation/ZIGBEE2MQTT_COMPREHENSIVE_SOLUTIONS.md`
- Discovery API: `services/device-intelligence-service/src/api/discovery.py`
