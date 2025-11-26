# Individual Home Testing Guide

## Overview

This test suite validates pattern and synergy detection on individual synthetic homes, matching the production architecture (single-home NUC deployments).

## Test Structure

### `test_single_home_patterns.py`

- **Auto-discovers** all 37 homes from `devices-v2` and `devices-v3` datasets
- **Parametrized tests** - runs each home separately
- **Two test modes**:
  - `test_pattern_detection_individual_home` - Tests 5 representative homes (quick)
  - `test_pattern_detection_all_homes` - Tests all 37 homes (comprehensive, marked `@pytest.mark.slow`)

## Usage

### Quick Test (5 Representative Homes)

```bash
# From project root
cd services/ai-automation-service
pytest tests/datasets/test_single_home_patterns.py::test_pattern_detection_individual_home -v
```

### Comprehensive Test (All 37 Homes)

```bash
# Run all homes (slow - may take 30+ minutes)
pytest tests/datasets/test_single_home_patterns.py::test_pattern_detection_all_homes -v

# Or skip slow tests
pytest tests/datasets/test_single_home_patterns.py -m "not slow" -v
```

### Parallel Execution

```bash
# Install pytest-xdist first
pip install pytest-xdist

# Run tests in parallel
pytest tests/datasets/test_single_home_patterns.py -n auto -v
```

### Test Specific Home

```bash
# Test a specific home
pytest tests/datasets/test_single_home_patterns.py::test_pattern_detection_individual_home -k "home1-us" -v
```

## Configuration

### Environment Variables

The test uses these environment variables (with defaults):

- `INFLUXDB_URL` - Default: `http://localhost:8086`
- `INFLUXDB_TOKEN` - Default: `homeiq-token`
- `INFLUXDB_ORG` - Default: `homeiq`
- `INFLUXDB_TEST_BUCKET` - Default: `home_assistant_events_test`

### Test Bucket Setup

The test uses a separate InfluxDB bucket (`home_assistant_events_test`) for isolation.

**Create test bucket** (if not exists):
```bash
docker exec homeiq-influxdb influx bucket create \
  --name home_assistant_events_test \
  --org homeiq \
  --token <your-token> \
  --retention 7d
```

Or via Docker Compose (add to `docker-compose.yml`):
```yaml
influxdb:
  environment:
    DOCKER_INFLUXDB_INIT_BUCKET: home_assistant_events_test
```

## Test Flow

1. **Load Home Configuration**
   - Reads YAML from `devices-v2/` or `devices-v3/`
   - Extracts devices, areas, and metadata
   - Converts to Home Assistant entity format

2. **Generate Synthetic Events**
   - Generates 30 days × 50 events/day = 1,500 events
   - Events include state changes, timestamps, attributes
   - Realistic device interactions (motion → light, etc.)

3. **Inject Events to InfluxDB**
   - Writes events to test bucket
   - Validates write success

4. **Fetch Events from Data API**
   - Retrieves events from InfluxDB via Data API
   - Validates event retrieval

5. **Run Pattern Detection**
   - Co-occurrence pattern detection
   - Time-of-day pattern detection
   - Collects detected patterns

6. **Calculate Metrics** (if ground truth available)
   - Precision, Recall, F1 Score
   - True Positives, False Positives, False Negatives
   - Compares detected vs. expected patterns

7. **Store Results**
   - Per-home metrics stored in `pytest.home_test_results`
   - Results aggregated and saved to JSON after all tests

## Results

### Per-Home Results

Each test stores:
```json
{
  "home": "home1-us",
  "dataset": "devices-v2",
  "devices": 12,
  "areas": 8,
  "events_generated": 1500,
  "events_injected": 1500,
  "events_fetched": 1500,
  "patterns_detected": 8,
  "tod_patterns_detected": 3,
  "expected_patterns": 10,
  "expected_synergies": 5,
  "metrics": {
    "precision": 0.85,
    "recall": 0.80,
    "f1": 0.82,
    "tp": 8,
    "fp": 2,
    "fn": 2
  },
  "timestamp": "2025-11-25T00:00:00Z"
}
```

### Aggregated Results

After all tests complete, results are saved to:
```
tests/datasets/results/home_test_results_YYYYMMDD_HHMMSS.json
```

Aggregated metrics include:
- Total homes tested
- Average precision/recall/F1
- Total devices, events, patterns
- Individual home results

## Troubleshooting

### InfluxDB Authentication Error

**Error**: `401 Unauthorized`

**Solution**:
1. Check InfluxDB token in environment
2. Verify bucket exists
3. Check InfluxDB is running: `docker ps | grep influxdb`

### No Homes Found

**Error**: `Home file not found`

**Solution**:
1. Ensure `home-assistant-datasets` is cloned
2. Check path: `services/tests/datasets/home-assistant-datasets/datasets/`
3. Verify `devices-v2/` and `devices-v3/` directories exist

### No Events Generated

**Error**: `No devices found in home_data`

**Solution**:
- Some datasets may not have device definitions
- Check dataset structure matches expected format
- Verify YAML parsing is working

### Pattern Detection Returns 0 Patterns

**Possible Causes**:
- Not enough events (increase `days` or `events_per_day`)
- Events don't have realistic relationships
- Pattern detection thresholds too high
- Check pattern detector configuration

## Best Practices

1. **Start with Representative Homes**
   - Test 5 homes first to validate setup
   - Then run comprehensive test on all 37 homes

2. **Use Test Bucket**
   - Always use `home_assistant_events_test` bucket
   - Keeps test data separate from production

3. **Monitor Resource Usage**
   - Large tests (all 37 homes) can be resource-intensive
   - Consider running in CI/CD with resource limits

4. **Review Results**
   - Check aggregated metrics for overall performance
   - Identify homes with low accuracy for investigation
   - Use results to fine-tune pattern detection algorithms

5. **Parallel Execution**
   - Use `pytest-xdist` for faster execution
   - Be mindful of InfluxDB connection limits

## Integration with CI/CD

### GitHub Actions Example

```yaml
- name: Run Individual Home Tests
  run: |
    cd services/ai-automation-service
    pytest tests/datasets/test_single_home_patterns.py::test_pattern_detection_individual_home -v
    
- name: Upload Test Results
  uses: actions/upload-artifact@v3
  if: always()
  with:
    name: home-test-results
    path: services/ai-automation-service/tests/datasets/results/
```

## Next Steps

1. **Fine-Tuning**: Use results to improve pattern detection algorithms
2. **Combined Testing**: Run combined home tests for ML model training
3. **Stratified Testing**: Group homes by size/type for targeted testing
4. **Continuous Improvement**: Track metrics over time to measure improvements

