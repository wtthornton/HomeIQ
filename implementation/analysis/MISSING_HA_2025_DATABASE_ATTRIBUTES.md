# Missing Home Assistant 2025 Database Attributes Analysis

**Date:** November 2025  
**Status:** Analysis Complete  
**Purpose:** Identify missing Home Assistant 2025 API attributes in AI Automation Service database schema

---

## Executive Summary

After reviewing the AI Automation Service database schema against Home Assistant 2025 API capabilities, **several important attributes are missing** that could enhance automation suggestions, entity resolution, and device intelligence. The missing attributes fall into three categories:

1. **Entity Registry Attributes** - Missing icon, options, labels, aliases
2. **Device Registry Attributes** - Missing labels, serial_number, model_id
3. **Entity State Attributes** - Missing some capability metadata fields

**Impact:** Missing attributes limit the service's ability to:
- Better match user queries to entities (aliases, labels)
- Organize and filter suggestions (labels)
- Provide richer entity context (options, current icon)
- Improve device identification (serial_number, model_id)

---

## 1. Entity Registry Missing Attributes

### Current Implementation

**What We Store (from `Entity` model in `data-api`):**
```python
# Core fields
entity_id, device_id, domain, platform, unique_id, area_id, disabled
# Name fields (2025 HA API)
name, name_by_user, original_name, friendly_name
# Capabilities
supported_features, capabilities, available_services
# Attributes
icon, device_class, unit_of_measurement
# Source tracking
config_entry_id
# Timestamps
created_at, updated_at
```

**What We Retrieve (from `HAEntity` in `device-intelligence-service`):**
```python
entity_id, name, original_name, device_id, area_id, platform, domain,
disabled_by, entity_category, hidden_by, has_entity_name, original_icon,
unique_id, translation_key, created_at, updated_at
```

### Missing Attributes

#### 1.1 `icon` (Current Icon)
**Home Assistant 2025 API:** Entity Registry includes `icon` field (current icon, not just `original_icon`)  
**Current Status:** ❌ **MISSING**  
**Why Important:**
- `original_icon` is the icon from the integration/platform
- `icon` is the current icon (may be user-customized)
- UI displays use current icon, not original
- Icon changes can indicate user preferences

**Impact:**
- Suggestion UI may show wrong icons
- Icon-based filtering won't work correctly
- User customization of icons not reflected

**Recommendation:** Add `icon` field to `Entity` model (separate from `original_icon`)

#### 1.2 `options` (Entity Options)
**Home Assistant 2025 API:** Entity Registry includes `options` field (entity-specific configuration)  
**Current Status:** ❌ **MISSING**  
**Why Important:**
- Contains entity-specific settings (e.g., light brightness defaults, sensor precision)
- Indicates user preferences for entity behavior
- Can inform automation suggestions (e.g., "this light is set to 50% default brightness")

**Example:**
```json
{
  "options": {
    "light": {
      "preferred_color": [255, 200, 150],
      "default_brightness": 128
    }
  }
}
```

**Impact:**
- Cannot detect user preferences for entity behavior
- Suggestions may not respect user-configured defaults
- Missing context for why certain automations make sense

**Recommendation:** Add `options` JSON field to `Entity` model

#### 1.3 `labels` (Entity Labels)
**Home Assistant 2025 API:** Entity Registry includes `labels` field (array of label IDs)  
**Current Status:** ❌ **MISSING**  
**Why Important:**
- Labels are user-defined organizational tags (e.g., "outdoor", "security", "entertainment")
- Enable filtering and grouping of entities
- Can inform automation suggestions (e.g., "all outdoor lights", "all security devices")

**Example:**
```json
{
  "labels": ["outdoor", "security", "motion"]
}
```

**Impact:**
- Cannot filter suggestions by user-defined labels
- Missing organizational context for entities
- Cannot suggest automations based on label groups

**Recommendation:** Add `labels` JSON array field to `Entity` model

