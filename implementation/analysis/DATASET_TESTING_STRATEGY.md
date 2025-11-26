# Dataset Testing Strategy for Single-Home NUC Applications

## Executive Summary

**Recommended Approach: Hybrid Strategy**
- **Primary**: Test each home individually (matches production architecture)
- **Secondary**: Combined dataset for stress testing and fine-tuning
- **Validation**: Both approaches for comprehensive coverage

## Context

- **Deployment Model**: Single-home NUC (Intel NUC or similar)
- **Architecture**: All 24 microservices on one machine, single Home Assistant instance
- **Available Data**: 37 synthetic homes from devices-v2/v3 datasets
- **Testing Goals**: Pattern detection, synergy detection, automation generation, fine-tuning

---

## Option 1: Individual Home Testing (Recommended Primary)

### Approach
Test each of the 37 homes separately, one at a time.

### Process
```
For each home (1-37):
  1. Load home configuration
  2. Generate synthetic events (30-90 days)
  3. Inject events to InfluxDB
  4. Run pattern detection
  5. Run synergy detection
  6. Calculate metrics vs ground truth
  7. Store results
  8. Clean up test data
```

### Pros ✅

1. **Matches Production Architecture**
   - Single-home deployment = single-home testing
   - Realistic device counts (10-50 devices per home)
   - Realistic area structure (5-10 areas per home)
   - Tests actual production scenarios

2. **Easier Debugging**
   - Isolated failures (know which home failed)
   - Smaller datasets = faster analysis
   - Clear test boundaries
   - Easier to reproduce issues

3. **Better Metrics**
   - Per-home precision/recall/F1 scores
   - Identify homes where detection works well/poorly
   - Home-specific pattern analysis
   - Can track improvements per home type

4. **Realistic Patterns**
   - Patterns reflect actual single-home behavior
   - No artificial cross-home correlations
   - Area-based patterns are realistic
   - Device relationships are authentic

5. **Faster Individual Tests**
   - Smaller datasets = faster processing
   - Can parallelize across homes
   - Quick feedback loop
   - CI/CD friendly

### Cons ❌

1. **More Test Runs**
   - 37 separate test executions
   - More setup/teardown overhead
   - More test infrastructure needed

2. **May Miss Edge Cases**
   - Some patterns only appear with many devices
   - Limited device diversity per test
   - May not stress-test scalability

3. **More Complex Test Orchestration**
   - Need test runner for multiple homes
   - Results aggregation needed
   - More complex reporting

### Use Cases

- ✅ **Primary validation** - Test that system works for single homes
- ✅ **Regression testing** - Ensure changes don't break single-home scenarios
- ✅ **Accuracy benchmarking** - Measure precision/recall per home type
- ✅ **Production validation** - Verify system works like production

---

## Option 2: Combined Home Testing (Recommended Secondary)

### Approach
Merge all 37 homes into one large synthetic home with all devices.

### Process
```
1. Load all 37 home configurations
2. Merge devices (prefix with home ID to avoid conflicts)
3. Merge areas (prefix with home ID)
4. Generate synthetic events for combined home
5. Inject events to InfluxDB
6. Run pattern detection
7. Run synergy detection
8. Calculate metrics
```

### Pros ✅

1. **Large Dataset for Fine-Tuning**
   - 37 homes × 10-50 devices = 370-1,850 devices
   - Massive event volume (millions of events)
   - Rich diversity of device types
   - Better for ML model training

2. **Stress Testing**
   - Tests system with many devices
   - Validates scalability limits
   - Identifies performance bottlenecks
   - Tests memory/CPU under load

3. **Edge Case Discovery**
   - Rare patterns only visible with large datasets
   - Complex multi-device relationships
   - Cross-home pattern detection (if relevant)
   - Stress-test pattern deduplication

4. **Single Test Run**
   - One comprehensive test
   - Simpler test execution
   - Single result set

### Cons ❌

1. **Not Realistic**
   - Production is single-home, not 37-home mega-home
   - Artificial device relationships
   - Unrealistic area structures
   - May create false patterns

2. **Harder to Debug**
   - Large dataset = harder to trace issues
   - Patterns may be artifacts of combination
   - Difficult to identify root causes
   - Complex result analysis

3. **False Patterns**
   - Devices from different homes may correlate artificially
   - Area relationships don't make sense
   - May detect patterns that don't exist in reality
   - Cross-home correlations are meaningless

4. **Resource Intensive**
   - Large dataset = more memory/CPU
   - Slower test execution
   - More storage needed
   - May hit system limits

### Use Cases

- ✅ **Fine-tuning ML models** - Large dataset for training
- ✅ **Stress testing** - Validate system limits
- ✅ **Performance benchmarking** - Test with large datasets
- ✅ **Edge case discovery** - Find rare patterns

---

## Recommended Hybrid Strategy

### Phase 1: Individual Home Testing (Primary)

**Purpose**: Validate single-home functionality (matches production)

**Implementation**:
```python
# Test runner for individual homes
@pytest.mark.parametrize("home_name", get_all_homes())
async def test_pattern_detection_single_home(home_name):
    """Test pattern detection on individual home"""
    # Load home
    # Generate events
    # Detect patterns
    # Validate against ground truth
    # Store metrics
```

**Metrics Collected**:
- Per-home precision/recall/F1
- Pattern detection accuracy
- Synergy detection accuracy
- Processing time per home
- Memory usage per home

