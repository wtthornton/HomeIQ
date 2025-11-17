# Device & Entity Data Usage Review

**Date:** November 17, 2025  
**Status:** Review Complete - Implementation Plan Created  
**Priority:** Critical  
**Purpose:** Ensure all services use correct device/entity information for AI prompts, suggestions, and YAML generation

## Executive Summary

This document reviews every service that uses device/entity data and ensures they're using:
1. ✅ Correct friendly names (name, name_by_user, original_name from Entity Registry)
2. ✅ Actual entity IDs (from HA Entity Registry, not generated)
3. ✅ Entity capabilities (supported_features, capabilities list)
4. ✅ Available services (service calls per entity)
5. ✅ Device metadata (manufacturer, model, sw_version, icon, device_class)

## Services Review

### 1. Entity Context Builder (`entity_context_builder.py`)

**Current Usage:**
- ✅ Uses `friendly_name` from enriched data
- ✅ Extracts capabilities from `supported_features` bitmask
- ✅ Includes entity attributes
- ⚠️ **ISSUE:** Uses `friendly_name` from enriched data (may be stale cache)
- ⚠️ **ISSUE:** Doesn't use `name`, `name_by_user`, `original_name` fields from database
- ⚠️ **ISSUE:** Doesn't use `available_services` from database
- ⚠️ **ISSUE:** Doesn't use device metadata (manufacturer, model)

**Required Changes:**
1. **Database-First Lookup:** Query database first for entity name fields
2. **Use All Name Fields:** Include `name`, `name_by_user`, `original_name` in context
3. **Include Available Services:** Add `available_services` to entity context JSON
4. **Include Device Metadata:** Add manufacturer, model, sw_version to context

**File:** `services/ai-automation-service/src/prompt_building/entity_context_builder.py`

**Changes Needed:**
```python
# Current (line 154):
'friendly_name': enriched.get('friendly_name') or entity.get('friendly_name'),

# Should be (database-first):
# Query database for entity
db_entity = await db_session.get(Entity, entity_id)
if db_entity:
    friendly_name = db_entity.friendly_name or db_entity.name or db_entity.original_name
    name = db_entity.name
    name_by_user = db_entity.name_by_user
    original_name = db_entity.original_name
    available_services = db_entity.available_services or []
    capabilities = db_entity.capabilities or []
    supported_features = db_entity.supported_features
    icon = db_entity.icon
    device_class = db_entity.device_class
else:
    # Fallback to enriched data
    friendly_name = enriched.get('friendly_name')
    available_services = []
    capabilities = enriched.get('capabilities', [])

# Include in entity_entry:
entity_entry = {
    'entity_id': entity_id,
    'friendly_name': friendly_name,
    'name': name,  # NEW
    'name_by_user': name_by_user,  # NEW
    'original_name': original_name,  # NEW
    'domain': domain,
    'type': self._determine_type(enriched),
    'state': enriched.get('state', 'unknown'),
    'capabilities': capabilities,  # From database first
    'supported_features': supported_features,  # NEW
    'available_services': available_services,  # NEW
    'icon': icon,  # NEW
    'device_class': device_class,  # NEW
    'attributes': attributes,
    'is_group': enriched.get('is_group', False),
    'integration': enriched.get('integration', 'unknown')
}

# Add device metadata if available
if db_entity and db_entity.device_id:
    device = await db_session.get(Device, db_entity.device_id)
    if device:
        entity_entry['device'] = {
            'manufacturer': device.manufacturer,
            'model': device.model,
            'sw_version': device.sw_version
        }
```

### 2. Unified Prompt Builder (`unified_prompt_builder.py`)

**Current Usage:**
- ✅ Uses device intelligence client for device context
- ✅ Includes capabilities in device context
- ⚠️ **ISSUE:** May not use database-friendly names
- ⚠️ **ISSUE:** Doesn't include available services in prompts
- ⚠️ **ISSUE:** Doesn't include device metadata in prompts

**Required Changes:**
1. **Include Available Services:** Add available services to device context
2. **Include Device Metadata:** Add manufacturer, model to device context
3. **Use Database Names:** Query database for friendly names

**File:** `services/ai-automation-service/src/prompt_building/unified_prompt_builder.py`

**Changes Needed:**
```python
# In _build_device_context_section():
# Add available services and device metadata
device_context_section += f"\nAvailable Services: {', '.join(device.get('available_services', []))}"
device_context_section += f"\nDevice: {device.get('manufacturer', 'Unknown')} {device.get('model', 'Unknown')}"
```

### 3. YAML Generation (`ask_ai_router.py` - `generate_automation_yaml`)

**Current Usage:**
- ✅ Uses validated entity IDs from registry
- ✅ Includes entity context JSON with capabilities
- ✅ Validates entity IDs exist
- ⚠️ **ISSUE:** Doesn't validate service calls against `available_services`
- ⚠️ **ISSUE:** Doesn't use `available_services` from database
- ⚠️ **ISSUE:** Service calls are hardcoded based on domain, not entity capabilities

