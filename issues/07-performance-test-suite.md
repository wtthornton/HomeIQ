# Issue #7: [P1] Add Performance Test Suite (pytest-benchmark)

**Status:** 🟢 Open
**Priority:** 🟡 P1 - High
**Effort:** 4-6 hours
**Dependencies:** None

## Description

Implement comprehensive performance regression tests using pytest-benchmark to ensure system meets CLAUDE.md performance targets.

## CLAUDE.md Performance Targets

| Operation | Target | Acceptable | Investigation |
|-----------|--------|------------|---------------|
| Health checks | <10ms | <50ms | >100ms |
| Device queries | <10ms | <50ms | >100ms |
| Event queries | <100ms | <200ms | >500ms |
| InfluxDB batch write | <100ms | <200ms | >500ms |

## Acceptance Criteria

- [ ] Benchmark all critical operations
- [ ] Verify targets from CLAUDE.md
- [ ] Performance regression detection
- [ ] Generate benchmark reports
- [ ] Track metrics over time

## Code Template

```python
# tests/performance/test_batch_processing.py
import pytest

def test_influxdb_batch_write_performance(benchmark):
    """Verify batch writes meet <100ms target"""
    events = generate_test_events(1000)

    result = benchmark(batch_processor.write_batch, events)

    # Target: <100ms for 1000 events
    assert result.stats.mean < 0.100
    assert result.stats.stddev < 0.020  # Consistent performance

@pytest.mark.asyncio
async def test_device_query_latency(benchmark):
    """Verify device queries meet <10ms target"""
    async def query():
        return await data_api.get_devices()

    result = benchmark.pedantic(query, iterations=100, rounds=10)

    # Property: 95th percentile <10ms
    assert result.stats.quantiles[3] < 0.010
```
