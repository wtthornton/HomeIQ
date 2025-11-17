# Device Fix Plan - 2025 HA API Compliance

**Date:** November 17, 2025  
**Status:** Planning  
**Priority:** Critical  
**Epic:** Device Management Fixes

## Executive Summary

The system is displaying incorrect device friendly names and generating invalid entity IDs in YAML automations. This plan addresses root causes across database schema, API endpoints, caching, and entity ID generation to ensure full compliance with Home Assistant 2025 API standards.

## Problem Analysis

### Issue 0: Missing Entity Capabilities and Service Information

**Current State:**
- Entity model doesn't store `supported_features` (bitmask indicating capabilities)
- No storage of available service calls per entity
- Service calls are hardcoded in prompts (light.turn_on, switch.turn_on, etc.)
- No validation that a service call is available for an entity
- No integration with HA `/api/services` endpoint to get available services per domain

**Impact:**
- System generates service calls that may not be supported by the entity
- No way to know what actions/features an entity supports (brightness, color, effects, etc.)
- YAML generation may use incorrect service calls
- Cannot validate service calls against entity capabilities

**Root Cause:**
- Entity capabilities (`supported_features`) are fetched but not stored in database
- HA Services API (`/api/services`) is not queried to get available services per domain
- Service call determination is hardcoded based on domain, not entity capabilities

### Issue 1: Missing Friendly Name Fields in Database

**Current State:**
- `Entity` model only stores: `entity_id`, `device_id`, `domain`, `platform`, `unique_id`, `area_id`, `disabled`
- Missing critical fields: `friendly_name`, `name`, `name_by_user`, `original_name`

**Impact:**
- UI shows auto-generated names like "Hue Color Downlight 1 5" instead of actual HA names like "Office Back Left"
- Entity registry data from HA contains `name` field (what shows in HA UI) but it's not stored

**Root Cause:**
- `bulk_upsert_entities()` in `data-api/src/devices_endpoints.py` doesn't extract or store entity registry name fields
- Entity model schema doesn't include these fields

### Issue 2: Incorrect Entity ID Generation

**Current State:**
- System generates entity IDs like `light.hue_color_downlight_1_5`, `light.hue_color_downlight_1_7`
- These IDs don't match actual HA entity IDs

**Impact:**
- YAML validation fails with "Invalid entity IDs" errors
- Automations can't be created because entity IDs don't exist in HA

**Root Cause:**
- Entity extraction/resolution logic generates IDs instead of using actual IDs from HA entity registry
- Entity registry data is fetched but actual entity IDs aren't being used correctly

### Issue 3: Entity Registry Data Not Fully Utilized

**Current State:**
- HA Entity Registry API returns:
  ```json
  {
    "entity_id": "light.hue_color_downlight_2_2",
    "name": "Office Back Left",  // <-- What shows in HA UI
    "original_name": "Hue Color Downlight 2 2",
    "name_by_user": null,
    "platform": "hue",
    "device_id": "...",
    "area_id": "office"
  }
  ```
- Only `entity_id`, `platform`, `device_id`, `area_id` are stored
- `name`, `original_name`, `name_by_user` are ignored

**Impact:**
- Friendly names must be fetched from HA State API or Entity Registry cache (slow, requires API calls)
- Cache can be stale (5-minute TTL), causing wrong names to display

## Solution Architecture

### Phase 1: Database Schema Updates

#### 1.1 Add Friendly Name Fields and Capabilities to Entity Model

**File:** `services/data-api/src/models/entity.py`

**Changes:**
```python
class Entity(Base):
    # ... existing fields ...
    
    # Entity Registry Name Fields (2025 HA API)
    name = Column(String)  # Primary friendly name from Entity Registry (what shows in HA UI)
    name_by_user = Column(String)  # User-customized name (if set)
    original_name = Column(String)  # Original name before user customization
    friendly_name = Column(String, index=True)  # Computed: name_by_user or name or original_name
    
    # Entity Capabilities (2025 HA API)
    supported_features = Column(Integer)  # Bitmask of supported features (from attributes.supported_features)
    capabilities = Column(JSON)  # Parsed capabilities list (brightness, color, effect, etc.)
    available_services = Column(JSON)  # List of available service calls for this entity (e.g., ["light.turn_on", "light.turn_off", "light.toggle"])
    icon = Column(String)  # Entity icon from attributes
    device_class = Column(String)  # Device class (e.g., "motion", "door", "temperature")
    unit_of_measurement = Column(String)  # Unit of measurement for sensors
```

