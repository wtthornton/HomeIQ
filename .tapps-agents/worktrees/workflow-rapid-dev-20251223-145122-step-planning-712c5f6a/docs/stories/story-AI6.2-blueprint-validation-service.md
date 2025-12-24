# Story AI6.2: Blueprint Validation Service for Patterns

**Story ID:** AI6.2  
**Epic:** AI-6 (Blueprint-Enhanced Suggestion Intelligence)  
**Status:** ✅ Ready for Review  
**Priority:** P0 (Foundation for Epic AI-6)  
**Story Points:** 2  
**Complexity:** Low-Medium  
**Estimated Effort:** 4-6 hours

---

## Story Description

Create service to validate detected patterns against blueprints and boost confidence scores for matches. This enables pattern suggestions to benefit from community validation.

## User Story

**As a** Home Assistant user,  
**I want** detected usage patterns to be validated against proven community automations,  
**So that** I have higher confidence in pattern-based suggestions backed by community validation.

---

## Acceptance Criteria

### AC1: Blueprint Validator Service Creation
- [x] Create `blueprint_discovery/blueprint_validator.py` service class
- [x] Service initialized with MinerIntegration instance
- [x] Service supports graceful degradation if automation-miner unavailable
- [x] Unit tests with >90% coverage

### AC2: Pattern-to-Blueprint Matching Logic
- [x] Match detected patterns to blueprints based on:
  - Device types involved
  - Use case alignment
  - Trigger/condition/action similarity
- [x] Calculate match score (0.0-1.0) for each pattern-blueprint pair
- [x] Return best matching blueprint for each pattern (match_score ≥ 0.7)

### AC3: Confidence Boost Calculation
- [x] Calculate confidence boost for validated patterns (0.1-0.3 increase)
- [x] Boost formula:
  - Base boost: 0.1 (pattern matched to blueprint)
  - Match score multiplier: (match_score - 0.7) * 0.5 (max 0.15 additional)
  - Blueprint quality multiplier: blueprint_quality * 0.05 (max 0.05 additional)
  - Total boost: min(0.3, base + match_multiplier + quality_multiplier)
- [x] Apply boost to pattern confidence scores

### AC4: Integration with Existing Pattern Detection
- [x] Service can validate time-of-day patterns
- [x] Service can validate co-occurrence patterns
- [x] Service can validate anomaly patterns
- [x] Returns validation results with boost values
- [x] Non-blocking: If validation fails, pattern confidence unchanged

### AC5: Unit Tests
- [x] Test pattern-to-blueprint matching logic
- [x] Test confidence boost calculation with various scenarios
- [x] Test integration with pattern types
- [x] Test graceful degradation
- [x] >90% code coverage

---

## Tasks / Subtasks

### Task 1: Create Blueprint Validator Service
- [x] Create `blueprint_discovery/blueprint_validator.py` file
- [x] Implement service class with MinerIntegration dependency
- [x] Add graceful degradation support

### Task 2: Implement Pattern-to-Blueprint Matching
- [x] Extract device types from pattern
- [x] Search blueprints matching pattern devices
- [x] Calculate match score based on:
  - Device type overlap
  - Use case alignment
  - Pattern similarity (trigger/condition/action)
- [x] Return best match (match_score ≥ 0.7)

### Task 3: Implement Confidence Boost Calculation
- [x] Implement boost calculation formula
- [x] Apply boost to pattern confidence scores
- [x] Ensure boost stays within 0.1-0.3 range
- [x] Return validation results with boost values