#### 1.4 `aliases` (Entity Aliases)
**Home Assistant 2025 API:** Entity Registry includes `aliases` field (array of alternative names)  
**Current Status:** ❌ **MISSING**  
**Why Important:**
- Aliases are alternative names users can assign to entities
- Improve entity resolution from natural language queries
- Better matching for user queries (e.g., "desk light" → `light.office_desk`)

**Example:**
```json
{
  "aliases": ["desk light", "work light", "office desk"]
}
```

**Impact:**
- Entity resolution may miss entities with aliases
- Natural language queries may not match aliased entities
- User-defined nicknames not leveraged for matching

**Recommendation:** Add `aliases` JSON array field to `Entity` model

#### 1.5 `name_by_user` (Entity Registry)
**Home Assistant 2025 API:** Entity Registry includes `name_by_user` field  
**Current Status:** ⚠️ **PARTIALLY MISSING**  
**Why Important:**
- `name_by_user` is the user-customized name (overrides `name`)
- We store `name_by_user` in `Entity` model, but it's not retrieved from Entity Registry API
- Entity Registry is the source of truth for user-customized names

**Current Gap:**
- `HAEntity` dataclass doesn't include `name_by_user`
- Entity Registry retrieval doesn't capture `name_by_user`
- We rely on State API `friendly_name` instead of Entity Registry `name_by_user`

**Impact:**
- May miss user-customized entity names
- Entity Registry is more reliable than State API for names

**Recommendation:** Add `name_by_user` to `HAEntity` dataclass and retrieval logic

---

## 2. Device Registry Missing Attributes

### Current Implementation

**What We Store (from `Device` model in `data-api`):**
```python
# Core fields
device_id, name, name_by_user, manufacturer, model, sw_version, area_id,
integration, entry_type, configuration_url, suggested_area
# Source tracking
config_entry_id, via_device
# Device intelligence (custom)
device_type, device_category, power_consumption_*, infrared_codes_json,
setup_instructions_url, troubleshooting_notes, device_features_json,
community_rating, last_capability_sync
# Timestamps
last_seen, created_at
```

**What We Retrieve (from `HADevice` in `device-intelligence-service`):**
```python
id, name, name_by_user, manufacturer, model, area_id, suggested_area,
integration, entry_type, configuration_url, config_entries, identifiers,
connections, sw_version, hw_version, via_device_id, disabled_by,
created_at, updated_at
```

### Missing Attributes

#### 2.1 `labels` (Device Labels)
**Home Assistant 2025 API:** Device Registry includes `labels` field (array of label IDs)  
**Current Status:** ❌ **MISSING**  
**Why Important:**
- Labels are user-defined organizational tags for devices
- Enable filtering and grouping of devices
- Can inform automation suggestions (e.g., "all outdoor devices", "all security devices")

**Example:**
```json
{
  "labels": ["outdoor", "security", "zigbee"]
}
```

**Impact:**
- Cannot filter suggestions by user-defined device labels
- Missing organizational context for devices
- Cannot suggest automations based on label groups

**Recommendation:** Add `labels` JSON array field to `Device` model

#### 2.2 `serial_number` (Device Serial Number)
**Home Assistant 2025 API:** Device Registry may include `serial_number` field (if available from integration)  
**Current Status:** ❌ **MISSING**  
**Why Important:**
- Serial numbers uniquely identify physical devices
- Useful for device tracking and troubleshooting
- Can help distinguish between multiple devices of same model

**Impact:**
- Cannot uniquely identify devices by serial number
- Troubleshooting may be harder without serial numbers
- Device tracking less precise

**Recommendation:** Add optional `serial_number` field to `Device` model

#### 2.3 `model_id` (Device Model ID)
**Home Assistant 2025 API:** Device Registry may include `model_id` field (if different from `model`)  
**Current Status:** ❌ **MISSING**  
**Why Important:**
- `model_id` is the manufacturer's model identifier
- May differ from `model` (display name vs. identifier)
- Useful for device capability lookup and matching

**Impact:**
- Device capability matching may be less accurate
- Model identification may miss variations

**Recommendation:** Add optional `model_id` field to `Device` model

---

## 3. Entity State Attributes (Partial Coverage)

