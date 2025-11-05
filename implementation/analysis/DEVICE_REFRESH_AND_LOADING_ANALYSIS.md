# Device Refresh and Loading Analysis

**Date:** January 6, 2025  
**Issue:** Many Office devices exist in Home Assistant but only 1 device was shown in the suggestion  
**Query:** "when I trigger my desk sensor, I want the lights to in the office to switch to 100% brightness and Natural light scene"

**Related Research:** See [HA_API_2025_RESEARCH.md](./HA_API_2025_RESEARCH.md) for comprehensive analysis of missing HA API calls and capabilities.

## Executive Summary

The system uses a **hybrid caching approach** with mixed real-time and cached data sources. During suggestion generation:

1. ✅ **Entity Attributes:** Real-time calls to Home Assistant API
2. ❌ **Entity List:** Cached in SQLite database (may be stale)
3. ❌ **Device Intelligence:** Cached in device-intelligence-service memory (refreshed every 5 minutes)

**The Problem:** The entity resolution logic queries cached data sources that may not include all Office devices, especially if:
- The database hasn't been updated recently
- Device-intelligence-service discovery loop hasn't run recently
- Entity resolution filtering logic is too restrictive

## 1. Are Devices Loaded in Our Database?

### Yes, But With Caveats

**Database Storage:**

1. **SQLite Database (data-api):**
   - Stores entities in `entities` table
   - Stores devices in `devices` table
   - Updated via bulk upsert from websocket-ingestion service

2. **Device Intelligence Service (In-Memory Cache):**
   - Stores devices in memory (`self.unified_devices`)
   - NOT stored in database
   - Refreshed every 5 minutes via discovery loop

### How Devices Get Into Database

**Flow:**
```
Home Assistant
    ↓
websocket-ingestion (discovers devices)
    ↓
POST /api/v1/internal/devices/bulk_upsert
    ↓
data-api SQLite database (entities & devices tables)
```

**Code Evidence:**

```673:768:services/data-api/src/devices_endpoints.py
@router.post("/internal/devices/bulk_upsert")
async def bulk_upsert_devices(
    devices: List[Dict[str, Any]],
    db: AsyncSession = Depends(get_db)
):
    """
    Internal endpoint for websocket-ingestion to bulk upsert devices from HA discovery
    
    Uses INSERT OR REPLACE for reliable upsert without SQLAlchemy metadata issues
    """
```

**Entities Storage:**

```319:369:services/data-api/src/devices_endpoints.py
@router.get("/api/entities", response_model=EntitiesListResponse)
async def list_entities(
    limit: int = Query(default=100, ge=1, le=10000, description="Maximum number of entities to return"),
    domain: Optional[str] = Query(default=None, description="Filter by domain (light, sensor, etc)"),
    platform: Optional[str] = Query(default=None, description="Filter by platform"),
    device_id: Optional[str] = Query(default=None, description="Filter by device ID"),
    db: AsyncSession = Depends(get_db)
):
    """List entities (SQLite) - Story 22.2"""
    # Build query
    query = select(Entity)
    
    # Apply filters
    if domain:
        query = query.where(Entity.domain == domain)
    if platform:
        query = query.where(Entity.platform == platform)
    if device_id:
        query = query.where(Entity.device_id == device_id)
```

**Issue:** If websocket-ingestion hasn't run discovery recently, or if there's a sync issue, the database may be missing devices.

## 2. Do We Call HA to Get Latest During Suggestion Creation?

### Partial Real-Time Calls

**YES - Entity Attributes (Real-Time):**
- `EntityAttributeService` makes real-time calls to HA API
- Fetches entity state, attributes, friendly_name, etc.

**NO - Entity List (Cached):**
- Queries SQLite database via `data_api_client.fetch_entities()`
- NOT a real-time call to HA

**NO - Device Intelligence (Cached):**
- Queries device-intelligence-service (in-memory cache)
- Cache refreshed every 5 minutes

### Call Flow During Suggestion Generation