**Priority:** `name` field is critical - this is what HA UI shows. `supported_features` and `available_services` are critical for automation generation.

#### 1.2 Create Database Migration

**File:** `services/data-api/alembic/versions/004_add_entity_name_fields.py`

**Migration Steps:**
1. Add `name`, `name_by_user`, `original_name`, `friendly_name` columns
2. Backfill `friendly_name` from existing data (if available from cache)
3. Create index on `friendly_name` for fast lookups

**Alpha Stage:** Can drop and recreate tables if needed (no production data)

### Phase 2: Fetch and Store HA Services Information

#### 2.1 Add HA Services API Client Method

**File:** `services/ai-automation-service/src/clients/ha_client.py`

**New Method:**
```python
async def get_services(self) -> Dict[str, Dict[str, Any]]:
    """
    Get all available services from Home Assistant.
    
    Returns:
        Dictionary mapping domain -> {service_name -> service_data}
        Example: {
            "light": {
                "turn_on": {"name": "Turn on", "description": "...", "fields": {...}},
                "turn_off": {"name": "Turn off", "description": "...", "fields": {...}},
                "toggle": {"name": "Toggle", "description": "...", "fields": {...}}
            },
            "switch": {
                "turn_on": {...},
                "turn_off": {...},
                "toggle": {...}
            }
        }
    """
    try:
        session = await self._get_session()
        url = f"{self.ha_url}/api/services"
        
        async with session.get(url) as response:
            if response.status == 200:
                services_data = await response.json()
                logger.info(f"✅ Retrieved {len(services_data)} service domains from HA")
                return services_data
            else:
                logger.warning(f"Failed to get services from HA: {response.status}")
                return {}
    except Exception as e:
        logger.error(f"Error getting services: {e}", exc_info=True)
        return {}
```

#### 2.2 Store Services Information in Database

**New Table:** `services/data-api/src/models/service.py`

```python
class Service(Base):
    """Available services per domain from HA"""
    __tablename__ = "services"
    
    # Composite primary key
    domain = Column(String, primary_key=True)  # e.g., "light"
    service_name = Column(String, primary_key=True)  # e.g., "turn_on"
    
    # Service metadata
    name = Column(String)  # Display name (e.g., "Turn on")
    description = Column(String)  # Service description
    fields = Column(JSON)  # Service fields/parameters
    target = Column(JSON)  # Target entity/area specification
    
    # Timestamps
    last_updated = Column(DateTime, default=datetime.utcnow)
```

**New Endpoint:** `services/data-api/src/devices_endpoints.py`

```python
@router.post("/internal/services/bulk_upsert")
async def bulk_upsert_services(
    services_data: Dict[str, Dict[str, Any]],
    db: AsyncSession = Depends(get_db)
):
    """Store available services from HA Services API"""
    # Implementation to store services per domain
```

### Phase 3: Update Data Ingestion

#### 3.1 Update bulk_upsert_entities Endpoint

**File:** `services/data-api/src/devices_endpoints.py`

**Current Code (Line 859-878):**
```python
entity = Entity(
    entity_id=entity_id,
    device_id=entity_data.get('device_id'),
    domain=domain,
    platform=entity_data.get('platform', 'unknown'),
    unique_id=entity_data.get('unique_id'),
    area_id=entity_data.get('area_id'),
    disabled=entity_data.get('disabled_by') is not None,
    created_at=datetime.now()
)
```

**Updated Code:**
```python
# Extract name fields from entity registry data
name = entity_data.get('name')  # Primary name (what shows in HA UI)
name_by_user = entity_data.get('name_by_user')  # User-customized name
original_name = entity_data.get('original_name')  # Original name

# Compute friendly_name (priority: name_by_user > name > original_name > entity_id)
friendly_name = name_by_user or name or original_name
if not friendly_name:
    # Fallback: derive from entity_id
    friendly_name = entity_id.split('.')[-1].replace('_', ' ').title()

# Fetch entity state to get capabilities (if available)
# Note: This requires HA State API call - may need to be done separately
# For now, store what we have from entity registry
supported_features = None  # Will be populated from state API if available
capabilities = None  # Will be parsed from supported_features
available_services = None  # Will be determined from domain + capabilities

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
    # NEW: Entity capabilities (will be enriched from state API)
    supported_features=supported_features,
    capabilities=capabilities,
    available_services=available_services,
    created_at=datetime.now()
)
```

