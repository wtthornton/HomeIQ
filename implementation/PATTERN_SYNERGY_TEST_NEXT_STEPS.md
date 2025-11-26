# Pattern & Synergy Test Execution - Next Steps

**Date:** November 25, 2025  
**Status:** Ready for Execution

---

## Quick Start Guide

### Step 1: Environment Setup

**Option A: Create .env.test file**
```bash
cd services/ai-automation-service
cp .env.example .env.test
# Edit .env.test with test values:
# HA_URL=http://192.168.1.86:8123
# HA_TOKEN=your_token_here
# MQTT_BROKER=192.168.1.86
# OPENAI_API_KEY=your_key_here
```

**Option B: Set Environment Variables**
```powershell
$env:HA_URL = "http://192.168.1.86:8123"
$env:HA_TOKEN = "your_token_here"
$env:MQTT_BROKER = "192.168.1.86"
$env:OPENAI_API_KEY = "your_key_here"
```

### Step 2: Run Tests

**Using the Test Runner Script:**
```bash
# From project root
python scripts/run_pattern_synergy_tests.py

# Pattern tests only
python scripts/run_pattern_synergy_tests.py --pattern-only

# Synergy tests only
python scripts/run_pattern_synergy_tests.py --synergy-only

# With JSON report
python scripts/run_pattern_synergy_tests.py --output test_results.json
```

**Using pytest directly:**
```bash
cd services/ai-automation-service

# All pattern and synergy tests
pytest tests/datasets/test_pattern*.py tests/datasets/test_synergy*.py tests/test_ml_pattern_detectors.py tests/test_synergy*.py -v

# Pattern tests only
pytest tests/datasets/test_pattern*.py tests/test_ml_pattern_detectors.py -v

# Synergy tests only
pytest tests/datasets/test_synergy*.py tests/test_synergy*.py -v
```

### Step 3: Analyze Results

After running tests, review:
1. Test execution summary
2. Failed tests (if any)
3. Metrics (precision, recall, F1)
4. Test coverage

### Step 4: Update Enhancement Plan

Update `implementation/PATTERN_SYNERGY_ENHANCEMENT_PLAN.md` with:
- Specific test results
- Metrics analysis
- Identified issues
- Prioritized enhancements

---

## Test Files Overview

### Pattern Detection Tests

1. **test_pattern_detection_comprehensive.py**
   - Comprehensive pattern detection with metrics
   - Co-occurrence, time-of-day, multi-factor patterns
   - Ground truth validation

2. **test_pattern_detection_with_datasets.py**
   - Basic pattern detection tests
   - Dataset loading validation

3. **test_single_home_patterns.py**
   - Single home dataset testing
   - Pattern detection on individual homes

4. **test_ml_pattern_detectors.py**
   - ML-based pattern detection
   - Sequence and contextual detectors

### Synergy Detection Tests

1. **test_synergy_detection_comprehensive.py**
   - Comprehensive synergy detection
   - All 16 relationship types
   - Pattern validation integration

2. **test_synergy_detector.py**
   - Basic synergy detector functionality
   - Confidence and impact scoring

3. **test_synergy_crud.py**
   - Database operations for synergies

4. **test_synergy_suggestion_generator.py**
   - Suggestion generation from synergies

---

## Expected Output

### Test Results Format

```
🧪 Pattern & Synergy Test Runner
================================================================================
Running: tests/datasets/test_pattern_detection_comprehensive.py
================================================================================
...

================================================================================
TEST EXECUTION SUMMARY
================================================================================
Total test files: 8
✅ Passed: 6
❌ Failed: 2
Timestamp: 2025-11-25T10:30:00
```

### Metrics to Collect

**Pattern Detection:**
- Precision (TP / (TP + FP))
- Recall (TP / (TP + FN))
- F1 Score (2 * (Precision * Recall) / (Precision + Recall))
- Pattern count vs expected count

**Synergy Detection:**
- Precision
- Recall
- F1 Score
- Relationship type coverage
- Pattern validation rate

---

## Enhancement Plan Update Process

After test execution:

1. **Document Results:**
   - Add test results to enhancement plan
   - Include metrics in plan
   - Document failures

2. **Prioritize Enhancements:**
   - Based on test results
   - Impact vs effort analysis
   - User value consideration

3. **Create Implementation Tasks:**
   - Break down enhancements
   - Estimate effort
   - Assign priorities

4. **Track Progress:**
   - Update plan as work progresses
   - Re-run tests after changes
   - Measure improvements

---

## Files Created

1. **scripts/run_pattern_synergy_tests.py**
   - Test runner script
   - Environment checking
   - Report generation

2. **implementation/PATTERN_SYNERGY_TEST_EXECUTION_PLAN.md**
   - Detailed test execution guide
   - Environment setup instructions
   - Test suite overview

3. **implementation/PATTERN_SYNERGY_ENHANCEMENT_PLAN.md**
   - Enhancement plan template
   - Expected areas for improvement
   - Implementation roadmap

4. **implementation/PATTERN_SYNERGY_TEST_NEXT_STEPS.md** (this file)
   - Quick start guide
   - Next steps summary

---

## Ready to Execute

All planning documents are ready. Next steps:

1. ✅ Test execution plan created
2. ✅ Test runner script created
3. ✅ Enhancement plan template created
4. ⏳ Execute tests (requires environment setup)
5. ⏳ Analyze results
6. ⏳ Update enhancement plan with findings
7. ⏳ Begin implementation

---

## Notes

- Tests require environment variables (HA_URL, HA_TOKEN, etc.)
- Some tests may require Docker or full environment setup
- Dataset tests require home-assistant-datasets to be available
- Test results will guide the specific enhancement priorities

