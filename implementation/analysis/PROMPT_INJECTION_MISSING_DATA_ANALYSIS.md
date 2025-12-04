# Prompt Injection Missing Data Analysis

**Date:** December 4, 2025  
**Status:** Analysis Complete  
**Issue:** Prompt injection missing entity state attributes (effects, themes, presets, etc.)

---

## Executive Summary

The prompt injection system is **missing critical entity state attributes** that are available in Home Assistant's 2025 API but not being extracted and injected into the LLM context. Specifically:

1. **Entity State Attributes** - `effect_list`, `preset_list`, `theme_list`, and other dynamic attributes
2. **Service Parameter Schemas** - Full parameter definitions with enum values (e.g., effect names)
3. **Entity-Specific Options** - Device-specific configuration from entity registry

---

## Current Prompt Injection Architecture

### What We DO Inject

1. **Entity Inventory** (`EntityInventoryService`)
   - Entity counts by domain/area
   - Entity IDs, friendly names, device IDs
   - Current states (on/off, etc.)
   - Aliases and labels
   - **Missing:** Entity state attributes (effect_list, etc.)

2. **Areas** (`AreasService`)
   - Area IDs and friendly names
   - Area aliases and icons
   - ✅ Complete

3. **Available Services** (`ServicesSummaryService`)
   - Service names by domain
   - Parameter types (string, int, etc.)
   - **Missing:** Enum values (e.g., effect names from effect_list)

4. **Device Capability Patterns** (`CapabilityPatternsService`)
   - Capability types (numeric, enum, composite)
   - Ranges and units
   - **Partially Missing:** Full enum lists (only shows first 5 effects)

5. **Helpers & Scenes** (`HelpersScenesService`)
   - Helper entity IDs and states
   - Scene entity IDs and names
   - ✅ Complete

---

## Missing Home Assistant 2025 API Data

### 1. Entity State Attributes (CRITICAL)

**What's Missing:**
- `effect_list` - List of available effects (WLED has 186+ effects)
- `effect` - Current effect name
- `preset_list` - Available presets (if supported)
- `theme_list` - Available themes (if supported)
- `supported_color_modes` - Color mode capabilities
- `color_mode` - Current color mode
- Other device-specific attributes

**Where It's Available:**
- **Home Assistant API:** `GET /api/states/{entity_id}`
- **Response includes:** Full state object with `attributes` dictionary

**Current Code:**
```python
# services/ha-ai-agent-service/src/services/entity_inventory_service.py:83
states = await self.ha_client.get_states()
state_map = {state.get("entity_id"): state for state in states}
```

**Problem:** We fetch all states but only use `state` field, not `attributes.effect_list`, etc.

**Example Missing Data:**
```json
{
  "entity_id": "light.office_wled",
  "state": "on",
  "attributes": {
    "effect_list": ["Fireworks", "Rainbow", "Chase", ... 186 total],
    "effect": "Fireworks",
    "rgb_color": [255, 0, 0],
    "brightness": 255,
    "supported_color_modes": ["rgb", "hs", "color_temp"]
  }
}
```

---

### 2. Service Parameter Schemas with Enum Values

**What's Missing:**
- Full parameter schemas for `light.turn_on` service
- Enum values for `effect` parameter (should list all effects from effect_list)
- Enum values for other parameters (fan_mode, hvac_mode, etc.)

**Where It's Available:**
- **Home Assistant API:** `GET /api/services/{domain}/{service}`
- **Response includes:** Full schema with enum values

**Current Code:**
```python
# services/ha-ai-agent-service/src/services/services_summary_service.py
services = await self.ha_client.get_services()
```

**Problem:** We get service names but not full parameter schemas with enum values.

**Example Missing Data:**
```json
{
  "light.turn_on": {
    "fields": {
      "effect": {
        "type": "string",
        "required": false,
        "selector": {
          "select": {
            "options": ["Fireworks", "Rainbow", "Chase", ...]
          }
        }
      }
    }
  }
}
```

---

### 3. Entity Registry Options

**What's Missing:**
- Entity-specific options/config from entity registry
- Default values (e.g., default brightness)
- Device-specific settings

**Where It's Available:**
- **Home Assistant WebSocket:** `config/entity_registry/list`
- **Field:** `options` dictionary in entity registry

**Current Code:**
- Entity registry is fetched but `options` field is not extracted/injected

---

## Why This Matters (WLED Example)

**User Request:** "Make the LED light in the office shoot fireworks every 15 mins"

