# Story 35.2: Correlation Engine Foundation

**Story ID:** 35.2  
**Epic:** 35 - External Data Integration & Correlation  
**Status:** Draft  
**Priority:** P0  
**Story Points:** 4  
**Estimated Effort:** 3-4 hours  
**Depends on:** Story 35.1, Epic 33 & 34

---

## Story Description

Create correlation engine class, implement weather → HVAC correlation rules, and implement carbon/pricing → energy device correlation rules.

## Acceptance Criteria

- [x] `SyntheticCorrelationEngine` class created
- [x] Weather → HVAC correlation rules implemented
- [x] Carbon/Pricing → Energy device correlation rules implemented
- [x] Rule-based validation (lightweight, no ML)
- [x] NUC-optimized (<100ms per home)

## Technical Requirements

```python
class SyntheticCorrelationEngine:
    """
    Rule-based correlation engine (lightweight, NUC-optimized).
    
    Validates relationships between external data and device events.
    """
    
    def validate_weather_hvac_correlation(
        self,
        weather_data: list[dict],
        hvac_events: list[dict]
    ) -> bool:
        """Validate weather-HVAC correlations"""
        # Rule-based validation
        pass
    
    def validate_energy_correlation(
        self,
        carbon_data: list[dict],
        pricing_data: list[dict],
        energy_events: list[dict]
    ) -> bool:
        """Validate carbon/pricing-energy device correlations"""
        # Rule-based validation
        pass
```

## Implementation Tasks

- [x] Create correlation engine class
- [x] Implement weather-HVAC rules
- [x] Implement energy device rules
- [x] Add validation logic
- [x] Create unit tests

## Definition of Done

- [x] Correlation engine created
- [x] Weather-HVAC rules implemented
- [x] Energy device rules implemented
- [x] All tests passing

---

## Dev Agent Record

### Agent Model Used
Claude Sonnet 4.5 (via Cursor)

### Completion Notes
- ✅ Created `SyntheticCorrelationEngine` class with rule-based validation
- ✅ Implemented weather → HVAC correlation rules (high temp → AC, low temp → heat)
- ✅ Implemented carbon/pricing → energy device correlation rules (low carbon → EV, high price → delay devices, solar peak → renewable)
- ✅ Added comprehensive validation logic with correlation scores
- ✅ Created unit tests (9 tests, all passing)
- ✅ NUC-optimized: Rule-based validation, <100ms per home
- ✅ Fixed rule ordering to prioritize solar peak (most specific rule first)

### File List
- `services/ai-automation-service/src/training/synthetic_correlation_engine.py` (NEW)
- `services/ai-automation-service/tests/training/test_synthetic_correlation_engine.py` (NEW)

### Change Log
- 2025-11-25: Story 35.2 completed - Correlation engine implemented with all validation rules

### Status
Ready for Review

---

**Created**: November 25, 2025  
**Completed**: November 25, 2025

