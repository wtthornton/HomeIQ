# Epic 56: Advanced Pattern Detection Framework
# Epic 57: ML Stack Modernization

> Source: [stale-branch-review-requirements.md](stale-branch-review-requirements.md)
> Created: 2026-03-06
> Status: SUPERSEDED — delivered by Epic 37 (Pattern Detection) and Epic 38 (ML Dependencies)

> **NOTE (2026-03-12):** Epic 56 was fully delivered by Epic 37 (Sprint 8, Mar 7) which implemented all 10 detectors.
> Epic 57 was mostly delivered by Epic 38 (Sprint 8, Mar 7). Only Story 57.6 (alignment audit) remained and is
> addressed by Epic 54, Story 54.4.

---

## Epic 56: Advanced Pattern Detection Framework

**Goal**: Expand the pattern detection capability from 2 detectors to 10, enabling richer automation suggestions and behavioral insights.

**Target Service**: `domains/pattern-analysis/ai-pattern-service/src/pattern_analyzer/`

**Architecture Constraints**:
- All detectors follow the existing convention: standalone class with `detect_patterns(events: pd.DataFrame) -> list[dict]`
- Support `min_occurrences`, `min_confidence`, `aggregate_client` constructor params
- Compatible with `confidence_calibrator.py`, `filters.py`, `pattern_deduplicator.py`, `pattern_cross_validator.py`
- Expose new detectors via `__init__.py` `__all__`
- No base class exists on master — detectors are standalone classes (not ABC-based)

**Existing (DO NOT rebuild)**:
- `time_of_day.py` — TimeOfDayPatternDetector (KMeans)
- `co_occurrence.py` — CoOccurrencePatternDetector (sliding window + association rules)

### Story 56.1: Sequence Detector (P1)
**Priority**: P1 — highest value for automation suggestions
**File**: `pattern_analyzer/sequence.py`

Detect sequential device activations (A → B → C).

**Acceptance Criteria**:
- Detect chains of 2-5 entities activating in consistent order
- Configurable `max_gap_seconds` (default 300s between steps)
- Use sliding window over event stream grouped by time proximity
- Return: entity sequence, avg time between steps, occurrence count, confidence
- Handle partial sequences (A → B seen without C)
- Unit tests with realistic HA event data

**Design Reference**: Branch `detectors.py` SequenceDetector (DBSCAN-based)

---

### Story 56.2: Duration Detector (P2)
**File**: `pattern_analyzer/duration.py`

Detect devices with consistent on/off state durations.

**Acceptance Criteria**:
- Calculate mean and std_dev of state durations per entity
- Flag entities with low std_dev relative to mean (consistent duration)
- Configurable `min_duration_seconds` (filter noise), `max_cv` (coefficient of variation threshold)
- Return: entity, avg duration, std_dev, occurrence count, confidence
- Unit tests covering edge cases (single-state entities, very short durations)

---

### Story 56.3: Day Type Detector (P2)
**File**: `pattern_analyzer/day_type.py`

Differentiate weekday vs weekend behavior patterns.

**Acceptance Criteria**:
- Separate event streams by weekday (Mon-Fri) vs weekend (Sat-Sun)
- Compare activation frequency, timing distributions between day types
- Identify entities with significantly different weekday/weekend behavior
- Return: entity, day_type, pattern differences, confidence
- Configurable day grouping (support custom workweek)
- Unit tests with mixed weekday/weekend event data

---

### Story 56.4: Room-Based Detector (P2)
**File**: `pattern_analyzer/room_based.py`

Detect multi-device patterns within the same area/room.

**Acceptance Criteria**:
- Group entities by `area_id` from HA entity registry
- Detect correlated activations within a room
- Identify "room routines" (e.g., bedroom: light + fan + blinds at 10 PM)
- Handle entities without `area_id` gracefully (skip or use "unassigned" group)
- Return: area, entity group, pattern description, confidence
- Integration with data-api for area metadata lookup
- Unit tests with area-tagged event data

---

### Story 56.5: Anomaly Detector (P2)
**File**: `pattern_analyzer/anomaly.py`

Detect unusual deviations from established patterns.

