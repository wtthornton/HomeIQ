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

### Story 37.1: Sequence Detector (REQ-PAT-01)
**Priority:** P1  
**Estimate:** 3 days

Detect sequential device activations (A → B → C patterns).

**Acceptance Criteria:**
- [ ] Implement `SequenceDetector` class extending `PatternDetector`
- [ ] Use sliding window with configurable gap tolerance (default: 5 minutes)
- [ ] Detect patterns like: motion sensor → light → thermostat
- [ ] Return: entity sequence, average time between steps, confidence score
- [ ] Minimum 3 occurrences to establish pattern
- [ ] Unit tests with >80% coverage
- [ ] Integration test with sample event data

**Technical Details:**
- Window size: configurable (default 30 minutes)
- Gap tolerance: configurable (default 5 minutes between steps)
- Confidence based on consistency of timing

---

### Story 37.2: Duration Detector (REQ-PAT-02)
**Priority:** P2  
**Estimate:** 2 days

Detect devices with consistent on/off durations.

**Acceptance Criteria:**
- [ ] Implement `DurationDetector` class extending `PatternDetector`
- [ ] Statistical analysis of state duration distributions
- [ ] Detect consistent patterns (e.g., bathroom light always on for 5-7 minutes)
- [ ] Flag anomalous durations (>2 standard deviations)
- [ ] Return: entity, average duration, std deviation, confidence
- [ ] Unit tests with >80% coverage

**Technical Details:**
- Use normal distribution fitting
- Minimum 10 state changes to establish baseline
- Track both "on" and "off" durations separately

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

### Story 37.4: Room-Based Detector (REQ-PAT-04)
**Priority:** P2  
**Estimate:** 3 days

Correlate device activity within the same area/room.

**Acceptance Criteria:**
- [ ] Implement `RoomBasedDetector` class extending `PatternDetector`
- [ ] Use `area_id` from Home Assistant entity registry
- [ ] Detect room-level behavioral patterns (e.g., "living room evening routine")
- [ ] Group co-occurring events by room
- [ ] Return: area_id, device_group, pattern_type, confidence
- [ ] Unit tests with >80% coverage

**Technical Details:**
- Requires area_id enrichment from websocket-ingestion (Epic 23)
- Fall back to entity_id prefix parsing if area_id unavailable
- Correlate within 2-minute windows

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

### Story 37.6: Anomaly Detector (REQ-PAT-06)
**Priority:** P2  
**Estimate:** 3 days

Statistical outlier detection on established patterns.

**Acceptance Criteria:**
- [ ] Implement `AnomalyDetector` class extending `PatternDetector`
- [ ] Detect unusual pattern deviations from baseline
- [ ] Security/diagnostic value (unexpected device activations)
- [ ] Configurable sensitivity threshold
- [ ] Return: entity, anomaly_type, severity, timestamp, context
- [ ] Unit tests with >80% coverage

**Technical Details:**
- Use Isolation Forest or DBSCAN for outlier detection
- Require 7+ days baseline before anomaly detection
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
