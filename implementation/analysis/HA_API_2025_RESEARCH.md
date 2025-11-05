# Home Assistant API 2025 Research - Missing Calls and Data

**Date:** January 6, 2025  
**Purpose:** Research HA API 2025 capabilities to identify missing calls and data that could improve device discovery and entity resolution  
**Status:** Complete Research

---

## Executive Summary

This document identifies **missing HA API calls and data** that could significantly improve our device discovery and entity resolution during suggestion creation. Key findings:

1. **✅ We're using:** Device registry, entity registry, area registry via WebSocket
2. **❌ We're missing:** Real-time entity queries by area/domain, entity attributes during resolution, WebSocket subscription for registry updates
3. **⚠️ We're partially using:** State API (only for single entities, not bulk queries by area)

**Critical Gap:** During suggestion generation, we query cached SQLite database instead of making real-time HA API calls to get the latest entity list.

---

## 1. Current HA API Usage

### What We're Currently Using

#### A. Device Intelligence Service (WebSocket)

**Location:** `services/device-intelligence-service/src/clients/ha_client.py`

**Endpoints Used:**
1. ✅ `config/device_registry/list` - Get all devices
2. ✅ `config/entity_registry/list` - Get all entities  
3. ✅ `config/area_registry/list` - Get all areas

**Code Reference:**
```284:386:services/device-intelligence-service/src/clients/ha_client.py
async def get_device_registry(self) -> List[HADevice]:
    """Get all devices from Home Assistant device registry."""
    try:
        response = await self.send_message({
            "type": "config/device_registry/list"
        })
        
async def get_entity_registry(self) -> List[HAEntity]:
    """Get all entities from Home Assistant entity registry."""
    try:
        response = await self.send_message({
            "type": "config/entity_registry/list"
        })
        
async def get_area_registry(self) -> List[HAArea]:
    """Get all areas from Home Assistant area registry."""
    try:
        response = await self.send_message({
            "type": "config/area_registry/list"
        })
```

**Limitations:**
- ❌ No filtering by area or domain (gets ALL entities)
- ❌ No real-time updates (cached, refreshed every 5 minutes)
- ❌ No subscription to registry changes

#### B. AI Automation Service (REST API)

**Location:** `services/ai-automation-service/src/clients/ha_client.py`

**Endpoints Used:**
1. ✅ `GET /api/states/{entity_id}` - Get single entity state
2. ✅ `GET /api/states` - Get all states (for domain filtering)
3. ✅ `GET /api/config` - Get HA version/config

**Code Reference:**
```750:833:services/ai-automation-service/src/clients/ha_client.py
async def get_entity_state(self, entity_id: str) -> Optional[Dict[str, Any]]:
    """Get current state and attributes for an entity from Home Assistant."""
    url = f"{self.ha_url}/api/states/{entity_id}"
    
async def get_entities_by_domain(self, domain: str) -> List[str]:
    """Get all entity IDs for a specific domain from Home Assistant."""
    url = f"{self.ha_url}/api/states"
    # Filters by domain prefix after fetching ALL states
```

**Limitations:**
- ❌ `get_entities_by_domain()` fetches ALL states then filters (inefficient)
- ❌ No method to get entities by area
- ❌ No method to get entities by area + domain combination
- ❌ No access to entity registry metadata (only states)

---

## 2. Missing HA API Capabilities (2025)

### A. Entity Registry Filtering (WebSocket)

**Available in HA 2025:** Entity registry supports filtering by area and domain via WebSocket commands.

**What We're Missing:**

#### 1. Get Entities by Area (WebSocket)

**Command:**
```json
{
  "id": 1,
  "type": "config/entity_registry/list",
  "area_id": "office"  // ⚠️ This parameter may not be supported directly
}
```

**Alternative Approach:** Use `get_states` with area filtering:
```json
{
  "id": 1,
  "type": "get_states",
  "area_id": "office"  // ⚠️ Check if this is supported
}
```

**Or:** Fetch all entities and filter client-side (current approach, but inefficient).

