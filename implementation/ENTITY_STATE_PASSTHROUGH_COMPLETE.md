# Entity State Passthrough Implementation

**Date:** October 29, 2025  
**Status:** ✅ Completed

## Summary

Implemented a passthrough method to Home Assistant API to fetch entity state with full attributes, including the `is_hue_group` attribute needed to distinguish Hue room groups from individual lights.

## Problem

Entity attributes (like `is_hue_group`) are not stored in our database, and device attributes differ from entity attributes. We need to call Home Assistant directly to get entity states with their complete attributes.

## Solution

Added a new method `get_entity_state()` to the `HomeAssistantClient` that passthroughs to HA's `/api/states/{entity_id}` endpoint.

## Changes Made

### File: `services/ai-automation-service/src/clients/ha_client.py`

**New Method:**
```python
async def get_entity_state(self, entity_id: str) -> Optional[Dict[str, Any]]:
    """
    Get current state and attributes for an entity from Home Assistant.
    
    This is a passthrough to HA's /api/states/{entity_id} endpoint.
    Returns the full state object including attributes like is_hue_group.
    """
```

**What it returns:**
```json
{
  "entity_id": "light.office",
  "state": "on",
  "attributes": {
    "friendly_name": "Office",
    "is_hue_group": true,  // ✅ This attribute!
    "supported_features": 43,
    "device_class": "light",
    ...
  }
}
```

## Usage

### Check if entity is a Hue room group:

```python
from ..clients.ha_client import HomeAssistantClient

# Initialize client
ha_client = HomeAssistantClient(ha_url, access_token)

# Get entity state with attributes
state = await ha_client.get_entity_state('light.office')

if state and state.get('attributes', {}).get('is_hue_group'):
    print("This is a Hue room group - controls all office lights!")
else:
    print("This is an individual light entity")
```

### In Entity Resolution:

```python
# Check entity type before mapping
state = await ha_client.get_entity_state(entity_id)

if state and state.get('attributes', {}).get('is_hue_group'):
    # It's a room group - use for controlling all lights
    entity_type = "group"
else:
    # It's an individual light
    entity_type = "individual"
```

## Benefits

1. **Real-time data** - Always get the latest state and attributes from Home Assistant
2. **No storage overhead** - Don't need to store attributes in database
3. **Correct attributes** - HA has the authoritative entity attributes
4. **Device vs Entity separation** - Device attributes are different from entity attributes
5. **Hue group detection** - Can now identify `is_hue_group: true` for room entities

## Next Steps

1. **Update entity resolution** to use this method when checking entity types
2. **Deploy the changes** to ai-automation-service
3. **Test** with the Hue room entities (`light.office` vs `light.hue_office_back_left`)

## Testing

After deployment, test:

```python
# Test 1: Hue room group
state = await ha_client.get_entity_state('light.office')
assert state['attributes']['is_hue_group'] == True

# Test 2: Individual light
state = await ha_client.get_entity_state('light.hue_office_back_left')
assert state['attributes'].get('is_hue_group') != True  # Should be false or missing
```

## Related Documentation

- `implementation/ENTITY_ATTRIBUTES_ANALYSIS.md` - Analysis of why attributes weren't being captured
- `implementation/HUE_ROOM_ENTITY_ANALYSIS.md` - Understanding of Hue room vs individual entities