### Current Implementation

**What We Store (from InfluxDB events):**
- State changes, attributes (brightness, color_temp, etc.)
- Device/area context
- Timestamps

**What We Retrieve (from State API):**
- Current state, attributes
- `friendly_name` (from State API, not Entity Registry)

### Missing Attributes

#### 3.1 Entity Registry as Source of Truth for Names
**Current Gap:**
- We use State API `friendly_name` for entity names
- Entity Registry `name` / `name_by_user` is more reliable
- Entity Registry is the source of truth for HA UI names

**Impact:**
- Entity names may be inconsistent
- User-customized names may not be reflected

**Recommendation:** Prioritize Entity Registry names over State API `friendly_name`

---

## 4. Summary of Missing Attributes

### Critical (High Impact)

1. **Entity `aliases`** - Critical for entity resolution from natural language
2. **Entity `name_by_user`** - Source of truth for user-customized names
3. **Entity `icon`** - Current icon (not just original_icon)

### Important (Medium Impact)

4. **Entity `labels`** - Organizational filtering and grouping
5. **Device `labels`** - Organizational filtering and grouping
6. **Entity `options`** - User preferences for entity behavior

### Nice to Have (Low Impact)

7. **Device `serial_number`** - Device tracking and troubleshooting
8. **Device `model_id`** - More precise model identification

---

## 5. Recommended Implementation Plan

### Phase 1: Critical Attributes (Immediate)

**Priority:** Add attributes that directly impact entity resolution and user experience

1. **Add Entity `aliases` field**
   - Add to `Entity` model in `data-api`
   - Update `HAEntity` dataclass to include `aliases`
   - Update Entity Registry retrieval to capture `aliases`
   - Update entity resolution logic to use `aliases` for matching

2. **Add Entity `name_by_user` field**
   - Already in `Entity` model, but not retrieved from Entity Registry
   - Update `HAEntity` dataclass to include `name_by_user`
   - Update Entity Registry retrieval to capture `name_by_user`
   - Prioritize Entity Registry `name_by_user` over State API `friendly_name`

3. **Add Entity `icon` field**
   - Add to `Entity` model (separate from `original_icon`)
   - Update `HAEntity` dataclass to include `icon`
   - Update Entity Registry retrieval to capture `icon`
   - Update UI to use current `icon` instead of `original_icon`

### Phase 2: Important Attributes (Short-Term)

**Priority:** Add attributes that enhance filtering and organization

4. **Add Entity `labels` field**
   - Add to `Entity` model as JSON array
   - Update `HAEntity` dataclass to include `labels`
   - Update Entity Registry retrieval to capture `labels`
   - Add label-based filtering to suggestion queries

5. **Add Device `labels` field**
   - Add to `Device` model as JSON array
   - Update `HADevice` dataclass to include `labels`
   - Update Device Registry retrieval to capture `labels`
   - Add label-based filtering to device queries

6. **Add Entity `options` field**
   - Add to `Entity` model as JSON
   - Update `HAEntity` dataclass to include `options`
   - Update Entity Registry retrieval to capture `options`
   - Use `options` to inform automation suggestions (e.g., default brightness)

### Phase 3: Nice to Have (Long-Term)

**Priority:** Add attributes for enhanced device tracking

7. **Add Device `serial_number` field**
   - Add optional field to `Device` model
   - Update `HADevice` dataclass to include `serial_number`
   - Update Device Registry retrieval to capture `serial_number`

8. **Add Device `model_id` field**
   - Add optional field to `Device` model
   - Update `HADevice` dataclass to include `model_id`
   - Update Device Registry retrieval to capture `model_id`

---

## 6. Database Schema Changes Required

### Entity Model Changes (`data-api/src/models/entity.py`)

```python
# Add these fields to Entity model:
icon = Column(String)  # Current icon (separate from original_icon)
name_by_user = Column(String)  # Already exists, but ensure it's populated from Entity Registry
aliases = Column(JSON)  # Array of alternative names
labels = Column(JSON)  # Array of label IDs
options = Column(JSON)  # Entity-specific options/config
```