#### 2. Get Entities by Area + Domain (WebSocket)

**What We Need:**
- Get all entities in "office" area
- Filter to only "light" domain
- Return entity registry metadata (not just states)

**Current Workaround:** Fetch all entities, filter by area_id and domain.

**Problem:** We're doing this in cached database, not real-time from HA.

---

### B. REST API Endpoints (2025)

**Available in HA 2025:**

#### 1. Template API - Filter Entities by Area

**Endpoint:** `POST /api/template`

**Capability:** Use Jinja2 templates to query entities by area and domain.

**Example:**
```python
template = """
{% set office_lights = states.light | selectattr('attributes.area_id', 'eq', 'office') | list %}
{{ office_lights | map(attribute='entity_id') | list | tojson }}
"""

response = requests.post(
    f"{ha_url}/api/template",
    headers={"Authorization": f"Bearer {token}"},
    json={"template": template}
)
office_light_entities = response.json()
```

**What We're Missing:**
- ❌ No template API usage for entity queries
- ❌ No helper method to get entities by area + domain

#### 2. Conversation API / Assist API

**Endpoint:** `POST /api/conversation/process`

**Capability:** HA's built-in conversation agent can resolve entities from natural language.

**What We're Missing:**
- ❌ Not using Assist API for entity resolution
- ❌ Could leverage HA's built-in entity matching

**Note:** Assist API is designed for LLM integration and may provide better entity resolution than our current approach.

---

### C. WebSocket Subscriptions (2025)

**Available in HA 2025:**

#### 1. Subscribe to Entity Registry Updates

**Command:**
```json
{
  "id": 1,
  "type": "subscribe_events",
  "event_type": "entity_registry_updated"
}
```

**What We're Missing:**
- ❌ Not subscribing to entity registry updates
- ❌ Missing real-time entity additions/removals
- ❌ Database can become stale

#### 2. Subscribe to Device Registry Updates

**Command:**
```json
{
  "id": 2,
  "type": "subscribe_events",
  "event_type": "device_registry_updated"
}
```

**What We're Missing:**
- ❌ Not subscribing to device registry updates
- ❌ Missing real-time device additions/removals

---

### D. Entity Registry Metadata (2025)

