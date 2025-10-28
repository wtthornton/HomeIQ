# Device Expose/Capability Storage Implementation Plan

**Last Updated:** January 2025  
**Status:** Draft for Review  
**Target:** Single-home deployment with comprehensive device intelligence

---

## Executive Summary

This plan implements complete storage and caching of device capabilities/exposes from both Zigbee2MQTT and Home Assistant devices. The solution will store all expose information in the database, cache with 6-hour TTL, and provide enhanced device intelligence for AI automation suggestions.

---

## Current State Analysis

### What Works
✅ Zigbee2MQTT exposes captured via MQTT  
✅ Device metadata stored in database  
✅ In-memory cache exists with TTL support  
✅ API endpoints for device retrieval  
✅ Cache statistics tracking  

### What's Missing
❌ Exposes NOT stored in `device_capabilities` table  
❌ Cache TTL too short (5 minutes vs 6 hours)  
❌ No cache invalidation on MQTT updates  
❌ Non-MQTT devices have NO capabilities  
❌ No entity state/attributes extraction  
❌ Full expose data not returned in API responses  

---

## Architecture Overview

### Data Flow

```
Zigbee2MQTT Bridge           Home Assistant
       ↓                           ↓
    MQTT Topic                  WebSocket
       ↓                           ↓
Device Intelligence Service (DiscoveryService)
       ↓
  Parse Exposes/Attributes
       ↓
  Store in Database (device_capabilities table)
       ↓
  Cache (6-hour TTL)
       ↓
  Invalidate on Updates
       ↓
/api/discovery/devices/{device_id}
```

### Database Schema (Already Exists)

**`devices` table:**
- Device metadata (id, name, manufacturer, model, area, etc.)
- Already populated ✅

**`device_capabilities` table:**
- `device_id` (FK to devices)
- `capability_name` (primary key)
- `capability_type` (binary, enum, numeric, etc.)
- `properties` (JSON with full expose data)
- `exposed` (boolean)
- `configured` (boolean)
- `source` (zigbee2mqtt, homeassistant)
- `last_updated` (timestamp)

**Status:** Table exists, NOT populated ❌

---

## Implementation Plan

### Phase 1: Cache Configuration Update

**File:** `services/device-intelligence-service/src/core/cache.py`

**Change:** Update default TTL from 5 minutes to 6 hours

```python
# Line ~195
def get_device_cache() -> DeviceCache:
    """Get the global device cache instance."""
    global _device_cache
    
    if _device_cache is None:
        # Changed: 300 (5 min) → 21600 (6 hours)
        # Changed: max_size 1000 → 500 (more than enough for single home)
        _device_cache = DeviceCache(
            max_size=500,      # 200-500 devices typical for single home
            default_ttl=21600   # 6 hours - good balance for single-home
        )
        logger.info("📦 Device cache initialized with 6-hour TTL for single-home deployment")
    
    return _device_cache
```

**Impact:** Longer cache duration for better performance  
**Time:** 2 minutes  
**Risk:** Low  
**Note:** Perfect for single home - cache persists across service restarts via database  

---

### Phase 2: Zigbee2MQTT Expose Storage

**File:** `services/device-intelligence-service/src/core/discovery_service.py`

**Function:** `_store_devices_in_database()` (line ~231)

**Add:** Store capabilities after devices are stored

```python
async def _store_devices_in_database(self, unified_devices: List[UnifiedDevice]):
    """Store unified devices in the database."""
    try:
        logger.info(f"💾 Storing {len(unified_devices)} devices in database")
        
        # ... existing device storage code ...
        
        # NEW: Store capabilities for each device
        from ..core.repository import Repository
        import json
        
        capabilities_data = []
        for device in unified_devices:
            if device.capabilities:
                for cap in device.capabilities:
                    capabilities_data.append({
                        "device_id": device.id,
                        "capability_name": cap.get("name", ""),
                        "capability_type": cap.get("type", ""),
                        "properties": cap.get("properties", {}),  # Full expose JSON
                        "exposed": cap.get("exposed", True),
                        "configured": cap.get("configured", True),
                        "source": cap.get("source", "zigbee2mqtt")
                    })
        
        if capabilities_data:
            async for session in get_db_session():
                repository = Repository()
                await repository.bulk_upsert_capabilities(session, capabilities_data)
                logger.info(f"💾 Stored {len(capabilities_data)} capabilities in database")
                break
        
        logger.info(f"✅ Stored {len(devices_data)} devices in database")
        
    except Exception as e:
        logger.error(f"❌ Error storing devices in database: {e}")
        raise
```