### Task 4: Integration with Pattern Detection
- [x] Add validation method for time-of-day patterns
- [x] Add validation method for co-occurrence patterns
- [x] Add validation method for anomaly patterns
- [x] Ensure non-blocking behavior (failures don't break pattern detection)

### Task 5: Unit Tests
- [x] Test pattern matching logic
- [x] Test confidence boost calculation
- [x] Test pattern type integration
- [x] Test graceful degradation
- [x] Achieve >90% coverage

---

## Technical Requirements

### File Structure

```
services/ai-automation-service/src/
├── blueprint_discovery/
│   ├── __init__.py
│   ├── opportunity_finder.py         # From Story AI6.1
│   └── blueprint_validator.py        # NEW (this story)
```

### Implementation Approach

**Service Class:**
```python
from typing import Any
from ...utils.miner_integration import MinerIntegration

class BlueprintValidator:
    """
    Validates detected patterns against blueprints.
    
    Calculates confidence boosts for validated patterns.
    """
    
    def __init__(self, miner: MinerIntegration):
        self.miner = miner
    
    async def validate_pattern(
        self,
        pattern: dict[str, Any],
        pattern_type: str  # 'time_of_day', 'co_occurrence', 'anomaly'
    ) -> dict[str, Any]:
        """
        Validate pattern against blueprints and return boost value.
        
        Returns:
            {
                'validated': bool,
                'match_score': float,
                'blueprint_match': dict | None,
                'confidence_boost': float  # 0.0-0.3
            }
        """
```

**Confidence Boost Formula:**
```python
def calculate_confidence_boost(
    self,
    match_score: float,
    blueprint_quality: float
) -> float:
    """
    Calculate confidence boost (0.1-0.3).
    
    Formula:
    - Base: 0.1
    - Match multiplier: (match_score - 0.7) * 0.5 (max 0.15)
    - Quality multiplier: blueprint_quality * 0.05 (max 0.05)
    - Total: min(0.3, 0.1 + match + quality)
    """
```

### Integration Points

- **Pattern Detection:** Patterns from `pattern_analyzer/` modules
- **MinerIntegration:** `services/ai-automation-service/src/utils/miner_integration.py`
- **Pattern Types:** time_of_day, co_occurrence, anomaly

---

## Dev Notes

### Pattern Structure

**Time-of-Day Pattern:**
```python
{
    'pattern_type': 'time_of_day',
    'device': 'light.office',
    'time_window': '07:00-07:30',
    'confidence': 0.75,
    'occurrences': 25
}
```

**Co-Occurrence Pattern:**
```python
{
    'pattern_type': 'co_occurrence',
    'devices': ['light.office', 'switch.desk_lamp'],
    'confidence': 0.68,
    'support': 15
}
```

**Anomaly Pattern:**
```python
{
    'pattern_type': 'anomaly',
    'device': 'light.bedroom',
    'expected_state': 'off',
    'actual_state': 'on',
    'confidence': 0.70
}
```

### Matching Logic

1. Extract device types from pattern
2. Search blueprints matching device types
3. Calculate match score:
   - Device overlap: 50% weight
   - Use case alignment: 30% weight
   - Pattern similarity: 20% weight
4. Return best match (score ≥ 0.7)

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
- Tests created in: `services/ai-automation-service/tests/test_blueprint_validator.py`

### Completion Notes List
- ✅ Created `BlueprintValidator` service class following 2025 best practices
- ✅ Added `BlueprintValidationConfig` class with extracted constants (2025 pattern)
- ✅ Pattern-to-blueprint matching with weighted scoring (50% device, 30% use case, 20% similarity)
- ✅ Confidence boost calculation with configurable formula (0.1-0.3 range)
- ✅ Support for all pattern types: time_of_day, co_occurrence, anomaly
- ✅ Graceful degradation when automation-miner unavailable (non-blocking)
- ✅ Structured logging with extra context fields (2025 best practice)
- ✅ Comprehensive unit tests (25+ test cases covering all scenarios)
- ✅ All acceptance criteria met

### File List
- `services/ai-automation-service/src/blueprint_discovery/blueprint_validator.py` (NEW - 512 lines)
- `services/ai-automation-service/src/blueprint_discovery/__init__.py` (UPDATED - exports BlueprintValidator)
- `services/ai-automation-service/tests/test_blueprint_validator.py` (NEW - 439 lines)

---

## QA Results
*QA Agent review pending*

