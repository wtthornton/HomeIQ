# Story AI23.1: Device Registry API Integration

**Epic:** Epic AI-23 - Device Registry & Entity Registry Integration  
**Status:** Ready for Review  
**Created:** 2025-12-05  
**Story Points:** 5  
**Priority:** ⚠️ **CRITICAL** - Fixes Area Filtering

---

## Story

**As a** system administrator,  
**I want** the HA AI Agent Service to use Device Registry API,  
**so that** entities can be correctly assigned to areas even when they inherit `area_id` from their device.

---

## Story Context

**Existing System Integration:**

- **Integrates with:** HA AI Agent Service (Port 8030, FastAPI 0.123.x, Python 3.12+)
- **Technology:** WebSocket API (2025 best practice), `websockets` library >=12.0,<13.0
- **Follows pattern:** Same WebSocket pattern as `_get_area_registry_websocket()` in HA Client
- **Touch points:**
  - `services/ha-ai-agent-service/src/clients/ha_client.py` - Add Device Registry methods
  - `services/ha-ai-agent-service/src/services/entity_inventory_service.py` - Use Device Registry for area resolution
  - `services/ha-ai-agent-service/src/services/context_builder.py` - Context enrichment

**Current Behavior:**
- Entity inventory only checks `entity.get("area_id")` directly
- Entities that inherit `area_id` from device are marked as "unassigned"
- Only 2 of 7 Office lights found (29% accuracy)

**New Behavior:**
- Device Registry fetched via WebSocket API
- `device_id → area_id` mapping created
- When `entity.area_id` is null, use `device.area_id` from mapping
- All 7 Office lights found (100% accuracy)
- Device metadata (manufacturer, model) included in entity context

---

## Acceptance Criteria

**Functional Requirements:**

1. Device Registry WebSocket method implemented in HA Client (`_get_device_registry_websocket()`) (AC#1)
2. `get_device_registry()` method with WebSocket/REST fallback (same pattern as Area Registry) (AC#2)
3. Device Registry fetched and cached in Entity Inventory Service (AC#3)
4. `device_id → area_id` mapping created (AC#4)
5. **CRITICAL:** When `entity.area_id` is null, use `device.area_id` from mapping (AC#5)
6. Device metadata (manufacturer, model) included in entity context (AC#6)
7. Unit tests for WebSocket and REST methods (AC#7)
8. Integration test: Office area filtering finds all 7 lights (AC#8)

**Integration Verification:**

- IV1: Existing entity resolution continues to work for entities with direct `area_id`
- IV2: Area filtering now finds entities that inherit `area_id` from device
- IV3: Token count remains within budget (55-58% usage)

**Technical Notes:**

- Use same WebSocket pattern as `_get_area_registry_websocket()` (2025 best practice)
- Use `websockets` library (already in requirements, not aiohttp WebSocket)
- Follow exact pattern: `websockets.connect()` → auth → send command → parse result
- Cache device registry with 5-minute TTL (same as entity inventory)
- Log device area resolution for debugging

---

## Tasks / Subtasks

- [x] **Task 1: Add Device Registry WebSocket method to HA Client** (AC: 1, 2)
  - [x] Implement `_get_device_registry_websocket()` method
  - [x] Use WebSocket command: `{"type": "config/device_registry/list"}`
  - [x] Follow same pattern as `_get_area_registry_websocket()`
  - [x] Handle authentication and error cases

- [x] **Task 2: Add Device Registry REST fallback** (AC: 2)
  - [x] Implement REST API fallback method
  - [x] Use `/api/config/device_registry/list` endpoint
  - [x] Create `get_device_registry()` method with WebSocket/REST fallback
  - [x] Add retry logic with tenacity

- [x] **Task 3: Integrate Device Registry in Entity Inventory Service** (AC: 3, 4, 5)
  - [x] Fetch Device Registry in `get_summary()` method
  - [x] Create `device_id → area_id` mapping
  - [x] Create `device_id → device_data` mapping for metadata
  - [x] **CRITICAL:** Update area resolution logic: `entity.area_id or device_area_map.get(entity.device_id)`
  - [x] Cache Device Registry with 5-minute TTL

- [x] **Task 4: Add device metadata to entity context** (AC: 6)
  - [x] Include manufacturer/model in entity examples
  - [x] Update entity summary format to show device metadata
  - [x] Add device metadata to domain samples

- [x] **Task 5: Write unit tests** (AC: 7)
  - [x] Test `_get_device_registry_websocket()` method
  - [x] Test `get_device_registry()` with WebSocket success
  - [x] Test `get_device_registry()` with REST fallback
  - [x] Test error handling

- [x] **Task 6: Write integration test** (AC: 8)
  - [x] Test Office area filtering finds all 7 lights
  - [x] Verify device area resolution works correctly
  - [x] Verify existing entities with direct area_id still work

- [ ] **Task 7: Update documentation** (AC: 3)
  - [ ] Document Device Registry integration
  - [ ] Update API documentation
  - [ ] Add examples of device area resolution

---

## Dev Notes

### Project Context

This story fixes a critical bug where entities inheriting `area_id` from devices are not found during area filtering. The fix requires integrating Home Assistant 2025 Device Registry API.

### Key Implementation Details

1. **WebSocket Pattern:** Use exact same pattern as Area Registry (already implemented)
2. **Area Resolution:** When `entity.area_id` is null, look up `device.area_id` from mapping
3. **Caching:** Device Registry cached with 5-minute TTL (same as entity inventory)
4. **Backward Compatibility:** Existing entities with direct `area_id` continue to work

### Files to Modify

- `services/ha-ai-agent-service/src/clients/ha_client.py` - Add Device Registry methods
- `services/ha-ai-agent-service/src/services/entity_inventory_service.py` - Use Device Registry for area resolution
- `services/ha-ai-agent-service/tests/test_ha_client.py` - Add Device Registry tests
- `services/ha-ai-agent-service/tests/test_entity_inventory_service.py` - Add integration tests

### Testing Strategy

1. Unit tests for WebSocket and REST methods
2. Integration test: Verify Office area filtering finds all 7 lights
3. Regression test: Verify existing entities with direct area_id still work

---

## Dev Agent Record

### Agent Model Used
Claude Sonnet 4.5

### Debug Log References
- None yet

### Completion Notes
- None yet

### File List
- `services/ha-ai-agent-service/src/clients/ha_client.py` - Added Device Registry WebSocket and REST methods
- `services/ha-ai-agent-service/src/services/entity_inventory_service.py` - Integrated Device Registry for area resolution
- `services/ha-ai-agent-service/tests/test_ha_client.py` - Added Device Registry tests
- `services/ha-ai-agent-service/tests/test_entity_inventory_service.py` - Added area resolution tests

### Change Log
- 2025-12-05: Story created
- 2025-12-05: Implemented Device Registry API integration
  - Added `_get_device_registry_websocket()` and `get_device_registry()` methods to HA Client
  - Integrated Device Registry in Entity Inventory Service for area resolution
  - Added device metadata (manufacturer, model) to entity context
  - Added comprehensive unit and integration tests

