# Story AI24.4: Entity Inventory & System Prompt Integration

**Epic:** Epic AI-24 - Device Mapping Library Architecture  
**Status:** In Progress  
**Created:** 2025-01-XX  
**Story Points:** 2  
**Priority:** Medium

---

## Story

**As an** AI agent,  
**I want** device mappings integrated into entity inventory and system prompt,  
**so that** I receive accurate device intelligence in context.

---

## Story Context

**Existing System Integration:**

- **Integrates with:** Device Mapping Library (Story AI24.1-3), Entity Inventory Service, System Prompt Builder
- **Technology:** HTTP client for device-intelligence-service API, Python
- **Location:** 
  - `services/ha-ai-agent-service/src/clients/device_intelligence_client.py` (new)
  - `services/ha-ai-agent-service/src/services/entity_inventory_service.py` (modify)
  - `services/ha-ai-agent-service/src/prompts/system_prompt.py` (modify)
- **Touch points:**
  - Entity Inventory Service: Use device mapping library for device type detection
  - System Prompt: Include device-specific guidelines from handlers

**Current Behavior:**
- Entity inventory has hardcoded device type detection (Hue Room, WLED segments)
- System prompt doesn't include device-specific guidelines
- Device type detection logic is duplicated and not extensible

**Target Behavior:**
- Entity inventory uses device mapping library for all device type detection
- Device relationships and enriched context from handlers included
- System prompt includes device-specific guidelines auto-generated from handlers
- Guidelines explain how to use device types (e.g., "Use Hue Room entities to control all lights in an area")

---

## Acceptance Criteria

1. ✅ Device Intelligence Service client created
2. ✅ Entity Inventory Service uses device mapping library
3. ✅ Device types identified using handlers (replaces hardcoded logic)
4. ✅ Device relationships included in context
5. ✅ Device-specific descriptions added (e.g., "Hue Room - controls all Office lights")
6. ✅ System prompt builder includes device-specific guidelines
7. ✅ Guidelines auto-generated from handler documentation
8. ✅ Unit tests for integration
9. ✅ Integration test: Context shows correct device types and relationships

---

## Integration Verification

- **IV1:** Existing entity inventory format maintained for non-special devices
- **IV2:** Device-specific context adds clarity without breaking existing logic
- **IV3:** System prompt includes device guidelines

---

## Technical Notes

- **Device Intelligence Service URL:** From settings (default: `http://device-intelligence-service:8028`)
- **API Endpoints:**
  - `POST /api/device-mappings/{device_id}/type`
  - `POST /api/device-mappings/{device_id}/relationships`
  - `POST /api/device-mappings/{device_id}/context`
- **System Prompt Section:** "## Device-Specific Guidelines"
- **Guidelines Source:** Handler `__doc__` strings and handler documentation

---

## Tasks

- [ ] **Task 1:** Create story file
- [ ] **Task 2:** Create Device Intelligence Service client
- [ ] **Task 3:** Integrate device mapping library into Entity Inventory Service
- [ ] **Task 4:** Replace hardcoded device type detection with handler calls
- [ ] **Task 5:** Add device relationships to entity context
- [ ] **Task 6:** Add device-specific descriptions to entity summaries
- [ ] **Task 7:** Update system prompt to include device-specific guidelines
- [ ] **Task 8:** Auto-generate guidelines from handler documentation
- [ ] **Task 9:** Write unit tests for integration
- [ ] **Task 10:** Write integration tests

---

## Dependencies

- Story AI24.1: Device Mapping Library Core Infrastructure ✅
- Story AI24.2: Hue Device Handler ✅
- Story AI24.3: Device Intelligence Service Integration ✅

---

## Testing Strategy

1. **Unit Tests:**
   - Test device intelligence client
   - Test entity inventory integration
   - Test system prompt generation

2. **Integration Tests:**
   - Test full flow: entity inventory → device mapping → context
   - Test system prompt includes device guidelines

---

## Notes

- Device mapping library is in a separate service, so we'll use HTTP calls
- Need to handle cases where device-intelligence-service is unavailable (graceful degradation)
- Cache device mapping results to avoid excessive API calls