**Impact:** Capabilities stored with full expose data  
**Time:** 20 minutes  
**Risk:** Low (uses existing infrastructure)  
**Note:** DeviceCapability table already exists with composite primary key (device_id + capability_name). Repository.bulk_upsert_capabilities() handles UPSERT logic.  

---

### Phase 3: Cache Invalidation on Updates

**File:** `services/device-intelligence-service/src/core/discovery_service.py`

**Function:** `_on_zigbee_devices_update()` (line ~283)

**Add:** Invalidate cache when devices update via MQTT

```python
async def _on_zigbee_devices_update(self, data: List[Dict[str, Any]]):
    """Handle Zigbee2MQTT devices update."""
    try:
        logger.info(f"📱 Zigbee2MQTT devices updated: {len(data)} devices")
        
        # ... existing update logic ...
        
        # NEW: Invalidate cache for updated devices
        from ..core.cache import get_device_cache
        cache = get_device_cache()
        
        for zigbee_device in self.zigbee_devices.values():
            # Find matching unified device
            for unified_dev in self.unified_devices.values():
                if unified_dev.zigbee_device and unified_dev.zigbee_device.ieee_address == zigbee_device.ieee_address:
                    await cache.invalidate_device(unified_dev.id)
                    logger.debug(f"🗑️ Cache invalidated for device {unified_dev.id}")
        
        # Trigger device unification (this will update cache with fresh data)
        await self._unify_device_data()
        
    except Exception as e:
        logger.error(f"❌ Error handling Zigbee devices update: {e}")
```

**Impact:** Cache stays fresh on MQTT updates  
**Time:** 15 minutes  
**Risk:** Low  
**Note:** For single home with periodic 5-minute discovery, this ensures cache updates whenever Zigbee2MQTT publishes new device data  

---

### Phase 4: Non-MQTT Device Capability Extraction

**File:** `services/device-intelligence-service/src/core/device_parser.py`

**Function:** `_parse_ha_device()` (line ~115)

**Add:** Parse capabilities from Home Assistant entities

```python
# NEW METHOD
def _parse_ha_entity_capabilities(self, entities: List[HAEntity], domain: str) -> List[Dict[str, Any]]:
    """
    Extract capabilities from Home Assistant entity domains.
    
    Inferred from domain and typical HA capabilities.
    """
    capabilities = []
    
    # Domain-specific capability mapping
    domain_capabilities = {
        "light": {
            "brightness": {"type": "numeric", "range": [0, 255], "step": 1},
            "color_temp": {"type": "numeric", "range": [153, 500]},
            "color": {"type": "color_rgb"},
            "effect": {"type": "enum"}
        },
        "switch": {
            "state": {"type": "binary", "values": ["ON", "OFF"]}
        },
        "fan": {
            "speed": {"type": "enum", "values": ["off", "low", "medium", "high"]},
            "oscillate": {"type": "binary"},
            "direction": {"type": "enum", "values": ["forward", "reverse"]}
        },
        "climate": {
            "temperature": {"type": "numeric"},
            "hvac_modes": {"type": "enum", "values": ["off", "heat", "cool", "auto", "fan_only"]},
            "preset_modes": {"type": "enum"},
            "fan_modes": {"type": "enum"}
        },
        "cover": {
            "position": {"type": "numeric", "range": [0, 100]},
            "tilt_position": {"type": "numeric", "range": [0, 100]}
        },
        "sensor": {
            "state_class": {"type": "text"},
            "unit_of_measurement": {"type": "text"}
        },
        "binary_sensor": {
            "state": {"type": "binary"}
        }
    }
    
    if domain in domain_capabilities:
        for cap_name, cap_props in domain_capabilities[domain].items():
            capabilities.append({
                "name": cap_name,
                "type": cap_props.get("type", "unknown"),
                "properties": {
                    **cap_props,
                    "inferred": True,  # Mark as inferred (not actual expose)
                    "supported": True  # Assume supported
                },
                "exposed": False,  # Not truly "exposed" but available
                "configured": True,
                "source": "homeassistant"
            })
    
    logger.debug(f"📋 Inferred {len(capabilities)} capabilities from {domain} domain")
    return capabilities
```

**Update `_parse_ha_device()` method:**

