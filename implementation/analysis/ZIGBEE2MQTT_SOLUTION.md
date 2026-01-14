# Zigbee2MQTT Device Capture - Solution Implementation

**Date:** January 16, 2026  
**Status:** Ready for Implementation  
**Priority:** High

## Problem Summary

Zigbee2MQTT devices exist in Home Assistant device registry, but they have `integration='mqtt'` instead of `integration='zigbee2mqtt'`. This prevents them from being properly identified and captured by HomeIQ.

## Root Cause

Zigbee2MQTT uses the **generic MQTT integration** in Home Assistant, not a dedicated 'zigbee2mqtt' integration. The config_entry domain is 'mqtt', so integration field resolution correctly sets `integration='mqtt'`. However, this doesn't distinguish Zigbee devices from other MQTT devices.

## Evidence from Playwright Investigation

**Zigbee2MQTT UI:** 6 devices online and communicating  
**Home Assistant Device Registry:** 7 MQTT devices (6 Zigbee + Bridge)  
**Integration Field:** All show `integration='mqtt'`

**Devices Found:**
- Bar Light Switch (Inovelli)
- Bar PF300 Sensor (Aqara)
- Office 4 Button Switch (Tuya)
- Office Fan Switch (Inovelli)
- Office FP300 Sensor (Aqara)
- Office Light Switch (Inovelli)
- Zigbee2MQTT Bridge

## Solution

Add logic to `websocket-ingestion` service to identify Zigbee devices within MQTT integration by checking device identifiers and connection to Zigbee2MQTT Bridge.

### Implementation Approach

**Location:** `services/websocket-ingestion/src/discovery_service.py`

**Strategy:** After resolving integration from config_entries, check if MQTT devices are Zigbee devices by:
1. Checking device identifiers for Zigbee patterns
2. Checking if device shares config_entry with Zigbee2MQTT Bridge
3. Setting `source='zigbee2mqtt'` and optionally updating `integration='zigbee2mqtt'`

### Code Changes

**Add after line 690** (after integration field resolution):

```python
                # Identify Zigbee devices within MQTT integration
                # Zigbee2MQTT devices use 'mqtt' integration but need to be identified as Zigbee
                if devices_data:
                    # Find Zigbee2MQTT Bridge device (to get its config_entry)
                    zigbee_bridge_config_entry = None
                    for device in devices_data:
                        manufacturer = device.get("manufacturer", "").lower()
                        model = device.get("model", "").lower()
                        if manufacturer == "zigbee2mqtt" or "bridge" in model:
                            config_entries = device.get("config_entries", [])
                            if config_entries:
                                zigbee_bridge_config_entry = config_entries[0] if isinstance(config_entries, list) else config_entries
                                logger.info(f"🔍 Found Zigbee2MQTT Bridge with config_entry: {zigbee_bridge_config_entry}")
                                break
                    
                    # Identify Zigbee devices
                    zigbee_devices_found = 0
                    for device in devices_data:
                        integration = device.get("integration", "").lower()
                        
                        # Only process MQTT integration devices
                        if integration != "mqtt":
                            continue
                        
                        is_zigbee = False
                        
                        # Method 1: Check if device shares config_entry with Zigbee2MQTT Bridge
                        if zigbee_bridge_config_entry:
                            config_entries = device.get("config_entries", [])
                            if config_entries:
                                device_entry = config_entries[0] if isinstance(config_entries, list) else config_entries
                                if device_entry == zigbee_bridge_config_entry:
                                    is_zigbee = True
                                    logger.debug(f"Identified {device.get('name', 'unknown')} as Zigbee (shares bridge config_entry)")
                        
                        # Method 2: Check device identifiers for Zigbee patterns
                        if not is_zigbee:
                            identifiers = device.get("identifiers", [])
                            for identifier in identifiers:
                                identifier_str = str(identifier).lower()
                                # Check for 'zigbee' or 'ieee' in identifier
                                if 'zigbee' in identifier_str or 'ieee' in identifier_str:
                                    is_zigbee = True
                                    logger.debug(f"Identified {device.get('name', 'unknown')} as Zigbee (identifier pattern: {identifier_str})")
                                    break
                                # Check for IEEE address pattern (0x followed by 8+ hex digits)
                                if identifier_str.startswith('0x') and len(identifier_str) >= 10:
                                    # Check if it looks like an IEEE address (hexadecimal)
                                    try:
                                        int(identifier_str[2:], 16)
                                        is_zigbee = True
                                        logger.debug(f"Identified {device.get('name', 'unknown')} as Zigbee (IEEE address pattern: {identifier_str})")
                                        break
                                    except ValueError:
                                        pass
                        
                        # Method 3: Check manufacturer/model patterns (fallback)
                        if not is_zigbee:
                            manufacturer = device.get("manufacturer", "").lower()
                            # Common Zigbee manufacturers (may have false positives)
                            zigbee_manufacturers = ["inovelli", "aqara", "tuya", "philips", "ikea", "sengled"]
                            if any(zm in manufacturer for zm in zigbee_manufacturers):
                                # Additional check: device must NOT be Zigbee Bridge itself
                                if "bridge" not in device.get("model", "").lower():
                                    # This is a weak signal, but could help identify devices
                                    # Consider this only if other methods failed
                                    pass
                        
                        if is_zigbee:
                            # Mark as Zigbee device
                            device["integration"] = "zigbee2mqtt"  # Update integration field
                            device["source"] = "zigbee2mqtt"  # Add source field for tracking
                            zigbee_devices_found += 1
                            logger.info(f"✅ Identified Zigbee device: {device.get('name', 'unknown')} (manufacturer: {device.get('manufacturer', 'unknown')})")
```

