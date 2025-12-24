# Epic AI-24: Device Mapping Library Architecture

**Status:** 📋 **PLANNED**  
**Type:** Brownfield Enhancement (Architecture)  
**Priority:** High  
**Effort:** 4 Stories (13 story points, ~20-25 hours estimated)  
**Created:** December 5, 2025  
**Last Updated:** December 5, 2025

---

## Epic Goal

Create an extensible device mapping library that enables rapid addition and updates of device-specific mappings (Hue Room groups, WLED segments, future device types) without modifying core code. This library will provide device intelligence to the AI agent, enabling accurate entity resolution and automation creation.

**Business Value:**
- **Rapid device support** - Add new device handlers in < 1 hour
- **Zero core code changes** - Configuration-driven approach
- **Consistent device intelligence** - Centralized device knowledge
- **Easy maintenance** - Isolated handlers, clear separation of concerns
- **Community extensibility** - Plugin architecture supports unlimited device types

---

## Existing System Context

### Current Functionality

**Current State:**
- Device-specific logic (Hue Room detection, WLED segment detection) is hardcoded in services
- Adding new device types requires code changes across multiple services
- Device intelligence is scattered across different services
- No centralized repository for device-specific knowledge

**Services Affected:**
- `services/ha-ai-agent-service/` - Entity inventory and context building
- `services/device-intelligence-service/` - Device capability discovery
- `services/ai-automation-service/` - Entity resolution and automation creation

### Technology Stack

- **Primary Service:** `services/device-intelligence-service/` (Port 8028)
- **Integration Service:** `services/ha-ai-agent-service/` (Port 8030)
- **Language:** Python 3.12+
- **Framework:** FastAPI 0.123.x (matches ha-ai-agent-service requirements)
- **Plugin System:** Python `importlib` (built-in, already used in codebase for test loading)
- **Configuration:** YAML files (simple, readable, no extra dependencies)
- **No External Dependencies:** Use built-in `importlib` instead of `pluggy` (simpler, no new dependencies)

### Integration Points

- Device Intelligence Service (core library location)
- HA AI Agent Service (entity inventory integration)
- System Prompt Builder (device-specific guidelines)
- Entity Inventory Service (device type detection)

---

## Enhancement Details

### What's Being Added/Changed

1. **Device Mapping Library Core** (NEW)
   - Plugin registry for dynamic handler loading
   - Base device handler interface (ABC)
   - Configuration loader with hot-reload support
   - Handler lifecycle management

2. **Hue Device Handler** (NEW - Proof of Concept)
   - Hue Room/Zone group detection
   - Individual light identification
   - Relationship mapping (lights to room groups)
   - Context enrichment for Hue devices

3. **WLED Device Handler** (NEW)
   - Master entity detection
   - Segment entity detection
   - Relationship mapping (segments to master)
   - Context enrichment for WLED devices

4. **Device Intelligence Service Integration** (NEW)
   - API endpoints for device mappings
   - Caching strategy (5-minute TTL)
   - Configuration reload endpoint
   - Device type/relationship queries

5. **Entity Inventory Service Integration** (ENHANCEMENT)
   - Use device mapping library for device type detection
   - Include device relationships in context
   - Add device-specific descriptions

6. **System Prompt Integration** (ENHANCEMENT)
   - Auto-generate device-specific guidelines from handlers
   - Include handler documentation in system prompt
   - Dynamic prompt updates based on active mappings

### How It Integrates

- **Non-Breaking Changes:** All enhancements are additive, existing functionality unchanged
- **Incremental Integration:** Each story builds on previous work
- **Plugin Architecture:** Handlers loaded dynamically, no core code changes for new devices
- **Configuration-Driven:** Device mappings defined in YAML/JSON files
- **Hot-Reloadable:** Configuration updates without service restart

---

## Success Criteria

1. **Functional:**
   - ✅ Can add new device handler without modifying core code
   - ✅ Device mappings hot-reloadable via configuration updates
   - ✅ Entity inventory service uses device mappings
   - ✅ System prompt includes device-specific guidelines
   - ✅ Hue Room groups and WLED segments detected correctly
   - ✅ Device relationships included in context

2. **Technical:**
   - ✅ Plugin registry working correctly
   - ✅ Configuration loader with hot-reload
   - ✅ API endpoints functional
   - ✅ Caching strategy implemented
   - ✅ Performance requirements met (<10ms lookup time)
   - ✅ Unit tests >90% coverage
   - ✅ Integration tests cover all paths

3. **Quality:**
   - ✅ All handlers documented
   - ✅ Configuration validation prevents errors
   - ✅ Monitoring and metrics in place
   - ✅ No regression in existing functionality

---

## Stories

### Phase 1: Core Library (Week 1-2)

#### Story AI24.1: Device Mapping Library Core Infrastructure
**Type:** Architecture  
**Points:** 5  
**Effort:** 8-10 hours  
**Priority:** High

