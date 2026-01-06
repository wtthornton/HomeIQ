# Zigbee2MQTT Devices Not Showing in HomeIQ - Root Cause & Fix

## Issue Summary

Zigbee2MQTT devices were not appearing in the HomeIQ dashboard because the `integration` field was not being populated when devices were stored in the database.

## Root Cause Analysis

### Home Assistant Device Registry API

Home Assistant's device registry (`config/device_registry/list`) does **not** directly provide an `integration` field. Instead, it provides:
- `config_entries`: Array of config entry IDs (e.g., `["abc123", "def456"]`)
- Other fields: `id`, `name`, `manufacturer`, `model`, etc.

### The Problem

1. **websocket-ingestion** was discovering devices from Home Assistant device registry
2. Devices were stored via `data-api` `/internal/devices/bulk_upsert` endpoint
3. The endpoint tried to extract `device_data.get('integration')` but this field was **never present** in the device data
4. Result: All devices had `integration = None` in the database
5. Zigbee2MQTT devices couldn't be filtered or displayed properly because they had no integration identifier

### Why Config Entries Discovery Was Disabled

The code had this comment:
```python
# TEMPORARY: Skip config entries - command not supported in this HA version
config_entries_data = []  # await self.discover_config_entries(websocket)
```

This was preventing the resolution of integration names from config entry IDs.

## Solution

### Fix Applied

1. **Enabled config entries discovery** - Uncommented and fixed the config entries discovery call
2. **Built config entry mapping** - Created a mapping from `config_entry_id` → `integration domain`
3. **Resolved integration field** - For each device, resolve the integration from its `config_entries` array using the mapping

### Code Changes

**File:** `services/websocket-ingestion/src/discovery_service.py`

1. **Enabled config entries discovery** (line 521):
```python
# Before:
config_entries_data = []  # await self.discover_config_entries(websocket)

# After:
config_entries_data = await self.discover_config_entries(websocket) if websocket else []
```

2. **Added integration resolution** (lines 637-660):
```python
# Build config_entry_id -> integration domain mapping
config_entry_map: dict[str, str] = {}
if config_entries_data:
    for entry in config_entries_data:
        entry_id = entry.get("entry_id")
        domain = entry.get("domain")
        if entry_id and domain:
            config_entry_map[entry_id] = domain
    logger.info(f"🔧 Built config entry mapping: {len(config_entry_map)} entries")

# Resolve integration field for devices from config_entries
if devices_data and config_entry_map:
    for device in devices_data:
        # Home Assistant device registry provides config_entries (array of IDs)
        # but not integration field directly - we need to resolve it
        if "integration" not in device or not device.get("integration"):
            config_entries = device.get("config_entries", [])
            if config_entries:
                # Use first config entry to resolve integration
                first_entry_id = config_entries[0] if isinstance(config_entries, list) else config_entries
                integration = config_entry_map.get(first_entry_id)
                if integration:
                    device["integration"] = integration
                    logger.debug(f"Resolved integration '{integration}' for device {device.get('name', 'unknown')} from config_entry {first_entry_id}")
```

## How It Works

1. **Discovery Phase:**
   - Discover devices from HA device registry (includes `config_entries` array)
   - Discover config entries from HA (includes `entry_id` and `domain`)

2. **Resolution Phase:**
   - Build mapping: `config_entry_id` → `integration domain`
   - For each device, look up its first `config_entry_id` in the mapping
   - Set `device["integration"] = domain` (e.g., "zigbee2mqtt", "hue", "mqtt")

3. **Storage Phase:**
   - Devices are stored with the resolved `integration` field
   - `data-api` bulk_upsert endpoint now receives devices with `integration` populated

## Testing

### Verification Steps

1. **Check logs** for integration resolution:
   ```
   🔧 Built config entry mapping: X entries
   Resolved integration 'zigbee2mqtt' for device [device_name] from config_entry [entry_id]
   ```

2. **Query database** to verify integration field:
   ```sql
   SELECT device_id, name, integration FROM devices WHERE integration = 'zigbee2mqtt';
   ```

3. **Check HomeIQ dashboard** - Zigbee2MQTT devices should now appear with correct integration filter

### Expected Behavior

- All devices should have `integration` field populated (not `None`)
- Zigbee2MQTT devices should have `integration = "zigbee2mqtt"`
- Devices can be filtered by integration in the dashboard
- Integration statistics should be accurate

## Related Files

- `services/websocket-ingestion/src/discovery_service.py` - Main fix location
- `services/data-api/src/devices_endpoints.py` - Device storage endpoint (already correct)
- `services/device-intelligence-service/src/core/device_parser.py` - Similar pattern for reference (`_resolve_integration` method)

## References

- Home Assistant Device Registry API: `config/device_registry/list`
- Home Assistant Config Entries API: `config_entries/list`
- Context7 Home Assistant Documentation: `/home-assistant/core`

## Status

✅ **FIXED** - Integration field is now resolved from config entries before device storage
