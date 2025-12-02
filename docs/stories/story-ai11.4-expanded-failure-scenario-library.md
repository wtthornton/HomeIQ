# Story AI11.4: Expanded Failure Scenario Library

**Epic:** AI-11 - Realistic Training Data Enhancement  
**Story ID:** AI11.4  
**Type:** Enhancement  
**Points:** 3  
**Status:** ✅ **COMPLETE**  
**Estimated Effort:** 6-8 hours  
**Created:** December 2, 2025  
**Completed:** December 2, 2025

---

## Story Description

Add 5 new failure scenarios to `SyntheticDeviceGenerator` to expand training data coverage from 5 to 10+ failure scenarios, improving model training for failure detection and prediction.

**Current State:**
- 5 basic failure scenarios (progressive, sudden, intermittent, battery, network)
- Limited coverage of real-world failure patterns
- Missing integration-level failures

**Target:**
- 10+ failure scenarios total
- Integration failures (Zigbee/Z-Wave disconnections)
- Configuration errors (invalid YAML, missing entities)
- Automation loops (recursive triggering)
- Resource exhaustion (memory/CPU spikes)
- API rate limiting (external services)
- Realistic symptom patterns for each failure type

---

## Acceptance Criteria

- [x] Integration failures (Zigbee/Z-Wave disconnections) implemented
- [x] Configuration errors (invalid YAML, missing entities) implemented
- [x] Automation loops (recursive triggering) implemented
- [x] Resource exhaustion (memory/CPU spikes) implemented
- [x] API rate limiting (external services) implemented
- [x] Realistic symptom patterns for each failure type
- [x] Failure scenarios can be assigned to devices during generation
- [x] Failure scenarios stored in device metadata
- [x] Unit tests for all failure scenarios (15 tests, all passing)
- [x] Backward compatible with existing device generation

---

## Technical Approach

### Failure Scenario Structure

Each failure scenario will include:
- **Type**: Unique identifier (e.g., 'integration_failure')
- **Description**: Human-readable description
- **Symptoms**: Dictionary of symptoms that manifest in device behavior
- **Affected Metrics**: Which device attributes/states are affected
- **Probability**: Base probability of occurrence
- **Duration**: How long the failure persists

### Integration Points

- `SyntheticDeviceGenerator._create_device()` - Assign failure scenarios to devices
- `SyntheticEventGenerator.generate_events()` - Apply failure symptoms to events
- Device metadata includes `failure_scenario` field when applicable

---

## Tasks

### Task 1: Define Failure Scenario Data Structures
- [x] Create `FAILURE_SCENARIOS` dictionary with 5 new scenarios
- [x] Define symptom patterns for each scenario
- [x] Add configuration for failure probability and duration

### Task 2: Implement Failure Scenario Assignment
- [x] Add method to randomly assign failure scenarios to devices
- [x] Ensure realistic distribution (not all devices fail)
- [x] Store failure scenario in device metadata

### Task 3: Unit Tests
- [x] Test each failure scenario assignment
- [x] Test symptom structure and validation
- [x] Test integration with device generation
- [x] Test edge cases (no failures, device type filtering, etc.)
- [x] All 15 tests passing

---

## Files Modified

- `services/ai-automation-service/src/training/synthetic_device_generator.py`
- `services/ai-automation-service/tests/training/test_failure_scenarios.py` (new)

---

## Definition of Done

- [x] All 5 new failure scenarios implemented
- [x] Failure scenarios can be assigned to devices
- [x] Failure scenarios stored in device metadata with symptoms
- [x] Unit tests pass (15 tests, 100% pass rate)
- [x] Code follows 2025 patterns (Python 3.11+, type hints)
- [x] Documentation updated with failure scenario descriptions

## Implementation Summary

**Files Modified:**
- `services/ai-automation-service/src/training/synthetic_device_generator.py`
  - Added `FAILURE_SCENARIOS` dictionary with 5 new scenarios
  - Added `_assign_failure_scenarios()` method
  - Integrated failure assignment into `generate_devices()`

**Files Created:**
- `services/ai-automation-service/tests/training/test_failure_scenarios.py`
  - 15 comprehensive unit tests
  - All tests passing

**Failure Scenarios Implemented:**
1. **integration_failure**: Zigbee/Z-Wave disconnections (10% probability)
2. **config_error**: Configuration errors (8% probability)
3. **automation_loop**: Recursive triggering (5% probability)
4. **resource_exhaustion**: Memory/CPU spikes (6% probability)
5. **api_rate_limit**: API rate limiting (5% probability)

**Next Steps:**
- Story AI11.5 will integrate failure symptoms into event generation
- Story AI11.9 will validate end-to-end failure scenario integration

---

## Related Stories

- **Story AI11.5**: Event Type Diversification (uses failure scenarios in events)
- **Story AI11.9**: End-to-End Pipeline Integration (validates failure scenario integration)

---

## Notes

- Failure scenarios should be realistic and based on common Home Assistant issues
- Symptoms should be detectable by pattern detection algorithms
- Failure probability should be configurable (default: 10-15% of devices)
- Consider failure cascades (one failure causing another)