**User Story:**
As a developer,
I want a plugin-based device mapping library,
so that I can add new device handlers without modifying core code.

**Acceptance Criteria:**
1. Base `DeviceHandler` abstract class defined with required methods:
   - `can_handle(device: dict) -> bool`
   - `identify_type(device: dict, entity: dict) -> DeviceType`
   - `get_relationships(device: dict, entities: list) -> dict`
   - `enrich_context(device: dict, entity: dict) -> dict`
2. Simple dictionary-based registry: `registry = {"hue": HueHandler(), "wled": WLEDHandler()}`
3. Configuration loader with YAML support (PyYAML already in requirements)
4. Handler registration via `__init__.py` imports (simple, no complex discovery)
5. Reload endpoint: `POST /api/device-mappings/reload` (no file watching complexity)
6. Unit tests for core library (>90% coverage)
7. Documentation: Handler development guide

**Integration Verification:**
- IV1: Existing device intelligence service continues to work
- IV2: Plugin registry can discover and load handlers
- IV3: Reload endpoint works correctly (restart acceptable for config changes)

**Technical Notes:**
- Use Python built-in `importlib` (no external dependencies, already used in codebase)
- Simple dictionary-based registry: `registry = {"hue": HueHandler(), "wled": WLEDHandler()}`
- Configuration files in `device_mappings/{device_type}/config.yaml`
- Registry auto-discovers handlers via `__init__.py` imports
- No hot-reload needed initially (simple restart is acceptable for this use case)

---

#### Story AI24.2: Hue Device Handler (Proof of Concept)
**Type:** Feature  
**Points:** 3  
**Effort:** 4-6 hours  
**Priority:** High

**User Story:**
As an AI agent,
I want Hue Room/Zone groups to be automatically detected,
so that automation creation can correctly use Room entities vs individual lights.

**Acceptance Criteria:**
1. Hue handler module created (`device_mappings/hue/handler.py`)
2. Hue Room/Zone group detection implemented (Model: "Room" or "Zone")
3. Individual light identification implemented
4. Relationship mapping (lights to room groups) implemented
5. Context enrichment for Hue devices
6. Configuration file (`device_mappings/hue/config.yaml`)
7. Handler registered in plugin registry
8. Unit tests for Hue handler
9. Integration test: Hue Room groups detected correctly

**Integration Verification:**
- IV1: Existing entity inventory continues to work for non-Hue devices
- IV2: Hue devices show correct device types in context
- IV3: Hue Room groups linked to individual lights correctly

**Technical Notes:**
- Detection: `device.manufacturer.lower() in ["signify", "philips"]` AND `device.model.lower() in ["room", "zone"]`
- Context format: "Office (Hue Room - controls all Office lights)"

---

### Phase 2: Integration (Week 3)

#### Story AI24.3: Device Intelligence Service Integration
**Type:** Integration  
**Points:** 3  
**Effort:** 4-6 hours  
**Priority:** High

**User Story:**
As a service,
I want device mapping API endpoints,
so that other services can query device types and relationships.

**Acceptance Criteria:**
1. Device mapping library integrated into Device Intelligence Service
2. API endpoints implemented:
   - `GET /api/device-mappings/{device_id}/type`
   - `GET /api/device-mappings/{device_id}/relationships`
   - `GET /api/device-mappings/{device_id}/context`
   - `POST /api/device-mappings/reload`
3. Caching strategy implemented (5-minute TTL)
4. Cache invalidation on configuration reload
5. Unit tests for API endpoints
6. Integration tests for full flow
7. API documentation (OpenAPI/Swagger)

**Integration Verification:**
- IV1: Existing Device Intelligence Service endpoints continue to work
- IV2: Device mapping endpoints return correct data
- IV3: Configuration reload updates cache correctly

**Technical Notes:**
- Location: `services/device-intelligence-service/src/device_mappings/`
- Cache key: `device_mapping_{device_id}`
- Cache TTL: 300 seconds (5 minutes)

---

#### Story AI24.4: Entity Inventory & System Prompt Integration
**Type:** Integration  
**Points:** 2  
**Effort:** 4-6 hours  
**Priority:** Medium

**User Story:**
As an AI agent,
I want device mappings integrated into entity inventory and system prompt,
so that I receive accurate device intelligence in context.

**Acceptance Criteria:**
1. Entity Inventory Service uses device mapping library
2. Device types identified using handlers
3. Device relationships included in context
4. Device-specific descriptions added (e.g., "Hue Room - controls all Office lights")
5. System prompt builder includes device-specific guidelines
6. Guidelines auto-generated from handler documentation
7. Unit tests for integration
8. Integration test: Context shows correct device types and relationships

**Integration Verification:**
- IV1: Existing entity inventory format maintained for non-special devices
- IV2: Device-specific context adds clarity without breaking existing logic
- IV3: System prompt includes device guidelines

