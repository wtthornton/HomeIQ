# Device Entities Missing Analysis

**Date:** January 6, 2025  
**Issue:** Presence-Sensor-FP2-8B8A device shows 0 entities in dashboard, but has 3 sensors in Home Assistant  
**Device ID:** `07765655ee253761bb57e33b0b04aa6b`

## Problem Summary

The dashboard popup for "Presence-Sensor-FP2-8B8A" shows "Entities (0)" even though Home Assistant shows 3 active sensors:
1. Light Sensor Light Level (119 lx)
2. PS FP2 - Desk (Detected)
3. PS FP2 - Office (Detected)

## Root Cause

The device exists in the `data-api` SQLite database, but **no entities are stored** with the matching `device_id`. This means:

1. ✅ Device discovery is working (device is stored)
2. ❌ Entity discovery/storage is not linking entities to the device

## Investigation Results

### Device Status
- **Device ID:** `07765655ee253761bb57e33b0b04aa6b`
- **Name:** `Presence-Sensor-FP2-8B8A`
- **Area:** `office`
- **Entity Count:** 0 (should be 3)

### API Query Results
```bash
GET /api/devices/07765655ee253761bb57e33b0b04aa6b
→ Returns device with entity_count: 0

GET /api/entities?device_id=07765655ee253761bb57e33b0b04aa6b
→ Returns empty array (0 entities)
```

### Expected Entity IDs
Based on Home Assistant UI, these entities should exist:
- `sensor.light_sensor_light_level` (or similar)
- `binary_sensor.ps_fp2_desk` (or similar)
- `binary_sensor.ps_fp2_office` (or similar)

## Possible Causes

1. **Entity discovery not running:** `websocket-ingestion` may not be discovering entities
2. **Device ID mismatch:** Entities stored with different device_id format
3. **Entity storage failure:** `bulk_upsert_entities` may be failing silently
4. **Case sensitivity:** Device ID format mismatch (e.g., `presence-sensor-fp2-8b8a` vs `Presence-Sensor-FP2-8B8A`)

## Code Flow

### Entity Discovery Path
1. `websocket-ingestion` → `discover_entities()` → Calls HA `config/entity_registry/list`
2. Entities stored via `store_discovery_results()` → `bulk_upsert_entities()` endpoint
3. `data-api` → `bulk_upsert_entities()` → Stores entities with `device_id` field

### Storage Logic
```python
# services/websocket-ingestion/src/discovery_service.py:122
async def discover_entities(self, websocket) -> List[Dict[str, Any]]:
    # Gets entities from HA with device_id field
    
# services/data-api/src/devices_endpoints.py:771
async def bulk_upsert_entities(entities: List[Dict[str, Any]]):
    entity = Entity(
        entity_id=entity_data.get('entity_id'),
        device_id=entity_data.get('device_id'),  # Must match device.device_id
        ...
    )
```

## Next Steps

1. **Trigger discovery refresh:** Force websocket-ingestion to rediscover entities
2. **Check entity storage:** Verify entities are being stored with correct device_id
3. **Check logs:** Look for errors in entity discovery/storage
4. **Verify device_id format:** Ensure HA device_id matches stored entity device_id

## Fix Required

The issue is likely that:
- Entity discovery runs on startup but may have missed entities
- Or entities are stored but with NULL/incorrect device_id
- Need to trigger a fresh discovery cycle

