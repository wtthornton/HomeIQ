# Story AI3.2: Same-Area Device Pair Detection

**Epic:** Epic-AI-3 - Cross-Device Synergy & Contextual Opportunities  
**Story ID:** AI3.2  
**Priority:** High  
**Estimated Effort:** 8-10 hours  
**Dependencies:** Story AI3.1 (Synergy Detector Foundation)

---

## User Story

**As a** system  
**I want** to detect specific device pair patterns in the same area  
**so that** I can suggest high-value automation opportunities

---

## Business Value

- **Focused Detection:** Targets most common/valuable automation patterns
- **High Success Rate:** Same-area pairs have >70% user approval rate
- **Educational:** Helps users discover automation possibilities
- **Quick Wins:** Low-complexity automations users can deploy immediately

---

## Acceptance Criteria

1. ✅ **Enhanced DevicePairAnalyzer:**
   - Extends AI3.1 with advanced pair matching
   - Analyzes device usage frequency from InfluxDB
   - Calculates area traffic patterns
   - Ranks pairs by combined impact score

2. ✅ **Usage Frequency Integration:**
   - Query InfluxDB for device event counts (last 30 days)
   - Higher usage → higher impact score
   - Inactive devices deprioritized

3. ✅ **Area Traffic Analysis:**
   - Calculate area usage from entity event frequency
   - High-traffic areas get priority (bedroom, kitchen > storage)
   - Boost impact scores for frequently used areas

4. ✅ **Advanced Impact Scoring:**
   - `impact_score = benefit_score * usage_freq * area_traffic * (1 - complexity_penalty)`
   - Ensures suggestions target highest-value opportunities

5. ✅ **Performance:**
   - InfluxDB queries < 5 seconds
   - Total analysis time <1 minute
   - Memory <100MB

---

## Tasks / Subtasks

### Task 1: Create DevicePairAnalyzer (AC: 1)

- [x] Create `services/ai-automation-service/src/synergy_detection/device_pair_analyzer.py`
- [x] Implement `DevicePairAnalyzer` class
- [x] Extend DeviceSynergyDetector to use analyzer
- [x] Add configurable impact boost factors

### Task 2: InfluxDB Usage Frequency Integration (AC: 2, 3)

- [x] Add InfluxDB client to DevicePairAnalyzer
- [x] Implement `get_device_usage_frequency()` method
- [x] Implement `get_area_traffic()` method
- [x] Cache usage data for batch performance

### Task 3: Advanced Impact Scoring (AC: 4)

- [x] Implement enhanced `calculate_impact_score()` method
- [x] Incorporate usage frequency (0.1-1.0 multiplier)
- [x] Incorporate area traffic (0.5-1.0 multiplier)
- [x] Test with varied device configurations

### Task 4: Testing (AC: 5)

- [x] Unit tests for DevicePairAnalyzer
- [x] Test usage frequency calculations
- [x] Test area traffic calculations
- [x] Test advanced impact scoring
- [x] Performance benchmarks

---

## Dev Notes

**Integration:** Enhances AI3.1 DeviceSynergyDetector  
**Database:** InfluxDB for usage stats  
**Performance:** Batch queries, caching required

---

## Dev Agent Record

### Agent Model Used
Claude Sonnet 4.5 (Dev Agent - James)

### Implementation Summary
Successfully implemented advanced device pair analysis with InfluxDB usage statistics integration. Enhanced synergy detection with usage frequency and area traffic analysis for more accurate impact scoring.

**Key Achievements:**
- ✅ DevicePairAnalyzer with InfluxDB integration
- ✅ Usage frequency calculation (0.1-1.0 based on events/day)
- ✅ Area traffic analysis (0.5-1.0 based on area activity)
- ✅ Advanced impact scoring formula
- ✅ Performance caching (device usage + area traffic)
- ✅ 12 comprehensive tests passing

**Performance:**
- Query time: <5 seconds for 30 days of data
- Memory efficient with caching
- Graceful degradation on InfluxDB failures

### File List

**New Files:**
- `services/ai-automation-service/src/synergy_detection/device_pair_analyzer.py`
- `services/ai-automation-service/tests/test_device_pair_analyzer.py` (12 tests)

**Modified Files:**
- `services/ai-automation-service/src/synergy_detection/__init__.py` (Export DevicePairAnalyzer)
- `services/ai-automation-service/src/synergy_detection/synergy_detector.py` (Integration with analyzer)
- `services/ai-automation-service/src/scheduler/daily_analysis.py` (Pass influxdb_client)

### Test Results
- 12/12 tests passing
- Total test suite: 39/39 passing (AI3.1 + AI3.2)
- Execution time: 0.64s

---

**Story Status:** ✅ **COMPLETE** - Ready for Review  
**Created:** 2025-10-18  
**Completed:** 2025-10-18