**Required Changes:**
1. **Validate Service Calls:** Check service calls against entity's `available_services`
2. **Use Available Services:** Include `available_services` in entity context
3. **Service Call Validation:** Reject invalid service calls before YAML generation

**File:** `services/ai-automation-service/src/api/ask_ai_router.py`

**Changes Needed:**
```python
# In generate_automation_yaml() (around line 1800):
# Add available services to validated_entities_text
if validated_entities:
    # Query database for available services
    for friendly_name, entity_id in validated_entities.items():
        db_entity = await db_session.get(Entity, entity_id)
        if db_entity and db_entity.available_services:
            validated_entities_text += f"\n  - {friendly_name} ({entity_id}): Available services: {', '.join(db_entity.available_services)}"

# Add service validation before YAML generation
service_validator = ServiceValidator()
for entity_id in validated_entities.values():
    # Determine service calls from suggestion
    suggested_services = extract_service_calls_from_suggestion(suggestion)
    for service in suggested_services:
        is_valid, error = await service_validator.validate_service_call(entity_id, service, db_session)
        if not is_valid:
            logger.warning(f"Invalid service call: {service} for {entity_id}: {error}")
            # Remove invalid service or use fallback
```

### 4. Suggestion Generation (`ask_ai_router.py` - `generate_suggestions_from_query`)

**Current Usage:**
- ✅ Uses entity context JSON
- ✅ Includes capabilities in context
- ⚠️ **ISSUE:** Doesn't use database-friendly names
- ⚠️ **ISSUE:** Doesn't include available services in prompts
- ⚠️ **ISSUE:** Doesn't include device metadata in prompts

**Required Changes:**
1. **Database-First Names:** Query database for friendly names
2. **Include Available Services:** Add to entity context JSON
3. **Include Device Metadata:** Add manufacturer, model to context

**File:** `services/ai-automation-service/src/api/ask_ai_router.py`

**Changes Needed:**
```python
# In generate_suggestions_from_query() (around line 3450):
# When building entity_context_json, query database first
for entity_id in resolved_entity_ids:
    db_entity = await db_session.get(Entity, entity_id)
    if db_entity:
        # Use database fields first
        entity_data = {
            'entity_id': entity_id,
            'friendly_name': db_entity.friendly_name,
            'name': db_entity.name,
            'name_by_user': db_entity.name_by_user,
            'original_name': db_entity.original_name,
            'capabilities': db_entity.capabilities or [],
            'available_services': db_entity.available_services or [],
            'supported_features': db_entity.supported_features,
            'icon': db_entity.icon,
            'device_class': db_entity.device_class
        }
        # Add device metadata
        if db_entity.device_id:
            device = await db_session.get(Device, db_entity.device_id)
            if device:
                entity_data['device'] = {
                    'manufacturer': device.manufacturer,
                    'model': device.model,
                    'sw_version': device.sw_version
                }
```

### 5. Entity Enrichment (`entity_attribute_service.py`)

**Current Usage:**
- ✅ Fetches from HA Entity Registry
- ✅ Uses Entity Registry `name` field for friendly_name
- ✅ Extracts capabilities from `supported_features`
- ⚠️ **ISSUE:** Doesn't query database first
- ⚠️ **ISSUE:** Doesn't store enriched data back to database
- ⚠️ **ISSUE:** Doesn't determine `available_services` from domain + capabilities

**Required Changes:**
1. **Database-First Lookup:** Query database first, fallback to HA API
2. **Store Enriched Data:** Update database with enriched capabilities
3. **Determine Available Services:** Use domain + capabilities to determine services

**File:** `services/ai-automation-service/src/services/entity_attribute_service.py`

**Changes Needed:**
```python
# In enrich_entity_with_attributes() (around line 148):
# Add database-first lookup
async def enrich_entity_with_attributes(
    self, 
    entity_id: str,
    db_session: Optional[AsyncSession] = None
) -> Optional[Dict[str, Any]]:
    # Try database first
    if db_session:
        db_entity = await db_session.get(Entity, entity_id)
        if db_entity and db_entity.friendly_name:
            # Use database data
            return {
                'entity_id': entity_id,
                'friendly_name': db_entity.friendly_name,
                'name': db_entity.name,
                'name_by_user': db_entity.name_by_user,
                'original_name': db_entity.original_name,
                'capabilities': db_entity.capabilities or [],
                'available_services': db_entity.available_services or [],
                'supported_features': db_entity.supported_features,
                'icon': db_entity.icon,
                'device_class': db_entity.device_class
            }
    
    # Fallback to HA API (existing logic)
    # ... existing code ...
    
    # After enriching, update database if db_session provided
    if db_session and enriched:
        await self._update_entity_in_database(db_session, entity_id, enriched)
```

