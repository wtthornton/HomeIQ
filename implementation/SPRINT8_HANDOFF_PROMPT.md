# Sprint 8 Handoff Prompt

**Copy and paste this prompt to continue Sprint 8 work in a new session.**

---

## Context

Continue Sprint 8 work on HomeIQ. Two epics are in progress:

### Epic 38: ML Dependencies Upgrade (5/8 complete)
- ✅ 38.1: Embedding compatibility test infrastructure
- ✅ 38.2: sentence-transformers 5.x assessment
- ✅ 38.3: sentence-transformers upgrade (3.3.1 → 5.x)
- ⏭️ 38.4: Skipped (re-indexing not required)
- ⬜ 38.5: transformers upgrade (4.46.1 → 4.50.x) — P2
- ⬜ 38.6: OpenVINO + Optimum-Intel upgrade — P3
- ⬜ 38.7: Model regeneration (if required) — P2
- ✅ 38.8: Documentation and rollback plan

### Epic 37: Pattern Detection Expansion (1/10 complete)
- ✅ 37.1: Sequence Detector (A → B → C patterns)
- ⬜ 37.2: Duration Detector — P2
- ⬜ 37.3: Day Type Detector — P2
- ⬜ 37.4: Room-Based Detector — P2
- ⬜ 37.5: Seasonal Detector — P3
- ⬜ 37.6: Anomaly Detector — P2
- ⬜ 37.7: Frequency Detector — P3
- ⬜ 37.8: Contextual Detector — P2
- ⬜ 37.9: Pattern Service Integration — P1
- ⬜ 37.10: Dashboard Integration — P2

## Key Files

- **Epic details:** `stories/epic-pattern-detection-expansion.md`, `stories/epic-ml-dependencies-upgrade.md`
- **Progress tracking:** `stories/OPEN-EPICS-INDEX.md`
- **Handoff details:** `implementation/SPRINT8_HANDOFF.md`
- **ML docs:** `docs/architecture/ml-pipeline.md`
- **Pattern detectors:** `domains/pattern-analysis/ai-pattern-service/src/pattern_analyzer/`

## Recommended Next Story

**Story 37.2: Duration Detector** (P2, 2 days)
- Detect devices with consistent on/off durations
- Location: `domains/pattern-analysis/ai-pattern-service/src/pattern_analyzer/duration.py`
- Follow `sequence.py` structure (same pattern as Story 37.1)
- Acceptance: Statistical analysis of state durations, unit tests >80%

Alternative options:
- Story 37.6 (Anomaly Detector) — High value for diagnostics
- Story 38.5 (transformers upgrade) — Continue ML upgrades

## Instructions

1. Read `stories/epic-pattern-detection-expansion.md` for Story 37.2 acceptance criteria
2. Review `domains/pattern-analysis/ai-pattern-service/src/pattern_analyzer/sequence.py` for implementation pattern
3. Implement Duration Detector following the same structure
4. Write unit tests (>80% coverage) and integration tests
5. Run TAPPS quality check: `tapps_quick_check("domains/pattern-analysis/ai-pattern-service/src/pattern_analyzer/duration.py")`
6. Update epic status in `stories/epic-pattern-detection-expansion.md`
7. Update `stories/OPEN-EPICS-INDEX.md` with progress

---

**Start prompt:** "Continue Sprint 8. Implement Story 37.2 (Duration Detector) following the pattern from 37.1 (Sequence Detector)."
