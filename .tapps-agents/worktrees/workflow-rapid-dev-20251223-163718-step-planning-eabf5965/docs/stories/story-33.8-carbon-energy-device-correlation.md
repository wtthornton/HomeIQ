# Story 33.8: Carbon-Energy Device Correlation

**Story ID:** 33.8  
**Epic:** 33 - Foundation External Data Generation  
**Status:** Ready for Review  
**Priority:** P0  
**Story Points:** 4  
**Estimated Effort:** 3-4 hours  
**Depends on:** Stories 33.5, 33.6, 33.7

---

## Story Description

Correlate carbon intensity with high-energy devices, implement EV charging patterns, and add HVAC carbon correlation.

## Acceptance Criteria

- [x] High-energy device correlation implemented
- [x] EV charging patterns prefer low-carbon periods
- [x] HVAC carbon correlation added
- [x] Correlation respects existing device events

## Implementation Tasks

- [x] Implement `_correlate_with_energy_devices()` method
- [x] Add EV charging optimization patterns
- [x] Add HVAC carbon correlation
- [x] Create unit tests

## Definition of Done

- [x] Energy device correlation implemented
- [x] EV charging patterns working
- [x] HVAC correlation added
- [x] All tests passing (38 tests, 99% coverage)

## Dev Agent Record

### Completion Notes
- ✅ Implemented `correlate_with_energy_devices()` main correlation method
- ✅ Implemented `_correlate_ev_charging()` - EV charging prefers low-carbon periods (solar peak, night)
- ✅ Implemented `_correlate_hvac_carbon()` - HVAC usage correlates with carbon intensity
- ✅ Implemented `_correlate_high_energy_devices()` - Water heater, pool pump, etc. correlation
- ✅ Correlation respects existing device events (preserves non-correlated events)
- ✅ Added comprehensive unit tests (5 new tests)
- ✅ All 38 tests passing with 99% code coverage

### File List
- `services/ai-automation-service/src/training/synthetic_carbon_intensity_generator.py` (updated)
- `services/ai-automation-service/tests/training/test_synthetic_carbon_intensity_generator.py` (updated)

### Change Log
- 2025-11-25: Story 33.8 completed - Carbon-energy device correlation implemented with 99% test coverage

---

**Created**: November 25, 2025

## QA Results

### Review Date: November 25, 2025

### Reviewed By: Quinn (Test Architect)

### Code Quality Assessment

Excellent correlation implementation with realistic low-carbon preferences. EV charging optimization properly identifies low-carbon periods and schedules charging accordingly. High-energy device correlation (water heater, pool pump) prefers low-carbon periods. HVAC carbon correlation adjusts usage based on carbon intensity. The correlation respects existing device events, preventing data loss.

### Refactoring Performed

No refactoring required. Correlation logic is well-designed.

### Compliance Check

- Coding Standards: ✓ Full compliance
- Project Structure: ✓ Files in correct locations
- Testing Strategy: ✓ 38 tests passing with 99% coverage (excellent)
- All ACs Met: ✓ All 4 acceptance criteria fully implemented

### Improvements Checklist

- [x] Code quality verified
- [x] Test coverage verified (99% - excellent)
- [x] Energy device correlation tested
- [x] EV charging patterns tested
- [x] HVAC carbon correlation tested
- [ ] Consider making carbon thresholds configurable per device type (future enhancement)

### Security Review

No security concerns.

### Performance Considerations

Correlation overhead is acceptable and within performance targets. The implementation efficiently processes carbon data and device events.

### Files Modified During Review

None - code quality is excellent.

### Gate Status

Gate: **PASS** → `docs/qa/gates/33.8-carbon-energy-device-correlation.yml`  
Quality Score: 98/100  
Risk Profile: Low risk - excellent test coverage, well-designed correlation logic

### Recommended Status

✓ **Ready for Done** - All acceptance criteria met, excellent test coverage, performance targets achieved.