#### 3.2 Enrich Entities with State API Data

**New Service:** `services/ai-automation-service/src/services/entity_capability_enrichment.py`

**Purpose:** Enrich entities with capabilities from HA State API after discovery

**Implementation:**
```python
async def enrich_entity_capabilities(
    entity_id: str,
    ha_client: HomeAssistantClient,
    services_cache: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Enrich entity with capabilities from State API.
    
    Fetches:
    - supported_features (bitmask)
    - Parsed capabilities (brightness, color, effect, etc.)
    - Available service calls based on domain + capabilities
    """
    # Fetch entity state
    state_data = await ha_client.get_entity_state(entity_id)
    if not state_data:
        return {}
    
    attributes = state_data.get('attributes', {})
    domain = entity_id.split('.')[0]
    
    # Parse supported_features
    supported_features = attributes.get('supported_features', 0)
    
    # Parse capabilities from supported_features
    capabilities = []
    if domain == 'light':
        if supported_features & 1:  # SUPPORT_BRIGHTNESS
            capabilities.append('brightness')
        if supported_features & 2:  # SUPPORT_COLOR_TEMP
            capabilities.append('color_temp')
        if supported_features & 16:  # SUPPORT_EFFECT
            capabilities.append('effect')
        if supported_features & 32:  # SUPPORT_RGB_COLOR
            capabilities.append('rgb_color')
        if supported_features & 64:  # SUPPORT_WHITE_VALUE
            capabilities.append('white_value')
        if supported_features & 128:  # SUPPORT_COLOR
            capabilities.append('color')
    
    # Determine available services from domain + services cache
    available_services = []
    if domain in services_cache:
        domain_services = services_cache[domain]
        # Common services for domain
        if 'turn_on' in domain_services:
            available_services.append(f'{domain}.turn_on')
        if 'turn_off' in domain_services:
            available_services.append(f'{domain}.turn_off')
        if 'toggle' in domain_services:
            available_services.append(f'{domain}.toggle')
    
    return {
        'supported_features': supported_features,
        'capabilities': capabilities,
        'available_services': available_services,
        'icon': attributes.get('icon'),
        'device_class': attributes.get('device_class'),
        'unit_of_measurement': attributes.get('unit_of_measurement')
    }
```

#### 3.3 Verify Entity Registry API Response Structure

**File:** `services/websocket-ingestion/src/discovery_service.py`

**Verify:** Entity registry discovery (line 130-212) receives full entity registry data including `name` fields

**Action:** Ensure `discover_entities()` passes complete entity registry data to `bulk_upsert_entities()`

### Phase 4: Update API Responses

#### 3.1 Update EntityResponse Model

**File:** `services/data-api/src/devices_endpoints.py`

**Current Model:**
```python
class EntityResponse(BaseModel):
    entity_id: str
    device_id: Optional[str]
    domain: str
    platform: str
    # ... no friendly_name fields
```

**Updated Model:**
```python
class EntityResponse(BaseModel):
    entity_id: str
    device_id: Optional[str]
    domain: str
    platform: str
    # NEW: Entity Registry name fields
    name: Optional[str] = Field(default=None, description="Primary friendly name from Entity Registry")
    name_by_user: Optional[str] = Field(default=None, description="User-customized name")
    original_name: Optional[str] = Field(default=None, description="Original name before customization")
    friendly_name: Optional[str] = Field(default=None, description="Computed friendly name (name_by_user or name)")
    # ... existing fields
```

#### 3.2 Update Entity Endpoint Responses

**Files:**
- `services/data-api/src/devices_endpoints.py` - `list_entities()` (line 352)
- `services/data-api/src/devices_endpoints.py` - `get_entity()` (line 427)

**Changes:** Include `name`, `name_by_user`, `original_name`, `friendly_name` in responses

### Phase 5: Fix Entity ID Generation

#### 4.1 Use Actual Entity IDs from Registry

**File:** `services/ai-automation-service/src/api/ask_ai_router.py`

**Problem:** Entity resolution logic generates IDs instead of using actual IDs from HA

**Solution:**
1. Always query Entity Registry for actual entity IDs
2. Never generate entity IDs - only use IDs that exist in HA
3. Validate all entity IDs against HA Entity Registry before using

