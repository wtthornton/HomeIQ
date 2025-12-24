# Story AI24.1: Device Mapping Library Core Infrastructure

**Epic:** Epic AI-24 - Device Mapping Library Architecture  
**Status:** Ready for Review  
**Created:** 2025-01-XX  
**Story Points:** 5  
**Priority:** High

---

## Story

**As a** developer,  
**I want** a plugin-based device mapping library,  
**so that** I can add new device handlers without modifying core code.

---

## Story Context

**Existing System Integration:**

- **Integrates with:** Device Intelligence Service (Port 8028, FastAPI 0.123.x, Python 3.12+)
- **Technology:** Python `importlib` (built-in), YAML configuration files
- **Location:** `services/device-intelligence-service/src/device_mappings/`
- **Touch points:**
  - New directory: `src/device_mappings/` - Core library
  - `src/main.py` - Register device mapping router
  - `src/api/device_mappings.py` - API endpoints (Story AI24.3)

**Current Behavior:**
- Device-specific logic (Hue Room detection, WLED segment detection) is hardcoded in services
- Adding new device types requires code changes across multiple services
- No centralized repository for device-specific knowledge

**New Behavior:**
- Plugin-based architecture with base handler interface
- Configuration-driven device mappings (YAML files)
- Simple dictionary-based registry
- Handler registration via `__init__.py` imports
- Reload endpoint for configuration updates

---

## Acceptance Criteria

**Functional Requirements:**

1. Base `DeviceHandler` abstract class defined with required methods (AC#1)
2. Simple dictionary-based registry: `registry = {"hue": HueHandler(), "wled": WLEDHandler()}` (AC#2)
3. Configuration loader with YAML support (PyYAML) (AC#3)
4. Handler registration via `__init__.py` imports (simple, no complex discovery) (AC#4)
5. Reload endpoint: `POST /api/device-mappings/reload` (no file watching complexity) (AC#5)
6. Unit tests for core library (>90% coverage) (AC#6)
7. Documentation: Handler development guide (AC#7)

**Technical Requirements:**

- Use Python built-in `importlib` (no external dependencies)
- Simple dictionary-based registry
- Configuration files in `device_mappings/{device_type}/config.yaml`
- Registry auto-discovers handlers via `__init__.py` imports
- No hot-reload needed initially (simple restart is acceptable)

**Integration Verification:**

- IV1: Existing device intelligence service continues to work
- IV2: Plugin registry can discover and load handlers
- IV3: Reload endpoint works correctly (restart acceptable for config changes)

---

## Tasks

- [x] **Task 1:** Create base `DeviceHandler` abstract class with required methods
- [x] **Task 2:** Create simple dictionary-based registry (`DeviceMappingRegistry`)
- [x] **Task 3:** Create configuration loader with YAML support
- [x] **Task 4:** Create handler registration system via `__init__.py` imports
- [x] **Task 5:** Create reload endpoint (`POST /api/device-mappings/reload`)
- [x] **Task 6:** Add PyYAML to requirements.txt
- [x] **Task 7:** Write unit tests for core library (>90% coverage)
- [x] **Task 8:** Create handler development guide documentation

---

## Implementation Notes

**File Structure:**
```
src/device_mappings/
├── __init__.py              # Registry initialization
├── base.py                  # Base DeviceHandler abstract class
├── registry.py              # DeviceMappingRegistry class
├── config_loader.py         # YAML configuration loader
└── README.md                # Handler development guide
```

**Base Handler Interface:**
```python
class DeviceHandler(ABC):
    @abstractmethod
    def can_handle(self, device: dict) -> bool:
        """Check if this handler can process the device"""
    
    @abstractmethod
    def identify_type(self, device: dict, entity: dict) -> DeviceType:
        """Identify device type (master, segment, group, individual)"""
    
    @abstractmethod
    def get_relationships(self, device: dict, entities: list) -> dict:
        """Get relationships (e.g., segments to master, lights to room)"""
    
    @abstractmethod
    def enrich_context(self, device: dict, entity: dict) -> dict:
        """Add device-specific context for AI agent"""
```

**Registry Pattern:**
```python
registry = DeviceMappingRegistry()
registry.register("hue", HueHandler())
registry.register("wled", WLEDHandler())
```

---

## Testing

**Unit Tests:**
- Test base handler interface
- Test registry registration and lookup
- Test configuration loader
- Test handler discovery
- Test reload endpoint

**Integration Tests:**
- Test registry with multiple handlers
- Test configuration loading from YAML files
- Test handler selection logic

---

## Definition of Done

- [ ] Base `DeviceHandler` abstract class implemented
- [ ] Simple dictionary-based registry implemented
- [ ] Configuration loader with YAML support implemented
- [ ] Handler registration via `__init__.py` imports working
- [ ] Reload endpoint implemented
- [ ] PyYAML added to requirements.txt
- [ ] Unit tests >90% coverage
- [ ] Handler development guide created
- [ ] All acceptance criteria met
- [ ] Code reviewed and approved

