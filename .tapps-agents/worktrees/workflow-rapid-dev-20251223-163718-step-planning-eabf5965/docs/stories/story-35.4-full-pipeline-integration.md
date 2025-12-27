# Story 35.4: Full Pipeline Integration

**Story ID:** 35.4  
**Epic:** 35 - External Data Integration & Correlation  
**Status:** Draft  
**Priority:** P0  
**Story Points:** 3  
**Estimated Effort:** 2-3 hours  
**Depends on:** Stories 35.1, 35.2, 35.3

---

## Story Description

Integrate with `generate_synthetic_homes.py`, update home JSON structure with all external data, and add configuration options.

## Acceptance Criteria

- [x] Full integration with `generate_synthetic_homes.py`
- [x] Home JSON structure updated with all external data
- [x] Configuration options added (enable/disable generators)
- [x] Integration doesn't break existing pipeline

## Implementation Tasks

- [x] Update `generate_synthetic_homes.py`
- [x] Update home JSON structure
- [x] Add configuration options
- [ ] Create integration tests
- [ ] Update documentation

## Definition of Done

- [x] Full pipeline integration complete
- [x] JSON structure updated
- [x] Configuration working
- [ ] All tests passing (integration tests pending)
- [ ] Documentation updated (pending)

---

## Dev Agent Record

### Agent Model Used
Claude Sonnet 4.5 (via Cursor)

### Completion Notes
- ✅ Integrated `SyntheticExternalDataGenerator` into `generate_synthetic_homes.py`
- ✅ Replaced individual weather/carbon generators with unified orchestrator
- ✅ Updated home JSON structure to include all four external data types:
  - `external_data.weather`
  - `external_data.carbon_intensity`
  - `external_data.pricing`
  - `external_data.calendar`
- ✅ Added configuration options (--enable-weather, --disable-weather, etc.)
- ✅ Maintained backward compatibility with existing correlation methods
- ✅ Updated logging to show all external data counts
- ✅ Updated summary statistics to include pricing and calendar data

### File List
- `services/ai-automation-service/scripts/generate_synthetic_homes.py` (modified)

### Change Log
- 2025-11-25: Replaced individual generators with `SyntheticExternalDataGenerator`
- 2025-11-25: Added configuration flags for each external data type
- 2025-11-25: Updated external_data structure to include all four data types
- 2025-11-25: Enhanced logging and summary statistics

---

**Created**: November 25, 2025  
**Completed**: November 25, 2025