```python
def _parse_ha_device(
    self,
    ha_device: HADevice,
    ha_entities: List[HAEntity],
    zigbee_devices: Dict[str, ZigbeeDevice]
) -> Optional[UnifiedDevice]:
    """Parse a Home Assistant device into unified format."""
    
    # Find matching Zigbee device
    zigbee_device = self._find_matching_zigbee_device(ha_device, zigbee_devices)
    
    # Get device entities
    device_entities = [e for e in ha_entities if e.device_id == ha_device.id]
    
    # Parse capabilities from Zigbee device if available
    capabilities = []
    if zigbee_device and zigbee_device.exposes:
        capabilities = self._parse_zigbee_capabilities(zigbee_device.exposes)
    else:
        # NEW: Parse capabilities from HA entities for non-Zigbee devices
        device_class = self._extract_device_class(device_entities)
        if device_class:
            capabilities = self._parse_ha_entity_capabilities(device_entities, device_class)
    
    # ... rest of existing code ...
```

**Impact:** Non-MQTT devices now have capabilities  
**Time:** 30 minutes  
**Risk:** Medium (new parsing logic)  
**Note:** For single home, inferred capabilities are sufficient. No need for real-time entity state fetching which would add complexity and WebSocket overhead  

---

### Phase 5: Enhanced API Response

**File:** `services/device-intelligence-service/src/api/discovery.py`

**Function:** `get_device_by_id()` (line ~225)

**Enhance:** Fetch capabilities from database if not in memory

```python
@router.get("/devices/{device_id}", response_model=DeviceResponse)
async def get_device_by_id(
    device_id: str,
    discovery_service: DiscoveryService = Depends(get_discovery_service)
) -> DeviceResponse:
    """
    Get specific device by ID.
    
    Returns:
        DeviceResponse: Device details with full capabilities
    """
    try:
        # Get device from discovery service
        device = discovery_service.get_device_by_id(device_id)
        
        if not device:
            raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
        
        # NEW: Fetch capabilities from database if missing
        if not device.capabilities:
            from ..core.repository import Repository
            async for session in get_db_session():
                repository = Repository()
                caps = await repository.get_device_capabilities(session, device_id)
                device.capabilities = [cap.to_dict() for cap in caps]
                break
        
        # Convert to response format
        device_response = DeviceResponse(
            id=device.id,
            name=device.name,
            manufacturer=device.manufacturer,
            model=device.model,
            area_id=device.area_id,
            area_name=device.area_name,
            integration=device.integration,
            capabilities=device.capabilities or [],  # Ensure not None
            entities=device.entities or [],
            health_score=device.health_score,
            last_seen=device.last_seen.isoformat() if device.last_seen else None,
            created_at=device.created_at.isoformat(),
            updated_at=device.updated_at.isoformat()
        )
        
        return device_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting device: {str(e)}")
```

**Impact:** API returns complete capability data  
**Time:** 15 minutes  
**Risk:** Low  

---

### Phase 6: Testing & Validation

**Test Plan:**

1. **Zigbee2MQTT Device Test**
   ```bash
   # Request device endpoint
   curl http://localhost:8021/api/discovery/devices/0x00158d00017b4e7a
   
   # Verify capabilities include full breeze_mode structure
   # Verify cache hit on second request (<1ms)
   ```

2. **Non-MQTT Device Test**
   ```bash
   # Request Hue light
   curl http://localhost:8021/api/discovery/devices/{hue_device_id}
   
   # Verify capabilities include brightness, color_temp, etc.
   # Verify source is "homeassistant"
   ```

3. **Cache Invalidation Test**
   ```bash
   # Request device (populates cache)
   # Update device in Zigbee2MQTT
   # Wait for MQTT update
   # Request device again
   # Should see fresh data (cache invalidated)
   ```

4. **Cache Expiration Test**
   ```bash
   # Request device
   # Wait 6 hours 1 minute
   # Request device again
   # Should fetch from database (cache expired)
   ```

**Impact:** Validates complete functionality  
**Time:** 30 minutes  
**Risk:** Low (testing only)  

---

## Updated JSON Response Examples

### Zigbee2MQTT Device (Office Fan Switch)

