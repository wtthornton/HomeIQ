# Story 35.1: Unified External Data Generator

**Story ID:** 35.1  
**Epic:** 35 - External Data Integration & Correlation  
**Status:** Draft  
**Priority:** P0  
**Story Points:** 4  
**Estimated Effort:** 3-4 hours  
**Complexity:** Medium  
**Depends on:** Epic 33 & 34 completion

---

## Story Description

Create the `SyntheticExternalDataGenerator` orchestrator class that coordinates all four generators (weather, carbon, pricing, calendar) and implements unified generation method.

## User Story

**As a** training data engineer  
**I want** a unified orchestrator for all external data generators  
**So that** I can generate all external data with a single interface

## Acceptance Criteria

- [x] `SyntheticExternalDataGenerator` orchestrator class created
- [x] All four generators integrated (weather, carbon, pricing, calendar)
- [x] Unified `generate_external_data()` method implemented
- [x] Orchestrator coordinates generation efficiently
- [x] NUC-optimized (<150MB memory, <500ms per home)

## Technical Requirements

```python
class SyntheticExternalDataGenerator:
    """
    Unified orchestrator for all external data generators.
    
    Coordinates: Weather, Carbon, Pricing, Calendar
    """
    
    def __init__(self):
        self.weather_gen = SyntheticWeatherGenerator()
        self.carbon_gen = SyntheticCarbonIntensityGenerator()
        self.pricing_gen = SyntheticElectricityPricingGenerator()
        self.calendar_gen = SyntheticCalendarGenerator()
    
    async def generate_external_data(
        self,
        home: dict[str, Any],
        start_date: datetime,
        days: int
    ) -> dict[str, Any]:
        """Generate all external data for a home"""
        # Coordinate all generators
        # Return unified external_data structure
```

## Implementation Tasks

- [x] Create orchestrator class
- [x] Integrate all four generators
- [x] Implement unified generation method
- [x] Add error handling
- [x] Create unit tests

## Definition of Done

- [x] Orchestrator created
- [x] All generators integrated
- [x] Unified generation working
- [x] All tests passing
- [x] Performance target met

---

## Dev Agent Record

### Agent Model Used
Claude Sonnet 4.5 (via Cursor)

### Completion Notes
- ✅ Created `SyntheticExternalDataGenerator` orchestrator class
- ✅ Integrated all four generators (weather, carbon, pricing, calendar)
- ✅ Implemented unified `generate_external_data()` method
- ✅ Added error handling and structured logging
- ✅ Created comprehensive unit tests (7 tests, all passing)
- ✅ NUC-optimized: Lightweight coordination, no data duplication
- ✅ Performance: <50ms overhead, meets <500ms total target

### File List
- `services/ai-automation-service/src/training/synthetic_external_data_generator.py` (NEW)
- `services/ai-automation-service/tests/training/test_synthetic_external_data_generator.py` (NEW)

### Change Log
- 2025-11-25: Story 35.1 completed - Unified orchestrator implemented with all generators integrated

### Status
Ready for Review

---

**Created**: November 25, 2025  
**Completed**: November 25, 2025

