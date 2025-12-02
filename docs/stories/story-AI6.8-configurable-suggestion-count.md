# Story AI6.8: Configurable Suggestion Count (5-50)

**Story ID:** AI6.8  
**Epic:** AI-6 (Blueprint-Enhanced Suggestion Intelligence)  
**Status:** ✅ Ready for Review  
**Priority:** P1 (Phase 3 Feature)  
**Story Points:** 2  
**Complexity:** Low  
**Estimated Effort:** 4-6 hours

---

## Story Description

Enable users to configure maximum suggestion count (5-50, default: 10) in both 3 AM run and Ask AI. Apply preference to limit suggestion output.

## User Story

**As a** Home Assistant user,  
**I want** to control how many suggestions I receive,  
**So that** I see the right amount of automation opportunities without being overwhelmed.

---

## Acceptance Criteria

### AC1: Preference Configuration
- [x] Preference `max_suggestions` (5-50, default: 10) - Implemented in Story AI6.7
- [x] Validation prevents invalid ranges (<5 or >50) - Implemented in Story AI6.7
- [x] Default value applied when preference not set - Implemented in Story AI6.7

### AC2: Applied in Phase 5 Description Generation
- [x] max_suggestions limit applied in Phase 5
- [x] Top N suggestions selected based on preference
- [x] Limit applies to combined suggestions (patterns + features + synergies + blueprints)

### AC3: Applied in Ask AI Suggestion Generation
- [x] max_suggestions limit applied in Ask AI queries
- [x] Limit applies to all suggestion types
- [x] Consistent behavior with 3 AM run
- [x] Applied in clarify endpoint as well

### AC4: Integration Tests
- [x] Test count limits in Phase 5
- [x] Test count limits in Ask AI
- [x] Test validation prevents invalid ranges
- [x] Test graceful degradation on preference loading errors

---

## Tasks / Subtasks

### Task 1: Implement Preference Integration
- [x] Use PreferenceManager to get max_suggestions
- [x] Apply limit in Phase 5 description generation
- [x] Apply limit in Ask AI suggestion generation
- [x] Apply limit in clarify endpoint
- [x] Use default (10) when preference not set

### Task 2: Testing
- [x] Test preference application in Phase 5
- [x] Test preference application in Ask AI
- [x] Test validation and defaults
- [x] Test graceful degradation on errors
- [x] Test combined suggestions (patterns + features + synergies + blueprints)

---

## Technical Requirements

**Preference Usage:**
```python
# Get preference
max_count = await preference_manager.get_max_suggestions()  # Default: 10

# Apply limit
suggestions = sorted_suggestions[:max_count]
```

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
- PreferenceManager integrated into Phase 5: `services/ai-automation-service/src/scheduler/daily_analysis.py`
- PreferenceManager integrated into Ask AI: `services/ai-automation-service/src/api/ask_ai_router.py`
- Integration tests created: `services/ai-automation-service/tests/test_max_suggestions_integration.py`

### Completion Notes List
- ✅ Integrated PreferenceManager into Phase 5 description generation
  - Replaced hardcoded `[:10]` limit with preference-based limit
  - Applied after ranking and sorting all suggestions
  - Includes graceful degradation with default fallback (10)
- ✅ Integrated PreferenceManager into Ask AI suggestion generation
  - Applied limit after combining regular suggestions with blueprint suggestions
  - Sorts by confidence before limiting
  - Includes graceful degradation on preference loading errors
- ✅ Integrated PreferenceManager into clarify endpoint
  - Applies same limit logic as main Ask AI endpoint
  - Ensures consistent behavior across all suggestion generation paths
- ✅ Created comprehensive integration tests
  - Tests for Phase 5 limit application
  - Tests for Ask AI limit application
  - Tests for range validation (5-50)
  - Tests for default value usage
  - Tests for graceful degradation
  - Tests for combined suggestions (all types)
  - Tests for blueprint suggestions inclusion
- ✅ All acceptance criteria met
- ✅ Preference validation prevents invalid ranges (implemented in Story AI6.7)
- ✅ Default value (10) applied when preference not set (implemented in Story AI6.7)

### File List
- `services/ai-automation-service/src/scheduler/daily_analysis.py` (UPDATED - integrated PreferenceManager in Phase 5)
- `services/ai-automation-service/src/api/ask_ai_router.py` (UPDATED - integrated PreferenceManager in Ask AI and clarify endpoints)
- `services/ai-automation-service/tests/test_max_suggestions_integration.py` (NEW - comprehensive integration tests)

---

## QA Results
*QA Agent review pending*

