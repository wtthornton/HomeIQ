# Energy Correlator Service - Test Plan

**Service:** energy-correlator (Port 8017)
**Priority:** HIGH - Critical processing service with complex correlation algorithms
**Current Coverage:** ~70% (9 test files, ~90 tests across unit and integration)
**Target Coverage:** >70%

---

## Overview

The energy-correlator service analyzes relationships between Home Assistant events and power consumption changes. It's a critical service for energy optimization insights and has complex algorithmic logic that requires comprehensive testing.

### Key Responsibilities
1. Query InfluxDB for recent HA events (last 5 minutes)
2. Correlate events with power consumption changes (±10 second window)
3. Calculate power deltas and percentage changes
4. Write correlations back to InfluxDB
5. Track statistics and health metrics
6. Expose HTTP API for health and statistics

---

## Test Structure

```
services/energy-correlator/
├── tests/
│   ├── conftest.py                      # Shared fixtures
│   ├── unit/
│   │   ├── test_correlator_logic.py     # Core correlation algorithms
│   │   ├── test_statistics.py           # Statistics tracking
│   │   ├── test_configuration.py        # Config validation
│   │   └── test_power_delta.py          # Power calculation logic
│   ├── integration/
│   │   ├── test_influxdb_queries.py     # InfluxDB read/write
│   │   ├── test_api_endpoints.py        # HTTP endpoints
│   │   └── test_event_processing.py     # End-to-end event flow
│   └── performance/
│       └── test_correlation_speed.py    # Performance benchmarks
└── pytest.ini                           # Test configuration
```

---

## 1. Unit Tests

### 1.1 Correlation Logic (HIGH PRIORITY)

**File:** `tests/unit/test_correlator_logic.py`

**Test Cases:**

```python
class TestCorrelationLogic:
    """Test core correlation algorithm logic"""

    async def test_power_delta_calculation():
        """
        GIVEN: Power before (2450W) and after (2510W)
        WHEN: Calculate delta
        THEN: Delta should be +60W
        """

    async def test_power_delta_percentage():
        """
        GIVEN: Power before (1850W) and after (4350W)
        WHEN: Calculate percentage change
        THEN: Percentage should be +135%
        """

    async def test_negative_power_delta():
        """
        GIVEN: Light turning off (2150W → 2030W)
        WHEN: Calculate delta
        THEN: Delta should be -120W (-5.6%)
        """

    async def test_min_power_delta_threshold():
        """
        GIVEN: Small power change (5W)
        WHEN: Apply threshold (10W minimum)
        THEN: Correlation should be skipped
        """

    async def test_significant_power_change():
        """
        GIVEN: Power change of 50W
        WHEN: Apply threshold (10W minimum)
        THEN: Correlation should be created
        """

    async def test_zero_power_before():
        """
        GIVEN: Power before is 0W
        WHEN: Calculate percentage change
        THEN: Should handle division by zero gracefully (return 0%)
        """

    async def test_correlation_window_boundaries():
        """
        GIVEN: Event at T0, power readings at T-5s and T+5s
        WHEN: Query power within correlation window
        THEN: Should find both readings
        """

    async def test_missing_power_data_before():
        """
        GIVEN: No power reading 5s before event
        WHEN: Attempt correlation
        THEN: Should skip correlation gracefully
        """

    async def test_missing_power_data_after():
        """
        GIVEN: No power reading 5s after event
        WHEN: Attempt correlation
        THEN: Should skip correlation gracefully
        """
```

**Coverage Target:** All calculation paths in `correlator.py:186-208`

---

### 1.2 Statistics Tracking

**File:** `tests/unit/test_statistics.py`

**Test Cases:**

