# Story AI6.1: Blueprint Opportunity Discovery Service Foundation

**Story ID:** AI6.1  
**Epic:** AI-6 (Blueprint-Enhanced Suggestion Intelligence)  
**Status:** ✅ Ready for Review  
**Priority:** P0 (Foundation for Epic AI-6)  
**Story Points:** 2  
**Complexity:** Low-Medium  
**Estimated Effort:** 4-6 hours

---

## Story Description

Create foundation service for discovering blueprint opportunities from user device inventory. Scan devices, search blueprints, calculate fit scores. This is the foundation service that enables proactive blueprint discovery before patterns are detected.

## User Story

**As a** Home Assistant user,  
**I want** the system to discover proven automation opportunities based on my device inventory,  
**So that** I receive suggestions for proven automations even without usage patterns yet.

---

## Acceptance Criteria

### AC1: Blueprint Opportunity Finder Service Creation
- [x] Create `services/ai-automation-service/src/blueprint_discovery/` directory structure
- [x] Create `opportunity_finder.py` service class
- [x] Service initialized with MinerIntegration instance
- [x] Service supports graceful degradation if automation-miner unavailable
- [x] Unit tests with >90% coverage

### AC2: Device Scanning from Home Assistant
- [x] Scan user device inventory from Home Assistant integration (via DataAPIClient)
- [x] Extract device types (light, switch, sensor, etc.) and integrations (hue, zwave, etc.)
- [x] Support batch device scanning (all devices at once)
- [x] Cache device inventory for 5 minutes (reduce HA API calls)
- [x] Handle errors gracefully (device fetch failures)

### AC3: Blueprint Search Integration
- [x] Use MinerIntegration to search blueprints by device type
- [x] Search blueprints by integration type
- [x] Filter by min_quality score (default: 0.7)
- [x] Support batch blueprint searches (multiple device types)
- [x] Handle automation-miner service unavailability gracefully

### AC4: Fit Score Calculation
- [x] Calculate fit score (0.0-1.0) for each blueprint opportunity
- [x] Fit score formula:
  - Device type compatibility: 60% weight
  - Integration compatibility: 20% weight
  - Use case relevance: 10% weight
  - Blueprint quality score: 10% weight
- [x] Filter opportunities with fit_score ≥ 0.6
- [x] Return top opportunities sorted by fit score

### AC5: Unit Tests
- [x] Test device scanning with mock DataAPIClient
- [x] Test blueprint search with mock MinerIntegration
- [x] Test fit score calculation with various device/blueprint combinations
- [x] Test graceful degradation when automation-miner unavailable
- [x] Test caching behavior
- [x] >90% code coverage

---

## Tasks / Subtasks

### Task 1: Create Blueprint Discovery Directory Structure
- [x] Create `services/ai-automation-service/src/blueprint_discovery/` directory
- [x] Create `__init__.py` file
- [x] Create `opportunity_finder.py` file

### Task 2: Implement Device Scanning
- [x] Create method to fetch devices from Home Assistant (via DataAPIClient)
- [x] Extract device types and integrations (from entities for accuracy)
- [x] Implement device inventory caching (5 min TTL)
- [x] Add error handling for HA API failures

### Task 3: Implement Blueprint Search
- [x] Integrate MinerIntegration for blueprint searches
- [x] Implement batch blueprint search (multiple device types)
- [x] Add min_quality filtering (default: 0.7)
- [x] Handle automation-miner unavailability gracefully

### Task 4: Implement Fit Score Calculation
- [x] Create fit score calculation method
- [x] Implement device type compatibility scoring (60% weight)
- [x] Implement integration compatibility scoring (20% weight)
- [x] Implement use case relevance scoring (10% weight)
- [x] Implement blueprint quality score weighting (10% weight)
- [x] Filter opportunities (fit_score ≥ 0.6)
- [x] Sort by fit score descending

### Task 5: Unit Tests
- [x] Test device scanning with mocked DataAPIClient
- [x] Test blueprint search with mocked MinerIntegration
- [x] Test fit score calculation logic
- [x] Test graceful degradation scenarios
- [x] Test caching behavior
- [x] Achieve >90% coverage

---

## Technical Requirements

### New File Structure

```
services/ai-automation-service/src/
├── blueprint_discovery/              # NEW (Epic AI-6)
│   ├── __init__.py
│   └── opportunity_finder.py         # Blueprint opportunity discovery
```

### Implementation Approach

