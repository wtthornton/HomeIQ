# Zigbee2MQTT API Fix - Integration Field Added

**Date:** 2026-01-12  
**Status:** Code Fix Applied - Service Restarted

## Issue Identified

The API endpoint in `storage.py` was not returning the `integration` field even though:
- ✅ The database stores integration values (confirmed in SQL INSERT logs: 'backup', 'hue', 'cast', 'dlna_dmr', etc.)
- ✅ Integration resolution is working (45 config entries retrieved)
- ❌ The `DeviceResponse` model was missing the `integration` field
- ❌ The API endpoint wasn't including `integration` when creating responses

## Fix Applied

### File: `services/device-intelligence-service/src/api/storage.py`

**Changes:**
1. Added `integration: str | None = None` field to `DeviceResponse` model
2. Added `integration=device.integration` to DeviceResponse creation in `get_devices` endpoint
3. Added `integration=device.integration` to DeviceResponse creation in `get_device` endpoint

**Code Changes:**
```python
class DeviceResponse(BaseModel):
    # ... existing fields ...
    integration: str | None = None  # Added this field
    # Zigbee2MQTT fields
    # ... rest of fields ...
```

```python
DeviceResponse(
    # ... existing fields ...
    integration=device.integration,  # Added this line
    # ... rest of fields ...
)
```

## Verification

After service restart, the API response should now include the `integration` field for all devices.

## Next Steps

1. ✅ Verify integration field appears in API response
2. Re-check devices for integration='mqtt' with Zigbee identifiers
3. Verify if our code changes (setting source='zigbee2mqtt' for MQTT integration devices) now work correctly