**Acceptance Criteria**:
- Build baseline from historical patterns (rolling 30-day window)
- Flag activations outside normal time windows (>2 std_dev from mean)
- Flag unusual state durations
- Flag unexpected entity activations (never/rarely used entities becoming active)
- Return: entity, anomaly type, expected vs actual, severity, confidence
- Do NOT flag known planned events (vacation mode, maintenance)
- Unit tests with injected anomalies

---

### Story 56.6: Contextual Detector (P2)
**File**: `pattern_analyzer/contextual.py`

Correlate device activity with external context (sun/weather/occupancy).

**Acceptance Criteria**:
- Correlate entity activations with sunrise/sunset times
- Correlate with weather conditions (from weather-api service)
- Correlate with calendar events / occupancy (from calendar-service)
- Identify context-dependent patterns (e.g., "lights on only when cloudy")
- Return: entity, context trigger, correlation strength, confidence
- Graceful degradation when context services unavailable
- Unit tests with mocked context data

**Dependencies**: weather-api (8011), calendar-service (8017)

---

### Story 56.7: Frequency Detector (P3)
**File**: `pattern_analyzer/frequency.py`

Detect entities with consistent daily/weekly activation counts.

**Acceptance Criteria**:
- Calculate daily and weekly activation frequency per entity
- Identify entities with consistent frequency (low coefficient of variation)
- Flag significant changes in frequency (trend detection)
- Return: entity, avg frequency, period, trend direction, confidence
- Unit tests with varying frequency patterns

---

### Story 56.8: Seasonal Detector (P3)
**File**: `pattern_analyzer/seasonal.py`

Track how patterns shift across seasons/months.

**Acceptance Criteria**:
- Compare activation patterns across calendar months
- Detect seasonal transitions (e.g., heating → cooling changeover)
- Identify entities with strong seasonal correlation
- Requires minimum 90 days of historical data (skip if insufficient)
- Return: entity, season, pattern shift description, confidence
- Unit tests with synthetic multi-month data

---

### Story 56.9: Pattern Analyzer Registry + API Integration
**File**: `pattern_analyzer/__init__.py`, `api/` routes

Wire all new detectors into the service.

**Acceptance Criteria**:
- Update `__init__.py` to export all 10 detectors in `__all__`
- Create `PatternRegistry` that manages detector instances and runs all/selected detectors
- Add API endpoint `POST /api/v1/patterns/detect` accepting detector selection + event window
- Add API endpoint `GET /api/v1/patterns/types` returning available detector metadata
- Ensure backward compatibility with existing detection endpoints
- Integration test running all 10 detectors on a sample dataset

---

### Story 56.10: Documentation + Pattern Result Standardization
**File**: `pattern_analyzer/README.md`, `pattern_analyzer/types.py`

**Acceptance Criteria**:
- Create standardized `PatternResult` dataclass (type, confidence, entities, metadata, occurrences)
- Retrofit existing TimeOfDay and CoOccurrence to return `PatternResult` (backward-compatible)
- Document all 10 detectors: purpose, algorithm, configuration, example output
- Add performance benchmarks (target: all 10 detectors < 5s for 10k events)

---

## Epic 57: ML Stack Modernization

**Goal**: Upgrade pinned ML dependencies to current versions, ensuring embedding compatibility and model stability.

**Risk**: HIGH for sentence-transformers (2 major versions), MEDIUM for transformers, LOW for openvino.

### Story 57.1: Embedding Compatibility Test Infrastructure
**Priority**: P1 — prerequisite for all other stories
**Files**: `tests/ml/`, `scripts/`

**Acceptance Criteria**:
- Create test script that generates embeddings with current `sentence-transformers==3.3.1`
- Store reference embeddings for standard test sentences using both models:
  - `all-MiniLM-L6-v2` (384-dim, used by some services)
  - `BAAI/bge-large-en-v1.5` (1024-dim, used by openvino-service)
- Script to compare old vs new embeddings (cosine similarity)
- Pass threshold: similarity >= 0.99 for same input
- Output: compatibility report (pass/fail per model, similarity scores)
- Runnable in CI and locally

---

### Story 57.2: sentence-transformers Upgrade (3.3.1 → 5.x)
**Priority**: P2 — blocked by Story 57.1 results
**Files**: `domains/ml-engine/openvino-service/requirements.txt`, `domains/ml-engine/model-prep/requirements.txt`