```python
class TestStatistics:
    """Test statistics tracking and reporting"""

    def test_initial_statistics():
        """
        GIVEN: New correlator instance
        WHEN: Get statistics
        THEN: All counters should be 0
        """

    async def test_event_counter_increment():
        """
        GIVEN: Process 10 events
        WHEN: Check total_events_processed
        THEN: Should be 10
        """

    async def test_correlation_rate_calculation():
        """
        GIVEN: 100 events processed, 15 correlations found
        WHEN: Calculate correlation_rate_pct
        THEN: Should be 15.0%
        """

    async def test_write_success_rate():
        """
        GIVEN: 15 correlations found, 15 written
        WHEN: Calculate write_success_rate_pct
        THEN: Should be 100.0%
        """

    async def test_write_failure_tracking():
        """
        GIVEN: 15 correlations found, 12 written (3 failures)
        WHEN: Calculate write_success_rate_pct
        THEN: Should be 80.0%
        """

    def test_statistics_reset():
        """
        GIVEN: Correlator with existing statistics
        WHEN: Call reset_statistics()
        THEN: All counters should return to 0
        """

    async def test_error_counter():
        """
        GIVEN: 3 InfluxDB write errors
        WHEN: Check errors counter
        THEN: Should be 3
        """
```

**Coverage Target:** All methods in `correlator.py:294-327`

---

### 1.3 Configuration Validation

**File:** `tests/unit/test_configuration.py`

**Test Cases:**

```python
class TestConfiguration:
    """Test service configuration and validation"""

    def test_missing_influxdb_token():
        """
        GIVEN: No INFLUXDB_TOKEN environment variable
        WHEN: Initialize service
        THEN: Should raise ValueError
        """

    def test_default_processing_interval():
        """
        GIVEN: No PROCESSING_INTERVAL set
        WHEN: Initialize service
        THEN: Should default to 60 seconds
        """

    def test_custom_processing_interval():
        """
        GIVEN: PROCESSING_INTERVAL=300
        WHEN: Initialize service
        THEN: Should use 300 seconds
        """

    def test_default_lookback_minutes():
        """
        GIVEN: No LOOKBACK_MINUTES set
        WHEN: Initialize service
        THEN: Should default to 5 minutes
        """

    def test_correlation_window_configuration():
        """
        GIVEN: Default correlator instance
        WHEN: Check correlation_window_seconds
        THEN: Should be 10 seconds
        """

    def test_min_power_delta_configuration():
        """
        GIVEN: Default correlator instance
        WHEN: Check min_power_delta
        THEN: Should be 10.0W
        """
```

**Coverage Target:** `main.py:30-58` and `correlator.py:23-44`

---

## 2. Integration Tests

### 2.1 InfluxDB Interactions (HIGH PRIORITY)

**File:** `tests/integration/test_influxdb_queries.py`

**Test Cases:**

```python
class TestInfluxDBQueries:
    """Test InfluxDB query and write operations"""

    @pytest.fixture
    async def mock_influxdb():
        """Mock InfluxDB client for testing"""
        # Return mock client with test data

    async def test_query_recent_events():
        """
        GIVEN: InfluxDB with 100 events in last 5 minutes
        WHEN: Query recent events
        THEN: Should return all 100 events
        """

    async def test_query_event_domain_filter():
        """
        GIVEN: Events from multiple domains (switch, light, sensor)
        WHEN: Query for correlation-eligible domains
        THEN: Should return only switch, light, climate, fan, cover events
        """

    async def test_query_empty_results():
        """
        GIVEN: No events in InfluxDB
        WHEN: Query recent events
        THEN: Should return empty list gracefully
        """

    async def test_get_power_at_time():
        """
        GIVEN: Power reading at specific timestamp
        WHEN: Query power at that time (±30s window)
        THEN: Should return correct power value
        """

    async def test_get_power_missing_data():
        """
        GIVEN: No power readings in time window
        WHEN: Query power at time
        THEN: Should return None
        """

    async def test_write_correlation_point():
        """
        GIVEN: Valid correlation data
        WHEN: Write to InfluxDB
        THEN: Point should be written with correct tags and fields
        """

    async def test_write_correlation_with_tags():
        """
        GIVEN: Correlation for switch.living_room_lamp
        WHEN: Write to InfluxDB
        THEN: Should include tags: entity_id, domain, state, previous_state
        """

    async def test_write_correlation_with_fields():
        """
        GIVEN: Correlation with power delta
        WHEN: Write to InfluxDB
        THEN: Should include fields: power_before_w, power_after_w, power_delta_w, power_delta_pct
        """

    async def test_influxdb_connection_retry():
        """
        GIVEN: InfluxDB temporarily unavailable
        WHEN: Service attempts connection
        THEN: Should retry gracefully
        """

    async def test_influxdb_write_error_handling():
        """
        GIVEN: InfluxDB write failure
        WHEN: Attempt to write correlation
        THEN: Should log error and increment error counter
        """
```