### Alternative: Use Source Field Only

If we want to keep `integration='mqtt'` but add identification:

```python
if is_zigbee:
    device["source"] = "zigbee2mqtt"  # Add source field
    # Keep integration='mqtt' for compatibility
    zigbee_devices_found += 1
```

## Verification Steps

After implementing fix:

1. **Restart websocket-ingestion service:**
   ```bash
   docker compose restart websocket-ingestion
   ```

2. **Check logs for Zigbee identification:**
   ```bash
   docker compose logs websocket-ingestion | grep -i zigbee
   ```

3. **Query database for Zigbee devices:**
   ```sql
   SELECT name, integration, source, manufacturer, model 
   FROM devices 
   WHERE integration='zigbee2mqtt' OR source='zigbee2mqtt'
   ORDER BY name;
   ```

4. **Verify in HomeIQ dashboard:**
   - Filter by integration='zigbee2mqtt'
   - Should see 6 Zigbee devices (excludes bridge)

## Expected Results

After fix implementation:
- ✅ 6 Zigbee devices identified with `integration='zigbee2mqtt'`
- ✅ Devices appear in HomeIQ dashboard when filtering by Zigbee2MQTT
- ✅ Source field set to 'zigbee2mqtt' for tracking
- ✅ Logs show device identification messages

## Testing Considerations

**False Positive Prevention:**
- Only identify devices that share config_entry with Zigbee2MQTT Bridge (strongest signal)
- Identifier pattern matching (secondary signal)
- Avoid manufacturer-based identification alone (too many false positives)

**Edge Cases:**
- Devices that are MQTT but not Zigbee (should remain `integration='mqtt'`)
- Zigbee Bridge device itself (should be identified but may want to exclude from counts)
- Devices with unusual identifier formats

## Related Code

**Reference Implementation:**
- `services/device-intelligence-service/src/core/discovery_service.py` (lines 418-444)
  - Already has similar logic for identifying Zigbee devices
  - Uses identifier pattern matching

**Difference:**
- `device-intelligence-service` works with `UnifiedDevice` objects
- `websocket-ingestion` works with raw device dictionaries from HA WebSocket API
- Need to adapt the logic to work with dictionary format

## Next Steps

1. **Implement the fix** in `services/websocket-ingestion/src/discovery_service.py`
2. **Test locally** with device discovery
3. **Verify logs** show Zigbee device identification
4. **Query database** to confirm devices are marked correctly
5. **Check dashboard** to verify devices appear with correct integration

## Related Documents

- `implementation/analysis/ZIGBEE2MQTT_PLAYWRIGHT_FINDINGS.md` - Playwright investigation results
- `implementation/analysis/ZIGBEE2MQTT_CURRENT_STATE_REVIEW.md` - Current state analysis
- `implementation/analysis/ZIGBEE2MQTT_NEXT_STEPS.md` - Action plan
