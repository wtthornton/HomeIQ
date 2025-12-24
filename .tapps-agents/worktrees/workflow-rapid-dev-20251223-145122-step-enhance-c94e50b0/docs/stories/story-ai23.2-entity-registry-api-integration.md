# Story AI23.2: Entity Registry API Integration

**Epic:** Epic AI-23 - Device Registry & Entity Registry Integration  
**Status:** Ready for Review  
**Created:** 2025-12-05  
**Story Points:** 3  
**Priority:** High

---

## Story

**As an** AI agent,  
**I want** entity aliases and metadata from Entity Registry API,  
**so that** entity resolution can match entities using multiple names and better context.

---

## Story Context

**Existing System Integration:**

- **Integrates with:** HA AI Agent Service (Port 8030, FastAPI 0.123.x, Python 3.12+)
- **Technology:** WebSocket API (2025 best practice), `websockets` library >=12.0,<13.0
- **Follows pattern:** Same WebSocket pattern as Device Registry and Area Registry
- **Touch points:**
  - `services/ha-ai-agent-service/src/clients/ha_client.py` - Add Entity Registry methods
  - `services/ha-ai-agent-service/src/services/entity_inventory_service.py` - Use Entity Registry for aliases
  - `services/ha-ai-agent-service/src/services/context_builder.py` - Context enrichment

**Current Behavior:**
- Entity resolution uses only entity_id and friendly_name
- No support for entity aliases (multiple names per entity)
- No entity categories or status information

**New Behavior:**
- Entity Registry fetched via WebSocket API
- Entity aliases included in entity context
- Entity categories and status included in context
- Aliases used in entity resolution logic
- Improved entity matching accuracy (85% → 95-98%)

---

## Acceptance Criteria

**Functional Requirements:**

1. Entity Registry WebSocket method implemented in HA Client (`_get_entity_registry_websocket()`) (AC#1)
2. `get_entity_registry()` method with WebSocket/REST fallback (AC#2)
3. Entity Registry fetched and cached in Entity Inventory Service (AC#3)
4. Entity aliases included in entity context (AC#4)
5. Entity categories and status included in context (AC#5)
6. Aliases used in entity resolution logic (AC#6)
7. Unit tests for WebSocket and REST methods (AC#7)
8. Integration test: Entity matching uses aliases correctly (AC#8)

**Integration Verification:**

- IV1: Existing entity resolution continues to work without aliases
- IV2: Entity resolution accuracy improved with aliases
- IV3: Token count remains within budget (58-65% usage)

**Technical Notes:**

- Use same WebSocket pattern as `_get_device_registry_websocket()` (2025 best practice)
- Use `websockets` library (already in requirements, not aiohttp WebSocket)
- Follow exact pattern: `websockets.connect()` → auth → send command → parse result
- Cache entity registry with 5-minute TTL
- Include aliases in entity examples in context

---

## Tasks / Subtasks

- [x] **Task 1: Add Entity Registry WebSocket method to HA Client** (AC: 1, 2)
  - [x] Implement `_get_entity_registry_websocket()` method
  - [x] Use WebSocket command: `{"type": "config/entity_registry/list"}`
  - [x] Follow same pattern as Device Registry
  - [x] Handle authentication and error cases

- [x] **Task 2: Add Entity Registry REST fallback** (AC: 2)
  - [x] Implement REST API fallback method
  - [x] Use `/api/config/entity_registry/list` endpoint
  - [x] Create `get_entity_registry()` method with WebSocket/REST fallback
  - [x] Add retry logic with tenacity

- [x] **Task 3: Integrate Entity Registry in Entity Inventory Service** (AC: 3, 4, 5)
  - [x] Fetch Entity Registry in `get_summary()` method
  - [x] Create `entity_id → entity_registry_data` mapping
  - [x] Include aliases in entity examples
  - [x] Include categories and status in context
  - [x] Cache Entity Registry with 5-minute TTL

- [x] **Task 4: Use aliases in entity resolution** (AC: 6)
  - [x] Update entity examples to show aliases
  - [x] Document alias usage in system prompt (if needed)
  - [x] Verify aliases improve matching accuracy

- [x] **Task 5: Write unit tests** (AC: 7)
  - [x] Test `_get_entity_registry_websocket()` method
  - [x] Test `get_entity_registry()` with WebSocket success
  - [x] Test `get_entity_registry()` with REST fallback
  - [x] Test error handling

- [x] **Task 6: Write integration test** (AC: 8)
  - [x] Test entity matching uses aliases correctly
  - [x] Verify aliases appear in entity context
  - [x] Verify existing entity resolution still works

---

## Dev Notes

### Project Context

This story adds Entity Registry API integration to improve entity resolution accuracy by supporting entity aliases and metadata.

### Key Implementation Details

1. **WebSocket Pattern:** Use exact same pattern as Device Registry (already implemented)
2. **Aliases:** Include entity aliases in entity examples for better matching
3. **Caching:** Entity Registry cached with 5-minute TTL (same as entity inventory)
4. **Backward Compatibility:** Existing entity resolution continues to work

### Files to Modify

- `services/ha-ai-agent-service/src/clients/ha_client.py` - Add Entity Registry methods
- `services/ha-ai-agent-service/src/services/entity_inventory_service.py` - Use Entity Registry for aliases
- `services/ha-ai-agent-service/tests/test_ha_client.py` - Add Entity Registry tests
- `services/ha-ai-agent-service/tests/test_entity_inventory_service.py` - Add alias tests

### Testing Strategy

1. Unit tests for WebSocket and REST methods
2. Integration test: Verify aliases appear in entity context
3. Regression test: Verify existing entity resolution still works

---

## Dev Agent Record

### Agent Model Used
Claude Sonnet 4.5

### Debug Log References
- None yet

### Completion Notes
- None yet

### File List
- `services/ha-ai-agent-service/src/clients/ha_client.py` - Added Entity Registry WebSocket and REST methods
- `services/ha-ai-agent-service/src/services/entity_inventory_service.py` - Integrated Entity Registry for aliases and metadata
- `services/ha-ai-agent-service/tests/test_ha_client.py` - Added Entity Registry tests
- `services/ha-ai-agent-service/tests/test_entity_inventory_service.py` - Added alias integration tests

### Change Log
- 2025-12-05: Story created
- 2025-12-05: Implemented Entity Registry API integration
  - Added `_get_entity_registry_websocket()` and `get_entity_registry()` methods to HA Client
  - Integrated Entity Registry in Entity Inventory Service for aliases and metadata
  - Added entity aliases and categories to entity context
  - Added comprehensive unit and integration tests