**Key Functions to Update:**
- `_resolve_entities_to_ids()` - Use Entity Registry lookup
- `generate_automation_yaml()` - Only use validated entity IDs from registry

#### 4.2 Entity Validation Against Registry

**File:** `services/ai-automation-service/src/services/entity_id_validator.py`

**Enhancement:** Add Entity Registry validation step before YAML generation

**Logic:**
```python
async def validate_entity_ids_exist(self, entity_ids: List[str]) -> Dict[str, bool]:
    """Validate entity IDs exist in HA Entity Registry"""
    registry = await self.ha_client.get_entity_registry()
    return {eid: eid in registry for eid in entity_ids}
```

### Phase 6: Service Call Validation

#### 6.1 Validate Service Calls Against Entity Capabilities

**File:** `services/ai-automation-service/src/services/service_validator.py`

**New Service:**
```python
class ServiceValidator:
    """Validate service calls against entity capabilities"""
    
    async def validate_service_call(
        self,
        entity_id: str,
        service: str,
        db_session: AsyncSession
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate that a service call is available for an entity.
        
        Returns:
            (is_valid, error_message)
        """
        # Get entity from database
        entity = await db_session.get(Entity, entity_id)
        if not entity:
            return False, f"Entity {entity_id} not found"
        
        # Check if service is in available_services
        if entity.available_services and service not in entity.available_services:
            return False, f"Service {service} not available for {entity_id}. Available: {entity.available_services}"
        
        # Validate service parameters against capabilities
        domain = service.split('.')[0]
        service_name = service.split('.')[1] if '.' in service else service
        
        if domain == 'light' and service_name == 'turn_on':
            # Check if brightness/color parameters are valid for entity capabilities
            if entity.capabilities:
                # Validation logic here
                pass
        
        return True, None
```

#### 6.2 Update YAML Generation to Use Validated Services

**File:** `services/ai-automation-service/src/api/ask_ai_router.py`

**Update:** `generate_automation_yaml()` to validate service calls before generating YAML

### Phase 7: Cache Updates

#### 5.1 Update Entity Registry Cache Structure

**File:** `services/ai-automation-service/src/services/entity_attribute_service.py`

**Current:** Cache stores full registry but friendly names come from cache lookup

**Enhancement:** Cache is already correct - just ensure it's used properly

**Action:** Verify `_get_friendly_name_from_registry()` uses `name` field correctly (already implemented)

#### 5.2 Database-First Friendly Name Lookup

**New Pattern:** Query database first, fallback to Entity Registry cache

**Benefits:**
- Faster (SQLite query vs API call)
- Always up-to-date (updated on discovery)
- No cache staleness issues

**Implementation:**
```python
async def get_friendly_name(self, entity_id: str, db_session: AsyncSession) -> Optional[str]:
    """Get friendly name from database first, fallback to cache"""
    # Try database first
    entity = await db_session.get(Entity, entity_id)
    if entity and entity.friendly_name:
        return entity.friendly_name
    
    # Fallback to Entity Registry cache
    registry = await self._get_entity_registry()
    return self._get_friendly_name_from_registry(entity_id, registry)
```

### Phase 8: UI Updates

#### 6.1 Update Frontend to Use friendly_name

**File:** `services/ai-automation-ui/src/pages/AskAI.tsx`

**Current:** Uses `friendly_name` from API response (may be missing)

**Action:** Ensure UI uses `friendly_name` field from EntityResponse

**Verification:** Check device display logic (line 1251-1300) uses correct field

## Implementation Steps

### Step 1: Database Schema Migration (Alpha - Can Drop/Recreate)

1. **Update Entity Model** (`services/data-api/src/models/entity.py`)
   - Add `name`, `name_by_user`, `original_name`, `friendly_name` columns
   - Add `supported_features`, `capabilities`, `available_services` columns
   - Add `icon`, `device_class`, `unit_of_measurement` columns
   - Add indexes on `friendly_name`, `supported_features`

2. **Create Services Table** (`services/data-api/src/models/service.py`)
   - Store available services per domain from HA Services API
   - Composite primary key: (domain, service_name)

3. **Create Migration Script** (`services/data-api/alembic/versions/004_add_entity_name_fields.py`)
   - Add entity name columns
   - Add entity capability columns
   - Create services table
   - Backfill data (if possible from cache)
   - Create indexes

