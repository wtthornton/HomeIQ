# Device Name Priority: name_by_user First

**Last Updated:** January 2025  
**Status:** Current Implementation

## Overview

The system prioritizes `name_by_user` (user-customized names) when displaying device names in automation suggestions and throughout the UI. This ensures users see their custom names from Home Assistant, allowing them to change device names in HA and have those changes reflected in the automation assistant.

## Name Field Priority

When computing `friendly_name` for display, the system uses this priority order:

1. **`name_by_user`** - User-customized name (highest priority)
   - Set by users in Home Assistant Entity Registry
   - Allows users to customize device names as they prefer
   - Example: "Office Back Left", "LR Back Left Ceiling"

2. **`name`** - Primary friendly name from Entity Registry
   - Default name shown in Home Assistant UI
   - Set by the integration or device manufacturer

3. **`original_name`** - Original auto-generated name
   - Fallback when user hasn't customized the name
   - Example: "Hue Color Downlight 1", "Hue Color Downlight 2"

4. **Entity ID derived** - Last resort fallback
   - Derived from entity_id if no other name available
   - Example: `light.hue_color_downlight_1_7` → "Hue Color Downlight 1 7"

## Implementation Locations

### Database Layer (`services/data-api/src/models/entity.py`)

The `Entity` model stores all name fields:
- `name_by_user` - User-customized name (PRIORITY: Used first for display)
- `name` - Primary friendly name from Entity Registry
- `original_name` - Original name before user customization
- `friendly_name` - Stored computed value: `name_by_user or name or original_name`

**Note:** `friendly_name` is computed at write time with priority: `name_by_user > name > original_name`

### Data API (`services/data-api/src/devices_endpoints.py`)

When storing entities from Home Assistant Entity Registry:

```python
# Compute friendly_name (priority: name_by_user > name > original_name > entity_id)
friendly_name = name_by_user or name or original_name
```

### Entity Context Builder (`services/ai-automation-service/src/prompt_building/entity_context_builder.py`)

When building entity context for LLM prompts:

```python
# Extract name fields from database
name = entity_metadata.get('name')
name_by_user = entity_metadata.get('name_by_user')
original_name = entity_metadata.get('original_name')

# Compute friendly_name prioritizing name_by_user (user-customized name)
# Priority: name_by_user > name > original_name
# This ensures users see their custom names from Home Assistant
friendly_name = name_by_user or name or original_name
```

### Entity Attribute Service (`services/ai-automation-service/src/services/entity_attribute_service.py`)

When enriching entities from Home Assistant Entity Registry:

```python
# Priority 1: Use 'name_by_user' field (user-customized name - highest priority)
# This ensures users see their custom names from Home Assistant when available
name_by_user = entity_data.get('name_by_user')
if name_by_user:
    return name_by_user

# Priority 2: Use 'name' field (what shows in HA UI)
name = entity_data.get('name')
if name:
    return name

# Priority 3: Use 'original_name' if name is None
original_name = entity_data.get('original_name')
if original_name:
    return original_name
```

## User Experience

### Before Fix

Users saw auto-generated names like:
- "Hue Color Downlight 1"
- "Hue Color Downlight 2"
- "Hue Color Downlight 15"

### After Fix

Users see their custom names from Home Assistant:
- "Office Back Left"
- "Office Back Right"
- "LR Back Left Ceiling"

## Benefits

1. **User Control**: Users can customize device names in Home Assistant and see those names in automation suggestions
2. **Consistency**: Device names match what users see in Home Assistant UI
3. **Flexibility**: Users can change names in HA and changes are reflected in the automation assistant
4. **Better UX**: More meaningful, user-friendly names instead of auto-generated technical names

## Related Files

- `services/data-api/src/models/entity.py` - Entity model with name fields
- `services/data-api/src/devices_endpoints.py` - Entity storage with name priority
- `services/ai-automation-service/src/prompt_building/entity_context_builder.py` - Entity context building
- `services/ai-automation-service/src/services/entity_attribute_service.py` - Entity enrichment from HA

## Testing

To verify name priority is working:

1. Set a custom name in Home Assistant Entity Registry (`name_by_user`)
2. Create an automation suggestion that includes that device
3. Verify the suggestion shows the custom name, not the auto-generated name
4. Change the name in HA and verify it updates in automation suggestions

## Notes

- The `friendly_name` field in the database is computed at write time, but the code always recomputes it when reading to ensure the latest `name_by_user` value is used
- This priority ensures that user customizations take precedence over system-generated names
- The priority order matches Home Assistant's own display logic for entity names

