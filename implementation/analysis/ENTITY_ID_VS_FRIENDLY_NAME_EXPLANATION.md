# Entity ID vs Friendly Name in Home Assistant YAML

## Answer: YAML MUST Use Entity IDs

**Home Assistant YAML automations REQUIRE entity IDs, NOT friendly names.**

- ✅ **YAML uses:** `light.hue_color_downlight_2_2` (entity ID)
- ❌ **YAML CANNOT use:** `"Office Front Right"` (friendly name) - This will cause "Entity not found" errors

## Where These Two Identifiers Come From

### 1. Entity ID (`light.hue_color_downlight_2_2`)

**Source:** Home Assistant Entity Registry

**Database Storage:**
- **Table:** `entities` (SQLite)
- **Field:** `entity_id` 
- **Format:** `domain.unique_id`
  - Example: `light.hue_color_downlight_2_2`
  - Domain: `light` (device type)
  - Unique ID: `hue_color_downlight_2_2` (manufacturer-specific identifier)

**How It's Stored:**
```sql
-- From services/data-api/src/models/entity.py
class Entity(Base):
    entity_id: str = Column(String, primary_key=True)  # e.g., "light.hue_color_downlight_2_2"
    domain: str = Column(String)  # e.g., "light"
    area_id: str = Column(String)  # e.g., "office"
```

**API Response:**
```json
{
  "entity_id": "light.hue_color_downlight_2_2",
  "domain": "light",
  "area_id": "office",
  "device_id": "...",
  ...
}
```

**Location in Code:**
- `services/data-api/src/devices_endpoints.py:355` - Returns `entity_id` field
 `services/data-api/src/models/entity.py:16` - Entity model definition

### 2. Friendly Name ("Office Front Right")

**Source:** Home Assistant State Attributes or Device Registry

**Where It Comes From:**
1. **Entity State Attributes** (primary source):
   - `state.attributes.friendly_name` - Display name from Home Assistant
   - Retrieved from `GET /api/states/{entity_id}`
   - Example: `"Office Front Right"`

2. **Device Registry** (fallback):
   - Device name from device registry
   - Location: `services/device-intelligence-service/src/clients/ha_client.py:337`
   - Field: `entity.name` or `entity.original_name`

3. **Generated** (fallback if not available):
   - Location: `services/ai-automation-service/src/clients/data_api_client.py:377-405`
   - Method: `extract_friendly_name()` generates from entity_id
   - Example: `light.hue_color_downlight_2_2` → "Hue Color Downlight 2 2"

**Database Storage:**
- **NOT directly stored** in Regular entities table
- Stored in device metadata or retrieved from HA state attributes
- Can be cached in entity attributes but not as primary identifier

**API Response:**
- Friendly name comes from Home Assistant state API:
  ```
  GET /api/states/light.hue_color_downlight_2_2
  Response: {
    "state": "on",
    "attributes": {
      "friendly_name": "Office Front Right",  ← This is the friendly name
      ...
    }
  }
  ```

**Location in Code:**
- `services/ai-automation-service/src/clients/data_api_client.py:509` - Extracts `friendly_name` from entity attributes
- `services/websocket-ingestion/src/models.py` - Captures attributes during event ingestion

## Why YAML Must Use Entity IDs

### Home Assistant Requirement

Home Assistant automation YAML **only accepts entity IDs** in the following contexts:

```yaml
# ✅ CORRECT - Uses entity ID
trigger:
  - platform: state
    entity_id: light.hue_color_downlight_2_2  # Entity ID required

action:
  - service: light.turn_on
    target:
      entity_id: light.hue_color_downlight_2_2  # Entity ID required
```

```yaml
# ❌ INCORRECT - Friendly name will fail
trigger:
  - platform: state
    entity_id: "Office Front Right"  # ERROR: Entity not found

action:
  - service: light.turn_on
    target:
      entity_id: "Office Front Right"  # ERROR: Entity not found
```

### Code Enforcement

The system explicitly enforces entity ID usage:

**Location:** `services/ai-automation-service/src/api/ask_ai_router.py:347-348`

```python
validated_entities_text = f"""
CRITICAL: Use ONLY the entity IDs listed above. Do NOT create new entity IDs.
"""
```

The YAML generation prompt tells OpenAI:
- Use **ONLY** the validated entity IDs
- Do **NOT** use friendly names
- Do **NOT** create new entity IDs

## Real Example from Your System

### Device Information:
- **Entity ID:** `light.hue_color_downlight_2_2`
- **Friendly Name:** "Office Front Right" (from HA attributes)
- **Area:** `office` (from database)
- **Domain:** `light`

### In YAML (REQUIRED):
```yaml
action:
  - service: light.turn_on
    target:
      entity_id: light.hue_color_downlight_2_2  # Must use entity ID
    data:
      brightness_pct: 100
```

### In Suggestions/UI (Friendly Name OK):
- Suggestion description: "Turn on Office Front Right pour"
- Quality report: "Devices Involved: Office Front Right"
- User-facing text: Shows friendly name for readability

## Summary

| Field | Used In | Source | Example |
|-------|---------|--------|---------|
| **Entity ID** | YAML automations<br/>API calls<br/>Database queries | Entity registry<br/>Database: `entities.entity_id` | `light.hue_color_downlight_2_2` |
| **Friendly Name** | User interface<br/>Suggestions<br/>Display text | State attributes<br/>Device registry<br/>Generated fallback | `"Office Front Right"` |

**Key Takeaway:**
- ✅ **YAML = Entity IDs only** (`light.hue_color_downlight_2_2`)
- ✅ **UI/Display = Friendly names** (`"Office Front Right"`)
- ❌ **YAML ≠ Friendly names** (will cause errors)

The system correctly uses entity IDs in generated YAML because Home Assistant requires them. Friendly names are only used for user-facing display and suggestions, not in automation YAML.