4. **Alpha Option:** Drop and recreate `entities` and `services` tables if no critical data

### Step 2: Fetch and Store HA Services

1. **Add `get_services()` Method** (`services/ai-automation-service/src/clients/ha_client.py`)
   - Fetch all services from HA `/api/services` endpoint
   - Return structured data: domain -> service_name -> service_data

2. **Create Services Storage** (`services/data-api/src/models/service.py`)
   - Create Service model with domain, service_name, metadata
   - Create bulk_upsert_services endpoint

3. **Initial Services Load** (`services/websocket-ingestion/src/discovery_service.py`)
   - Fetch services on discovery startup
   - Store in database via bulk_upsert_services

### Step 3: Update Data Ingestion

1. **Update `bulk_upsert_entities()`** (`services/data-api/src/devices_endpoints.py:847`)
   - Extract `name`, `name_by_user`, `original_name` from entity registry data
   - Compute `friendly_name` (priority: name_by_user > name > original_name)
   - Store all fields in Entity model
   - Note: Capabilities will be enriched separately from State API

2. **Create Entity Capability Enrichment** (`services/ai-automation-service/src/services/entity_capability_enrichment.py`)
   - Fetch entity state from HA State API
   - Parse `supported_features` bitmask
   - Determine capabilities (brightness, color, effect, etc.)
   - Determine available services based on domain + capabilities
   - Update Entity records with capability data

3. **Verify Discovery Service** (`services/websocket-ingestion/src/discovery_service.py`)
   - Ensure `discover_entities()` returns full entity registry data
   - Verify `store_discovery_results()` passes complete data to bulk_upsert
   - Trigger capability enrichment after entity discovery

### Step 4: Update API Responses

1. **Update EntityResponse Model** (`services/data-api/src/devices_endpoints.py:48`)
   - Add `name`, `name_by_user`, `original_name`, `friendly_name` fields

2. **Update Endpoint Responses**
   - `list_entities()` - Include name fields in response
   - `get_entity()` - Include name fields in response

### Step 5: Fix Entity ID Generation

1. **Update Entity Resolution** (`services/ai-automation-service/src/api/ask_ai_router.py`)
   - Always query Entity Registry for actual entity IDs
   - Never generate entity IDs
   - Validate against registry before use

2. **Add Entity Registry Validation** (`services/ai-automation-service/src/services/entity_id_validator.py`)
   - Validate all entity IDs exist in HA Entity Registry
   - Reject invalid IDs before YAML generation

### Step 6: Service Call Validation

1. **Create Service Validator** (`services/ai-automation-service/src/services/service_validator.py`)
   - Validate service calls against entity capabilities
   - Check if service is in entity's available_services list
   - Validate service parameters against entity capabilities

2. **Update YAML Generation** (`services/ai-automation-service/src/api/ask_ai_router.py`)
   - Validate all service calls before YAML generation
   - Use entity's available_services to determine valid service calls
   - Reject invalid service calls with clear error messages

### Step 7: Update Caching Strategy

1. **Database-First Lookup** (`services/ai-automation-service/src/services/entity_attribute_service.py`)
   - Query database first for friendly names
   - Fallback to Entity Registry cache if not in DB

2. **Cache Invalidation**
   - Clear Entity Registry cache when discovery runs
   - Update database on entity registry events

### Step 8: Testing & Validation

1. **Unit Tests**
   - Test Entity model with name fields
   - Test bulk_upsert_entities with name fields
   - Test friendly_name computation logic

2. **Integration Tests**
   - Test entity discovery stores name fields
   - Test API responses include name fields
   - Test entity ID validation against registry

3. **Manual Testing**
   - Verify friendly names display correctly in UI
   - Verify entity IDs in YAML match HA entity IDs
   - Verify automations create successfully

## Database Schema Changes

### Entity Table - New Columns

