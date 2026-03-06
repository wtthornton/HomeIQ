# Sprint 8 Handoff — Pattern Detection + ML Upgrades

**Last Updated:** 2026-03-06  
**Status:** In Progress

## Executive Summary

Sprint 8 covers two epics:
- **Epic 37:** Pattern Detection Expansion (10 stories, 0 complete)
- **Epic 38:** ML Dependencies Upgrade (8 stories, 5 complete)

## Epic 38: ML Dependencies Upgrade — Status

### Completed Stories (5/8)

| Story | Description | Status | Notes |
|-------|-------------|--------|-------|
| 38.1 | Embedding Compatibility Test Infrastructure | ✅ Complete | `tests/ml/` created |
| 38.2 | sentence-transformers 5.x Assessment | ✅ Complete | Upgrade deemed safe |
| 38.3 | sentence-transformers Upgrade | ✅ Complete | 3.3.1 → 5.x |
| 38.4 | Embedding Re-indexing | ⏭️ Skipped | Not required |
| 38.8 | Documentation and Rollback Plan | ✅ Complete | `docs/architecture/ml-pipeline.md` |

### Remaining Stories (3)

| Story | Description | Priority | Estimate | Blocked By |
|-------|-------------|----------|----------|------------|
| 38.5 | transformers Upgrade (4.46.1 → 4.50.x) | P2 | 2 days | None |
| 38.6 | OpenVINO + Optimum-Intel Upgrade | P3 | 1 day | None |
| 38.7 | Model Regeneration (if required) | P2 | 2 days | 38.5, 38.6 |

### Key Files Changed

- `domains/ml-engine/openvino-service/requirements.txt` — sentence-transformers 5.x
- `domains/ml-engine/model-prep/requirements.txt` — sentence-transformers 5.x
- `libs/homeiq-memory/pyproject.toml` — sentence-transformers 5.x
- `TECH_STACK.md` — Updated ML versions
- `docs/architecture/ml-pipeline.md` — **NEW** comprehensive ML docs

### Decision: Can Proceed to Epic 37

Epic 38 remaining stories (38.5-38.7) are P2/P3 and do not block Epic 37. They can be completed:
- Opportunistically during Epic 37
- In a future sprint
- Before production deployment (recommended)

---

## Epic 37: Pattern Detection Expansion — Status

### All Stories Pending (0/10)

| Story | Description | Priority | Estimate |
|-------|-------------|----------|----------|
| 37.1 | Sequence Detector | P1 | 3 days |
| 37.2 | Duration Detector | P2 | 2 days |
| 37.3 | Day Type Detector | P2 | 2 days |
| 37.4 | Room-Based Detector | P2 | 3 days |
| 37.5 | Seasonal Detector | P3 | 2 days |
| 37.6 | Anomaly Detector | P2 | 3 days |
| 37.7 | Frequency Detector | P3 | 2 days |
| 37.8 | Contextual Detector | P2 | 3 days |
| 37.9 | Pattern Service Integration | P1 | 2 days |
| 37.10 | Dashboard Integration | P2 | 2 days |

### Recommended Execution Order

1. **37.1** (Sequence Detector) — Core P1 functionality
2. **37.2** (Duration Detector) — Builds on sequence analysis
3. **37.6** (Anomaly Detector) — High value for diagnostics
4. **37.4** (Room-Based Detector) — Leverages area_id from Epic 23
5. **37.3** (Day Type Detector) — Weekday/weekend analysis
6. **37.8** (Contextual Detector) — External integrations
7. **37.9** (Pattern Service Integration) — Wire up all detectors
8. **37.10** (Dashboard Integration) — UI visibility
9. **37.5** (Seasonal Detector) — Requires 90+ days data
10. **37.7** (Frequency Detector) — Lower priority

### Prerequisites

- ai-pattern-service running (`domains/pattern-analysis/`)
- data-api for event queries
- weather-api for contextual correlation (Story 37.8)
- calendar-service for occupancy correlation (Story 37.8)

---

## Next Actions

To continue Sprint 8, choose one:

### Option A: Start Epic 37 (Pattern Detection)
```
Story 37.1: Sequence Detector
- Location: domains/pattern-analysis/ai-pattern-service/src/pattern_analyzer/
- Base class: PatternDetector
- Acceptance: Detect A → B → C patterns, unit tests >80%
```

### Option B: Complete Epic 38 (ML Upgrades)
```
Story 38.5: transformers Upgrade
- Update transformers from 4.46.1 to 4.50.x
- Test compatibility with sentence-transformers 5.x
- Verify model loading in openvino-service
```

---

## Reference Links

- [Epic 37 Full Details](../stories/epic-pattern-detection-expansion.md)
- [Epic 38 Full Details](../stories/epic-ml-dependencies-upgrade.md)
- [ML Pipeline Architecture](../docs/architecture/ml-pipeline.md)
- [sentence-transformers Assessment](./analysis/sentence-transformers-upgrade-assessment.md)
- [Open Epics Index](../stories/OPEN-EPICS-INDEX.md)