**Technical Notes:**
- Entity Inventory Service calls device mapping library
- System prompt includes section: "## Device-Specific Guidelines"
- Guidelines generated from handler `__doc__` strings

---

### Phase 3: Additional Handlers (Week 4)

#### Story AI24.5: WLED Device Handler
**Type:** Feature  
**Points:** 2  
**Effort:** 3-4 hours  
**Priority:** Medium

**User Story:**
As an AI agent,
I want WLED master and segment entities to be automatically detected,
so that automation creation can correctly use master entities vs segment entities.

**Acceptance Criteria:**
1. WLED handler module created (`device_mappings/wled/handler.py`)
2. WLED master entity detection implemented
3. WLED segment entity detection implemented (`_segment_` in entity_id)
4. Relationship mapping (segments to master) implemented
5. Context enrichment for WLED devices
6. Configuration file (`device_mappings/wled/config.yaml`)
7. Handler registered in plugin registry
8. Unit tests for WLED handler
9. Integration test: WLED master/segments detected correctly

**Integration Verification:**
- IV1: Existing entity inventory continues to work for non-WLED devices
- IV2: WLED devices show correct device types in context
- IV3: WLED segments linked to master correctly

**Technical Notes:**
- Detection: `entity.manufacturer.lower() in ["wled", "foss"]` AND `"_segment_" in entity.entity_id`
- Context format: "Office (WLED master - controls entire strip)" + segments

---

## Compatibility Requirements

- **CR1:** Existing device intelligence service API remains unchanged
- **CR2:** Entity inventory service backward compatible
- **CR3:** System prompt enhancements are additive (no breaking changes)
- **CR4:** Plugin architecture doesn't affect existing functionality

---

## Risk Assessment

**Primary Risk:** Plugin architecture complexity could introduce bugs

**Mitigation:**
- Comprehensive unit and integration tests
- Configuration validation framework
- Handler isolation (one handler failure doesn't break others)
- Feature flag to disable device mappings if needed

**Rollback Plan:**
- Feature flag to disable device mapping library
- Fallback to existing hardcoded logic
- No database changes required (easy rollback)

**Technical Risks:**
- **Low Risk:** Simple dictionary-based registry (no complex plugin system)
- **Low Complexity:** Built-in `importlib` already used in codebase (test loading)
- **High Value:** Enables rapid device support without core changes

---

## Implementation Plan

### Phase 1: Core Library (Week 1-2)
1. Create base device handler interface
2. Implement plugin registry
3. Create configuration loader
4. Implement Hue Room handler (proof of concept)
5. Unit tests for core library

### Phase 2: Integration (Week 3)
1. Integrate with device-intelligence-service
2. Add API endpoints
3. Integrate with entity inventory service
4. Update system prompt generation
5. Integration tests

### Phase 3: Additional Handlers (Week 4)
1. Implement WLED segment handler
2. Add more device types (LIFX, TP-Link, etc.) - optional
3. Documentation
4. Performance optimization

### Phase 4: Production Readiness (Week 5)
1. Monitoring and metrics
2. Error handling improvements
3. Documentation completion
4. Production deployment

---

## Performance Requirements

- **Device mapping lookup:** < 10ms (p95)
- **Configuration reload:** < 1 second
- **No performance degradation** with 100+ device types
- **Scalability:** Support 1000+ device types

---

## Definition of Done

- [ ] All stories completed with acceptance criteria met
- [ ] Device mapping library core implemented
- [ ] Hue and WLED handlers implemented
- [ ] Device Intelligence Service integration complete
- [ ] Entity Inventory Service integration complete
- [ ] System prompt includes device-specific guidelines
- [ ] Unit tests >90% coverage
- [ ] Integration tests cover all paths
- [ ] Performance requirements met
- [ ] Documentation complete (handler development guide, API docs)
- [ ] Monitoring and metrics in place
- [ ] No regression in existing functionality
- [ ] Code reviewed and approved

---

## Future Enhancements

**Phase 2 Features:**
- AI-assisted device handler generation (LLM generates handler from device documentation)
- Community-contributed device handlers (plugin marketplace)
- Device capability inference from mappings
- Automated testing of device handlers against real devices

**Phase 3 Features:**
- Device handler versioning and A/B testing
- Machine learning for device type detection
- Device relationship graph visualization
- Device handler performance analytics

---

## References

- **Research Document:** `implementation/analysis/home-assistant-2025-api-research.md`
- **Device Intelligence Service:** `services/device-intelligence-service/`
- **HA AI Agent Service:** `services/ha-ai-agent-service/`
- **Entity Inventory Service:** `services/ha-ai-agent-service/src/services/entity_inventory_service.py`
- **System Prompt:** `services/ha-ai-agent-service/src/prompts/system_prompt.py`

---

## Change Log

| Change | Date | Version | Description | Author |
|--------|------|---------|-------------|--------|
| Initial Epic Creation | 2025-12-05 | 1.0 | Created epic from research document | BMAD Master |

