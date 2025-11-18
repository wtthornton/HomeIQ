# Entity Registry Name Fields Issue - Recommendations

**Date:** January 2025  
**Issue:** Entity registry name fields (name, name_by_user, original_name, friendly_name) are NULL in database  
**Root Cause:** Discovery service failing due to WebSocket concurrency ("Concurrent call to receive() is not allowed")

## Problem Analysis

### Current Architecture Issue

1. **WebSocket Concurrency Conflict:**
   - `connection_manager.py:223` - Main event loop calls `client.listen()` which continuously receives messages
   - `connection_manager.py:319` - Discovery service tries to use same WebSocket with `discover_all(websocket)`
   - `discovery_service.py:305` - `_wait_for_response()` calls `websocket.receive()` directly
   - **Result:** "Concurrent call to receive() is not allowed" error

2. **Discovery Flow:**
   ```
   Connection → Subscribe to Events → Start listen() loop → Discovery tries to use same WebSocket → FAILS
   ```

3. **Evidence:**
   - Entities exist in database but name fields are NULL
   - `bulk_upsert_entities` endpoint correctly extracts name fields (lines 896-901 in devices_endpoints.py)
   - Discovery never successfully completes to populate these fields

## Recommended Solutions (Ranked)

### ✅ **Option 1: Use HTTP API for Discovery (RECOMMENDED)**

**Why:** Cleanest solution, avoids concurrency entirely, already proven pattern

**Implementation:**
- Convert `discover_devices()` and `discover_entities()` to use HTTP API (like `discover_services()` already does)
- Use endpoints:
  - `GET /api/config/device_registry/list`
  - `GET /api/config/entity_registry/list`
- Remove WebSocket dependency from discovery methods
- Keep WebSocket only for event streaming

**Pros:**
- ✅ No concurrency issues
- ✅ Simpler code (no message ID tracking)
- ✅ Already proven pattern (services discovery uses HTTP)
- ✅ Can run discovery independently of WebSocket connection
- ✅ Scripts already demonstrate this works (`refresh-entity-registry.py`)

**Cons:**
- ⚠️ Requires HTTP URL and token (already available in env)

**Effort:** Low (2-3 hours)
**Risk:** Low

**Code Changes:**
```python
# discovery_service.py - New methods
async def discover_devices_http(self) -> List[Dict[str, Any]]:
    """Discover devices via HTTP API"""
    ha_url = os.getenv('HA_HTTP_URL') or os.getenv('HOME_ASSISTANT_URL', 'http://192.168.1.86:8123')
    ha_token = os.getenv('HA_TOKEN') or os.getenv('HOME_ASSISTANT_TOKEN')
    
    headers = {
        "Authorization": f"Bearer {ha_token}",
        "Content-Type": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{ha_url}/api/config/device_registry/list", headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                logger.error(f"Failed to fetch devices: {response.status}")
                return []

async def discover_entities_http(self) -> List[Dict[str, Any]]:
    """Discover entities via HTTP API"""
    # Similar implementation using /api/config/entity_registry/list
```

---

### Option 2: Separate WebSocket Connection for Discovery

**Why:** Maintains WebSocket pattern, isolates discovery from event streaming

**Implementation:**
- Create separate WebSocket connection in discovery service
- Use it only for discovery operations
- Close after discovery completes

**Pros:**
- ✅ Isolates discovery from event streaming
- ✅ No changes to existing WebSocket client code

**Cons:**
- ⚠️ More complex (managing two WebSocket connections)
- ⚠️ Higher resource usage
- ⚠️ Still potential for connection limits

**Effort:** Medium (4-6 hours)
**Risk:** Medium

**Code Pattern:**
```python
# discovery_service.py
async def discover_all_standalone(self) -> Dict[str, Any]:
    """Discover using separate WebSocket connection"""
    websocket_url = f"{ha_url}/api/websocket"
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(websocket_url, headers=auth_headers) as ws:
            # Auth flow
            # Run discovery
            # Close connection
```

---

### Option 3: Message Router/Queue Pattern

**Why:** Allows discovery to intercept messages from main receive loop

**Implementation:**
- Create message router that routes messages to appropriate handlers
- Discovery registers interest in specific message IDs
- Main loop routes responses to discovery when message ID matches

**Pros:**
- ✅ Single WebSocket connection
- ✅ No HTTP API dependency

**Cons:**
- ⚠️ Complex architecture change
- ⚠️ Requires refactoring message handling
- ⚠️ Higher risk of bugs

**Effort:** High (8-12 hours)
**Risk:** High

---

### Option 4: Trigger Discovery Before Listen Loop

**Why:** Simple timing fix

**Implementation:**
- Run discovery immediately after connection, before starting `listen()` loop
- Only works for initial discovery, not periodic refreshes

**Pros:**
- ✅ Minimal code changes

**Cons:**
- ⚠️ Doesn't solve periodic refresh problem
- ⚠️ Still has concurrency risk if discovery takes too long
- ⚠️ Doesn't help if connection drops and reconnects

