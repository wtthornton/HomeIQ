# Story AI23.3: Device Type Detection & Context Enrichment

**Epic:** Epic AI-23 - Device Registry & Entity Registry Integration  
**Status:** Ready for Review  
**Created:** 2025-12-05  
**Story Points:** 3  
**Priority:** Medium

---

## Story

**As an** AI agent,  
**I want** device-specific intelligence (Hue Room groups, WLED segments),  
**so that** automation creation can correctly use group entities vs individual entities.

---

## Story Context

**Existing System Integration:**

- **Integrates with:** HA AI Agent Service (Port 8030, FastAPI 0.123.x, Python 3.12+)
- **Technology:** Device Registry data (from Story AI23.1)
- **Follows pattern:** Context enrichment in Entity Inventory Service
- **Touch points:**
  - `services/ha-ai-agent-service/src/services/entity_inventory_service.py` - Device type detection logic
  - `services/ha-ai-agent-service/src/prompts/system_prompt.py` - System prompt with device-specific guidelines

**Current Behavior:**
- No distinction between Hue Room groups and individual lights
- No distinction between WLED master entities and segments
- Context doesn't show device relationships

**New Behavior:**
- Hue Room/Zone groups identified (Model: "Room" or "Zone")
- WLED master/segment detection (`_segment_` in entity_id)
- Device relationships included in context (segments → master, lights → room)
- Context format shows device types: "Office (Hue Room - controls all Office lights)"
- System prompt updated with device-specific guidelines

---

## Acceptance Criteria

**Functional Requirements:**

1. Hue Room/Zone group detection implemented (Model: "Room" or "Zone") (AC#1)
2. WLED master/segment detection implemented (`_segment_` in entity_id) (AC#2)
3. Device relationships included in context (e.g., segments → master, lights → room) (AC#3)
4. Context format shows device types: "Office (Hue Room - controls all Office lights)" (AC#4)
5. System prompt updated with device-specific guidelines (AC#5)
6. Unit tests for detection logic (AC#6)
7. Integration test: Context shows correct device types and relationships (AC#7)

**Integration Verification:**

- IV1: Existing entity context format maintained for non-special devices
- IV2: Device-specific context adds clarity without breaking existing logic
- IV3: System prompt guidelines improve automation creation accuracy

**Technical Notes:**

- Detection logic in Entity Inventory Service
- Context enrichment adds device-specific descriptions
- System prompt includes guidelines for Hue Room groups and WLED segments

---

## Tasks / Subtasks

- [x] **Task 1: Implement Hue Room/Zone group detection** (AC: 1)
  - [x] Check device model for "Room" or "Zone" (case-insensitive)
  - [x] Mark devices as Hue Room groups
  - [x] Link individual lights to Room groups via device_id

- [x] **Task 2: Implement WLED master/segment detection** (AC: 2)
  - [x] Check entity_id for `_segment_` pattern
  - [x] Identify master entities (not segments)
  - [x] Link segments to master entities

- [x] **Task 3: Add device relationships to context** (AC: 3)
  - [x] Create device relationship mapping
  - [x] Include relationships in entity examples
  - [x] Format: "Office (Hue Room - controls all Office lights)"

- [x] **Task 4: Update context format with device types** (AC: 4)
  - [x] Add device type descriptions to entity summary
  - [x] Show device relationships in examples
  - [x] Maintain backward compatibility

- [x] **Task 5: Update system prompt** (AC: 5)
  - [x] Add guidelines for Hue Room groups
  - [x] Add guidelines for WLED segments
  - [x] Document when to use group vs individual entities

- [x] **Task 6: Write unit tests** (AC: 6)
  - [x] Test Hue Room detection
  - [x] Test WLED segment detection
  - [x] Test device relationship mapping

- [x] **Task 7: Write integration test** (AC: 7)
  - [x] Test context shows correct device types
  - [x] Test device relationships appear in context
  - [x] Verify non-special devices still work

---

## Dev Notes

### Project Context

This story adds device-specific intelligence to help the AI agent understand device relationships and use the correct entities in automations.

### Key Implementation Details

1. **Hue Room Detection:** Check device model for "Room" or "Zone"
2. **WLED Detection:** Check entity_id for `_segment_` pattern
3. **Context Format:** Add device type descriptions without breaking existing format
4. **System Prompt:** Add guidelines for device-specific usage

### Files to Modify

- `services/ha-ai-agent-service/src/services/entity_inventory_service.py` - Device type detection logic
- `services/ha-ai-agent-service/src/prompts/system_prompt.py` - System prompt guidelines
- `services/ha-ai-agent-service/tests/test_entity_inventory_service.py` - Device type tests

### Testing Strategy

1. Unit tests for detection logic
2. Integration test: Verify device types appear in context
3. Regression test: Verify non-special devices still work

---

## Dev Agent Record

### Agent Model Used
Claude Sonnet 4.5

### Debug Log References
- None yet

### Completion Notes
- None yet

### File List
- `services/ha-ai-agent-service/src/services/entity_inventory_service.py` - Added device type detection logic (Hue Room, WLED)
- `services/ha-ai-agent-service/src/prompts/system_prompt.py` - Added device-specific guidelines
- `services/ha-ai-agent-service/tests/test_entity_inventory_service.py` - Added device type detection tests

### Change Log
- 2025-12-05: Story created
- 2025-12-05: Implemented device type detection and context enrichment
  - Added Hue Room/Zone group detection (model contains "Room" or "Zone")
  - Added WLED master/segment detection (entity_id contains "_segment_")
  - Added device relationships to context
  - Updated system prompt with device-specific guidelines
  - Added comprehensive tests

