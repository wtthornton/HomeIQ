# Devices Summary Service - Injection Details

## Overview
The `DevicesSummaryService` injects device information into the AI agent's context under the `DEVICES:` section.

## Data Sources

### 1. Home Assistant Device Registry
- Fetched via `ha_client.get_device_registry()`
- Source: Home Assistant REST API

### 2. Home Assistant Area Registry  
- Fetched via `ha_client.get_area_registry()`
- Used for friendly area name mapping

### 3. Data API (Entity Counts)
- Fetched via `data_api_client.fetch_entities(limit=10000)`
- Counts entities per device

### 4. Device Intelligence Service (Zigbee2MQTT)
- Fetched via `GET {device_intelligence_url}/api/devices?limit=1000`
- Provides Zigbee2MQTT-specific metadata

## Device Fields Collected

### From Home Assistant Device Registry:
- `device_id` - Device unique identifier
- `name` - Device friendly name
- `manufacturer` - Device manufacturer
- `model` - Device model
- `area_id` - Area/room assignment
- `disabled_by` - Disabled status (stored but not displayed)
- `sw_version` - Software version (stored but not displayed)
- `hw_version` - Hardware version (stored but not displayed)

### From Data API:
- `entity_count` - Number of entities associated with device

### From Device Intelligence Service (Zigbee2MQTT):
- `lqi` - Link Quality Indicator (0-255)
- `availability_status` - Device availability ("enabled", "disabled", "offline")
- `battery_level` - Battery percentage (0-100)
- `battery_low` - Boolean flag for low battery warning

## Output Format

### Structure:
```
DEVICES:

Area Name (X devices):
  - Device Name (Manufacturer Model) [X entities] [Zigbee Info] [id: device_id]
  - Device Name 2 (Manufacturer Model) [X entities] [Zigbee Info] [id: device_id]
  ... and Y more devices

Another Area (Z devices):
  - Device Name 3 (Manufacturer Model) [X entities] [Zigbee Info] [id: device_id]

Unassigned (W devices):
  - Device Name 4 (Manufacturer Model) [X entities] [Zigbee Info] [id: device_id]
```

### Device Line Format Details:

**Base Format:**
```
Device Name (Manufacturer Model) [X entities] [Zigbee Info] [id: device_id]
```

**Component Breakdown:**
1. **Device Name** - Always included
2. **(Manufacturer Model)** - Included only if not "Unknown"
3. **[X entities]** - Included only if entity_count > 0
4. **[Zigbee Info]** - Included only if Zigbee data exists:
   - `LQI: 123` - If LQI is not None
   - `Status: disabled` - If status exists and not "enabled"
   - `Battery: 85%` - If battery_level is not None
   - `Battery Low` - If battery_low is True
   - Format: `[LQI: 123, Battery: 85%]` (comma-separated)
5. **[id: device_id]** - Always included for reference

### Examples:

**Basic Device (no Zigbee):**
```
Office Desk Light (Philips Hue A19) [3 entities] [id: abc123def456]
```

**Device with Zigbee Info:**
```
Living Room Motion Sensor (Aqara PIR) [2 entities] [LQI: 245, Battery: 92%] [id: xyz789ghi012]
```

**Device with Low Battery:**
```
Kitchen Door Sensor (Aqara Contact) [1 entity] [LQI: 180, Battery: 15%, Battery Low] [id: sensor123]
```

**Device with Status:**
```
Bedroom Light (IKEA Tradfri) [4 entities] [LQI: 200, Status: disabled] [id: light456]
```

**Device with Unknown Manufacturer:**
```
Unknown Device [1 entity] [id: unknown123]
```

## Grouping

### By Area:
- Devices are grouped by `area_id`
- Areas are sorted alphabetically by friendly name
- Each area shows: `Area Name (X devices):`

### Unassigned Devices:
- Devices without `area_id` are grouped under "Unassigned"
- Same format as area-grouped devices

## Truncation

### Default Behavior (skip_truncation=False):
- **Per Area:** Max 20 devices per area (shows "... and X more devices" if exceeded)
- **Unassigned:** Max 20 devices (shows "... and X more devices" if exceeded)
- **Total:** Max 4000 characters (truncates with "... (truncated)")

### Debug Mode (skip_truncation=True):
- All devices shown (no limits)
- Full detail for debugging

## Caching

- **Cache Key:** `devices_summary`
- **TTL:** 600 seconds (10 minutes)
- **Cache Behavior:** Only cached when `skip_truncation=False`
- **Cache Bypass:** Debug endpoints use `skip_truncation=True` to always get fresh data

## Context Injection

The formatted summary is injected into the AI context as:

```
DEVICES:
{formatted_summary}
```

This appears in the "Injected Context (Tier 1)" section of the debug screen.

## Notes

1. **Zigbee Data Availability:** Zigbee2MQTT data is optional and only shown if:
   - Device Intelligence Service is accessible
   - Device has Zigbee metadata stored
   - Fields have non-null values

2. **Manufacturer/Model Display:** Only shown if not "Unknown Unknown"

3. **Entity Count:** Only shown if > 0

4. **Area Names:** Uses friendly names from area registry, falls back to formatted area_id

5. **Device ID:** Always included for AI agent to reference specific devices

