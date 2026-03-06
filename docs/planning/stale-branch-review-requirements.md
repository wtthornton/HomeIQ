# Stale Branch Review — Requirements Extracted

> Generated: 2026-03-06
> Source branches reviewed before deletion:
> - `claude/phase-3a-full-ml-updates-01CdqopgzKaF27zA8BSNAtz3` (Nov 2025)
> - `claude/review-ai5-2-story-011CUT68Ja123vL4aDY11rh4` (Oct 2025)

## Branch 1: Phase 3A ML Updates

### What It Did
- Upgraded `sentence-transformers` from `3.3.1` to `5.1.2` (2 major versions)
- Upgraded `scikit-learn`, `spacy`, `transformers`, `torch`, `openvino`, `optimum-intel`
- Targeted old `services/` paths (pre-restructure)

### Current State on Master
- `sentence-transformers==3.3.1` pinned in `openvino-service` and `model-prep`
- `transformers==4.46.1` pinned in `openvino-service`
- `scikit-learn>=1.5.0,<2.0.0` across 5 services (already upgraded in Phase 3)
- `torch>=2.5.0` across 5 services (already upgraded)
- `spacy` not used on master (NER service removed/consolidated)

### Extractable Requirements

#### REQ-ML-01: sentence-transformers Upgrade (DEFERRED — needs planning)
- **Current**: `==3.3.1` (openvino-service, model-prep)
- **Target**: `>=5.0.0` (latest stable)
- **Risk**: HIGH — 2 major version jump, embeddings may be incompatible
- **Prerequisite**: Embedding compatibility testing (cosine similarity >= 0.99 for `all-MiniLM-L6-v2` / `BAAI/bge-large-en-v1.5`)
- **Impact**: openvino-service, model-prep, any service using stored embeddings
- **Decision needed**: Re-index stored embeddings or verify backward compatibility
- **Priority**: P2 — not blocking, current version works, but falling behind

#### REQ-ML-02: transformers Upgrade
- **Current**: `==4.46.1` (openvino-service), `>=4.45.0` (nlp-fine-tuning), `>=4.46.0` (model-prep)
- **Target**: `>=4.50.0` (or latest compatible with sentence-transformers pin)
- **Risk**: MEDIUM — must stay compatible with pinned sentence-transformers
- **Priority**: P2

#### REQ-ML-03: openvino + optimum-intel Upgrade
- **Current**: `>=2024.5.0` (model-prep), not pinned in openvino-service requirements
- **Target**: `>=2025.x` (latest)
- **Risk**: LOW — minor version bumps
- **Priority**: P3

---

## Branch 2: Pattern Detection Framework (10 Detectors)

### What It Did
Added 10 rule-based pattern detectors to `ai-automation-service` (old path):
1. TimeOfDayDetector, 2. CoOccurrenceDetector, 3. SequenceDetector,
4. ContextualDetector, 5. DurationDetector, 6. DayTypeDetector,
7. RoomBasedDetector, 8. SeasonalDetector, 9. AnomalyDetector, 10. FrequencyDetector

### Current State on Master
Master already has in `domains/pattern-analysis/ai-pattern-service/src/pattern_analyzer/`:
- `time_of_day.py` — TimeOfDayPatternDetector (KMeans-based, more mature than branch version)
- `co_occurrence.py` — CoOccurrenceDetector (with noise filtering, domain exclusions)
- `confidence_calibrator.py` — Confidence calibration
- `filters.py` — Pattern filtering
- `pattern_cross_validator.py` — Cross-validation
- `pattern_deduplicator.py` — Deduplication

**Already implemented (2 of 10)**: TimeOfDay, CoOccurrence — master's versions are more mature
(incremental processing, aggregate storage, noise filtering, domain overrides).

### Extractable Requirements — Missing Detectors

#### REQ-PAT-01: Sequence Detector (A → B → C patterns)
- Detect sequential device activations (e.g., motion sensor → light → thermostat)
- Use sliding window with configurable gap tolerance
- Return entity sequence, average time between steps, confidence
- **Priority**: P1 — high value for automation suggestions

#### REQ-PAT-02: Duration Detector (consistent state durations)
- Detect devices with consistent on/off durations
- Statistical analysis of state duration distributions
- Flag anomalous durations
- **Priority**: P2

#### REQ-PAT-03: Day Type Detector (weekday vs weekend)
- Compare activation patterns between weekdays and weekends
- Separate pattern sets for each day type
- Useful for time-aware automation rules
- **Priority**: P2

#### REQ-PAT-04: Room-Based Detector (multi-device room patterns)
- Correlate device activity within the same area/room
- Detect room-level behavioral patterns
- Requires area_id from Home Assistant entity registry
- **Priority**: P2

#### REQ-PAT-05: Seasonal Detector (monthly/quarterly behavior changes)
- Track how patterns shift across seasons
- Detect heating/cooling transitions, daylight-dependent behaviors
- Requires 90+ days of historical data
- **Priority**: P3 — needs long data history

#### REQ-PAT-06: Anomaly Detector (unusual pattern deviations)
- Statistical outlier detection on established patterns
- Security/diagnostic value (unexpected device activations)
- **Priority**: P2

#### REQ-PAT-07: Frequency Detector (consistent activation counts)
- Detect devices with consistent daily/weekly activation counts
- Flag changes in frequency as potential issues
- **Priority**: P3

#### REQ-PAT-08: Contextual Detector (sun/weather/occupancy correlation)
- Correlate device activity with external context (sunrise/sunset, weather, occupancy)
- Requires integration with weather-api and calendar-service
- **Priority**: P2

### Implementation Notes
- Branch used `pandas` + `DBSCAN` (sklearn) — consistent with master's approach
- Branch targeted `ai-automation-service`; master moved pattern detection to `ai-pattern-service`
- All new detectors should follow master's `PatternDetector` base class pattern
  (incremental processing, aggregate storage, noise filtering)
- Branch code is NOT directly mergeable — wrong paths, old architecture, less mature
  than what master already has for TimeOfDay/CoOccurrence
- Use branch code as **design reference only**, implement fresh on current architecture

---

## Summary

| Requirement | Source | Priority | Status |
|-------------|--------|----------|--------|
| REQ-ML-01: sentence-transformers 5.x | Phase 3A | P2 | Deferred — needs embed testing |
| REQ-ML-02: transformers upgrade | Phase 3A | P2 | Blocked by sentence-transformers pin |
| REQ-ML-03: openvino upgrade | Phase 3A | P3 | Low risk, do anytime |
| REQ-PAT-01: Sequence detector | AI5-2 | P1 | Not implemented |
| REQ-PAT-02: Duration detector | AI5-2 | P2 | Not implemented |
| REQ-PAT-03: Day type detector | AI5-2 | P2 | Not implemented |
| REQ-PAT-04: Room-based detector | AI5-2 | P2 | Not implemented |
| REQ-PAT-05: Seasonal detector | AI5-2 | P3 | Not implemented |
| REQ-PAT-06: Anomaly detector | AI5-2 | P2 | Not implemented |
| REQ-PAT-07: Frequency detector | AI5-2 | P3 | Not implemented |
| REQ-PAT-08: Contextual detector | AI5-2 | P2 | Not implemented |
