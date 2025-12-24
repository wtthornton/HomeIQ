# Story 33.4: Weather-HVAC Correlation

**Story ID:** 33.4  
**Epic:** 33 - Foundation External Data Generation  
**Status:** Ready for Review  
**Priority:** P0  
**Story Points:** 4  
**Estimated Effort:** 3-4 hours  
**Complexity:** Medium  
**Depends on:** Stories 33.1, 33.2, 33.3

---

## Story Description

Correlate weather data with HVAC device events, implementing temperature-driven HVAC patterns and window state correlation to create realistic device-weather relationships.

## User Story

**As a** training data engineer  
**I want** weather data correlated with HVAC and window device events  
**So that** synthetic training data reflects realistic relationships between weather and device behavior

## Acceptance Criteria

### AC1: Temperature-Driven HVAC Patterns
- [x] `correlate_with_hvac()` method implemented
- [x] AC turns on when temperature > threshold (e.g., 25°C)
- [x] Heat turns on when temperature < threshold (e.g., 18°C)
- [x] HVAC intensity correlates with temperature extremes
- [x] Correlation respects existing device events

### AC2: Window State Correlation
- [x] Window open/closed states correlate with weather
- [x] Windows open in nice weather (sunny, 18-25°C)
- [x] Windows closed in extreme weather (hot/cold, rainy)
- [x] Window events added or adjusted based on weather

### AC3: Integration with Event Generator
- [x] Weather correlation works with existing `SyntheticEventGenerator`
- [x] Can adjust existing events or add new events
- [x] Correlation is optional (can be disabled)
- [x] Performance impact minimal (<50ms overhead)

## Technical Requirements

### Correlation Logic
```python
def _correlate_with_hvac(
    self,
    weather_data: list[dict],
    device_events: list[dict],
    hvac_devices: list[dict]
) -> list[dict]:
    """
    Correlate weather with HVAC device events.
    
    Rules:
    - AC on when temp > 25°C
    - Heat on when temp < 18°C
    - Intensity based on temperature delta
    """
    for weather_point in weather_data:
        temp = weather_point['temperature']
        if temp > 25:
            # Add/modify AC event
            pass
        elif temp < 18:
            # Add/modify heat event
            pass
```

## Implementation Tasks

- [x] Implement HVAC correlation logic
- [x] Implement window state correlation
- [x] Integrate with event generator
- [x] Create unit tests
- [x] Performance testing

## Dependencies

- Stories 33.1, 33.2, 33.3
- `SyntheticEventGenerator` (existing)

## Definition of Done

- [x] HVAC correlation implemented
- [x] Window correlation implemented
- [x] Integration complete
- [x] All tests passing (49 tests total, 6 new correlation tests)
- [x] Performance target met

## Dev Agent Record

### Completion Notes
- ✅ Implemented `correlate_with_hvac()` method for temperature-driven HVAC patterns
- ✅ Implemented `correlate_with_windows()` method for window state correlation
- ✅ AC activates when temperature > 25°C (cooling mode)
- ✅ Heat activates when temperature < 18°C (heating mode)
- ✅ Windows open in nice weather (sunny, 18-25°C)
- ✅ Windows close in extreme weather (rainy, hot/cold)
- ✅ Correlation methods work with existing event generator
- ✅ Added comprehensive unit tests (6 new tests)
- ✅ All 49 tests passing with 98% code coverage

### File List
- `services/ai-automation-service/src/training/synthetic_weather_generator.py` (updated)
- `services/ai-automation-service/tests/training/test_synthetic_weather_generator.py` (updated)

### Change Log
- 2025-11-25: Story 33.4 completed - Weather-HVAC correlation implemented with 49 tests passing

---

**Created**: November 25, 2025  
**Depends on**: Stories 33.1, 33.2, 33.3

## QA Results

### Review Date: November 25, 2025

### Reviewed By: Quinn (Test Architect)

### Code Quality Assessment

Excellent correlation implementation. The HVAC correlation logic properly simulates AC activation (temp > 25°C) and heat activation (temp < 18°C) with intensity based on temperature extremes. Window correlation is realistic - windows open in nice weather (sunny, 18-25°C) and close in extreme conditions. The correlation respects existing device events, preventing data loss.

### Refactoring Performed

No refactoring required. Correlation logic is well-designed and maintainable.

### Compliance Check

- Coding Standards: ✓ Full compliance
- Project Structure: ✓ Files in correct locations
- Testing Strategy: ✓ 49 tests passing with 98% coverage (excellent)
- All ACs Met: ✓ All 3 acceptance criteria fully implemented

### Improvements Checklist

- [x] Code quality verified
- [x] Test coverage verified (98% - excellent)
- [x] HVAC correlation tested
- [x] Window correlation tested
- [x] Integration with event generator verified
- [ ] Consider making temperature thresholds configurable per device (future enhancement)

### Security Review

No security concerns.

### Performance Considerations

Correlation overhead is minimal and within performance targets. The implementation efficiently processes weather data and device events.

### Files Modified During Review

None - code quality is excellent.

### Gate Status

Gate: **PASS** → `docs/qa/gates/33.4-weather-hvac-correlation.yml`  
Quality Score: 95/100  
Risk Profile: Low risk - excellent test coverage, well-designed correlation logic

### Recommended Status

✓ **Ready for Done** - All acceptance criteria met, excellent test coverage, performance targets achieved.