```2032:2222:services/ai-automation-service/src/api/ask_ai_router.py
async def generate_suggestions_from_query(
    query: str, 
    entities: List[Dict[str, Any]], 
    user_id: str
) -> List[Dict[str, Any]]:
    # Step 1: Resolve entity IDs
    available_entities = await entity_validator._get_available_entities(
        domain=query_domain,
        area_id=query_location
    )
    # ⚠️ This queries SQLite database, NOT HA directly
    
    # Step 2: Enrich entities
    enriched_data = await enrich_entities_comprehensively(
        entity_ids=set(resolved_entity_ids),
        ha_client=ha_client,  # ✅ Real-time HA calls for attributes
        device_intelligence_client=_device_intelligence_client,  # ❌ Cached data
        data_api_client=None
    )
```

**Entity Resolution Logic:**

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
    try:
        if self.data_api_client:
            logger.info(f"🔍 Fetching entities from data-api (domain={domain}, area_id={area_id}, integration={integration})")
            entities = await self.data_api_client.fetch_entities(
                domain=domain,
                area_id=area_id,
                platform=integration  # Note: data API uses 'platform' for integration
            )
            # ⚠️ This queries SQLite database, NOT HA directly
            return entities
```

**Device Intelligence Service Discovery Loop:**

```132:150:services/device-intelligence-service/src/core/discovery_service.py
async def _discovery_loop(self):
    """Main discovery loop."""
    logger.info("🔄 Starting discovery loop")
    
    # Initial discovery
    await self._perform_discovery()
    
    # Periodic discovery
    while self.running:
        try:
            await asyncio.sleep(300)  # 5 minutes
            if self.running:
                await self._perform_discovery()
        except asyncio.CancelledError:
            break
```

**Discovery fetches from HA:**

```174:195:services/device-intelligence-service/src/core/discovery_service.py
async def _discover_home_assistant(self):
    """Discover devices, entities, and areas from Home Assistant."""
    try:
        logger.info("🏠 Discovering Home Assistant data")
        
        # Get device registry
        self.ha_devices = await self.ha_client.get_device_registry()
        
        # Get entity registry
        self.ha_entities = await self.ha_client.get_entity_registry()
        
        # Get area registry
        self.ha_areas = await self.ha_client.get_area_registry()
        
        # Update parser with areas
        self.device_parser.update_areas(self.ha_areas)
        
        logger.info(f"📱 HA Discovery: {len(self.ha_devices)} devices, {len(self.ha_entities)} entities, {len(self.ha_areas)} areas")
```

## 3. What Happened - Root Cause Analysis

### The Problem: Cached Data Sources

**Issue 1: Entity Resolution Uses Cached Database**

When the query mentions "office", the system:
1. Extracts location: "office" and domain: "light"
2. Calls `entity_validator._get_available_entities(domain="light", area_id="office")`
3. This queries SQLite database via `data_api_client.fetch_entities()`
4. **If database is stale, it may not have all Office devices**

**Issue 2: Device Intelligence Service Cache**

Device intelligence enrichment:
1. Queries device-intelligence-service: `get_all_devices(limit=200)`
2. Device-intelligence-service returns cached data from memory
3. Cache refreshed every 5 minutes
4. **If cache is stale, newer devices won't be included**

**Issue 3: Entity Filtering Logic**

The entity resolution may be too restrictive:
- Location extraction: "office" → area_id="office"
- Domain extraction: "lights" → domain="light"
- Query filters by BOTH domain AND area
- **May miss devices that don't match both filters exactly**

**Code Evidence:**

```2077:2094:services/ai-automation-service/src/api/ask_ai_router.py
# Fetch ALL entities matching the query context (all office lights, not just one)
available_entities = await entity_validator._get_available_entities(
    domain=query_domain,
    area_id=query_location
)

if available_entities:
    # Get all entity IDs that match the query context
    resolved_entity_ids = [e.get('entity_id') for e in available_entities if e.get('entity_id')]
    logger.info(f"✅ Found {len(resolved_entity_ids)} entities matching query context (location={query_location}, domain={query_domain})")