```sql
-- Entity Registry Name Fields
ALTER TABLE entities ADD COLUMN name TEXT;
ALTER TABLE entities ADD COLUMN name_by_user TEXT;
ALTER TABLE entities ADD COLUMN original_name TEXT;
ALTER TABLE entities ADD COLUMN friendly_name TEXT;

-- Entity Capabilities
ALTER TABLE entities ADD COLUMN supported_features INTEGER;
ALTER TABLE entities ADD COLUMN capabilities TEXT;  -- JSON array
ALTER TABLE entities ADD COLUMN available_services TEXT;  -- JSON array

-- Entity Attributes
ALTER TABLE entities ADD COLUMN icon TEXT;
ALTER TABLE entities ADD COLUMN device_class TEXT;
ALTER TABLE entities ADD COLUMN unit_of_measurement TEXT;

-- Indexes
CREATE INDEX idx_entity_friendly_name ON entities(friendly_name);
CREATE INDEX idx_entity_supported_features ON entities(supported_features);
CREATE INDEX idx_entity_device_class ON entities(device_class);
```

### Services Table - New Table

```sql
CREATE TABLE services (
    domain TEXT NOT NULL,
    service_name TEXT NOT NULL,
    name TEXT,
    description TEXT,
    fields TEXT,  -- JSON
    target TEXT,  -- JSON
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (domain, service_name)
);

CREATE INDEX idx_services_domain ON services(domain);
```

### Migration Script Structure

```python
def upgrade():
    op.add_column('entities', sa.Column('name', sa.String(), nullable=True))
    op.add_column('entities', sa.Column('name_by_user', sa.String(), nullable=True))
    op.add_column('entities', sa.Column('original_name', sa.String(), nullable=True))
    op.add_column('entities', sa.Column('friendly_name', sa.String(), nullable=True))
    op.create_index('idx_entity_friendly_name', 'entities', ['friendly_name'])

def downgrade():
    op.drop_index('idx_entity_friendly_name', 'entities')
    op.drop_column('entities', 'friendly_name')
    op.drop_column('entities', 'original_name')
    op.drop_column('entities', 'name_by_user')
    op.drop_column('entities', 'name')
```

## API Changes

### EntityResponse Model - New Fields

```python
class EntityResponse(BaseModel):
    # ... existing fields ...
    # Entity Registry Name Fields
    name: Optional[str] = None  # Primary friendly name from Entity Registry
    name_by_user: Optional[str] = None  # User-customized name
    original_name: Optional[str] = None  # Original name before customization
    friendly_name: Optional[str] = None  # Computed friendly name
    
    # Entity Capabilities
    supported_features: Optional[int] = None  # Bitmask of supported features
    capabilities: Optional[List[str]] = None  # Parsed capabilities (brightness, color, etc.)
    available_services: Optional[List[str]] = None  # Available service calls
    
    # Entity Attributes
    icon: Optional[str] = None
    device_class: Optional[str] = None
    unit_of_measurement: Optional[str] = None
```

### ServiceResponse Model - New Model

```python
class ServiceResponse(BaseModel):
    domain: str
    service_name: str
    name: Optional[str] = None
    description: Optional[str] = None
    fields: Optional[Dict[str, Any]] = None
    target: Optional[Dict[str, Any]] = None
```

### Endpoint Changes

**GET /api/entities**
- Response now includes `name`, `name_by_user`, `original_name`, `friendly_name`

**GET /api/entities/{entity_id}**
- Response now includes `name`, `name_by_user`, `original_name`, `friendly_name`

## Cache Strategy Updates

### Database-First Lookup Pattern

```python
# Priority order:
# 1. Database (fastest, always up-to-date)
# 2. Entity Registry cache (5-minute TTL)
# 3. HA State API (slowest, last resort)
```

### Cache Invalidation

- Clear Entity Registry cache when discovery runs
- Update database on entity registry update events
- Database is source of truth (updated on discovery)

## Testing Checklist

### Database Schema
- [ ] Entity model includes name fields
- [ ] Migration script runs successfully
- [ ] Indexes created correctly
- [ ] Data backfilled (if applicable)

### Data Ingestion
- [ ] bulk_upsert_entities stores name fields
- [ ] friendly_name computed correctly
- [ ] Discovery service passes complete data

### API Responses
- [ ] EntityResponse includes name fields
- [ ] list_entities returns name fields
- [ ] get_entity returns name fields

### Entity ID Generation
- [ ] Entity IDs come from Entity Registry
- [ ] No entity IDs are generated
- [ ] Entity IDs validated before use

### UI Display
- [ ] Friendly names display correctly
- [ ] Entity IDs match HA entity IDs
- [ ] YAML generation uses correct IDs

## Rollback Plan

**Alpha Stage:** Can drop and recreate tables