**Benefits**:
- Validates production-like scenarios
- Identifies homes where detection works well/poorly
- Provides realistic accuracy metrics
- Easy to debug failures

### Phase 2: Combined Dataset Testing (Secondary)

**Purpose**: Fine-tuning and stress testing

**Implementation**:
```python
async def test_pattern_detection_combined_homes():
    """Test with all homes combined for fine-tuning"""
    # Load all homes
    # Merge devices/areas
    # Generate large event dataset
    # Run detection
    # Use for fine-tuning ML models
```

**Use Cases**:
- Fine-tune ML pattern detectors
- Stress test system limits
- Discover rare patterns
- Performance benchmarking

### Phase 3: Stratified Testing

**Purpose**: Test different home types and sizes

**Group Homes By**:
- **Size**: Small (10-20 devices), Medium (20-40), Large (40+)
- **Type**: Single-family, Apartment, Multi-story
- **Device Diversity**: High (many types), Low (few types)
- **Area Count**: Few (3-5), Many (8-12)

**Test Strategy**:
```python
# Test representative homes from each group
test_homes = {
    'small': ['home1-us', 'home2-dk'],
    'medium': ['home5-us', 'home7-dk'],
    'large': ['home10-us', 'home15-dk']
}
```

---

## Implementation Recommendations

### 1. Test Structure

```
tests/datasets/
├── test_single_home_patterns.py      # Individual home tests
├── test_combined_home_patterns.py    # Combined home tests
├── test_stratified_patterns.py        # Stratified testing
└── conftest.py                       # Shared fixtures
```

### 2. Test Execution

**Individual Homes** (Primary):
```bash
# Run all individual home tests
pytest tests/datasets/test_single_home_patterns.py -v

# Run specific home
pytest tests/datasets/test_single_home_patterns.py::test_home1_us -v

# Parallel execution
pytest tests/datasets/test_single_home_patterns.py -n auto
```

**Combined Homes** (Secondary):
```bash
# Run combined home test (for fine-tuning)
pytest tests/datasets/test_combined_home_patterns.py -v -m "fine_tuning"
```

### 3. Metrics Collection

**Per-Home Metrics**:
```python
{
    "home": "home1-us",
    "devices": 12,
    "areas": 6,
    "events": 3000,
    "patterns_detected": 8,
    "patterns_expected": 10,
    "precision": 0.85,
    "recall": 0.80,
    "f1": 0.82,
    "processing_time_seconds": 2.3
}
```

**Aggregated Metrics**:
```python
{
    "total_homes": 37,
    "avg_precision": 0.84,
    "avg_recall": 0.79,
    "avg_f1": 0.81,
    "homes_above_threshold": 32,
    "homes_below_threshold": 5
}
```

### 4. Fine-Tuning Workflow

```python
# 1. Individual home testing (validation)
results = run_individual_home_tests()

# 2. Identify homes with low accuracy
low_accuracy_homes = [h for h in results if h['f1'] < 0.75]

# 3. Combined dataset fine-tuning
combined_data = load_all_homes()
fine_tuned_model = fine_tune_on_combined_data(combined_data)

# 4. Re-test individual homes
improved_results = run_individual_home_tests(model=fine_tuned_model)

# 5. Validate improvement
assert avg_f1_improved(improved_results) > avg_f1(results)
```

---

## Decision Matrix

| Criteria | Individual Homes | Combined Homes | Winner |
|----------|----------------|----------------|--------|
| **Matches Production** | ✅ Yes | ❌ No | Individual |
| **Realistic Patterns** | ✅ Yes | ❌ No | Individual |
| **Easy Debugging** | ✅ Yes | ❌ No | Individual |
| **Fine-Tuning Data** | ⚠️ Limited | ✅ Excellent | Combined |
| **Stress Testing** | ⚠️ Limited | ✅ Excellent | Combined |
| **Test Speed** | ✅ Fast | ❌ Slow | Individual |
| **Accuracy Metrics** | ✅ Per-home | ⚠️ Aggregate | Individual |
| **Edge Cases** | ⚠️ Limited | ✅ Many | Combined |

**Verdict**: Use **Individual Homes** as primary, **Combined Homes** as secondary.

---

## Recommended Test Plan

### Daily/CI Testing
- ✅ Run individual home tests (sample: 5-10 representative homes)
- ✅ Fast feedback (< 5 minutes)
- ✅ Validates production-like scenarios

### Weekly Testing
- ✅ Run all 37 individual home tests
- ✅ Comprehensive validation
- ✅ Track metrics over time

### Fine-Tuning Cycles
- ✅ Use combined dataset for ML model training
- ✅ Re-validate on individual homes
- ✅ Measure improvement

### Stress Testing
- ✅ Periodic combined home tests
- ✅ Validate system limits
- ✅ Performance benchmarking

---

## Conclusion

**For Single-Home NUC Applications:**

1. **Primary Testing**: Individual homes (matches production)
   - Validates realistic scenarios
   - Easier debugging
   - Better metrics
   - Faster execution

2. **Secondary Testing**: Combined homes (fine-tuning/stress)
   - Large dataset for ML training
   - Stress testing
   - Edge case discovery

3. **Best Practice**: Hybrid approach
   - Individual homes for validation
   - Combined homes for fine-tuning
   - Both for comprehensive coverage

**Recommended Split**:
- 80% individual home testing (validation)
- 20% combined home testing (fine-tuning/stress)

This ensures your system works correctly for single-home deployments (production) while also benefiting from large-scale data for model improvement.

