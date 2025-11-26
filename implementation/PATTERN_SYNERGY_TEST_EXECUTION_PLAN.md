# Pattern & Synergy Test Execution Plan

**Date:** November 25, 2025  
**Status:** Planning

---

## Test Suite Overview

### Pattern Detection Tests

1. **Comprehensive Pattern Tests** (`tests/datasets/test_pattern_detection_comprehensive.py`)
   - `test_pattern_detection_accuracy_co_occurrence` - Co-occurrence pattern accuracy
   - `test_pattern_detection_accuracy_time_of_day` - Time-of-day pattern accuracy
   - `test_pattern_detection_accuracy_multi_factor` - Multi-factor pattern accuracy
   - `test_pattern_type_diversity` - Pattern type diversity validation
   - `test_pattern_detection_with_blueprint_validation` - Blueprint-validated patterns
   - `test_pattern_detection_on_multiple_datasets` - Multi-dataset testing

2. **Basic Pattern Tests** (`tests/datasets/test_pattern_detection_with_datasets.py`)
   - `test_dataset_loader_can_load_assist_mini` - Dataset loading validation
   - `test_pattern_detection_on_synthetic_home` - Basic pattern detection

3. **Single Home Pattern Tests** (`tests/datasets/test_single_home_patterns.py`)
   - Tests pattern detection on individual home datasets

4. **ML Pattern Detector Tests** (`tests/test_ml_pattern_detectors.py`)
   - ML-based pattern detection tests

### Synergy Detection Tests

1. **Comprehensive Synergy Tests** (`tests/datasets/test_synergy_detection_comprehensive.py`)
   - `test_synergy_detection_accuracy` - Synergy detection accuracy
   - `test_relationship_type_coverage` - All 16 relationship types
   - `test_motion_to_light_synergy` - Most common relationship
   - `test_door_to_lock_synergy` - Security-critical relationship
   - `test_synergy_pattern_validation` - Pattern validation integration
   - `test_multi_device_chain_detection` - 3-device and 4-device chains
   - `test_synergy_benefit_scoring` - Benefit score validation
   - `test_ml_discovered_synergies` - ML-discovered synergies
   - `test_synergy_detection_on_multiple_datasets` - Multi-dataset testing

2. **Synergy Detector Tests** (`tests/test_synergy_detector.py`)
   - Basic synergy detector functionality

3. **Synergy CRUD Tests** (`tests/test_synergy_crud.py`)
   - Database operations for synergies

4. **Synergy Suggestion Generator Tests** (`tests/test_synergy_suggestion_generator.py`)
   - Suggestion generation from synergies

---

## Execution Steps

### Step 1: Environment Setup

**Required Environment Variables:**
```bash
HA_URL=http://192.168.1.86:8123
HA_TOKEN=your_token_here
MQTT_BROKER=192.168.1.86
OPENAI_API_KEY=your_key_here
```

**Create `.env.test` file:**
```bash
# In services/ai-automation-service/
cp .env.example .env.test
# Edit .env.test with test values
```

### Step 2: Run Pattern Tests

```bash
# Run comprehensive pattern tests
pytest tests/datasets/test_pattern_detection_comprehensive.py -v

# Run basic pattern tests
pytest tests/datasets/test_pattern_detection_with_datasets.py -v

# Run single home pattern tests
pytest tests/datasets/test_single_home_patterns.py -v

# Run ML pattern detector tests
pytest tests/test_ml_pattern_detectors.py -v

# Run all pattern tests
pytest tests/datasets/test_pattern*.py tests/test_ml_pattern_detectors.py -v
```

### Step 3: Run Synergy Tests

```bash
# Run comprehensive synergy tests
pytest tests/datasets/test_synergy_detection_comprehensive.py -v

# Run synergy detector tests
pytest tests/test_synergy_detector.py -v

# Run synergy CRUD tests
pytest tests/test_synergy_crud.py -v

# Run synergy suggestion generator tests
pytest tests/test_synergy_suggestion_generator.py -v

# Run all synergy tests
pytest tests/datasets/test_synergy*.py tests/test_synergy*.py -v
```

