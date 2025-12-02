# Story AI6.10: Blueprint Preference Configuration

**Story ID:** AI6.10  
**Epic:** AI-6 (Blueprint-Enhanced Suggestion Intelligence)  
**Status:** ✅ Ready for Review  
**Priority:** P1 (Phase 3 Feature)  
**Story Points:** 2  
**Complexity:** Low  
**Estimated Effort:** 4-6 hours

---

## Story Description

Enable users to configure blueprint preference (low/medium/high) affecting blueprint opportunity ranking. Higher preference ranks blueprint opportunities higher.

## User Story

**As a** Home Assistant user,  
**I want** to control how much I prioritize blueprint-based suggestions,  
**So that** blueprint opportunities are ranked according to my preferences.

---

## Acceptance Criteria

### AC1: Blueprint Preference Configuration
- [x] Preference `blueprint_preference` (low/medium/high, default: medium) - Implemented in Story AI6.7
- [x] Validation prevents invalid values - Implemented in Story AI6.7
- [x] Default value applied when preference not set - Implemented in Story AI6.7

### AC2: Ranking Impact
- [x] High preference: blueprint opportunities ranked higher (weight: 1.5x)
- [x] Medium preference: blueprint opportunities normal ranking (weight: 1.0x)
- [x] Low preference: blueprint opportunities ranked lower (weight: 0.5x)

### AC3: Applied in Ranking
- [x] Blueprint preference weighting applied in Phase 5 ranking
- [x] Blueprint preference weighting applied in Ask AI ranking
- [x] Blueprint preference weighting applied in clarify endpoint
- [x] Other suggestions unaffected by preference

### AC4: Integration Tests
- [x] Test ranking with high preference
- [x] Test ranking with medium preference
- [x] Test ranking with low preference
- [x] Test validation
- [x] Test blueprint opportunity detection
- [x] Test graceful degradation on errors

---

## Tasks / Subtasks

### Task 1: Implement Preference Weighting
- [x] Get blueprint_preference from PreferenceManager
- [x] Calculate weight multiplier (0.5x, 1.0x, 1.5x)
- [x] Apply weight to blueprint opportunity scores
- [x] Apply in ranking logic (Phase 5 and Ask AI)

### Task 2: Testing
- [x] Test weighting with each preference level
- [x] Test ranking impact
- [x] Test validation
- [x] Test blueprint opportunity detection
- [x] Test non-blueprint suggestions unaffected
- [x] Test graceful degradation

---

## Technical Requirements

**Preference Weighting:**
```python
blueprint_weight_multiplier = {
    "low": 0.5,
    "medium": 1.0,
    "high": 1.5
}

# Apply to blueprint opportunity scores
adjusted_score = blueprint_score * multiplier
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
- BlueprintRanker service created: `services/ai-automation-service/src/blueprint_discovery/blueprint_ranker.py`
- Integrated into Phase 5: `services/ai-automation-service/src/scheduler/daily_analysis.py`
- Integrated into Ask AI: `services/ai-automation-service/src/api/ask_ai_router.py`
- Integration tests created: `services/ai-automation-service/tests/test_blueprint_preference_ranking.py`

### Completion Notes List
- ✅ Created BlueprintRanker service class with weighting logic
- ✅ Implemented blueprint preference weight multipliers:
  - High preference: 1.5x multiplier (ranks blueprints higher)
  - Medium preference: 1.0x multiplier (normal ranking)
  - Low preference: 0.5x multiplier (ranks blueprints lower)
- ✅ Blueprint opportunity detection:
  - Detects `type: 'blueprint_opportunity'`
  - Detects `source` containing 'blueprint' or 'Epic-AI-6'
  - Detects `blueprint_validated: True`
  - Detects presence of `blueprint_id`
- ✅ Applied weighting to blueprint opportunity confidence/ranking scores
- ✅ Integrated into Phase 5 ranking (after creativity filtering, before max_suggestions limit)
- ✅ Integrated into Ask AI ranking (after creativity filtering, before max_suggestions limit)
- ✅ Integrated into clarify endpoint
- ✅ Non-blueprint suggestions unaffected by preference
- ✅ Re-ranking uses blueprint-weighted scores
- ✅ Option to preserve order or re-rank after weighting
- ✅ Graceful degradation on errors (returns original suggestions)
- ✅ Comprehensive integration tests (13 test cases covering all scenarios)
- ✅ All acceptance criteria met

### File List
- `services/ai-automation-service/src/blueprint_discovery/blueprint_ranker.py` (NEW - BlueprintRanker service)
- `services/ai-automation-service/src/blueprint_discovery/__init__.py` (UPDATED - exports BlueprintRanker)
- `services/ai-automation-service/src/scheduler/daily_analysis.py` (UPDATED - integrated blueprint preference weighting in Phase 5)
- `services/ai-automation-service/src/api/ask_ai_router.py` (UPDATED - integrated blueprint preference weighting in Ask AI and clarify)
- `services/ai-automation-service/tests/test_blueprint_preference_ranking.py` (NEW - comprehensive integration tests)

---

## QA Results
*QA Agent review pending*

