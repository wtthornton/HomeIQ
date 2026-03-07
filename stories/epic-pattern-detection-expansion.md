# Epic 37: Pattern Detection Expansion

**Priority:** P1 High  
**Estimated Duration:** 2-3 weeks  
**Status:** Open  
**Created:** 2026-03-06  
**Source:** Stale branch review (claude/review-ai5-2-story-011CUT68Ja123vL4aDY11rh4)

## Overview

Expand the pattern detection capabilities in `ai-pattern-service` with 8 additional detectors extracted from the reviewed stale branch. The current implementation has TimeOfDay and CoOccurrence detectors; this epic adds the remaining detector types for comprehensive behavioral pattern analysis.

## Background

The stale branch contained 10 pattern detectors targeting the old `ai-automation-service` path. Master already has mature implementations of TimeOfDay and CoOccurrence (with KMeans, noise filtering, domain exclusions). This epic implements the 8 missing detectors using the modern `PatternDetector` base class architecture.

## Implementation Notes

- All detectors should follow the `PatternDetector` base class pattern in `domains/pattern-analysis/ai-pattern-service/src/pattern_analyzer/`
- Use incremental processing with aggregate storage
- Include noise filtering and domain overrides
- Branch code is design reference only - implement fresh on current architecture
- Use `pandas` + `DBSCAN` (sklearn) consistent with existing detectors

## Stories

### Story 37.1: Sequence Detector (REQ-PAT-01) ✓ COMPLETE
**Priority:** P1  
**Estimate:** 3 days  
**Completed:** 2026-03-06

Detect sequential device activations (A → B → C patterns).

**Acceptance Criteria:**
- [x] Implement `SequenceDetector` class extending `PatternDetector`
- [x] Use sliding window with configurable gap tolerance (default: 5 minutes)
- [x] Detect patterns like: motion sensor → light → thermostat
- [x] Return: entity sequence, average time between steps, confidence score
- [x] Minimum 3 occurrences to establish pattern
- [x] Unit tests with >80% coverage (25 unit tests)
- [x] Integration test with sample event data (6 integration tests)

**Technical Details:**
- Window size: configurable (default 30 minutes)
- Gap tolerance: configurable (default 5 minutes between steps)
- Confidence based on consistency of timing

**Implementation:**
- `src/pattern_analyzer/sequence.py` — SequencePatternDetector class (598 lines)
- `tests/pattern_analyzer/test_sequence.py` — 25 unit tests
- `tests/pattern_analyzer/test_sequence_integration.py` — 6 integration tests
- Quality score: 68.36 (higher than existing co_occurrence.py at 65.6)

---

### Story 37.2: Duration Detector (REQ-PAT-02) ✓ COMPLETE
**Priority:** P2  
**Estimate:** 2 days  
**Completed:** 2026-03-06

Detect devices with consistent on/off durations.

**Acceptance Criteria:**
- [x] Implement `DurationPatternDetector` class
- [x] Statistical analysis of state duration distributions
- [x] Detect consistent patterns (e.g., bathroom light always on for 5-7 minutes)
- [x] Flag anomalous durations (>2 standard deviations)
- [x] Return: entity, average duration, std deviation, confidence
- [x] Unit tests with >80% coverage (35+ test cases)

**Technical Details:**
- Use normal distribution fitting
- Minimum 10 state changes to establish baseline (configurable)
- Track both "on" and "off" durations separately
- Coefficient of variation filtering for consistency
- Auto-off and alert automation suggestions

**Implementation:**
- `src/pattern_analyzer/duration.py` — DurationPatternDetector class (593 lines)
- `tests/pattern_analyzer/test_duration.py` — 35+ unit tests
- Quality score: 69.08 (higher than sequence.py at 68.36)

---

### Story 37.3: Day Type Detector (REQ-PAT-03)
**Priority:** P2  
**Estimate:** 2 days

Compare activation patterns between weekdays and weekends.

**Acceptance Criteria:**
- [ ] Implement `DayTypeDetector` class extending `PatternDetector`
- [ ] Separate pattern analysis for weekdays vs weekends
- [ ] Identify devices with significantly different behavior by day type
- [ ] Return: entity, weekday_pattern, weekend_pattern, variance_score
- [ ] Unit tests with >80% coverage

**Technical Details:**
- Use day of week from event timestamps
- Calculate activation count and timing distributions per day type
- Flag entities with >30% variance between day types

---

### Story 37.4: Room-Based Detector (REQ-PAT-04) ✓ COMPLETE
**Priority:** P2
**Estimate:** 3 days
**Completed:** 2026-03-06

Correlate device activity within the same area/room.

**Acceptance Criteria:**
- [x] Implement `RoomBasedPatternDetector` class
- [x] Use `area_id` from Home Assistant entity registry
- [x] Detect room-level behavioral patterns (e.g., "living room evening routine")
- [x] Group co-occurring events by room (2-minute windows)
- [x] Return: area_id, device_group, pattern_type, confidence
- [x] Unit tests with >80% coverage (56 test cases)

**Technical Details:**
- Requires area_id enrichment from websocket-ingestion (Epic 23)
- Fall back to entity_id prefix parsing if area_id unavailable
- Correlate within 2-minute windows