1. **Database Rollback:**
   ```sql
   DROP TABLE entities;
   -- Recreate from previous schema
   ```

2. **Code Rollback:**
   - Revert Entity model changes
   - Revert bulk_upsert_entities changes
   - Revert API response changes

3. **Cache Rollback:**
   - Clear Entity Registry cache
   - Restart services

## Success Criteria

### Device & Entity Information
1. ✅ Entity model includes `name`, `name_by_user`, `original_name`, `friendly_name` fields
2. ✅ Entity model includes `supported_features`, `capabilities`, `available_services` fields
3. ✅ Database stores entity registry name fields on discovery
4. ✅ Database stores entity capabilities from State API
5. ✅ Database stores available services per domain from HA Services API
6. ✅ API responses include friendly name fields
7. ✅ API responses include capability and service information

### Entity ID & Service Validation
8. ✅ Entity IDs in YAML match actual HA entity IDs
9. ✅ Service calls are validated against entity capabilities
10. ✅ Only valid service calls are used in YAML generation
11. ✅ YAML validation passes (no "Invalid entity IDs" errors)
12. ✅ YAML validation passes (no "Invalid service calls" errors)

### UI Display
13. ✅ UI displays correct friendly names (e.g., "Office Back Left" not "Hue Color Downlight 1 5")
14. ✅ UI shows entity capabilities (brightness, color, effects, etc.)
15. ✅ UI shows available actions/services for each entity

### Automation Generation
16. ✅ Automations create successfully in HA
17. ✅ Service calls match entity capabilities
18. ✅ Service parameters are valid for entity (e.g., brightness only for lights that support it)

## Timeline

- **Phase 1:** Database schema updates (3 hours)
  - Entity model updates (name fields + capabilities)
  - Services table creation
  - Migration scripts
- **Phase 2:** HA Services API integration (3 hours)
  - Add get_services() method
  - Create services storage
  - Initial services load
- **Phase 3:** Data ingestion updates (3 hours)
  - Update bulk_upsert_entities
  - Create capability enrichment service
  - Integrate with discovery
- **Phase 4:** API response updates (2 hours)
  - Update EntityResponse model
  - Update endpoints
- **Phase 5:** Entity ID generation fixes (4 hours)
  - Fix entity resolution
  - Add validation
- **Phase 6:** Service call validation (4 hours)
  - Create service validator
  - Update YAML generation
- **Phase 7:** Cache updates (2 hours)
  - Database-first lookup
  - Cache invalidation
- **Phase 8:** Testing & validation (4 hours)
  - Unit tests
  - Integration tests
  - Manual testing

**Total Estimated Time:** 25 hours

## Dependencies

- Home Assistant 2025 API Entity Registry structure
- SQLite database (can modify schema freely in Alpha)
- Entity Registry cache (already implemented)
- Discovery service (already implemented)

## Notes

- **Alpha Stage:** Can delete/recreate tables, no production data concerns
- **2025 HA API:** Entity Registry `name` field is source of truth for UI display
- **Priority:** `name` field is critical - this is what HA UI shows
- **Performance:** Database-first lookup is faster than API calls

## Related Files

### Database
- `services/data-api/src/models/entity.py` - Entity model
- `services/data-api/src/models/service.py` - Service model (NEW)
- `services/data-api/src/devices_endpoints.py` - bulk_upsert_entities endpoint
- `services/data-api/alembic/versions/` - Migration scripts

### Services
- `services/websocket-ingestion/src/discovery_service.py` - Entity discovery
- `services/ai-automation-service/src/services/entity_attribute_service.py` - Entity enrichment
- `services/ai-automation-service/src/services/entity_capability_enrichment.py` - Capability enrichment (NEW)
- `services/ai-automation-service/src/services/service_validator.py` - Service validation (NEW)
- `services/ai-automation-service/src/api/ask_ai_router.py` - Entity resolution
- `services/ai-automation-service/src/services/entity_id_validator.py` - Entity validation
- `services/ai-automation-service/src/clients/ha_client.py` - HA client (add get_services method)

### Frontend
- `services/ai-automation-ui/src/pages/AskAI.tsx` - Device display

## References

- Home Assistant 2025 API Documentation: Entity Registry
- Current Implementation: `services/ai-automation-service/src/clients/ha_client.py:989` - get_entity_registry()
- Cache Audit Report: `implementation/CACHE_AUDIT_REPORT.md`

