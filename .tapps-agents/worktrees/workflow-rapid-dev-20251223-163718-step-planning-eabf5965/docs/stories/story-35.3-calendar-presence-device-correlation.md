# Story 35.3: Calendar-Presence-Device Correlation

**Story ID:** 35.3  
**Epic:** 35 - External Data Integration & Correlation  
**Status:** Draft  
**Priority:** P0  
**Story Points:** 4  
**Estimated Effort:** 3-4 hours  
**Depends on:** Story 35.2

---

## Story Description

Implement calendar → presence correlation, implement presence → device correlation, and add validation logic.

## Acceptance Criteria

- [x] Calendar → presence correlation implemented
- [x] Presence → device correlation implemented
- [x] Validation logic added
- [x] All correlations validated

## Implementation Tasks

- [x] Implement calendar-presence correlation
- [x] Implement presence-device correlation
- [x] Add validation logic
- [x] Create unit tests

## Definition of Done

- [x] Calendar-presence correlation implemented
- [x] Presence-device correlation implemented
- [x] Validation working
- [x] All tests passing

---

## Dev Agent Record

### Agent Model Used
Claude Sonnet 4.5 (via Cursor)

### Completion Notes
- ✅ Extended `SyntheticCorrelationEngine` with calendar-presence-device correlation
- ✅ Implemented calendar → presence correlation (away/home/work detection)
- ✅ Implemented presence → device correlation rules:
  - Away → Security on, lights off
  - Home → Comfort settings, lights on
  - Work → Reduced device activity
- ✅ Added comprehensive validation logic with correlation scores
- ✅ Created unit tests (5 new tests, 14 total tests, all passing)
- ✅ Integrated calendar-presence validation into `validate_all_correlations()`
- ✅ NUC-optimized: Lightweight rule-based validation

### File List
- `services/ai-automation-service/src/training/synthetic_correlation_engine.py` (modified)
- `services/ai-automation-service/tests/training/test_synthetic_correlation_engine.py` (modified)

### Change Log
- 2025-11-25: Added `validate_calendar_presence_correlation()` method
- 2025-11-25: Extended `validate_all_correlations()` to include calendar-presence validation
- 2025-11-25: Added 5 new unit tests for calendar-presence correlation

---

**Created**: November 25, 2025  
**Completed**: November 25, 2025