### Device Model Changes (`data-api/src/models/device.py`)

```python
# Add these fields to Device model:
labels = Column(JSON)  # Array of label IDs
serial_number = Column(String, nullable=True)  # Optional serial number
model_id = Column(String, nullable=True)  # Optional model ID
```

### HAEntity Dataclass Changes (`device-intelligence-service/src/clients/ha_client.py`)

```python
@dataclass
class HAEntity:
    # ... existing fields ...
    name_by_user: str | None  # ADD: User-customized name
    icon: str | None  # ADD: Current icon (not just original_icon)
    aliases: list[str]  # ADD: Alternative names
    labels: list[str]  # ADD: Label IDs
    options: dict[str, Any] | None  # ADD: Entity options
```

### HADevice Dataclass Changes (`device-intelligence-service/src/clients/ha_client.py`)

```python
@dataclass
class HADevice:
    # ... existing fields ...
    labels: list[str]  # ADD: Label IDs
    serial_number: str | None  # ADD: Optional serial number
    model_id: str | None  # ADD: Optional model ID
```

---

## 7. Impact Assessment

### Entity Resolution Improvements

**With `aliases` and `name_by_user`:**
- ✅ Better matching for natural language queries
- ✅ User-defined nicknames properly recognized
- ✅ More accurate entity resolution

**Example:**
```
User Query: "turn on my desk light"
Current: May not find if entity is named "Office Desk Light"
With aliases: Matches if "desk light" is in aliases array
```

### Suggestion Filtering Improvements

**With `labels`:**
- ✅ Filter suggestions by user-defined categories
- ✅ Group automations by label (e.g., "all outdoor automations")
- ✅ Better organization of suggestions

**Example:**
```
User Query: "automate all my outdoor lights"
Current: Must manually identify outdoor entities
With labels: Filter by "outdoor" label automatically
```

### User Preference Detection

**With `options`:**
- ✅ Detect user preferences for entity behavior
- ✅ Suggest automations that respect user defaults
- ✅ Better context for why automations make sense

**Example:**
```
Entity: light.office_desk
Options: { "default_brightness": 128 }
Suggestion: "Turn on office desk light at 50% brightness (your preferred setting)"
```

---

## 8. Testing Checklist

### Entity Registry Attributes

- [ ] Verify `aliases` are retrieved from Entity Registry API
- [ ] Verify `name_by_user` is retrieved from Entity Registry API
- [ ] Verify `icon` is retrieved from Entity Registry API
- [ ] Verify `labels` are retrieved from Entity Registry API
- [ ] Verify `options` are retrieved from Entity Registry API
- [ ] Test entity resolution with aliases
- [ ] Test entity resolution with name_by_user
- [ ] Test label-based filtering

### Device Registry Attributes

- [ ] Verify `labels` are retrieved from Device Registry API
- [ ] Verify `serial_number` is retrieved (if available)
- [ ] Verify `model_id` is retrieved (if available)
- [ ] Test label-based device filtering

### Database Schema

- [ ] Verify new fields are added to Entity model
- [ ] Verify new fields are added to Device model
- [ ] Verify database migrations work correctly
- [ ] Verify indexes are created for new fields (if needed)

---

## 9. References

- **Home Assistant Entity Registry API:** https://developers.home-assistant.io/docs/api/rest#get-apiconfigentity_registrylist
- **Home Assistant Device Registry API:** https://developers.home-assistant.io/docs/api/rest#get-apiconfigdevice_registrylist
- **Current Entity Model:** `services/data-api/src/models/entity.py`
- **Current Device Model:** `services/data-api/src/models/device.py`
- **HA Client:** `services/device-intelligence-service/src/clients/ha_client.py`
- **HA API Research:** `implementation/analysis/HA_API_2025_RESEARCH.md`

---

**Status:** Analysis Complete ✅  
**Next Step:** Implement Phase 1 (Critical Attributes)  
**Estimated Effort:** 
- Phase 1: 4-6 hours
- Phase 2: 3-4 hours
- Phase 3: 2-3 hours

