# Zigbee2MQTT Device Capture - Playwright Investigation Findings

**Date:** January 16, 2026  
**Investigation Method:** Direct browser inspection via Playwright  
**Status:** Root Cause Identified

## Executive Summary

✅ **Zigbee2MQTT devices exist** in Home Assistant device registry  
❌ **Integration field = "MQTT"** (not "zigbee2mqtt")  
❌ **All devices have `integration='mqtt'`** which prevents proper filtering

## Findings from Playwright Investigation

### 1. Zigbee2MQTT UI Verification

**Zigbee2MQTT Interface:** http://192.168.1.86:8123/45df7312_zigbee2mqtt/ingress

**Devices Found in Zigbee2MQTT:**
1. Bar Light Switch (0x9035eafffec911ef)
2. Office 4 Button Switch (0x90395efffe357b59)
3. Office FP300 Sensor (0x54ef44100146c0f4)
4. Bar PF300 Sensor (0x54ef44100146c22c)
5. Office Fan Switch (0x048727fffe196715)
6. Office Light Switch (0x9035eafffec90e8f)

**Status:** All 6 devices are online and communicating with Zigbee2MQTT bridge.

### 2. Home Assistant Device Registry Verification

**Device Registry URL:** http://192.168.1.86:8123/config/devices/dashboard

**Filter Applied:** Integration = "MQTT"  
**Results:** 7 devices (6 Zigbee devices + Zigbee2MQTT Bridge)

**MQTT Devices Found in Home Assistant:**

| Device Name | Integration | Manufacturer | Model | Battery |
|------------|-------------|--------------|-------|---------|
| Bar Light Switch | **MQTT** | Inovelli | 2-in-1 switch + dimmer | — |
| Bar PF300 Sensor | **MQTT** | Aqara | Presence sensor FP300 | 100% |
| Office 4 Button Switch | **MQTT** | Tuya | Wireless switch with 4 buttons | 100% |
| Office Fan Switch | **MQTT** | Inovelli | Fan controller | — |
| Office FP300 Sensor | **MQTT** | Aqara | Presence sensor FP300 | 100% |
| Office Light Switch | **MQTT** | Inovelli | 2-in-1 switch + dimmer | — |
| Zigbee2MQTT Bridge | **MQTT** | Zigbee2MQTT | Bridge | — |

### 3. Key Finding: Integration Field Mismatch

**Issue:** All Zigbee2MQTT devices have `integration='mqtt'` in Home Assistant, not `integration='zigbee2mqtt'`.

**Why This Matters:**
- websocket-ingestion resolves integration from config_entries
- Config entry domain for Zigbee2MQTT devices is **'mqtt'** (not 'zigbee2mqtt')
- Integration field fix correctly resolves to 'mqtt'
- But devices need to be identified as Zigbee devices for proper capture

**Evidence:**
- Zigbee2MQTT Bridge device exists with manufacturer="Zigbee2MQTT"
- All Zigbee devices have manufacturer="Inovelli" or "Aqara" or "Tuya"
- All have integration="MQTT" (generic MQTT integration, not Zigbee2MQTT-specific)

## Root Cause Analysis

### The Problem

1. **Zigbee2MQTT Integration Uses Generic MQTT Integration:**
   - Zigbee2MQTT devices are integrated into Home Assistant via the generic MQTT integration
   - Config entry domain is 'mqtt', not 'zigbee2mqtt'
   - Integration field resolution correctly sets `integration='mqtt'`
   - But this doesn't distinguish Zigbee devices from other MQTT devices

2. **Integration Field Not Sufficient for Identification:**
   - All Zigbee devices have `integration='mqtt'` (same as non-Zigbee MQTT devices)
   - Need additional logic to identify Zigbee devices
   - Possible identifiers:
     - Device identifiers (IEEE addresses like `0x9035eafffec911ef`)
     - Manufacturer name patterns
     - Connection to Zigbee2MQTT Bridge device
     - Entity identifiers containing 'zigbee' or 'ieee'

