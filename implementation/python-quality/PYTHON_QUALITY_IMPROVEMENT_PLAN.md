# Python Code Quality Improvement Plan

**Date:** December 3, 2025  
**Status:** In Progress  
**Target:** Document 13 C-rated functions, refactor 2 E-rated functions

---

## Current Status

### C-Rated Functions (11 remaining to document)
- ✅ `_check_time_constraints` (safety_validator.py) - C (13) - DOCUMENTED
- ✅ `_check_bulk_device_off` (safety_validator.py) - C (12) - DOCUMENTED
- ⏳ `_check_climate_extremes` (safety_validator.py) - C (11) - PENDING
- ⏳ `_check_security_disable` (safety_validator.py) - C (11) - PENDING
- ⏳ `extract_entities_from_query` (ask_ai_router.py) - C (17) - PENDING
- ⏳ `generate_suggestions_from_query` (ask_ai_router.py) - C (16) - PENDING
- ⏳ `deploy_suggestion` (deployment_router.py) - C (15) - PENDING
- ⏳ `_run_analysis_pipeline` (analysis_router.py) - C (14) - PENDING
- ⏳ `detect_patterns` (co_occurrence.py) - C (14) - PENDING
- ⏳ `detect_patterns` (time_of_day.py) - C (14) - PENDING
- ⏳ `_generate_use_cases` (conversational_router.py) - C (12) - PENDING
- ⏳ `refine_description` (conversational_router.py) - C (11) - PENDING
- ⏳ `test_suggestion_from_query` (ask_ai_router.py) - C (11) - PENDING

### E-Rated Functions (2 to refactor)
- 🔴 `_build_device_context` (suggestion_router.py) - E (37) - NEEDS REFACTORING
- 🔴 `run_daily_analysis` (daily_analysis.py) - E (40) - NEEDS REFACTORING

---

## E-Rated Function Refactoring Plans

### 1. `_build_device_context` (suggestion_router.py) - E (37)

**Current Issues:**
- ~170 lines with high cyclomatic complexity
- Duplicate logic for device1/device2 processing
- Nested conditionals (device ID vs entity ID detection)
- Multiple try/except blocks with similar error handling
- Complex branching for different pattern types

**Refactoring Strategy:**
1. Extract helper function: `_get_device_metadata_by_id(device_id)` - handles device ID vs entity ID logic
2. Extract helper function: `_build_single_device_context(device_id)` - processes single device
3. Extract helper function: `_build_co_occurrence_context(device1, device2)` - processes co-occurrence pattern
4. Simplify main function to route by pattern_type and delegate to helpers

**Expected Result:**
- Main function: ~30 lines (complexity < 10)
- Helper functions: ~40-50 lines each (complexity < 15)
- Total complexity reduction: 37 → ~15 (main) + ~12 (helpers) = 27 (distributed)

**Priority:** HIGH (core suggestion generation)

---

### 2. `run_daily_analysis` (daily_analysis.py) - E (40)

**Current Issues:**
- ~500+ lines handling entire daily analysis pipeline
- Multiple phases (6 phases) in single function
- Complex error handling and logging
- Multiple external service calls
- State management mixed with business logic

**Refactoring Strategy:**
1. Extract phase methods:
   - `_phase_1_device_capability_update()`
   - `_phase_2_fetch_events()`
   - `_phase_3_pattern_detection()`
   - `_phase_4_feature_analysis()`
   - `_phase_5_suggestion_generation()`
   - `_phase_6_publish_results()`
2. Extract helper: `_initialize_clients()` - setup data clients
3. Extract helper: `_get_home_type()` - home type detection
4. Main function becomes orchestrator calling phases sequentially

**Expected Result:**
- Main function: ~50 lines (complexity < 10)
- Phase functions: ~50-100 lines each (complexity < 15)
- Total complexity reduction: 40 → ~10 (main) + ~12-15 per phase = distributed

**Priority:** HIGH (daily automation pipeline)

---

## C-Rated Function Documentation Plan

### Documentation Template
Each function will receive:
- Comprehensive docstring with purpose and rationale
- Algorithm/process explanation
- Parameter documentation with types
- Return value documentation
- Examples (good vs bad patterns where applicable)
- Complexity note and refactoring suggestions

### Priority Order
1. Safety validator functions (critical safety rules)
2. Core router functions (ask_ai_router, deployment_router)
3. Pattern detection functions (co_occurrence, time_of_day)
4. Analysis and conversational functions

---

## Implementation Steps

### Phase 1: Document High-Priority C-Rated Functions (2-3 functions)
1. `_check_climate_extremes` - Safety critical
2. `_check_security_disable` - Safety critical
3. `extract_entities_from_query` - Core functionality

### Phase 2: Refactor E-Rated Functions (2 functions)
1. Refactor `_build_device_context` first (smaller scope)
2. Refactor `run_daily_analysis` second (larger scope)

### Phase 3: Document Remaining C-Rated Functions (8 functions)
- Complete documentation for all remaining C-rated functions

---

## Success Metrics

- ✅ All 13 C-rated functions documented
- ✅ Both E-rated functions refactored (complexity < 20)
- ✅ No functional changes (all tests pass)
- ✅ Improved code maintainability
- ✅ Reduced cognitive load for developers

---

## Timeline

- **Phase 1:** 2-3 hours (document 2-3 C-rated functions)
- **Phase 2:** 4-6 hours (refactor 2 E-rated functions)
- **Phase 3:** 3-4 hours (document remaining C-rated functions)
- **Total:** ~10-13 hours

---

## Notes

- All refactoring must maintain backward compatibility
- All changes must pass existing tests
- Documentation should follow existing patterns from completed functions
- Refactoring should be incremental (one function at a time)