**What Entity Registry Provides (We're Missing):**

1. **Entity Attributes:**
   - `friendly_name` - Display name
   - `device_class` - Device class (motion, temperature, etc.)
   - `unit_of_measurement` - Unit (if applicable)
   - `icon` - Icon identifier
   - `capabilities` - Supported features
   - `supported_features` - Feature flags

2. **Entity Relationships:**
   - `device_id` - Parent device
   - `area_id` - Assigned area
   - `config_entry_id` - Integration config entry
   - `platform` - Integration platform

3. **Entity Status:**
   - `disabled_by` - Why entity is disabled (if applicable)
   - `hidden_by` - Why entity is hidden (if applicable)
   - `entity_category` - Category (config, diagnostic, etc.)

**Current Gap:** We get entity attributes from `/api/states/{entity_id}`, but we don't get entity registry metadata during bulk queries.

---

## 3. Recommended Improvements

### Priority 1: Real-Time Entity Queries by Area

**Problem:** We query cached SQLite database instead of HA API during suggestion generation.

**Solution:** Add real-time HA API query for entities by area + domain.

**Implementation:**

#### A. Add WebSocket Method to HA Client

```python
# services/ai-automation-service/src/clients/ha_client.py

async def get_entities_by_area_and_domain(
    self, 
    area_id: str, 
    domain: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get entities from HA entity registry filtered by area and optionally domain.
    
    Uses WebSocket API for real-time data.
    
    Args:
        area_id: Area ID to filter by (e.g., "office")
        domain: Optional domain filter (e.g., "light")
        
    Returns:
        List of entity registry entries with full metadata
    """
    # Get all entities from entity registry
    response = await self.websocket_client.send_message({
        "type": "config/entity_registry/list"
    })
    
    entities = response.get("result", [])
    
    # Filter by area_id
    filtered = [
        e for e in entities 
        if e.get("area_id") == area_id
    ]
    
    # Filter by domain if specified
    if domain:
        filtered = [
            e for e in filtered 
            if e.get("domain") == domain or e.get("entity_id", "").startswith(f"{domain}.")
        ]
    
    return filtered
```

#### B. Use in Entity Resolution

**Location:** `services/ai-automation-service/src/services/entity_validator.py`

**Current Code:**
```183:217:services/ai-automation-service/src/services/entity_validator.py
async def _get_available_entities(
    self,
    domain: Optional[str] = None,
    area_id: Optional[str] = None,
    integration: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get available entities from data-api with optional filtering.
    """
    if self.data_api_client:
        entities = await self.data_api_client.fetch_entities(
            domain=domain,
            area_id=area_id,
            platform=integration
        )
        # ⚠️ This queries SQLite database, NOT HA directly
        return entities
```

**Improved Code:**
```python
async def _get_available_entities(
    self,
    domain: Optional[str] = None,
    area_id: Optional[str] = None,
    integration: Optional[str] = None,
    use_realtime: bool = True  # NEW: Option to use real-time HA API
) -> List[Dict[str, Any]]:
    """
    Get available entities with optional filtering.
    
    Args:
        use_realtime: If True, query HA API directly. If False, use cached database.
    """
    if use_realtime and self.ha_client:
        # ✅ Real-time query from HA
        entities = await self.ha_client.get_entities_by_area_and_domain(
            area_id=area_id,
            domain=domain
        )
        return entities
    else:
        # Fallback to cached database
        if self.data_api_client:
            entities = await self.data_api_client.fetch_entities(
                domain=domain,
                area_id=area_id,
                platform=integration
            )
            return entities
    return []
```

---

### Priority 2: Template API for Complex Queries

**Problem:** We need to query entities by area + domain, but entity registry doesn't support direct filtering.

**Solution:** Use HA Template API for flexible queries.

**Implementation:**

```python
# services/ai-automation-service/src/clients/ha_client.py

async def get_entities_by_area_template(
    self,
    area_id: str,
    domain: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get entities by area using HA Template API.
    
    More flexible than WebSocket API, supports complex queries.
    """
    if domain:
        template = f"""
        {{% set entities = states.{domain} | selectattr('attributes.area_id', 'eq', '{area_id}') | list %}}
        {{{{ entities | map(attribute='entity_id') | list | tojson }}}}
        """
    else:
        template = f"""
        {{% set all_entities = states | list %}}
        {{% set filtered = all_entities | selectattr('attributes.area_id', 'eq', '{area_id}') | list %}}
        {{{{ filtered | map(attribute='entity_id') | list | tojson }}}}
        """
    
    response = await self._retry_request(
        'POST',
        '/api/template',
        return_json=True,
        json={"template": template}
    )
    
    entity_ids = response if isinstance(response, list) else []
    
    # Get full entity registry data for each entity
    entities = []
    for entity_id in entity_ids:
        entity_data = await self.get_entity_registry_entry(entity_id)
        if entity_data:
            entities.append(entity_data)
    
    return entities

async def get_entity_registry_entry(self, entity_id: str) -> Optional[Dict[str, Any]]:
    """Get entity registry entry for a specific entity."""
    # Would need WebSocket client or REST API endpoint
    # Check if HA has REST endpoint for this
    pass
```

**Note:** Template API returns states, not entity registry entries. We'd need to combine with entity registry lookup.

---

### Priority 3: WebSocket Subscriptions for Real-Time Updates

**Problem:** Device/entity registry cache becomes stale (5-minute refresh).

**Solution:** Subscribe to registry update events.

**Implementation:**

```python
# services/device-intelligence-service/src/clients/ha_client.py

async def subscribe_to_registry_updates(self):
    """Subscribe to device and entity registry update events."""
    
    # Subscribe to entity registry updates
    await self.send_message({
        "type": "subscribe_events",
        "event_type": "entity_registry_updated"
    })
    
    # Subscribe to device registry updates
    await self.send_message({
        "type": "subscribe_events",
        "event_type": "device_registry_updated"
    })
    
    logger.info("✅ Subscribed to registry update events")

async def _handle_registry_event(self, event_data: Dict[str, Any]):
    """Handle registry update event."""
    event_type = event_data.get("event", {}).get("event_type")
    
    if event_type == "entity_registry_updated":
        action = event_data.get("event", {}).get("action")  # create, update, remove
        entity_id = event_data.get("event", {}).get("entity_id")
        
        if action == "create":
            # New entity added - refresh cache
            await self._refresh_entity_cache(entity_id)
        elif action == "remove":
            # Entity removed - remove from cache
            await self._remove_entity_from_cache(entity_id)
        elif action == "update":
            # Entity updated - refresh cache
            await self._refresh_entity_cache(entity_id)
    
    elif event_type == "device_registry_updated":
        action = event_data.get("event", {}).get("action")
        device_id = event_data.get("event", {}).get("device_id")
        
        # Similar handling for device updates
        await self._handle_device_update(action, device_id)
```

---

### Priority 4: Assist API for Entity Resolution

**Problem:** Our entity extraction from natural language may not match HA's understanding.

**Solution:** Use HA's Assist API for entity resolution.

**Available in HA 2025:** Assist API endpoint

**Endpoint:** `POST /api/conversation/process`

**Example:**
```python
async def resolve_entities_with_assist_api(
    self,
    query: str
) -> Dict[str, Any]:
    """
    Use HA's Assist API to resolve entities from natural language.
    
    Returns structured response with matched entities.
    """
    response = await self._retry_request(
        'POST',
        '/api/conversation/process',
        return_json=True,
        json={
            "text": query,
            "language": "en",
            "conversation_id": None
        }
    )
    
    # Parse response to extract entities
    # Assist API returns structured intent with entity matches
    return response
```

**Benefits:**
- ✅ Uses HA's built-in entity matching
- ✅ Understands HA-specific terminology
- ✅ Returns structured intent data

**Limitations:**
- ⚠️ Requires HA version 2024.5+
- ⚠️ May not be suitable for all query types
- ⚠️ Response format may vary by HA version

---

## 4. Critical Missing Data During Suggestion Generation

### Current Flow (PROBLEM):

```
User Query: "when I trigger my desk sensor, I want the lights to in the office to switch to 100% brightness"
    ↓
Entity Resolution: Queries SQLite database (cached, may be stale)
    ↓
Entity Enrichment: Gets entity attributes from HA API (real-time) ✅
    ↓
Suggestion Generation: Uses enriched entities
```

### Problem: Entity List is Stale

**What Happens:**
1. User has Office devices in HA
2. Database may not have all Office devices (sync issue)
3. Entity resolution queries database → Missing devices
4. Enrichment only enriches entities that were found → Missing devices never enriched

### Recommended Flow (SOLUTION):

```
User Query: "when I trigger my desk sensor, I want the lights to in the office to switch to 100% brightness"
    ↓
Entity Resolution: Queries HA API directly (real-time) ✅
    ↓
Entity Enrichment: Gets entity attributes from HA API (real-time) ✅
    ↓
Suggestion Generation: Uses enriched entities
```

---

## 5. Implementation Recommendations

### Immediate (Fix Current Issue):

1. **Add Real-Time Entity Query Method**
   - Add `get_entities_by_area_and_domain()` to HA client
   - Use WebSocket API to get entity registry
   - Filter by area_id and domain client-side

2. **Update Entity Resolution to Use Real-Time**
   - Modify `_get_available_entities()` to query HA API directly
   - Add `use_realtime=True` parameter (default)
   - Fallback to database if HA API unavailable

3. **Test with Office Devices**
   - Verify all Office devices are found
   - Verify all Office lights are found
   - Verify sensor entities are found

### Short-Term (1-2 weeks):

1. **Add WebSocket Subscriptions**
   - Subscribe to entity_registry_updated events
   - Update cache when entities added/removed
   - Reduce cache staleness

2. **Add Template API Support**
   - Use Template API for complex queries
   - Support area + domain filtering
   - Support device relationship queries

### Long-Term (1-2 months):

1. **Integrate Assist API**
   - Use for entity resolution from natural language
   - Leverage HA's built-in entity matching
   - Improve suggestion accuracy

2. **Optimize Caching Strategy**
   - Real-time queries for suggestion generation
   - Cached queries for background tasks
   - Smart cache invalidation

---

## 6. Code Locations for Implementation

### Files to Modify:

1. **HA Client (REST):**
   - `services/ai-automation-service/src/clients/ha_client.py`
   - Add `get_entities_by_area_and_domain()`
   - Add `get_entities_by_area_template()`

2. **HA Client (WebSocket):**
   - `services/device-intelligence-service/src/clients/ha_client.py`
   - Add `subscribe_to_registry_updates()`
   - Add event handlers

3. **Entity Validator:**
   - `services/ai-automation-service/src/services/entity_validator.py`
   - Modify `_get_available_entities()` to use real-time HA API

4. **Suggestion Generation:**
   - `services/ai-automation-service/src/api/ask_ai_router.py`
   - Update `generate_suggestions_from_query()` to use real-time queries

---

## 7. Testing Checklist

### Verify Real-Time Entity Queries:

- [ ] Query Office area → Returns all Office entities
- [ ] Query Office area + light domain → Returns all Office lights
- [ ] Query Office area + binary_sensor domain → Returns all Office sensors
- [ ] Verify PS FP2 - Desk sensor is found
- [ ] Verify PS FP2 - Office sensor is found
- [ ] Verify all Office lights are found

### Verify Cache Updates:

- [ ] Add new entity in HA → Cache updates within 1 minute
- [ ] Remove entity in HA → Cache updates within 1 minute
- [ ] Update entity area → Cache updates within 1 minute

### Verify Suggestion Generation:

- [ ] Office query finds all Office devices
- [ ] Suggestion includes all relevant Office lights
- [ ] Suggestion includes all relevant Office sensors
- [ ] No missing devices in suggestions

---

## 8. Summary

### What We're Missing:

1. **❌ Real-Time Entity Queries:** We query cached database instead of HA API
2. **❌ Area + Domain Filtering:** No efficient way to get entities by area + domain
3. **❌ Registry Update Subscriptions:** Cache becomes stale (5-minute refresh)
4. **❌ Template API Usage:** Not using HA's flexible template queries
5. **❌ Assist API Integration:** Not leveraging HA's built-in entity resolution

### What We Should Do:

1. **✅ Add Real-Time Entity Queries:** Query HA API directly during suggestion generation
2. **✅ Add Area + Domain Filtering:** Implement efficient filtering methods
3. **✅ Subscribe to Registry Updates:** Keep cache fresh in real-time
4. **✅ Use Template API:** For complex queries and filtering
5. **✅ Consider Assist API:** For better entity resolution from natural language

### Priority:

1. **CRITICAL:** Add real-time entity queries (fixes current issue)
2. **HIGH:** Add registry update subscriptions (prevents future issues)
3. **MEDIUM:** Add template API support (improves flexibility)
4. **LOW:** Consider Assist API integration (future enhancement)

---

## 9. References

- **Home Assistant WebSocket API:** `docs/research/home-assistant-device-discovery-research.md`
- **Current HA Client:** `services/ai-automation-service/src/clients/ha_client.py`
- **Entity Resolution:** `services/ai-automation-service/src/services/entity_validator.py`
- **Suggestion Generation:** `services/ai-automation-service/src/api/ask_ai_router.py`
- **Device Intelligence Client:** `services/device-intelligence-service/src/clients/ha_client.py`

---

**Status:** Research Complete ✅  
**Next Step:** Implement Priority 1 (Real-Time Entity Queries)  
**Estimated Effort:** 2-4 hours for Priority 1 implementation

