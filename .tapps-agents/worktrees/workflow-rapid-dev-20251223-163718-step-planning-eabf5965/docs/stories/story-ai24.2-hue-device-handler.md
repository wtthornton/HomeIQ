# Story AI24.2: Hue Device Handler (Proof of Concept)

**Epic:** Epic AI-24 - Device Mapping Library Architecture  
**Status:** Ready for Review  
**Created:** 2025-01-XX  
**Story Points:** 3  
**Priority:** High

---

## Story

**As an** AI agent,  
**I want** Hue Room/Zone groups to be automatically detected,  
**so that** automation creation can correctly use Room entities vs individual lights.

---

## Story Context

**Existing System Integration:**

- **Integrates with:** Device Mapping Library (Story AI24.1)
- **Technology:** Python, YAML configuration
- **Location:** `services/device-intelligence-service/src/device_mappings/hue/`
- **Touch points:**
  - `src/device_mappings/hue/handler.py` - Hue handler implementation
  - `src/device_mappings/hue/config.yaml` - Hue configuration
  - `src/device_mappings/hue/__init__.py` - Handler registration

**Current Behavior:**
- Hue Room/Zone groups not distinguished from individual lights
- No relationship mapping between Room groups and individual lights
- Context doesn't indicate when an entity is a Room group

**New Behavior:**
- Hue Room/Zone groups automatically detected (Model: "Room" or "Zone")
- Individual lights identified separately
- Relationship mapping (lights to room groups)
- Context enrichment with device-specific descriptions

---

## Acceptance Criteria

**Functional Requirements:**

1. Hue handler module created (`device_mappings/hue/handler.py`) (AC#1)
2. Hue Room/Zone group detection implemented (Model: "Room" or "Zone") (AC#2)
3. Individual light identification implemented (AC#3)
4. Relationship mapping (lights to room groups) implemented (AC#4)
5. Context enrichment for Hue devices (AC#5)
6. Configuration file (`device_mappings/hue/config.yaml`) (AC#6)
7. Handler registered in plugin registry (AC#7)
8. Unit tests for Hue handler (AC#8)
9. Integration test: Hue Room groups detected correctly (AC#9)

**Technical Requirements:**

- Detection: `device.manufacturer.lower() in ["signify", "philips"]` AND `device.model.lower() in ["room", "zone"]`
- Context format: "Office (Hue Room - controls all Office lights)"
- Individual lights linked to Room groups via area_id

**Integration Verification:**

- IV1: Existing entity inventory continues to work for non-Hue devices
- IV2: Hue devices show correct device types in context
- IV3: Hue Room groups linked to individual lights correctly

---

## Tasks

- [x] **Task 1:** Create Hue handler module (`device_mappings/hue/handler.py`)
- [x] **Task 2:** Implement `can_handle()` method (manufacturer/model detection)
- [x] **Task 3:** Implement `identify_type()` method (Room/Zone vs individual)
- [x] **Task 4:** Implement `get_relationships()` method (lights to room groups)
- [x] **Task 5:** Implement `enrich_context()` method (device-specific descriptions)
- [x] **Task 6:** Create configuration file (`device_mappings/hue/config.yaml`)
- [x] **Task 7:** Create `__init__.py` with register function
- [x] **Task 8:** Write unit tests for Hue handler
- [x] **Task 9:** Write integration test

---

## Implementation Notes

**Detection Logic:**
```python
# Room/Zone Group Detection
if device.get("manufacturer", "").lower() in ["signify", "philips"]:
    if device.get("model", "").lower() in ["room", "zone"]:
        # This is a Hue Room/Zone group
        return DeviceType.GROUP

# Individual Light Detection
if device.get("manufacturer", "").lower() in ["signify", "philips"]:
    if device.get("model", "").lower() not in ["room", "zone"]:
        # This is an individual Hue light
        return DeviceType.INDIVIDUAL
```

**Context Format:**
```
Office (light.office, Hue Room - controls all Office lights)
  - Individual lights in room:
    - Office Go (light.office_go, Hue go)
    - Office Back Right (light.office_back_right, Hue color downlight)
```

---

## Testing

**Unit Tests:**
- Test `can_handle()` with various manufacturers/models
- Test `identify_type()` for Room/Zone groups vs individual lights
- Test `get_relationships()` for lights to room groups
- Test `enrich_context()` for device descriptions

**Integration Tests:**
- Test handler registration
- Test handler selection for Hue devices
- Test Room group detection with real device data

---

## Definition of Done

- [ ] Hue handler module created
- [ ] Room/Zone group detection implemented
- [ ] Individual light identification implemented
- [ ] Relationship mapping implemented
- [ ] Context enrichment implemented
- [ ] Configuration file created
- [ ] Handler registered in plugin registry
- [ ] Unit tests written
- [ ] Integration test written
- [ ] All acceptance criteria met
- [ ] Code reviewed and approved