### 6. Entity Validation Context (`ask_ai_router.py` - `_build_entity_validation_context_with_comprehensive_data`)

**Current Usage:**
- ✅ Includes capabilities
- ✅ Includes supported_features
- ⚠️ **ISSUE:** Uses `friendly_name` from entities list (may not be from database)
- ⚠️ **ISSUE:** Doesn't include `available_services`
- ⚠️ **ISSUE:** Doesn't include device metadata

**Required Changes:**
1. **Database-First Names:** Query database for friendly names
2. **Include Available Services:** Add to context
3. **Include Device Metadata:** Add manufacturer, model

**File:** `services/ai-automation-service/src/api/ask_ai_router.py`

**Changes Needed:**
```python
# In _build_entity_validation_context_with_comprehensive_data() (around line 100):
# Query database for entity information
for entity in entities:
    entity_id = entity.get('entity_id', 'unknown')
    
    # Query database first
    db_entity = await db_session.get(Entity, entity_id) if db_session else None
    if db_entity:
        entity_name = db_entity.friendly_name or db_entity.name or db_entity.original_name
        capabilities = db_entity.capabilities or []
        available_services = db_entity.available_services or []
        supported_features = db_entity.supported_features
    else:
        # Fallback to entity dict
        entity_name = entity.get('name', entity.get('friendly_name', entity_id))
        capabilities = entity.get('capabilities', [])
        available_services = []
        supported_features = entity.get('supported_features')
    
    section = f"- {entity_name} ({entity_id}, domain: {domain})\n"
    
    # Add available services
    if available_services:
        section += f"  Available Services: {', '.join(available_services)}\n"
    
    # Add capabilities (existing code)
    # ...
```

### 7. Service Call Determination (`ask_ai_router.py` - `_determine_service_calls_for_entity`)

**Current Usage:**
- ✅ Uses capabilities to determine service calls
- ✅ Hardcodes service calls based on domain
- ⚠️ **ISSUE:** Doesn't use `available_services` from database
- ⚠️ **ISSUE:** Doesn't validate service calls against entity capabilities

**Required Changes:**
1. **Use Available Services:** Query database for `available_services`
2. **Validate Service Calls:** Only use services in `available_services` list
3. **Service Parameter Validation:** Validate parameters against capabilities

**File:** `services/ai-automation-service/src/api/ask_ai_router.py`

**Changes Needed:**
```python
# In _determine_service_calls_for_entity() (around line 2739):
# Query database for available services
db_entity = await db_session.get(Entity, entity_id) if db_session else None
available_services = []
if db_entity and db_entity.available_services:
    available_services = db_entity.available_services
else:
    # Fallback: determine from domain + capabilities
    available_services = determine_services_from_domain_and_capabilities(domain, capabilities)

# Only use services that are in available_services list
if domain == 'light':
    if 'light.turn_on' in available_services:
        service_calls.append({'service': 'light.turn_on', ...})
    if 'light.turn_off' in available_services:
        service_calls.append({'service': 'light.turn_off', ...})
    # Don't add services not in available_services
```

### 8. Device Intelligence Client (`device_intelligence_client.py`)

**Current Usage:**
- ✅ Fetches device data from device-intelligence-service
- ✅ Includes device capabilities
- ⚠️ **ISSUE:** May not use database-friendly names
- ⚠️ **ISSUE:** Doesn't include entity-level available services

**Required Changes:**
1. **Cross-Reference with Entity DB:** Use entity database for friendly names
2. **Include Entity Services:** Add entity-level available services

**File:** `services/ai-automation-service/src/clients/device_intelligence_client.py`

**Changes Needed:**
```python
# When fetching device data, also query entity database
# Add entity_id lookup to get friendly names and available services
```

## Implementation Plan

### Phase 1: Database-First Lookup Pattern

**Goal:** All services query database first, fallback to HA API

**Changes:**
1. Update `EntityContextBuilder` to accept `db_session` parameter
2. Update `enrich_entity_with_attributes` to query database first
3. Update all prompt builders to use database-first lookup

**Files:**
- `services/ai-automation-service/src/prompt_building/entity_context_builder.py`
- `services/ai-automation-service/src/services/entity_attribute_service.py`
- `services/ai-automation-service/src/api/ask_ai_router.py`

### Phase 2: Include Available Services

**Goal:** All prompts and YAML generation use `available_services` from database

**Changes:**
1. Add `available_services` to entity context JSON
2. Include `available_services` in validation context
3. Use `available_services` for service call determination
4. Validate service calls against `available_services`

**Files:**
- `services/ai-automation-service/src/prompt_building/entity_context_builder.py`
- `services/ai-automation-service/src/api/ask_ai_router.py`
- `services/ai-automation-service/src/services/service_validator.py` (NEW)

