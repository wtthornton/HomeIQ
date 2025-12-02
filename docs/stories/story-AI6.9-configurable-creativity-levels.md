# Story AI6.9: Configurable Creativity Levels

**Story ID:** AI6.9  
**Epic:** AI-6 (Blueprint-Enhanced Suggestion Intelligence)  
**Status:** ✅ Ready for Review  
**Priority:** P1 (Phase 3 Feature)  
**Story Points:** 3  
**Complexity:** Medium  
**Estimated Effort:** 6-8 hours

---

## Story Description

Implement creativity level system (conservative/balanced/creative) affecting confidence thresholds and suggestion types. Apply filtering based on user preference.

## User Story

**As a** Home Assistant user,  
**I want** to control how experimental my suggestions are,  
**So that** I receive suggestions matching my comfort level with automation complexity.

---

## Acceptance Criteria

### AC1: Creativity Levels Defined
- [x] Creativity levels: conservative, balanced, creative
- [x] Each level has configuration:
  - min_confidence threshold
  - blueprint_weight (preference for blueprint opportunities)
  - experimental_boost (boost for experimental suggestions)
  - max_experimental (max experimental suggestions allowed)

### AC2: Creativity Configuration
- [x] Conservative: high confidence (0.85), blueprint-focused, no experimental
- [x] Balanced: moderate confidence (0.70), balanced approach, 2 experimental max
- [x] Creative: lower confidence (0.55), more experimental, 5 experimental max

### AC3: Applied in Phase 5 and Ask AI
- [x] Creativity filtering applied in Phase 5 description generation
- [x] Creativity filtering applied in Ask AI suggestion generation
- [x] Creativity filtering applied in clarify endpoint
- [x] Suggestions filtered by confidence threshold
- [x] Experimental suggestions limited per level

### AC4: Integration Tests
- [x] Test filtering with conservative level
- [x] Test filtering with balanced level
- [x] Test filtering with creative level
- [x] Test experimental limits
- [x] Test blueprint weight boosting
- [x] Test graceful degradation on errors

---

## Tasks / Subtasks

### Task 1: Define Creativity Configuration
- [x] Create creativity config dictionary (CreativityConfig class)
- [x] Define thresholds for each level
- [x] Implement configuration access

### Task 2: Implement Filtering Logic
- [x] Filter by min_confidence threshold
- [x] Apply blueprint_weight to ranking
- [x] Limit experimental suggestions
- [x] Apply filtering in Phase 5 and Ask AI
- [x] Apply filtering in clarify endpoint

### Task 3: Testing
- [x] Test each creativity level (conservative, balanced, creative)
- [x] Test confidence filtering
- [x] Test experimental limits
- [x] Test blueprint weight boosting
- [x] Test experimental detection
- [x] Test integration (Phase 5 and Ask AI)

---

## Technical Requirements

### Creativity Configuration

```python
CREATIVITY_CONFIG = {
    "conservative": {
        "min_confidence": 0.85,
        "blueprint_weight": 0.8,
        "experimental_boost": 0.0,
        "max_experimental": 0
    },
    "balanced": {
        "min_confidence": 0.70,
        "blueprint_weight": 0.6,
        "experimental_boost": 0.1,
        "max_experimental": 2
    },
    "creative": {
        "min_confidence": 0.55,
        "blueprint_weight": 0.4,
        "experimental_boost": 0.3,
        "max_experimental": 5
    }
}
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
- CreativityFilter service created: `services/ai-automation-service/src/blueprint_discovery/creativity_filter.py`
- Integrated into Phase 5: `services/ai-automation-service/src/scheduler/daily_analysis.py`
- Integrated into Ask AI: `services/ai-automation-service/src/api/ask_ai_router.py`
- Integration tests created: `services/ai-automation-service/tests/test_creativity_filtering.py`

### Completion Notes List
- ✅ Created CreativityFilter service class with full filtering logic
- ✅ Defined CreativityConfig with all three levels (conservative, balanced, creative)
- ✅ Implemented confidence threshold filtering based on creativity level
- ✅ Implemented blueprint weight boosting for blueprint-validated suggestions
- ✅ Implemented experimental suggestion detection and limiting
- ✅ Conservative level: min_confidence=0.85, no experimental, blueprint-focused (weight=0.8)
- ✅ Balanced level: min_confidence=0.70, max 2 experimental, balanced approach (weight=0.6)
- ✅ Creative level: min_confidence=0.55, max 5 experimental, more experimental (weight=0.4)
- ✅ Integrated creativity filtering into Phase 5 description generation
- ✅ Integrated creativity filtering into Ask AI suggestion generation
- ✅ Integrated creativity filtering into clarify endpoint
- ✅ Filtering applied before max_suggestions limit (filters first, then limits)
- ✅ Graceful degradation on errors (returns all suggestions if filtering fails)
- ✅ Comprehensive integration tests (13 test cases covering all scenarios)
- ✅ All acceptance criteria met

### File List
- `services/ai-automation-service/src/blueprint_discovery/creativity_filter.py` (NEW - CreativityFilter service)
- `services/ai-automation-service/src/blueprint_discovery/__init__.py` (UPDATED - exports CreativityFilter)
- `services/ai-automation-service/src/scheduler/daily_analysis.py` (UPDATED - integrated creativity filtering in Phase 5)
- `services/ai-automation-service/src/api/ask_ai_router.py` (UPDATED - integrated creativity filtering in Ask AI and clarify)
- `services/ai-automation-service/tests/test_creativity_filtering.py` (NEW - comprehensive integration tests)

---

## QA Results
*QA Agent review pending*