**Coverage Target:** All InfluxDB interactions in `correlator.py:104-154, 210-248, 250-293`

---

### 2.2 API Endpoints

**File:** `tests/integration/test_api_endpoints.py`

**Test Cases:**

```python
class TestAPIEndpoints:
    """Test HTTP API endpoints"""

    @pytest.fixture
    async def test_client():
        """Create test HTTP client"""
        # Return aiohttp test client

    async def test_health_endpoint():
        """
        GIVEN: Running service
        WHEN: GET /health
        THEN: Should return 200 with health status
        """

    async def test_health_response_structure():
        """
        GIVEN: Running service
        WHEN: GET /health
        THEN: Response should include: status, service, uptime_seconds, last_successful_fetch
        """

    async def test_statistics_endpoint():
        """
        GIVEN: Service with processing history
        WHEN: GET /statistics
        THEN: Should return correlation statistics
        """

    async def test_statistics_response_structure():
        """
        GIVEN: Service with statistics
        WHEN: GET /statistics
        THEN: Response should include: total_events_processed, correlations_found, correlation_rate_pct
        """

    async def test_reset_statistics_endpoint():
        """
        GIVEN: Service with existing statistics
        WHEN: POST /statistics/reset
        THEN: Should reset all counters to 0
        """

    async def test_reset_statistics_response():
        """
        GIVEN: Statistics reset request
        WHEN: POST /statistics/reset
        THEN: Should return {"message": "Statistics reset"}
        """

    async def test_health_check_after_errors():
        """
        GIVEN: Service with failed fetches
        WHEN: GET /health
        THEN: Should report failed_fetches > 0 and success_rate < 1.0
        """
```

**Coverage Target:** All endpoints in `main.py:124-147`

---

### 2.3 End-to-End Event Processing

**File:** `tests/integration/test_event_processing.py`

**Test Cases:**

```python
class TestEventProcessing:
    """Test complete event processing pipeline"""

    async def test_process_single_event():
        """
        GIVEN: Single switch.on event with power change
        WHEN: Process event
        THEN: Should create one correlation
        """

    async def test_process_multiple_events():
        """
        GIVEN: 10 events in InfluxDB
        WHEN: Process recent events
        THEN: Should process all 10 events
        """

    async def test_process_only_eligible_domains():
        """
        GIVEN: Mix of switch, sensor, and binary_sensor events
        WHEN: Process recent events
        THEN: Should only process switch events
        """

    async def test_skip_small_power_changes():
        """
        GIVEN: Event with 5W power change (below threshold)
        WHEN: Process event
        THEN: Should skip correlation
        """

    async def test_correlate_hvac_event():
        """
        GIVEN: HVAC turning on with 2500W power increase
        WHEN: Process event
        THEN: Should create correlation with large power_delta
        """

    async def test_correlate_light_off_event():
        """
        GIVEN: Light turning off with 120W decrease
        WHEN: Process event
        THEN: Should create correlation with negative power_delta
        """

    async def test_continuous_processing_loop():
        """
        GIVEN: Service running continuous loop
        WHEN: Wait for 2 processing cycles
        THEN: Should process events twice
        """

    async def test_error_recovery():
        """
        GIVEN: InfluxDB query error
        WHEN: Processing loop continues
        THEN: Should log error, wait 60s, and retry
        """
```

**Coverage Target:** Complete flow from `main.py:86-122` through `correlator.py:71-102`

---

## 3. Performance Tests

### 3.1 Correlation Speed Benchmarks

**File:** `tests/performance/test_correlation_speed.py`

**Test Cases:**

