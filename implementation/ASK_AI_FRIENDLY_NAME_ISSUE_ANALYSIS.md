# Ask AI Friendly Name Issue - Analysis

## Problem

The UI is showing friendly names like:
- "Hue Color Downlight 4"
- "Hue Color Downlight 17"
- "Hue Color Downlight 14"
- "Hue Color Downlight 1"

But Home Assistant shows the actual device names as:
- "Office Back Left"
- "Office Back Right"
- "Office Front Left"
- "Office Front Right"

## Root Cause

### Current Implementation

The code is using **State API** (`/api/states/{entity_id}`) which returns:
```python
attributes.get('friendly_name')  # Line 89 in entity_attribute_service.py
```

### The Problem

In Home Assistant, there are **two different sources** for entity names:

1. **Entity Registry** (`/api/config/entity_registry/list`)
   - Contains the entity's `name` field
   - This is what shows in the HA UI
   - This is the "correct" friendly name

2. **State API** (`/api/states/{entity_id}`)
   - Contains `attributes.friendly_name`
   - This is often auto-generated or may not match the Entity Registry name
   - Can be different from what shows in the UI

### Why This Happens

The `attributes.friendly_name` from the State API is often:
- Auto-generated from the device name + entity type
- May not reflect user customizations
- May not match what's in the Entity Registry

The Entity Registry `name` field is:
- The actual name shown in the HA UI
- User-customizable
- The "source of truth" for entity names

## Solution

We need to use the **Entity Registry API** to get the correct entity names.

### Home Assistant 2025 API

**Entity Registry Endpoint:**
```
GET /api/config/entity_registry/list
```

Returns:
```json
{
  "entities": [
    {
      "entity_id": "light.hue_color_downlight_1_7",
      "name": "Office Back Left",  // <-- This is what we need!
      "platform": "hue",
      "config_entry_id": "...",
      "device_id": "...",
      "area_id": "...",
      ...
    }
  ]
}
```

### Implementation Changes Needed

1. **Add Entity Registry Client Method** (`ha_client.py`)
   ```python
   async def get_entity_registry(self) -> Dict[str, Dict[str, Any]]:
       """Get entity registry from HA."""
       # Returns dict mapping entity_id -> entity registry data
   ```

2. **Update EntityAttributeService** (`entity_attribute_service.py`)
   - Fetch entity registry data
   - Use `entity_registry[entity_id]['name']` as primary source
   - Fallback to `attributes.friendly_name` if registry name not available

3. **Priority Order for Friendly Name:**
   1. Entity Registry `name` (primary - what shows in HA UI)
   2. Entity Registry `original_name` (if name is None)
   3. State API `attributes.friendly_name` (fallback)
   4. Derived from entity_id (last resort)

## Files to Modify

1. `services/ai-automation-service/src/clients/ha_client.py`
   - Add `get_entity_registry()` method

2. `services/ai-automation-service/src/services/entity_attribute_service.py`
   - Update `enrich_entity_with_attributes()` to use Entity Registry
   - Cache entity registry data for performance

3. `services/ai-automation-service/src/api/ask_ai_router.py`
   - Ensure EntityAttributeService is initialized with entity registry support

## Testing

1. Query Entity Registry API directly to verify names match HA UI
2. Test that enriched entities use Entity Registry names
3. Verify fallback logic works if Entity Registry unavailable
4. Check that UI shows correct names matching HA

## References

- Home Assistant Entity Registry API: `/api/config/entity_registry/list`
- Home Assistant State API: `/api/states/{entity_id}`
- The Entity Registry `name` field is what shows in the HA UI

