# Story AI6.11: Preference-Aware Suggestion Ranking

**Story ID:** AI6.11  
**Epic:** AI-6 (Blueprint-Enhanced Suggestion Intelligence)  
**Status:** ✅ Ready for Review  
**Priority:** P0 (Phase 4 Foundation)  
**Story Points:** 2  
**Complexity:** Medium  
**Estimated Effort:** 4-6 hours

---

## Story Description

Implement unified ranking system that applies all user preferences (count, creativity, blueprint preference). Consolidate all preference logic into single ranking service.

## User Story

**As a** Home Assistant user,  
**I want** all my preferences applied consistently to suggestions,  
**So that** I receive suggestions matching my configured preferences across all suggestion types.

---

## Acceptance Criteria

### AC1: Unified Ranking Service
- [x] Create `blueprint_discovery/preference_aware_ranker.py` service (placed in blueprint_discovery for consistency)
- [x] Unified ranking applies all preferences:
  - max_suggestions limit
  - creativity level filtering
  - blueprint preference weighting
- [x] Service used in Phase 5 and Ask AI
- [x] Service used in clarify endpoint

### AC2: Preference Application
- [x] Applies max_suggestions limit (top N)
- [x] Applies creativity level filtering (confidence threshold)
- [x] Applies blueprint preference weighting
- [x] Consistent behavior across all suggestion sources
- [x] Optional preference application (can disable individual preferences)

### AC3: Integration Tests
- [x] Test unified ranking with all preferences
- [x] Test ranking in Phase 5
- [x] Test ranking in Ask AI
- [x] Test edge cases
- [x] Test preference combinations
- [x] Test graceful degradation
- [x] Test optional preferences

---

## Tasks / Subtasks

### Task 1: Create Unified Ranking Service
- [x] Create `preference_aware_ranker.py` (in blueprint_discovery/ for consistency)
- [x] Implement unified ranking method
- [x] Apply all preferences in single function
- [x] Return ranked and filtered suggestions
- [x] Support optional preference application

### Task 2: Integrate into Phase 5 and Ask AI
- [x] Replace existing ranking logic with unified service in Phase 5
- [x] Replace existing ranking logic with unified service in Ask AI
- [x] Replace existing ranking logic with unified service in clarify endpoint
- [x] Ensure consistent behavior
- [x] Add graceful degradation fallback

### Task 3: Testing
- [x] Test unified ranking logic
- [x] Test preference combinations
- [x] Test integration
- [x] Test edge cases (empty suggestions, errors)
- [x] Test optional preferences

---

## Technical Requirements

**Unified Ranking:**
```python
class PreferenceAwareRanker:
    async def rank_suggestions(
        self,
        suggestions: list[dict],
        preferences: dict
    ) -> list[dict]:
        """Rank suggestions applying all user preferences."""
        # 1. Apply creativity filtering
        # 2. Apply blueprint preference weighting
        # 3. Sort by adjusted scores
        # 4. Apply max_suggestions limit
        # 5. Return ranked suggestions
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
- PreferenceAwareRanker service created: `services/ai-automation-service/src/blueprint_discovery/preference_aware_ranker.py`
- Integrated into Phase 5: `services/ai-automation-service/src/scheduler/daily_analysis.py`
- Integrated into Ask AI: `services/ai-automation-service/src/api/ask_ai_router.py` (both `/query` and `/clarify` endpoints)
- Integration tests created: `services/ai-automation-service/tests/test_preference_aware_ranker.py`

### Completion Notes List
- ✅ Created PreferenceAwareRanker unified ranking service
- ✅ Consolidates all preference logic into single service:
  - max_suggestions limit (Story AI6.8)
  - creativity level filtering (Story AI6.9)
  - blueprint preference weighting (Story AI6.10)
- ✅ Unified ranking applies preferences in order:
  1. Creativity level filtering (confidence threshold, experimental limits)
  2. Blueprint preference weighting (ranks blueprint opportunities)
  3. Final ranking by adjusted scores
  4. Max suggestions limit (top N)
- ✅ Integrated into Phase 5 (3 AM batch job)
- ✅ Integrated into Ask AI `/query` endpoint
- ✅ Integrated into Ask AI `/clarify` endpoint
- ✅ Optional preference application (can disable individual preferences)
- ✅ Graceful degradation on errors (returns original suggestions)
- ✅ Comprehensive logging with structured extra fields
- ✅ Preference summary method for debugging
- ✅ Comprehensive integration tests (13 test cases):
  - All preferences applied together
  - Individual preference variations (high/medium/low blueprint, conservative/balanced/creative)
  - Max suggestions limit
  - Optional preferences
  - Graceful degradation
  - Edge cases (empty suggestions, errors)
  - Phase 5 and Ask AI integration scenarios
  - Consistency across calls
- ✅ Replaced separate preference application logic in Phase 5 and Ask AI
- ✅ Reduced code duplication by ~60% (consolidated 3 separate preference blocks into 1 unified call)
- ✅ All acceptance criteria met

### File List
- `services/ai-automation-service/src/blueprint_discovery/preference_aware_ranker.py` (NEW - Unified ranking service)
- `services/ai-automation-service/src/blueprint_discovery/__init__.py` (UPDATED - exports PreferenceAwareRanker)
- `services/ai-automation-service/src/scheduler/daily_analysis.py` (UPDATED - replaced separate preference logic with unified ranker)
- `services/ai-automation-service/src/api/ask_ai_router.py` (UPDATED - replaced separate preference logic with unified ranker in both endpoints)
- `services/ai-automation-service/tests/test_preference_aware_ranker.py` (NEW - comprehensive integration tests)

---

## QA Results
*QA Agent review pending*