```

**Issue 4: Missing Sensor Entities**

The user's query mentions "desk sensor" which has multiple entities:
- Light Sensor Light Level
- PS FP2 - Desk (binary_sensor)
- PS FP2 - Office (binary_sensor)

But the query extraction likely:
- Extracted "office" as location
- Extracted "lights" as domain
- **Missed "desk sensor" entities** (different domain: binary_sensor)

## 4. Evidence from Screenshots

### What's in Home Assistant

From the screenshots, we can see:
- **Presence-Sensor-FP2-8B8A** device with:
  - Light Sensor Light Level
  - PS FP2 - Desk (binary_sensor)
  - PS FP2 - Office (binary_sensor)
- **Many Office devices:**
  - Office (Philips Hue) - Room
  - Office (WLED)
  - Office Back Left, Back Right, Front Left, Front Right (Hue lights)
  - Office Go (Hue)
  - Samsung TV
  - HP Printer
  - And more...

### What Was Shown in Suggestion

- Only "Office" device (1 device)
- Missing all the individual lights
- Missing the sensor entities

## 5. Root Cause Summary

### Primary Issues

1. **Stale Database Cache:**
   - Entity list comes from SQLite database
   - May not have all Office devices if sync is behind

2. **Stale Device Intelligence Cache:**
   - Device intelligence refreshed every 5 minutes
   - May miss recently added devices

3. **Overly Restrictive Filtering:**
   - Filters by both domain AND area
   - May exclude devices that don't match exactly

4. **Missing Multi-Entity Device Handling:**
   - "Presence-Sensor-FP2-8B8A" has 3 entities
   - System may only be finding 1 entity per device

5. **Domain Mismatch:**
   - Query mentions "desk sensor" (binary_sensor domain)
   - But domain extraction likely found "light" domain
   - Sensor entities filtered out

## 6. Recommendations

### Immediate Fixes

1. **Add Real-Time HA Query Option:**
   ```python
   # In _get_available_entities, add option to query HA directly
   if use_realtime_ha:
       entities = await ha_client.get_entities_by_area(area_id, domain)
   else:
       entities = await data_api_client.fetch_entities(...)
   ```

2. **Force Refresh Device Intelligence:**
   - Add endpoint to trigger immediate discovery
   - Call before suggestion generation if cache is stale

3. **Improve Entity Resolution:**
   - Don't filter by domain when location is specified
   - Return ALL entities in the area, then filter by relevance

4. **Handle Multi-Entity Devices:**
   - When device is found, include ALL its entities
   - Don't just return the first entity

5. **Better Domain Extraction:**
   - Extract multiple domains (light + binary_sensor)
   - Don't filter out sensor entities when query mentions sensors

### Long-Term Improvements

1. **Real-Time Entity Resolution:**
   - Always query HA directly during suggestion generation
   - Use database as fallback only

2. **Cache Invalidation:**
   - Track cache freshness
   - Refresh if cache is > 1 minute old

3. **Better Entity Matching:**
   - Match all entities in the area, not just by domain
   - Include related entities (e.g., all entities from same device)

4. **Comprehensive Device Discovery:**
   - Ensure all device entities are discovered
   - Include sub-entities (like PS FP2 - Desk, PS FP2 - Office)

## 7. Code References

### Entity Resolution
- `services/ai-automation-service/src/services/entity_validator.py` - `_get_available_entities()`
- `services/ai-automation-service/src/api/ask_ai_router.py` - `generate_suggestions_from_query()`

### Device Intelligence
- `services/device-intelligence-service/src/core/discovery_service.py` - Discovery loop
- `services/ai-automation-service/src/services/comprehensive_entity_enrichment.py` - Device intelligence enrichment

### Database Storage
- `services/data-api/src/devices_endpoints.py` - Entity/device storage
- `services/websocket-ingestion/src/discovery_service.py` - Device discovery

## 8. Summary

**Are devices loaded in DB?**
- ✅ Yes, in SQLite database (entities & devices tables)
- ⚠️ May be stale if sync hasn't run recently

**Do we call HA during suggestion creation?**
- ✅ YES - Entity attributes (real-time)
- ❌ NO - Entity list (cached in database)
- ❌ NO - Device intelligence (cached in memory, refreshed every 5 min)

**What happened?**
- Entity resolution queried cached database
- Database may not have all Office devices
- Device intelligence cache may be stale
- Filtering logic too restrictive (domain + area)
- Missing multi-entity device handling
- Sensor entities filtered out due to domain mismatch

**Solution:**
- Add real-time HA query option for entity resolution
- Force refresh device intelligence before suggestion generation
- Improve entity filtering to include all area devices
- Handle multi-entity devices properly
- Better domain extraction for queries with multiple device types