### Step 4: Run All Pattern & Synergy Tests

```bash
# Run all pattern and synergy tests
pytest tests/datasets/test_pattern*.py tests/datasets/test_synergy*.py tests/test_ml_pattern_detectors.py tests/test_synergy*.py -v --tb=short

# With coverage
pytest tests/datasets/test_pattern*.py tests/datasets/test_synergy*.py tests/test_ml_pattern_detectors.py tests/test_synergy*.py -v --cov=src --cov-report=html
```

### Step 5: Generate Test Report

```bash
# Generate HTML report
pytest tests/datasets/test_pattern*.py tests/datasets/test_synergy*.py tests/test_ml_pattern_detectors.py tests/test_synergy*.py -v --html=test_report.html --self-contained-html

# Generate JSON report
pytest tests/datasets/test_pattern*.py tests/datasets/test_synergy*.py tests/test_ml_pattern_detectors.py tests/test_synergy*.py -v --json-report --json-report-file=test_report.json
```

---

## Expected Test Results

### Pattern Detection Metrics

**Target Metrics:**
- Precision: > 0.5 (50% of detected patterns are correct)
- Recall: > 0.6 (60% of expected patterns are found)
- F1 Score: > 0.55 (balanced precision/recall)

**Pattern Types:**
- Co-occurrence patterns
- Time-of-day patterns
- Multi-factor patterns
- Anomaly patterns

### Synergy Detection Metrics

**Target Metrics:**
- Precision: > 0.7 (70% of detected synergies are correct)
- Recall: > 0.6 (60% of expected synergies are found)
- F1 Score: > 0.65 (balanced precision/recall)

**Relationship Types (16 total):**
- motion_to_light (most common)
- door_to_lock (security-critical)
- temp_to_climate
- occupancy_to_light
- And 12 more...

---

## Test Execution Script

Create a script to run all tests and generate a report:

```python
# scripts/run_pattern_synergy_tests.py
import subprocess
import json
from datetime import datetime

def run_tests():
    """Run all pattern and synergy tests"""
    test_files = [
        "tests/datasets/test_pattern_detection_comprehensive.py",
        "tests/datasets/test_pattern_detection_with_datasets.py",
        "tests/datasets/test_single_home_patterns.py",
        "tests/test_ml_pattern_detectors.py",
        "tests/datasets/test_synergy_detection_comprehensive.py",
        "tests/test_synergy_detector.py",
        "tests/test_synergy_crud.py",
        "tests/test_synergy_suggestion_generator.py"
    ]
    
    results = {}
    for test_file in test_files:
        print(f"\n{'='*80}")
        print(f"Running: {test_file}")
        print(f"{'='*80}")
        
        result = subprocess.run(
            ["pytest", test_file, "-v", "--tb=short", "--json-report", "--json-report-file=temp_report.json"],
            capture_output=True,
            text=True
        )
        
        results[test_file] = {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
        
        # Try to parse JSON report
        try:
            with open("temp_report.json", "r") as f:
                report = json.load(f)
                results[test_file]["report"] = report
        except:
            pass
    
    # Generate summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for r in results.values() if r["returncode"] == 0)
    failed = len(results) - passed
    
    print(f"Total test files: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    return results

if __name__ == "__main__":
    results = run_tests()
    
    # Save results
    with open(f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
        json.dump(results, f, indent=2)
```

---

## Next Steps After Test Execution

1. **Analyze Results:**
   - Review test output
   - Identify failing tests
   - Calculate metrics (precision, recall, F1)
   - Compare with targets

2. **Create Enhancement Plan:**
   - Based on test results
   - Identify areas for improvement
   - Prioritize enhancements
   - Create implementation roadmap

3. **Document Findings:**
   - Test results summary
   - Metrics analysis
   - Enhancement recommendations
   - Implementation plan

---

## Notes

- Tests require environment variables (HA_URL, HA_TOKEN, etc.)
- Some tests may require Docker or full environment setup
- Dataset tests require home-assistant-datasets to be available
- ML tests may require additional dependencies