**Acceptance Criteria**:
- Upgrade `sentence-transformers` from `==3.3.1` to `>=5.0.0`
- Run embedding compatibility tests from Story 57.1
- If similarity < 0.99: document re-indexing plan (Story 57.5)
- If similarity >= 0.99: proceed with upgrade
- Verify: embedding generation latency, model loading time, memory usage
- Update all import paths if API changed between 3.x and 5.x
- Smoke test openvino-service and model-prep endpoints

**Decision Gate**: Results of Story 57.1 determine whether this story proceeds or defers to Story 57.5.

---

### Story 57.3: transformers Upgrade (4.46.1 → 4.50+)
**Priority**: P2
**Files**: `domains/ml-engine/openvino-service/requirements.txt`, `domains/ml-engine/nlp-fine-tuning/requirements.txt`, `domains/ml-engine/model-prep/requirements.txt`

**Acceptance Criteria**:
- Upgrade `transformers` to `>=4.50.0` (or latest compatible with sentence-transformers pin)
- Verify NER pipeline still works (nlp-fine-tuning)
- Verify model loading in openvino-service
- Verify tokenizer compatibility
- Run existing ML tests

**Constraint**: Must remain compatible with whichever sentence-transformers version is active.

---

### Story 57.4: openvino + optimum-intel Upgrade
**Priority**: P3 — low risk
**Files**: `domains/ml-engine/model-prep/requirements.txt`, `domains/ml-engine/openvino-service/requirements.txt`

**Acceptance Criteria**:
- Upgrade `openvino` to `>=2025.0.0`
- Upgrade `optimum-intel` to `>=1.25.0`
- Verify INT8 quantization pipeline still works
- Verify model conversion and inference
- Run existing openvino-service tests

---

### Story 57.5: Embedding Re-indexing Plan (CONDITIONAL)
**Priority**: P2 — only if Story 57.1 shows similarity < 0.99
**Files**: `scripts/reindex-embeddings.py`, `docs/operations/`

**Acceptance Criteria**:
- Script to re-generate all stored embeddings with new model version
- Backup existing embeddings before re-indexing
- Progress tracking and resume capability (for large datasets)
- Verification step: compare search results before/after
- Runbook in `docs/operations/embedding-reindex.md`
- Estimated downtime and rollback procedure

---

### Story 57.6: ML Dependency Alignment Audit
**Priority**: P3
**Files**: all `requirements.txt` with ML deps

**Acceptance Criteria**:
- Audit all services for ML dependency version consistency
- Ensure `torch`, `numpy`, `scikit-learn` versions are aligned across services
- Remove any unnecessary ML dependency pins
- Update `docs/planning/library-upgrade-plan.md` with Phase 3A completion status
- Create compatibility matrix document

---

## Execution Order

```
Epic 56 (Pattern Detectors) — independent, can start immediately
  56.10 (types/standardization) → 56.1 (sequence, P1) → 56.2-56.6 (P2, parallel) → 56.7-56.8 (P3) → 56.9 (registry)

Epic 57 (ML Stack) — sequential, gated
  57.1 (test infra) → 57.2 (sentence-transformers) ──┐
                    → 57.3 (transformers)             ├→ 57.6 (audit)
                    → 57.4 (openvino)                 │
                    → 57.5 (re-index, conditional) ───┘
```

## Estimated Scope

| Epic | Stories | New Files | Modified Files | Risk |
|------|---------|-----------|----------------|------|
| 56   | 10      | ~12 new .py files + tests | 2-3 existing | LOW — additive, no breaking changes |
| 57   | 6       | ~3 test/script files | 4-6 requirements.txt | HIGH — embedding compatibility |

## Dependencies

| Story | Depends On | External |
|-------|-----------|----------|
| 56.4 (room) | data-api area metadata | — |
| 56.6 (contextual) | weather-api, calendar-service | — |
| 57.2 (sentence-transformers) | 57.1 (test infra) | PyPI package availability |
| 57.3 (transformers) | 57.2 decision | — |
| 57.5 (re-index) | 57.1 results showing similarity < 0.99 | — |