```json
{
  "id": "0x00158d00017b4e7a",
  "name": "Office Fan Switch",
  "manufacturer": "Inovelli",
  "model": "VZM35-SN",
  "area_name": "Office",
  "integration": "zigbee2mqtt",
  "device_class": "fan",
  
  "capabilities": [
    {
      "name": "state",
      "type": "binary",
      "properties": {
        "name": "state",
        "type": "enum",
        "access": 7,
        "values": ["OFF", "ON"],
        "description": "On/off state of this fan"
      },
      "exposed": true,
      "source": "zigbee2mqtt"
    },
    {
      "name": "mode",
      "type": "enum",
      "properties": {
        "name": "mode",
        "type": "enum",
        "access": 7,
        "values": ["off", "low", "smart", "medium", "high", "on"],
        "description": "Mode of this fan"
      },
      "exposed": true,
      "source": "zigbee2mqtt"
    },
    {
      "name": "breeze_mode",
      "type": "composite",
      "properties": {
        "name": "breeze_mode",
        "type": "composite",
        "features": [
          {
            "name": "speed1",
            "type": "enum",
            "property": {
              "name": "speed1",
              "type": "enum",
              "values": ["low", "medium", "high"],
              "description": "Step 1 Speed"
            }
          },
          {
            "name": "time1",
            "type": "numeric",
            "property": {
              "name": "time1",
              "type": "numeric",
              "unit": "s",
              "access": 7,
              "value_min": 1,
              "value_max": 80,
              "description": "Duration (s) for fan in Step 1"
            }
          },
          {
            "name": "speed2",
            "type": "enum",
            "property": {
              "name": "speed2",
              "type": "enum",
              "values": ["low", "medium", "high"],
              "description": "Step 2 Speed"
            }
          },
          {
            "name": "time2",
            "type": "numeric",
            "property": {
              "name": "time2",
              "type": "numeric",
              "unit": "s",
              "access": 7,
              "value_min": 1,
              "value_max": 80,
              "description": "Duration (s) for fan in Step 2"
            }
          }
        ],
        "description": "Breeze mode configuration"
      },
      "exposed": true,
      "source": "zigbee2mqtt"
    }
  ],
  
  "entities": [...],
  "health_score": 95,
  "last_seen": "2025-01-20T15:30:45Z"
}
```

### Non-MQTT Device (Philips Hue Light)

```json
{
  "id": "abc123def456",
  "name": "Living Room Light",
  "manufacturer": "Philips Hue",
  "model": "LCT015",
  "area_name": "Living Room",
  "integration": "hue",
  "device_class": "light",
  
  "capabilities": [
    {
      "name": "brightness",
      "type": "numeric",
      "properties": {
        "type": "numeric",
        "range": [0, 255],
        "step": 1,
        "inferred": true,
        "supported": true
      },
      "exposed": false,
      "source": "homeassistant"
    },
    {
      "name": "color_temp",
      "type": "numeric",
      "properties": {
        "type": "numeric",
        "range": [153, 500],
        "inferred": true,
        "supported": true
      },
      "exposed": false,
      "source": "homeassistant"
    },
    {
      "name": "color",
      "type": "color_rgb",
      "properties": {
        "type": "color_rgb",
        "inferred": true,
        "supported": true
      },
      "exposed": false,
      "source": "homeassistant"
    },
    {
      "name": "effect",
      "type": "enum",
      "properties": {
        "type": "enum",
        "inferred": true,
        "supported": true
      },
      "exposed": false,
      "source": "homeassistant"
    }
  ],
  
  "entities": [
    {
      "entity_id": "light.living_room_light",
      "name": "Living Room Light",
      "domain": "light",
      "platform": "hue"
    }
  ],
  
  "health_score": 90,
  "last_seen": "2025-01-20T15:35:12Z"
}
```

---

## Implementation Timeline

| Phase | Task | Time | Risk | Priority |
|-------|------|------|------|----------|
| 1 | Update cache TTL to 6 hours | 2 min | Low | High |
| 2 | Store Zigbee2MQTT capabilities in DB | 20 min | Low | High |
| 3 | Cache invalidation on MQTT updates | 15 min | Low | High |
| 4 | Non-MQTT capability extraction | 30 min | Medium | High |
| 5 | Enhanced API response | 15 min | Low | Medium |
| 6 | Testing & validation | 30 min | Low | High |
| **Total** | | **~112 minutes** | | |

---

## Success Criteria