**Current Behavior:**
- LLM knows light exists (`light.office_wled`)
- LLM knows it supports `effect` capability (from capability patterns)
- **LLM does NOT know:**
  - What effects are available (Fireworks, Rainbow, etc.)
  - Exact effect name format ("Fireworks" vs "fireworks" vs "Fireworks 1")
  - Current effect value

**Result:** LLM may generate incorrect effect names or ask user for clarification.

**With Full Data:**
- LLM would see: `effect_list: ["Fireworks", "Rainbow", "Chase", ...]`
- LLM would know exact effect name: `effect: "Fireworks"`
- LLM would generate correct automation immediately

---

## Home Assistant 2025 API Endpoints We're NOT Calling

### 1. Entity State Endpoint (Per Entity)
```
GET /api/states/{entity_id}
```
**Purpose:** Get full state with attributes for specific entity  
**Current Usage:** Only used in `get_entity_state()` for individual lookups  
**Missing:** Not used for bulk attribute extraction in prompt injection

### 2. Service Schema Endpoint
```
GET /api/services/{domain}/{service}
```
**Purpose:** Get full service schema with enum values  
**Current Usage:** Not called  
**Missing:** Full parameter schemas with enum values

### 3. Entity Registry with Options
```
WebSocket: config/entity_registry/list
```
**Purpose:** Get entity registry with options field  
**Current Usage:** Options field not extracted  
**Missing:** Entity-specific configuration

---

## Recommended Solution

### Phase 1: Extract Entity State Attributes

**Modify:** `EntityInventoryService.get_summary()`

**Add:**
1. Extract `effect_list` from entity states for light entities
2. Extract `preset_list`, `theme_list` if available
3. Extract `supported_color_modes`
4. Format as: `"light.office_wled: effect_list (186 effects: Fireworks, Rainbow, ...), rgb_color, brightness (0-255)"`

**Code Change:**
```python
# In entity_inventory_service.py
for entity in entities:
    entity_id = entity.get("entity_id", "")
    state = state_map.get(entity_id, {})
    attributes = state.get("attributes", {})
    
    # Extract effect_list for lights
    if domain == "light" and "effect_list" in attributes:
        effects = attributes.get("effect_list", [])
        if effects:
            # Add to sample info
            sample["effect_list"] = effects[:10]  # First 10 effects
            sample["effect_list_count"] = len(effects)
```

### Phase 2: Enhance Service Schemas

**Modify:** `ServicesSummaryService.get_summary()`

**Add:**
1. Call `GET /api/services/{domain}/{service}` for each service
2. Extract enum values from parameter schemas
3. Format as: `"light.turn_on: effect (enum: Fireworks, Rainbow, ...), brightness (0-255)"`

### Phase 3: Add Entity-Specific Attributes Section

**New Service:** `EntityAttributesService`

**Purpose:** Extract and format entity state attributes for context injection

**Format:**
```
ENTITY ATTRIBUTES:
light.office_wled:
  effect_list: [Fireworks, Rainbow, Chase, ... (186 total)]
  current_effect: Fireworks
  supported_color_modes: [rgb, hs, color_temp]
  brightness: 0-255
```

---

## Impact Assessment

### Current State
- ✅ LLM knows entities exist
- ✅ LLM knows basic capabilities (brightness, rgb_color, effect)
- ❌ LLM does NOT know available effect names
- ❌ LLM does NOT know exact parameter values

### With Fix
- ✅ LLM knows entities exist
- ✅ LLM knows basic capabilities
- ✅ LLM knows available effect names (Fireworks, Rainbow, etc.)
- ✅ LLM knows exact parameter values
- ✅ LLM can generate correct automations without asking user

---

## Implementation Priority

1. **HIGH:** Extract `effect_list` from entity states (WLED, Hue effects)
2. **MEDIUM:** Extract service parameter enum values
3. **LOW:** Extract entity registry options

---

## Related Files

- `services/ha-ai-agent-service/src/services/entity_inventory_service.py` - Add attribute extraction
- `services/ha-ai-agent-service/src/services/services_summary_service.py` - Add enum extraction
- `services/ha-ai-agent-service/src/clients/ha_client.py` - Already has `get_entity_state()` method
- `services/ha-ai-agent-service/src/services/capability_patterns_service.py` - Fallback tries to extract but from wrong source

---

## Conclusion

The prompt injection system is missing **entity state attributes** that are critical for generating accurate automations. Specifically:

1. **Effect lists** - Not extracted from entity states
2. **Service enum values** - Not extracted from service schemas
3. **Entity options** - Not extracted from entity registry

**Solution:** Extract these attributes from Home Assistant API responses and inject them into the context prompt.