**Effort:** Low (1 hour)
**Risk:** Medium (doesn't fully solve problem)

---

## Recommended Implementation Plan

### Phase 1: Implement HTTP API Discovery (Option 1)

1. **Update `discovery_service.py`:**
   - Add `discover_devices_http()` method
   - Add `discover_entities_http()` method
   - Update `discover_all()` to use HTTP methods
   - Keep WebSocket methods for backward compatibility (deprecated)

2. **Update `connection_manager.py`:**
   - Call `discover_all()` without WebSocket parameter (or make it optional)
   - Discovery service handles HTTP internally

3. **Testing:**
   - Verify entities are discovered with name fields populated
   - Verify no WebSocket concurrency errors
   - Verify discovery can run independently

### Phase 2: Verify Name Fields Population

1. **Check specific devices:**
   - Run discovery
   - Query database for `light.hue_color_downlight_1_5`
   - Verify `name_by_user = "LR Back Right Ceiling"` (or correct value from HA)

2. **Verify all Hue devices:**
   - Check all 4 Hue devices mentioned
   - Ensure name fields are populated from HA Entity Registry

### Phase 3: Add Periodic Refresh (Optional)

1. **Add scheduled discovery:**
   - Run discovery every 30 minutes (or configurable)
   - Use HTTP API (no concurrency issues)
   - Update entity registry name fields if changed in HA

---

## Immediate Action Items

1. ✅ **Implement Option 1 (HTTP API Discovery)**
   - Convert `discover_devices()` to HTTP
   - Convert `discover_entities()` to HTTP
   - Test and verify name fields populate

2. ✅ **Verify Entity Mapping**
   - Run `scripts/check-ha-entity-names.py` to see actual entity IDs and names in HA
   - Map "Hue Office Back Left" to correct entity_id
   - Verify `name_by_user` values match expectations

3. ✅ **Test Discovery**
   - Run discovery via HTTP API
   - Verify `bulk_upsert_entities` receives complete entity data
   - Verify database has name fields populated

---

## Code Reference

**Current HTTP API Pattern (Services Discovery):**
```374:416:HomeIQ/services/websocket-ingestion/src/discovery_service.py
    async def discover_services(self, websocket: ClientWebSocketResponse) -> Dict[str, Dict[str, Any]]:
        """
        Discover available services from Home Assistant Services API.
        
        Epic 2025: Fetch all available services per domain for service validation.
        
        Args:
            websocket: Connected WebSocket client
            
        Returns:
            Dictionary mapping domain -> {service_name -> service_data}
        """
        try:
            logger.info("🔍 Discovering services from HA Services API...")
            
            # Use HTTP API to fetch services (Services API doesn't have WebSocket command)
            import aiohttp
            import os
            
            ha_url = os.getenv('HA_HTTP_URL') or os.getenv('HOME_ASSISTANT_URL', 'http://192.168.1.86:8123')
            ha_token = os.getenv('HA_TOKEN') or os.getenv('HOME_ASSISTANT_TOKEN')
            
            if not ha_token:
                logger.warning("⚠️  No HA token available for services discovery")
                return {}
            
            headers = {
                "Authorization": f"Bearer {ha_token}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{ha_url}/api/services", headers=headers) as response:
                    if response.status == 200:
                        services_data = await response.json()
                        logger.info(f"✅ Retrieved {len(services_data)} service domains from HA")
                        return services_data
                    else:
                        logger.warning(f"Failed to get services from HA: {response.status}")
                        return {}
        except Exception as e:
            logger.error(f"Error discovering services: {e}", exc_info=True)
            return {}
```

**bulk_upsert_entities (Correctly Extracts Name Fields):**
```896:925:HomeIQ/services/data-api/src/devices_endpoints.py
            # Extract name fields from entity registry data
            name = entity_data.get('name')  # Primary name (what shows in HA UI)
            name_by_user = entity_data.get('name_by_user')  # User-customized name
            original_name = entity_data.get('original_name')  # Original name
            
            # Compute friendly_name (priority: name_by_user > name > original_name > entity_id)
            friendly_name = name_by_user or name or original_name
            if not friendly_name:
                # Fallback: derive from entity_id
                friendly_name = entity_id.split('.')[-1].replace('_', ' ').title()
            
            # Capabilities will be enriched separately from State API
            # For now, set to None - will be populated by entity_capability_enrichment service
            supported_features = None
            capabilities = None
            available_services = None
            
            # Create entity instance
            entity = Entity(
                entity_id=entity_id,
                device_id=entity_data.get('device_id'),
                domain=domain,
                platform=entity_data.get('platform', 'unknown'),
                unique_id=entity_data.get('unique_id'),
                area_id=entity_data.get('area_id'),
                disabled=entity_data.get('disabled_by') is not None,
                # NEW: Entity Registry name fields
                name=name,
                name_by_user=name_by_user,
                original_name=original_name,
                friendly_name=friendly_name,
```

**Working HTTP API Script:**
- `scripts/refresh-entity-registry.py` - Demonstrates HTTP API works perfectly
- `scripts/standalone-entity-discovery.py` - Demonstrates separate WebSocket works

---

## Decision Matrix

| Option | Effort | Risk | Maintainability | Performance | **Recommendation** |
|--------|--------|------|-----------------|-------------|-------------------|
| **Option 1: HTTP API** | Low | Low | High | High | ✅ **BEST** |
| Option 2: Separate WS | Medium | Medium | Medium | Medium | ⚠️ Acceptable |
| Option 3: Message Router | High | High | Low | High | ❌ Over-engineered |
| Option 4: Timing Fix | Low | Medium | High | High | ⚠️ Partial solution |

---

## Conclusion

**Recommended Approach:** Implement Option 1 (HTTP API Discovery)

This is the cleanest, lowest-risk solution that:
- Eliminates WebSocket concurrency issues completely
- Follows existing pattern (services discovery already uses HTTP)
- Allows discovery to run independently
- Simplifies code (no message ID tracking needed)
- Has proven working examples in existing scripts

**Next Steps:**
1. Implement HTTP API discovery methods
2. Update `discover_all()` to use HTTP methods
3. Test and verify name fields populate correctly
4. Verify specific Hue device mappings

