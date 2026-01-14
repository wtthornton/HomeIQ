# Zigbee2MQTT Device Identification - Implementation Status

**Date:** January 13, 2026  
**Status:** ✅ Implementation Complete - Awaiting Discovery Run

## Summary

Implemented automatic identification of Zigbee devices within the MQTT integration in the `websocket-ingestion` service. This fix addresses the issue where Zigbee2MQTT devices are listed under the "MQTT" integration in Home Assistant's device registry, preventing them from being correctly identified as Zigbee devices in HomeIQ.

## Implementation Details

### File Modified
- **`services/websocket-ingestion/src/discovery_service.py`**

### Changes Made

1. **Zigbee2MQTT Bridge Detection** (Lines ~677-691):
   - Searches for the Zigbee2MQTT Bridge device by checking:
     - `manufacturer` contains "zigbee2mqtt"
     - `model` contains "bridge" AND `name` contains "zigbee"
   - Extracts the bridge's `config_entry` for use in device identification

2. **Zigbee Device Identification** (Lines ~693-751):
   - Processes all devices with `integration="mqtt"`
   - **Method 1: Config Entry Matching**
     - Checks if device shares the same `config_entry` as the Zigbee2MQTT Bridge
     - If match found, identifies device as Zigbee
   
   - **Method 2: Identifier Pattern Matching**
     - Checks device `identifiers` for Zigbee patterns:
       - Contains "zigbee" or "ieee" strings
       - IEEE address pattern: `0x` followed by 8+ hexadecimal digits
     - If pattern matches, identifies device as Zigbee

3. **Integration Field Update**:
   - Sets `integration` field to `"zigbee2mqtt"` for identified devices
   - Sets `source` field to `"zigbee2mqtt"` for tracking
   - Logs identification for debugging

## Code Logic

```python
# Find Zigbee2MQTT Bridge device
zigbee_bridge_config_entry = None
for device in devices_data:
    manufacturer = str(device.get("manufacturer", "")).lower()
    model = str(device.get("model", "")).lower()
    name = str(device.get("name", "")).lower()
    if "zigbee2mqtt" in manufacturer or ("bridge" in model and "zigbee" in name):
        config_entries = device.get("config_entries", [])
        if config_entries:
            zigbee_bridge_config_entry = config_entries[0] if isinstance(config_entries, list) else config_entries
            break

# Identify Zigbee devices within MQTT integration
for device in devices_data:
    if str(device.get("integration", "")).lower() != "mqtt":
        continue
    
    is_zigbee = False
    
    # Method 1: Check config_entry match with bridge
    if zigbee_bridge_config_entry:
        config_entries = device.get("config_entries", [])
        if config_entries:
            device_entry = config_entries[0] if isinstance(config_entries, list) else config_entries
            if device_entry == zigbee_bridge_config_entry:
                is_zigbee = True
    
    # Method 2: Check identifier patterns
    if not is_zigbee:
        identifiers = device.get("identifiers", [])
        for identifier in identifiers:
            identifier_str = str(identifier).lower()
            if 'zigbee' in identifier_str or 'ieee' in identifier_str:
                is_zigbee = True
                break
            # Check IEEE address pattern (0x followed by hex digits)
            if identifier_str.startswith('0x') and len(identifier_str) >= 10:
                try:
                    int(identifier_str[2:], 16)
                    is_zigbee = True
                    break
                except ValueError:
                    pass
    
    if is_zigbee:
        device["integration"] = "zigbee2mqtt"
        device["source"] = "zigbee2mqtt"
```

## Verification Steps

1. **Wait for Next Discovery Run**:
   - Device discovery runs on service startup and periodically
   - Check logs for messages like:
     - `"Found Zigbee2MQTT Bridge with config_entry: {id}"`
     - `"Identified {n} Zigbee devices within MQTT integration"`
     - `"Identified Zigbee device: {name}"`

2. **Check Database**:
   ```powershell
   # Query data-api for devices with integration='zigbee2mqtt'
   Invoke-RestMethod -Uri "http://localhost:8006/api/v2/devices?integration=zigbee2mqtt"
   ```

3. **Check Dashboard**:
   - Navigate to HomeIQ dashboard
   - Filter devices by integration: `zigbee2mqtt`
   - Verify Zigbee devices are now visible

## Next Steps

1. **Monitor Logs**:
   ```powershell
   docker compose logs websocket-ingestion -f | Select-String -Pattern "Zigbee|Bridge|Identified"
   ```

2. **Trigger Discovery** (if needed):
   - Restart `websocket-ingestion` service to trigger immediate discovery
   - Or wait for scheduled discovery run

3. **Verify Results**:
   - Check database for devices with `integration='zigbee2mqtt'`
   - Verify devices appear in dashboard with correct integration

## Related Documents

- `implementation/analysis/ZIGBEE2MQTT_CURRENT_STATE_REVIEW.md` - Initial state analysis
- `implementation/analysis/ZIGBEE2MQTT_PLAYWRIGHT_FINDINGS.md` - Home Assistant inspection results
- `implementation/analysis/ZIGBEE2MQTT_SOLUTION.md` - Proposed solution details
- `implementation/analysis/ZIGBEE2MQTT_DEVICES_FIX.md` - Integration field fix details

## Status

✅ **Code Implementation**: Complete  
⏳ **Discovery Run**: Pending (will run on next scheduled discovery or service restart)  
⏳ **Verification**: Awaiting discovery results  
