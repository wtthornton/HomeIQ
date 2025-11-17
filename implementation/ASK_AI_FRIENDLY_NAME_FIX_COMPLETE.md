# Ask AI Friendly Name Fix - Implementation Complete

## Summary

Fixed the friendly name issue by implementing Entity Registry API support. The system now uses Home Assistant's Entity Registry (source of truth) instead of State API attributes for entity names.

## Problem

The UI was showing auto-generated names like:
- "Hue Color Downlight 4"
- "Hue Color Downlight 17"

Instead of the actual names from Home Assistant:
- "Office Back Left"
- "Office Back Right"
- "Office Front Left"
- "Office Front Right"

## Root Cause

The code was using the **State API** (`/api/states/{entity_id}`) which returns `attributes.friendly_name`. This is often auto-generated and doesn't match what shows in the HA UI.

The **Entity Registry API** (`/api/config/entity_registry/list`) contains the actual entity names as shown in the HA UI and is the source of truth.

## Solution Implemented

### 1. Added Entity Registry API Support (`ha_client.py`)

Added `get_entity_registry()` method that:
- Fetches entity registry from `/api/config/entity_registry/list`
- Returns dictionary mapping `entity_id -> entity registry data`
- Includes the `name` field (what shows in HA UI)

### 2. Updated EntityAttributeService (`entity_attribute_service.py`)

**Added:**
- Entity Registry caching (loaded once, reused for all entities)
- `_get_entity_registry()` method with caching
- `_get_friendly_name_from_registry()` method with priority logic

**Updated:**
- `enrich_entity_with_attributes()` now uses Entity Registry as primary source
- Friendly name priority:
  1. Entity Registry `name` field (what shows in HA UI) ✅
  2. Entity Registry `original_name` field (if name is None)
  3. State API `attributes.friendly_name` (fallback)
  4. Derived from entity_id (last resort)

**Also improved:**
- Uses Entity Registry for `device_id` and `area_id` when available
- Better logging to show which source was used for friendly name

## Files Modified

1. `services/ai-automation-service/src/clients/ha_client.py`
   - Added `get_entity_registry()` method (line ~989)

2. `services/ai-automation-service/src/services/entity_attribute_service.py`
   - Added Entity Registry caching
   - Added `_get_entity_registry()` method
   - Added `_get_friendly_name_from_registry()` method
   - Updated `enrich_entity_with_attributes()` to use Entity Registry

## Deployment

✅ **Deployed** - Service rebuilt and restarted

## Testing

To verify the fix:

1. **Create a new automation suggestion** in the Ask AI UI
2. **Check device names** - Should now match Home Assistant UI names
3. **Check Debug Panel** - Should show correct friendly names
4. **Verify in HA** - Compare names in UI with HA Settings → Devices & Services → Entities

## Expected Behavior

### Before Fix
- Names: "Hue Color Downlight 4", "Hue Color Downlight 17" (auto-generated)
- Source: State API `attributes.friendly_name`

### After Fix
- Names: "Office Back Left", "Office Back Right" (from HA UI)
- Source: Entity Registry `name` field

## Performance

- Entity Registry is cached after first load
- No performance impact - registry loaded once per service instance
- Fallback to State API if Entity Registry unavailable

## Status

✅ **Complete** - Entity Registry API integration implemented and deployed
✅ **No Linting Errors** - All code passes linting checks
✅ **Ready for Testing** - Manual testing recommended