**Implementation:**
- `src/pattern_analyzer/room_based.py` — RoomBasedPatternDetector class
- `tests/pattern_analyzer/test_room_based.py` — 56 unit tests
- Quality score: 69.56 (consistent with other detectors)
- Features: area_id fallback, time-of-day periods, subset detection, automation suggestions

---

### Story 37.5: Seasonal Detector (REQ-PAT-05)
**Priority:** P3  
**Estimate:** 2 days

Track how patterns shift across seasons.

**Acceptance Criteria:**
- [ ] Implement `SeasonalDetector` class extending `PatternDetector`
- [ ] Detect heating/cooling transitions
- [ ] Identify daylight-dependent behaviors
- [ ] Return: entity, season, pattern_shift, confidence
- [ ] Graceful degradation if <90 days of data
- [ ] Unit tests with >80% coverage

**Technical Details:**
- Requires 90+ days of historical data for meaningful results
- Use astronomical seasons (equinox/solstice dates)
- Track sunrise/sunset correlation

---

### Story 37.6: Anomaly Detector (REQ-PAT-06) ✓ COMPLETE
**Priority:** P2  
**Estimate:** 3 days  
**Completed:** 2026-03-06

Statistical outlier detection on established patterns.

**Acceptance Criteria:**
- [x] Implement `AnomalyPatternDetector` class
- [x] Detect unusual pattern deviations from baseline
- [x] Security/diagnostic value (unexpected device activations)
- [x] Configurable sensitivity threshold
- [x] Return: entity, anomaly_type, severity, timestamp, context
- [x] Unit tests with >80% coverage (40+ test cases)

**Technical Details:**
- Statistical z-score based outlier detection
- Require 7+ days baseline before anomaly detection (configurable)
- Categorize: timing, frequency, duration, absence anomalies

**Implementation:**
- `src/pattern_analyzer/anomaly.py` — AnomalyPatternDetector class (691 lines)
- `tests/pattern_analyzer/test_anomaly.py` — 40+ unit tests
- Quality score: 69.12 (clean lint, clean security)
- Categorize: timing anomaly, frequency anomaly, sequence anomaly

---

### Story 37.7: Frequency Detector (REQ-PAT-07)
**Priority:** P3  
**Estimate:** 2 days

Detect devices with consistent daily/weekly activation counts.

**Acceptance Criteria:**
- [ ] Implement `FrequencyDetector` class extending `PatternDetector`
- [ ] Track daily and weekly activation counts per entity
- [ ] Flag significant changes in frequency as potential issues
- [ ] Return: entity, daily_avg, weekly_avg, variance, trend
- [ ] Unit tests with >80% coverage

**Technical Details:**
- Rolling 7-day and 30-day windows
- Alert threshold: >50% change from baseline
- Track trend direction (increasing/decreasing/stable)

---

### Story 37.8: Contextual Detector (REQ-PAT-08)
**Priority:** P2  
**Estimate:** 3 days

Correlate device activity with external context.

**Acceptance Criteria:**
- [ ] Implement `ContextualDetector` class extending `PatternDetector`
- [ ] Correlate with sunrise/sunset times
- [ ] Correlate with weather conditions (via weather-api)
- [ ] Correlate with calendar events (via calendar-service)
- [ ] Return: entity, context_type, correlation_strength, confidence
- [ ] Unit tests with >80% coverage

**Technical Details:**
- Integration with weather-api (port 8009) for temperature/conditions
- Integration with calendar-service (port 8013) for occupancy hints
- Use sun position from Home Assistant sun.sun entity

---

### Story 37.9: Pattern Service Integration
**Priority:** P1  
**Estimate:** 2 days

Integrate all new detectors into the pattern analysis pipeline.

**Acceptance Criteria:**
- [ ] Register all 8 new detectors in pattern service startup
- [ ] Add configuration options for enabling/disabling individual detectors
- [ ] Update `/api/patterns/stats` endpoint with new detector metrics
- [ ] Add `/api/patterns/detectors` endpoint listing available detectors
- [ ] Performance testing: <5s for full pattern analysis on 10k events
- [ ] Documentation update

---

### Story 37.10: Dashboard Integration
**Priority:** P2  
**Estimate:** 2 days

Display new pattern types in the AI Automation UI.

**Acceptance Criteria:**
- [ ] Add pattern type filter for new detector types
- [ ] Visualization for sequence patterns (timeline view)
- [ ] Visualization for anomalies (alert-style cards)
- [ ] Room-based pattern grouping view
- [ ] Update pattern detail modal with new fields

---

## Dependencies

- ai-pattern-service (domains/pattern-analysis/)
- data-api for event queries
- weather-api for contextual correlation
- calendar-service for occupancy correlation
- websocket-ingestion area_id enrichment (Epic 23)

## Success Metrics

- 8 new detector types operational
- Pattern detection coverage: >80% of device behaviors categorized
- False positive rate: <10%
- Query performance: <5s for full analysis

## Risks

- Seasonal detector requires 90+ days of data (may not be immediately testable)
- Contextual detector depends on external service availability
- Room-based detector requires area_id enrichment to be enabled

## Definition of Done

- [ ] All 10 stories complete
- [ ] All unit tests passing (>80% coverage)
- [ ] Integration tests with sample data
- [ ] Documentation updated
- [ ] TAPPS quality gate passing for all new files
- [ ] No regression in existing pattern detection
