# Next Steps and Test Plan

**Date:** November 25, 2025  
**Status:** Ready for Testing

---

## Completed Work

### ✅ 1. Individual Home Test Runner
- Auto-discovers 37 homes from devices-v2/v3
- Parametrized tests (each home separately)
- Per-home metrics collection
- Results aggregation to JSON

### ✅ 2. Event Scaling Implementation
- Doubled events: 7.5 events/device/day (50% of production)
- Device and area-based scaling
- Larger homes get more events (realistic)

### ✅ 3. Device-Type-Specific Event Generation
- Implemented device-type-specific frequencies
- Based on production data analysis
- Realistic event patterns per device type

---

## Next Steps

### Step 1: Run Quick Test (5 Homes)
**Purpose:** Validate implementation works correctly

```bash
cd services/ai-automation-service
pytest tests/datasets/test_single_home_patterns.py::test_pattern_detection_individual_home -v
```

**Expected:**
- 5 homes tested
- Device-type-specific event generation
- Pattern detection runs successfully
- Results saved to JSON

### Step 2: Review Test Results
**Purpose:** Validate event counts and patterns

**Check:**
- Events per device type match recommendations
- Pattern detection finds realistic patterns
- No errors or warnings
- Results JSON is created

### Step 3: Run Comprehensive Test (All 37 Homes)
**Purpose:** Full validation across all homes

```bash
pytest tests/datasets/test_single_home_patterns.py::test_pattern_detection_all_homes -v
```

**Expected:**
- All 37 homes tested
- ~77,700 total events (estimated)
- Results aggregated
- Metrics calculated

### Step 4: Analyze Results
**Purpose:** Identify improvements and validate accuracy

**Review:**
- Per-home precision/recall/F1 scores
- Homes with low accuracy
- Event count distribution
- Pattern detection quality

### Step 5: Fine-Tune (If Needed)
**Purpose:** Adjust based on results

**Potential Adjustments:**
- Device-type frequencies
- Pattern detection thresholds
- Event generation patterns
- Area multipliers

---

## Test Execution Plan

### Quick Test (5 Minutes)
1. Run 5 representative homes
2. Validate event generation
3. Check pattern detection
4. Review basic metrics

### Comprehensive Test (30-60 Minutes)
1. Run all 37 homes
2. Collect full metrics
3. Generate aggregated results
4. Analyze patterns

### Validation Test
1. Compare with production patterns
2. Validate event frequencies
3. Check pattern quality
4. Document findings

---

## Success Criteria

### ✅ Test Execution
- All tests pass
- No errors or warnings
- Results JSON created
- Metrics calculated

### ✅ Event Generation
- Device-type-specific frequencies applied
- Events distributed correctly
- Realistic event patterns
- Appropriate event counts

### ✅ Pattern Detection
- Patterns detected successfully
- Realistic co-occurrences found
- Time-of-day patterns identified
- Metrics within expected ranges

---

## Ready to Test

**Current Status:** ✅ Implementation Complete

**Next Action:** Run quick test to validate

**Command:**
```bash
cd services/ai-automation-service
pytest tests/datasets/test_single_home_patterns.py::test_pattern_detection_individual_home -v
```