```python
class TestCorrelationPerformance:
    """Performance benchmarks for correlation processing"""

    @pytest.mark.slow
    async def test_process_100_events_speed():
        """
        GIVEN: 100 events to process
        WHEN: Process all events
        THEN: Should complete in < 5 seconds
        Target: ~200-500 events/second
        """

    @pytest.mark.slow
    async def test_process_1000_events_speed():
        """
        GIVEN: 1000 events to process
        WHEN: Process all events
        THEN: Should complete in < 30 seconds
        """

    @pytest.mark.slow
    async def test_influxdb_query_performance():
        """
        GIVEN: Query for 5 minutes of events
        WHEN: Execute query
        THEN: Should complete in < 50ms
        """

    @pytest.mark.slow
    async def test_power_lookup_performance():
        """
        GIVEN: Single power lookup query
        WHEN: Get power at time
        THEN: Should complete in < 50ms
        """

    @pytest.mark.slow
    async def test_write_batch_performance():
        """
        GIVEN: 100 correlations to write
        WHEN: Write all correlations
        THEN: Should complete in < 2 seconds
        """

    @pytest.mark.slow
    async def test_memory_usage():
        """
        GIVEN: Processing 10,000 events
        WHEN: Monitor memory usage
        THEN: Should stay below 100MB
        """
```

**Performance Targets (from README.md):**
- Events per second: 200-500
- InfluxDB query time: <50ms
- Total cycle time: 2-5 seconds per iteration
- Memory usage: 50-100MB

---

## 4. Error Handling Tests

### 4.1 Resilience Testing

**File:** `tests/unit/test_error_handling.py`

**Test Cases:**

```python
class TestErrorHandling:
    """Test error handling and resilience"""

    async def test_influxdb_connection_failure():
        """
        GIVEN: InfluxDB unavailable
        WHEN: Service starts
        THEN: Should raise exception with clear error message
        """

    async def test_query_timeout():
        """
        GIVEN: InfluxDB query timeout
        WHEN: Query events
        THEN: Should handle timeout gracefully
        """

    async def test_malformed_event_data():
        """
        GIVEN: Event with missing entity_id
        WHEN: Process event
        THEN: Should skip event and log warning
        """

    async def test_invalid_power_value():
        """
        GIVEN: Power reading with non-numeric value
        WHEN: Calculate delta
        THEN: Should handle gracefully and skip
        """

    async def test_write_failure_recovery():
        """
        GIVEN: InfluxDB write failure
        WHEN: Continue processing
        THEN: Should log error, increment counter, continue
        """

    async def test_continuous_loop_exception_recovery():
        """
        GIVEN: Exception in processing loop
        WHEN: Exception occurs
        THEN: Should log error, wait 60s, continue loop
        """
```

---

## 5. Test Fixtures

### 5.1 Shared Fixtures (conftest.py)

```python
# tests/conftest.py

import pytest
from datetime import datetime, timedelta
from typing import List, Dict

@pytest.fixture
def mock_influxdb_client():
    """Mock InfluxDB client for testing"""
    from unittest.mock import AsyncMock, MagicMock

    client = MagicMock()
    client.query = AsyncMock()
    client.write_points = MagicMock()
    client.connect = MagicMock()
    client.close = MagicMock()

    return client

@pytest.fixture
def sample_events() -> List[Dict]:
    """Sample HA events for testing"""
    now = datetime.utcnow()

    return [
        {
            'time': now - timedelta(seconds=30),
            'entity_id': 'switch.living_room_lamp',
            'domain': 'switch',
            'state': 'on',
            'previous_state': 'off'
        },
        {
            'time': now - timedelta(seconds=60),
            'entity_id': 'climate.living_room',
            'domain': 'climate',
            'state': 'heating',
            'previous_state': 'idle'
        },
        {
            'time': now - timedelta(seconds=90),
            'entity_id': 'light.bedroom',
            'domain': 'light',
            'state': 'off',
            'previous_state': 'on'
        }
    ]

@pytest.fixture
def sample_power_data() -> Dict:
    """Sample power readings for testing"""
    return {
        'before': 2450.0,
        'after': 2510.0,
        'delta': 60.0,
        'delta_pct': 2.45
    }

@pytest.fixture
async def correlator_instance(mock_influxdb_client):
    """Create correlator instance with mocked dependencies"""
    from src.correlator import EnergyEventCorrelator

    correlator = EnergyEventCorrelator(
        influxdb_url='http://test-influxdb:8086',
        influxdb_token='test-token',
        influxdb_org='test-org',
        influxdb_bucket='test-bucket'
    )

    # Inject mock client
    correlator.client = mock_influxdb_client

    return correlator

@pytest.fixture
async def service_instance():
    """Create service instance for integration testing"""
    from src.main import EnergyCorrelatorService
    import os

    # Set test environment
    os.environ['INFLUXDB_TOKEN'] = 'test-token'
    os.environ['PROCESSING_INTERVAL'] = '10'  # Faster for tests
    os.environ['LOOKBACK_MINUTES'] = '5'

    service = EnergyCorrelatorService()

    yield service

    # Cleanup
    await service.shutdown()
```