3. **Current Code Doesn't Handle This:**
   - Integration field fix resolves to 'mqtt' (correct)
   - But no logic to detect Zigbee devices within MQTT integration
   - Need to identify devices with Zigbee characteristics

## Device Identification Patterns

### Pattern 1: Device Identifiers

Zigbee devices typically have IEEE address identifiers:
- Format: `zigbee2mqtt:<ieee_address>` or similar
- Example: `0x9035eafffec911ef` (seen in Zigbee2MQTT UI)

### Pattern 2: Entity Names

Zigbee entities often have patterns:
- Device names match Zigbee2MQTT friendly names
- Entities may have 'zigbee' in entity_id

### Pattern 3: Zigbee2MQTT Bridge Connection

Devices connected via Zigbee2MQTT Bridge:
- Bridge device has manufacturer="Zigbee2MQTT"
- Zigbee devices share config_entry with bridge

## Next Steps - Solution

### Option 1: Enhanced Integration Resolution (RECOMMENDED)

**Approach:** Identify Zigbee devices within MQTT integration by checking identifiers and bridge connection.

**Implementation:**
1. When integration='mqtt', check device identifiers for IEEE address patterns
2. Check if device shares config_entry with Zigbee2MQTT Bridge
3. Set `source='zigbee2mqtt'` for identified devices
4. Optionally update `integration` field to 'zigbee2mqtt' (if desired)

**Code Location:** `services/websocket-ingestion/src/discovery_service.py`

**Changes Needed:**
```python
# After resolving integration from config_entries
if device.get("integration") == "mqtt":
    # Check if device has Zigbee identifiers
    identifiers = device.get("identifiers", [])
    is_zigbee = False
    
    for identifier in identifiers:
        identifier_str = str(identifier).lower()
        # Check for IEEE address pattern (0x...) or zigbee identifiers
        if '0x' in identifier_str and len(identifier_str) > 8:
            is_zigbee = True
            break
        if 'zigbee' in identifier_str or 'ieee' in identifier_str:
            is_zigbee = True
            break
    
    # Also check if device is connected to Zigbee2MQTT Bridge
    if not is_zigbee:
        config_entries = device.get("config_entries", [])
        # Check if any config_entry corresponds to Zigbee2MQTT Bridge
        # (Would need to check bridge device's config_entry)
    
    if is_zigbee:
        # Mark as Zigbee device
        device["integration"] = "zigbee2mqtt"  # Or keep 'mqtt' and add source field
        device["source"] = "zigbee2mqtt"
```

### Option 2: Check Zigbee2MQTT Bridge Connection

**Approach:** Identify devices that share config_entry with Zigbee2MQTT Bridge device.

**Implementation:**
1. Find Zigbee2MQTT Bridge device (manufacturer="Zigbee2MQTT")
2. Get its config_entry_id
3. Mark all devices sharing that config_entry as Zigbee devices

### Option 3: Use Device Identifiers

**Approach:** Check device identifiers for IEEE address patterns (0x followed by hex digits).

**Implementation:**
1. Check device.identifiers for patterns matching IEEE addresses
2. If found, mark as Zigbee device

## Verification Plan

After implementing fix:

1. **Restart websocket-ingestion service**
2. **Check logs** for Zigbee device identification
3. **Query database** for devices with `integration='zigbee2mqtt'` or `source='zigbee2mqtt'`
4. **Verify dashboard** shows Zigbee devices with correct integration filter

## Screenshots Captured

- `ha-initial-page.png` - Home Assistant overview dashboard
- `ha-device-registry.png` - Device registry showing all devices
- `ha-mqtt-devices-filtered.png` - Filtered view showing 7 MQTT devices (6 Zigbee + Bridge)

## Related Documents

- `implementation/analysis/ZIGBEE2MQTT_CURRENT_STATE_REVIEW.md` - Comprehensive review
- `implementation/analysis/ZIGBEE2MQTT_NEXT_STEPS.md` - Action plan
- `implementation/analysis/ZIGBEE2MQTT_DEVICES_FIX.md` - Integration field fix documentation