### Phase 3: Include Device Metadata

**Goal:** All prompts include device metadata (manufacturer, model, sw_version)

**Changes:**
1. Join Entity with Device table in database queries
2. Include device metadata in entity context JSON
3. Include device metadata in validation context

**Files:**
- `services/ai-automation-service/src/prompt_building/entity_context_builder.py`
- `services/ai-automation-service/src/api/ask_ai_router.py`

### Phase 4: Use All Name Fields

**Goal:** Use `name`, `name_by_user`, `original_name` fields from database

**Changes:**
1. Query database for all name fields
2. Include all name fields in entity context
3. Use `name` (Entity Registry) as primary, fallback to others

**Files:**
- `services/ai-automation-service/src/prompt_building/entity_context_builder.py`
- `services/ai-automation-service/src/api/ask_ai_router.py`

### Phase 5: Service Call Validation

**Goal:** Validate all service calls against entity capabilities and available services

**Changes:**
1. Create `ServiceValidator` service
2. Validate service calls before YAML generation
3. Reject invalid service calls with clear errors

**Files:**
- `services/ai-automation-service/src/services/service_validator.py` (NEW)
- `services/ai-automation-service/src/api/ask_ai_router.py`

## Code Changes Summary

### 1. Entity Context Builder Updates

**File:** `services/ai-automation-service/src/prompt_building/entity_context_builder.py`

**Key Changes:**
- Add `db_session` parameter to `build_entity_context_json()`
- Query database first for entity information
- Include `name`, `name_by_user`, `original_name`, `available_services`
- Include device metadata (manufacturer, model, sw_version)
- Include `supported_features`, `icon`, `device_class`

### 2. YAML Generation Updates

**File:** `services/ai-automation-service/src/api/ask_ai_router.py`

**Key Changes:**
- Query database for `available_services` before YAML generation
- Include `available_services` in validated_entities_text
- Validate service calls against `available_services`
- Use database-friendly names in prompts

### 3. Entity Enrichment Updates

**File:** `services/ai-automation-service/src/services/entity_attribute_service.py`

**Key Changes:**
- Add `db_session` parameter to enrichment methods
- Query database first, fallback to HA API
- Update database with enriched data
- Determine `available_services` from domain + capabilities

### 4. Service Validator (NEW)

**File:** `services/ai-automation-service/src/services/service_validator.py`

**Purpose:** Validate service calls against entity capabilities and available services

**Methods:**
- `validate_service_call(entity_id, service, db_session)` - Validate single service
- `validate_service_parameters(entity_id, service, parameters, db_session)` - Validate parameters
- `get_available_services(entity_id, db_session)` - Get available services for entity

## Testing Checklist

### Entity Context Builder
- [ ] Database-first lookup works correctly
- [ ] All name fields included in context
- [ ] Available services included in context
- [ ] Device metadata included in context
- [ ] Fallback to HA API works when database unavailable

### YAML Generation
- [ ] Uses database-friendly names
- [ ] Includes available services in prompts
- [ ] Validates service calls against available_services
- [ ] Rejects invalid service calls
- [ ] Uses correct entity IDs from database

### Entity Enrichment
- [ ] Database-first lookup works
- [ ] Updates database with enriched data
- [ ] Determines available_services correctly
- [ ] Fallback to HA API works

### Service Validation
- [ ] Validates service calls exist in available_services
- [ ] Validates service parameters against capabilities
- [ ] Provides clear error messages
- [ ] Works with all entity domains

## Success Criteria

1. ✅ All services use database-first lookup for entity information
2. ✅ All prompts include friendly names from database (name, name_by_user, original_name)
3. ✅ All prompts include available services for each entity
4. ✅ All prompts include device metadata (manufacturer, model, sw_version)
5. ✅ YAML generation validates service calls against available_services
6. ✅ Service calls match entity capabilities
7. ✅ Entity IDs are actual HA entity IDs (not generated)
8. ✅ AI prompts have complete entity information for best suggestions

## Related Files

### Core Services
- `services/ai-automation-service/src/prompt_building/entity_context_builder.py`
- `services/ai-automation-service/src/prompt_building/unified_prompt_builder.py`
- `services/ai-automation-service/src/services/entity_attribute_service.py`
- `services/ai-automation-service/src/services/service_validator.py` (NEW)
- `services/ai-automation-service/src/api/ask_ai_router.py`

### Database Models
- `services/data-api/src/models/entity.py`
- `services/data-api/src/models/device.py`
- `services/data-api/src/models/service.py` (NEW)

## Next Steps

1. Implement database-first lookup pattern
2. Add available_services to all entity contexts
3. Create ServiceValidator service
4. Update all prompt builders to use complete entity information
5. Test all services with database-first lookup
6. Validate service calls in YAML generation