---

## 6. Test Execution Plan

### 6.1 Local Development

```bash
# Run all tests
cd services/energy-correlator
pytest

# Run unit tests only
pytest tests/unit -v

# Run integration tests
pytest tests/integration -v

# Run with coverage
pytest --cov=src --cov-report=html --cov-report=term

# Run performance tests
pytest tests/performance -m slow -v

# Run specific test file
pytest tests/unit/test_correlator_logic.py -v
```

### 6.2 CI/CD Integration

The new GitHub Actions workflow (`.github/workflows/test.yml`) will automatically:
1. Run all tests on PR
2. Generate coverage reports
3. Upload coverage to Codecov
4. Fail build if tests fail

---

## 7. Priority & Timeline

### Week 1 (Immediate)
1. Create test directory structure
2. Write `conftest.py` with shared fixtures
3. Implement unit tests for correlation logic (1.1)
4. Implement statistics tests (1.2)
5. Target: 40% coverage

### Week 2 (Short Term)
1. Implement configuration tests (1.3)
2. Implement InfluxDB integration tests (2.1)
3. Implement API endpoint tests (2.2)
4. Target: 70% coverage

### Week 3 (Medium Term)
1. Implement end-to-end event processing tests (2.3)
2. Implement error handling tests (4.1)
3. Target: 85% coverage

### Week 4 (Optional)
1. Implement performance benchmarks (3.1)
2. Document test results
3. Target: 90%+ coverage

---

## 8. Success Criteria

- [ ] All unit tests passing (1.1, 1.2, 1.3)
- [ ] All integration tests passing (2.1, 2.2, 2.3)
- [ ] Code coverage >70%
- [ ] Critical paths covered (correlation algorithm, InfluxDB queries)
- [ ] Error handling validated
- [ ] Performance benchmarks documented
- [ ] Tests run in CI/CD on every PR
- [ ] Zero regression bugs in production

---

## 9. Test Data Requirements

### InfluxDB Test Data
- 100+ sample HA events across multiple domains
- Power readings with various delta ranges (5W, 50W, 500W, 2500W)
- Events with missing data (test resilience)
- Time-synchronized event + power data

### Mock Responses
- InfluxDB query responses (Flux format)
- InfluxDB write confirmations
- Error responses (connection failures, timeouts)

---

## 10. Known Edge Cases

1. **Power reading at exact event time** - Should find within ±30s window
2. **Multiple events within 10 seconds** - Each should correlate independently
3. **Power spike then immediate return** - Should capture momentary changes
4. **Zero power consumption** - Handle division by zero in percentage calc
5. **Negative power readings** - Validate handling (shouldn't happen but might)
6. **Very large power deltas** - HVAC systems can cause 2000W+ changes
7. **Rapid on/off cycles** - Multiple correlations in short time

---

## 11. Documentation Updates

After test implementation:
- [ ] Update README.md with test execution instructions
- [ ] Add test coverage badge
- [ ] Document test data requirements
- [ ] Update CLAUDE.md with service test status

---

## Appendix: File References

| File | Lines | Critical Logic |
|------|-------|----------------|
| `src/correlator.py` | 186-208 | Power delta calculation |
| `src/correlator.py` | 156-208 | Event correlation logic |
| `src/correlator.py` | 210-248 | Power lookup queries |
| `src/correlator.py` | 250-293 | Write correlation to InfluxDB |
| `src/correlator.py` | 294-327 | Statistics tracking |
| `src/main.py` | 86-122 | Continuous processing loop |
| `src/main.py` | 124-147 | API endpoints |

---

**Document Version:** 1.0
**Created:** November 14, 2025
**Last Updated:** November 14, 2025
**Status:** Ready for Implementation
