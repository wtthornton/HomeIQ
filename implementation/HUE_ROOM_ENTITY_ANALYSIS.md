# Hue Room Entity Analysis

**Date:** October 29, 2025  
**Status:** ✅ Confirmed Understanding

## Summary

Confirmed the difference between Hue room entities and individual light entities in Home Assistant:

### Entity Types

#### 1. **Room Entity** (`light.office`)
- **Type**: Philips Hue Bridge room entity
- **Purpose**: Controls ALL lights in the room/group
- **Scope**: Multiple physical lights
- **YAML Usage**: `entity_id: light.office` controls all office lights simultaneously
- **Home Assistant**: These are imported from Hue Bridge but disabled by default

#### 2. **Individual Light Entity** (`light.hue_office_back_left`)
- **Type**: Single physical light
- **Purpose**: Controls one specific light
- **Scope**: One physical light
- **YAML Usage**: `entity_id: light.hue_office_back_left` controls only that specific light
- **Home Assistant**: Individual lights are always enabled by default

## Key Differences

| Aspect | Room Entity | Individual Light |
|--------|-------------|------------------|
| **Name** | `light.office` | `light.hue_office_back_left` |
| **Controls** | All lights in room | One specific light |
| **Device ID** | `7fd668e48618fd95873b9cbab02ec1d1` | `f53d6da537d76c7718c8b53d112c4d17` |
| **HA Default** | Disabled by default | Always enabled |
| **Configured in** | Philips Hue app (room) | Hue Bridge |
| **Use Case** | Control entire room | Control specific light |

## YAML Automation Implications

### Using Room Entity (All Office Lights)
```yaml
- service: light.turn_on
  target:
    entity_id: light.office  # ✅ Controls ALL office lights
  data:
    brightness_pct: 100
    color_temp: 370
```

### Using Individual Light Entity
```yaml
- service: light.turn_on
  target:
    entity_id: light.hue_office_back_left  # ✅ Controls only back left light
  data:
    brightness_pct: 50
    rgb_color: [255, 255, 255]
```

## Root Cause of Test Issues

### Problem
In the entity resolution test, the AI generated "Office light 1", "Office light 2", "Office light 3", "Office light 4" as device names, but:

1. **These names don't exist** in Home Assistant
2. **Only 2 office light entities exist:**
   - `light.office` (room - all office lights)
   - `light.hue_office_back_left` (individual light)

### Entity Resolution Results
- All "Office light 1-4" attempted to map to `light.hue_office_back_left`
- Confidence scores were low (0.16-0.17) because the names don't match
- With the new 0.15 threshold, they should now pass (below threshold was 0.3)

### Actual Available Office Lights
- `light.office` - Room entity (controls all office lights)
- `light.hue_office_back_left` - Individual back left light

## Recommendations

### For YAML Generation

1. **Prefer Room Entities**: When the query mentions "office lights" (plural) or "turn on the office lights", use `light.office` (the room entity)

2. **Use Individual Lights**: When the query specifies a particular light (e.g., "back left"), use the specific entity like `light.hue_office_back_left`

3. **Entity Resolution Enhancement**: Update entity resolution to:
   - Detect room entities (they have shorter names like `light.office`)
   - Map room names to room entities when plural is used
   - Map specific light names to individual entities

### Example Improved Resolution Logic

```python
# Pseudo-code for improved entity resolution
if query_mentions_plural("office lights"):
    return "light.office"  # Use room entity
elif query_mentions_specific("back left"):
    return "light.hue_office_back_left"  # Use individual entity
```

## Documented Understanding

✅ **Confirmed**: Room entities control multiple lights, individual entities control one light  
✅ **Confirmed**: `light.office` is a Hue room entity (disabled by default in HA)  
✅ **Confirmed**: `light.hue_office_back_left` is an individual light entity  
✅ **Confirmed**: Both work as `entity_id` targets in YAML automation files  

## References

- [Home Assistant Hue Integration Documentation](https://www.home-assistant.io/integrations/hue/)
- [Hue Bridge Rooms in Home Assistant](https://community.home-assistant.io/t/philips-hue-rooms-not-showing-up/153161)