**Service Class:**
```python
from typing import Any
from ...clients.home_assistant_client import HomeAssistantClient
from ...utils.miner_integration import MinerIntegration

class BlueprintOpportunityFinder:
    """
    Discovers blueprint opportunities from user device inventory.
    
    Scans devices, searches blueprints, calculates fit scores.
    """
    
    def __init__(
        self,
        ha_client: HomeAssistantClient,
        miner: MinerIntegration
    ):
        self.ha_client = ha_client
        self.miner = miner
        self._device_cache: dict[str, Any] = {}
        self._cache_ttl = 300  # 5 minutes
    
    async def find_opportunities(
        self,
        min_fit_score: float = 0.6,
        min_blueprint_quality: float = 0.7,
        limit: int = 50
    ) -> list[dict[str, Any]]:
        """Discover blueprint opportunities from device inventory."""
        # 1. Scan devices
        # 2. Search blueprints
        # 3. Calculate fit scores
        # 4. Filter and sort
        # 5. Return top opportunities
```

**Fit Score Calculation:**
```python
def calculate_fit_score(
    self,
    blueprint: dict[str, Any],
    device_types: list[str],
    integrations: list[str]
) -> float:
    """
    Calculate fit score (0.0-1.0) for blueprint opportunity.
    
    Formula:
    - Device type compatibility: 60%
    - Integration compatibility: 20%
    - Use case relevance: 10%
    - Blueprint quality: 10%
    """
```

### Integration Points

- **Home Assistant Client:** `services/ai-automation-service/src/clients/home_assistant_client.py`
- **MinerIntegration:** `services/ai-automation-service/src/utils/miner_integration.py`
- **Existing Blueprint Matching:** `services/ai-automation-service/src/services/blueprints/matcher.py` (reference for scoring logic)

### Error Handling

- **Automation-miner unavailable:** Return empty list, log warning
- **Home Assistant API failure:** Return empty list, log error
- **Invalid device data:** Skip invalid devices, continue processing

---

## Dev Notes

### Context from Architecture Docs

**Tech Stack** (from `docs/architecture/tech-stack.md`):
- Python 3.12+
- FastAPI 0.115.x
- SQLAlchemy 2.0+ (async ORM)
- httpx for async HTTP

**Coding Standards** (from `docs/architecture/coding-standards.md`):
- Async/await: All I/O operations must be async
- Type hints: Required for all function signatures
- Error handling: Use `try/except` with specific exceptions, log errors
- Logging: Structured logging with correlation IDs

### Existing Infrastructure

**Home Assistant Client:**
- Already exists in `services/ai-automation-service/src/clients/home_assistant_client.py`
- Provides device/entity fetching capabilities
- Supports async operations

**MinerIntegration:**
- Already exists in `services/ai-automation-service/src/utils/miner_integration.py`
- Provides `search_blueprints()` method
- Handles service availability checking

**Blueprint Matcher:**
- Reference `services/ai-automation-service/src/services/blueprints/matcher.py` for scoring logic patterns
- Similar fit score calculation concepts can be reused

### Performance Considerations

- **Caching:** Device inventory cached for 5 minutes to reduce HA API calls
- **Batch Operations:** Search multiple device types in single batch
- **Async Operations:** All I/O operations async (HA API, blueprint search)
- **Graceful Degradation:** Service continues working if automation-miner unavailable

---

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-11-26 | 1.0 | Story created for Epic AI-6 | Dev Agent |

---

## Dev Agent Record

### Agent Model Used
claude-sonnet-4.5

### Debug Log References
- Implementation completed: 2025-12-01
- Service created in: `services/ai-automation-service/src/blueprint_discovery/`
- Tests created in: `services/ai-automation-service/tests/test_blueprint_opportunity_finder.py`

### Completion Notes List
- ✅ Created `blueprint_discovery` directory structure with `__init__.py` and `opportunity_finder.py`
- ✅ Implemented `BlueprintOpportunityFinder` service class with all required functionality
- ✅ Device scanning uses `DataAPIClient` (via `fetch_devices()` and `fetch_entities()`) as used throughout codebase
- ✅ Device type and integration extraction from entities (more accurate than device names)
- ✅ 5-minute caching implemented for device/entity inventory
- ✅ Blueprint search integrated with `MinerIntegration.search_blueprints()`
- ✅ Batch blueprint search with deduplication by blueprint ID
- ✅ Graceful degradation when automation-miner unavailable (returns empty list, logs warning)
- ✅ Fit score calculation with weighted formula (60% device, 20% integration, 10% use case, 10% quality)
- ✅ Comprehensive unit tests with >90% coverage (18 test cases covering all scenarios)
- ✅ All acceptance criteria met

### File List
- `services/ai-automation-service/src/blueprint_discovery/__init__.py` (NEW)
- `services/ai-automation-service/src/blueprint_discovery/opportunity_finder.py` (NEW - 434 lines)
- `services/ai-automation-service/tests/test_blueprint_opportunity_finder.py` (NEW - 441 lines)

---

## QA Results
*QA Agent review pending*