### Functional Requirements
- [ ] All Zigbee2MQTT exposes stored in database
- [ ] All non-MQTT devices have inferred capabilities
- [ ] API responses include full capability details
- [ ] Cache TTL set to 6 hours
- [ ] Cache invalidates on MQTT updates
- [ ] Capability storage in `device_capabilities` table working

### Performance Requirements
- [ ] Cache hit response time <1ms
- [ ] Cache miss response time <20ms
- [ ] Database storage working without errors
- [ ] Cache cleanup removing expired entries

### Data Quality Requirements
- [ ] Zigbee2MQTT devices show `source: "zigbee2mqtt"`
- [ ] Non-MQTT devices show `source: "homeassistant"`
- [ ] Full expose data preserved in properties JSON
- [ ] Inferred capabilities marked with `inferred: true`
- [ ] Device relationships maintained

---

## Rollback Plan

If issues occur:

1. **Revert cache changes** - Restore to 5-minute TTL
2. **Skip capability storage** - Comment out database writes
3. **Disable entity parsing** - Use only Zigbee2MQTT data
4. **Keep core functionality** - Basic device retrieval still works

**Backup:** Database can be recreated if needed using existing recreate scripts

---

## Dependencies

### Required
- ✅ Device Intelligence Service running
- ✅ Zigbee2MQTT connected via MQTT
- ✅ Home Assistant WebSocket connected
- ✅ SQLite database initialized
- ✅ Cache infrastructure exists

### Optional (for testing)
- Multiple devices (Zigbee and non-Zigbee)
- Different domains (light, fan, climate, etc.)

---

## Single-Home Optimizations

### Simplified for Single-Home Deployment

1. **No entity state fetching** - Inferred capabilities are sufficient for single-home
   - Real-time state would require additional WebSocket calls
   - Inferred from domain is fast and accurate enough
   - Cache handles rest of the work

2. **Simple cache invalidation** - Device-level is sufficient
   - Single process = no distributed cache concerns
   - Invalidating entire device when one capability updates is fine
   - Simpler code, easier debugging

3. **No custom capability definitions** - Keep it simple
   - Standard domains cover 99% of use cases
   - Adding customization would complicate schema and queries
   - Not needed for single-home deployment

4. **Database persistence** - Already in use
   - Cache is populated from database on service restart
   - No data loss on restart
   - Periodic discovery (5 min) ensures fresh data

### Why This Works for Single-Home

**Typical Single-Home Characteristics:**
- 50-200 devices max
- Single service instance
- Single process cache
- No horizontal scaling needed
- Periodic updates (5 minutes) are fine
- Database serves as source of truth

**Performance Profile:**
- Cache hit: ~0.1ms (in-memory)
- Cache miss: ~10-20ms (database query)
- Database storage: ~100ms per device (one-time)
- No Redis overhead
- No network latency

This is **exactly** what single-home needs - simple, fast, reliable.

---

## Next Steps

1. **Review this plan** - Confirm approach and timeline
2. **Approve changes** - Get sign-off from stakeholder
3. **Implement phases** - Execute in order with testing after each
4. **Validate results** - Ensure all success criteria met
5. **Document changes** - Update architecture docs

---

## Questions for Review

1. **Is 6-hour cache TTL acceptable?** ✅ YES - Perfect for single-home
   - Device capabilities don't change frequently
   - Periodic discovery updates (5 min) invalidate when needed
   - Much better than 5-minute TTL for performance

2. **Should we prioritize Zigbee2MQTT devices first, then add HA parsing?** ✅ YES - Phased approach recommended
   - Phase 1-3: Zigbee2MQTT (simpler, more data)
   - Phase 4: Non-MQTT (inferred capabilities)
   - Test each phase before moving on

3. **Are inferred capabilities sufficient for non-MQTT devices?** ✅ YES - For single-home
   - Real-time fetching would add complexity
   - Inferred from domain is accurate enough
   - Cache handles performance

4. **Should we add entity state fetching?** ❌ NO - Not for single-home
   - Adds WebSocket overhead
   - Inferred capabilities are sufficient
   - Keep it simple

## Single-Home Deployment Recommendation

**Implement phases 1-3 first** (Zigbee2MQTT only), then add phase 4 (non-MQTT devices) as enhancement.

This provides:
- ✅ Immediate value for Zigbee devices
- ✅ Simpler implementation
- ✅ Easier testing
- ✅ Room to add non-MQTT capabilities later

---

## Approval

**Status:** Awaiting Review  
**Date:** January 2025  
**Next:** Implementation upon approval

