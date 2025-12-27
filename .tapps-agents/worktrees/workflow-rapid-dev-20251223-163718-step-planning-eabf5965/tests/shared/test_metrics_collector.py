"""
Comprehensive Tests for Metrics Collector
Modern 2025 Patterns: Decorator testing, context manager testing

Module: shared/metrics_collector.py
Coverage Target: >90%
"""

import pytest
import time
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from hypothesis import given, strategies as st, settings

# Import module under test
from metrics_collector import (
    MetricsCollector,
    get_metrics_collector,
    _metrics_collectors
)


# ============================================================================
# Metrics Collector Initialization Tests
# ============================================================================

class TestMetricsCollectorInit:
    """Test Metrics Collector initialization"""

    def test_initialization_basic(self):
        """Test basic metrics collector initialization"""
        collector = MetricsCollector(service_name="test-service")

        assert collector.service_name == "test-service"
        assert collector.influxdb_client is None
        assert len(collector.counters) == 0
        assert len(collector.gauges) == 0
        assert len(collector.timers) == 0
        assert collector.start_time > 0

    def test_initialization_with_influxdb_client(self):
        """Test initialization with InfluxDB client"""
        mock_client = Mock()
        collector = MetricsCollector(
            service_name="test-service",
            influxdb_client=mock_client
        )

        assert collector.influxdb_client == mock_client

    @patch('metrics_collector.psutil.Process')
    def test_initialization_with_psutil(self, mock_process_class):
        """Test initialization successfully creates psutil process"""
        mock_process = Mock()
        mock_process_class.return_value = mock_process

        collector = MetricsCollector(service_name="test")

        assert collector.process == mock_process

    @patch('metrics_collector.psutil.Process')
    def test_initialization_handles_psutil_failure(self, mock_process_class):
        """Test graceful handling of psutil failures"""
        mock_process_class.side_effect = Exception("psutil not available")

        collector = MetricsCollector(service_name="test")

        assert collector.process is None


# ============================================================================
# Counter Tests
# ============================================================================

class TestMetricsCollectorCounters:
    """Test counter functionality"""

    def test_increment_counter_basic(self, metrics_collector):
        """Test basic counter increment"""
        metrics_collector.increment_counter("requests")

        assert metrics_collector.counters["requests"] == 1

    def test_increment_counter_with_value(self, metrics_collector):
        """Test counter increment with custom value"""
        metrics_collector.increment_counter("requests", value=5)

        assert metrics_collector.counters["requests"] == 5

    def test_increment_counter_multiple_times(self, metrics_collector):
        """Test multiple counter increments"""
        metrics_collector.increment_counter("requests")
        metrics_collector.increment_counter("requests")
        metrics_collector.increment_counter("requests", value=3)

        assert metrics_collector.counters["requests"] == 5

    def test_increment_counter_with_tags(self, metrics_collector):
        """Test counter with tags"""
        metrics_collector.increment_counter(
            "requests",
            tags={"endpoint": "/health", "method": "GET"}
        )
        metrics_collector.increment_counter(
            "requests",
            tags={"endpoint": "/health", "method": "GET"}
        )
        metrics_collector.increment_counter(
            "requests",
            tags={"endpoint": "/api", "method": "POST"}
        )

        # Check tagged counters are separate
        health_key = metrics_collector._make_key(
            "requests",
            {"endpoint": "/health", "method": "GET"}
        )
        api_key = metrics_collector._make_key(
            "requests",
            {"endpoint": "/api", "method": "POST"}
        )

        assert metrics_collector.counters[health_key] == 2
        assert metrics_collector.counters[api_key] == 1


# ============================================================================
# Gauge Tests
# ============================================================================

class TestMetricsCollectorGauges:
    """Test gauge functionality"""

    def test_set_gauge_basic(self, metrics_collector):
        """Test basic gauge setting"""
        metrics_collector.set_gauge("temperature", 22.5)

        assert metrics_collector.gauges["temperature"] == 22.5

    def test_set_gauge_overwrites_value(self, metrics_collector):
        """Test gauge value is overwritten"""
        metrics_collector.set_gauge("temperature", 20.0)
        metrics_collector.set_gauge("temperature", 25.0)

        assert metrics_collector.gauges["temperature"] == 25.0

    def test_set_gauge_with_tags(self, metrics_collector):
        """Test gauge with tags"""
        metrics_collector.set_gauge(
            "temperature",
            22.5,
            tags={"location": "living_room"}
        )
        metrics_collector.set_gauge(
            "temperature",
            19.5,
            tags={"location": "bedroom"}
        )

        living_room_key = metrics_collector._make_key(
            "temperature",
            {"location": "living_room"}
        )
        bedroom_key = metrics_collector._make_key(
            "temperature",
            {"location": "bedroom"}
        )

        assert metrics_collector.gauges[living_room_key] == 22.5
        assert metrics_collector.gauges[bedroom_key] == 19.5


# ============================================================================
# Timer Tests
# ============================================================================

class TestMetricsCollectorTimers:
    """Test timer functionality"""

    def test_record_timing_basic(self, metrics_collector):
        """Test basic timing recording"""
        metrics_collector.record_timing("operation", 150.5)

        timer = metrics_collector.timers["operation"]
        assert timer['count'] == 1
        assert timer['total'] == 150.5
        assert timer['min'] == 150.5
        assert timer['max'] == 150.5

    def test_record_timing_multiple_values(self, metrics_collector):
        """Test recording multiple timing values"""
        metrics_collector.record_timing("operation", 100.0)
        metrics_collector.record_timing("operation", 200.0)
        metrics_collector.record_timing("operation", 150.0)

        timer = metrics_collector.timers["operation"]
        assert timer['count'] == 3
        assert timer['total'] == 450.0
        assert timer['min'] == 100.0
        assert timer['max'] == 200.0

    def test_timer_context_manager(self, metrics_collector):
        """Test timer context manager"""
        with metrics_collector.timer("slow_operation"):
            time.sleep(0.01)  # 10ms

        timer = metrics_collector.timers["slow_operation"]
        assert timer['count'] == 1
        assert timer['total'] >= 10  # At least 10ms
        assert timer['min'] >= 10
        assert timer['max'] >= 10

    def test_timer_context_manager_with_tags(self, metrics_collector):
        """Test timer context manager with tags"""
        with metrics_collector.timer("api_call", tags={"endpoint": "/health"}):
            time.sleep(0.005)  # 5ms

        key = metrics_collector._make_key("api_call", {"endpoint": "/health"})
        assert key in metrics_collector.timers
        assert metrics_collector.timers[key]['count'] == 1

    def test_timer_context_manager_exception_handling(self, metrics_collector):
        """Test timer still records when exception occurs"""
        try:
            with metrics_collector.timer("failing_operation"):
                time.sleep(0.005)
                raise ValueError("Test error")
        except ValueError:
            pass

        # Timer should still be recorded
        assert "failing_operation" in metrics_collector.timers
        assert metrics_collector.timers["failing_operation"]['count'] == 1


# ============================================================================
# Timer Decorator Tests
# ============================================================================

class TestMetricsCollectorDecorators:
    """Test timer decorator functionality"""

    def test_timing_decorator_sync_function(self, metrics_collector):
        """Test timing decorator on synchronous function"""

        @metrics_collector.timing_decorator("test_func")
        def slow_function():
            time.sleep(0.01)
            return "result"

        result = slow_function()

        assert result == "result"
        assert "test_func" in metrics_collector.timers
        assert metrics_collector.timers["test_func"]['count'] == 1

    def test_timing_decorator_uses_function_name(self, metrics_collector):
        """Test decorator uses function name if no name provided"""

        @metrics_collector.timing_decorator()
        def my_function():
            return "done"

        result = my_function()

        assert result == "done"
        assert "my_function_duration" in metrics_collector.timers

    @pytest.mark.asyncio
    async def test_timing_decorator_async_function(self, metrics_collector):
        """Test timing decorator on async function"""

        @metrics_collector.timing_decorator("async_test")
        async def async_slow_function():
            await asyncio.sleep(0.01)
            return "async_result"

        result = await async_slow_function()

        assert result == "async_result"
        assert "async_test" in metrics_collector.timers
        assert metrics_collector.timers["async_test"]['count'] == 1

    def test_timing_decorator_with_tags(self, metrics_collector):
        """Test timing decorator with tags"""

        @metrics_collector.timing_decorator("api_endpoint", tags={"method": "GET"})
        def api_call():
            time.sleep(0.005)
            return "data"

        result = api_call()

        assert result == "data"
        key = metrics_collector._make_key("api_endpoint", {"method": "GET"})
        assert key in metrics_collector.timers

    def test_timing_decorator_preserves_function_attributes(self, metrics_collector):
        """Test decorator preserves function name and docstring"""

        @metrics_collector.timing_decorator()
        def documented_function():
            """This is a documented function"""
            return True

        assert documented_function.__name__ == "documented_function"
        assert documented_function.__doc__ == "This is a documented function"


# ============================================================================
# System Metrics Tests
# ============================================================================

class TestMetricsCollectorSystemMetrics:
    """Test system metrics collection"""

    @patch('metrics_collector.psutil.Process')
    def test_get_system_metrics_success(self, mock_process_class):
        """Test successful system metrics collection"""
        # Mock process with metrics
        mock_process = Mock()
        mock_process.cpu_percent.return_value = 25.5
        mock_process.num_threads.return_value = 10
        mock_process.memory_info.return_value = Mock(rss=104857600)  # 100MB
        mock_process.memory_percent.return_value = 5.2
        mock_process.num_fds.return_value = 50

        mock_process_class.return_value = mock_process

        collector = MetricsCollector(service_name="test")
        metrics = collector.get_system_metrics()

        assert 'timestamp' in metrics
        assert 'uptime_seconds' in metrics
        assert metrics['cpu']['percent'] == 25.5
        assert metrics['cpu']['num_threads'] == 10
        assert metrics['memory']['rss_bytes'] == 104857600
        assert metrics['memory']['rss_mb'] == 100.0
        assert metrics['memory']['percent'] == 5.2
        assert metrics['file_descriptors'] == 50

    @patch('metrics_collector.psutil.Process')
    def test_get_system_metrics_no_process(self, mock_process_class):
        """Test system metrics when process is None"""
        mock_process_class.side_effect = Exception("Process unavailable")

        collector = MetricsCollector(service_name="test")
        metrics = collector.get_system_metrics()

        # Should still return basic metrics
        assert 'timestamp' in metrics
        assert 'uptime_seconds' in metrics
        # But no CPU/memory metrics
        assert 'cpu' not in metrics
        assert 'memory' not in metrics

    @patch('metrics_collector.psutil.Process')
    def test_get_system_metrics_no_file_descriptors(self, mock_process_class):
        """Test system metrics on Windows (no file descriptors)"""
        mock_process = Mock()
        mock_process.cpu_percent.return_value = 10.0
        mock_process.num_threads.return_value = 5
        mock_process.memory_info.return_value = Mock(rss=52428800)
        mock_process.memory_percent.return_value = 2.5
        # num_fds raises AttributeError on Windows
        mock_process.num_fds.side_effect = AttributeError("Windows")

        mock_process_class.return_value = mock_process

        collector = MetricsCollector(service_name="test")
        metrics = collector.get_system_metrics()

        assert 'file_descriptors' not in metrics
        assert 'cpu' in metrics  # Other metrics should work


# ============================================================================
# Get All Metrics Tests
# ============================================================================

class TestMetricsCollectorGetAllMetrics:
    """Test getting all metrics"""

    def test_get_all_metrics_comprehensive(self, metrics_collector):
        """Test getting all metrics returns complete data"""
        # Add various metrics
        metrics_collector.increment_counter("requests", value=100)
        metrics_collector.set_gauge("active_connections", 42)
        metrics_collector.record_timing("response_time", 150.0)
        metrics_collector.record_timing("response_time", 200.0)

        all_metrics = metrics_collector.get_all_metrics()

        assert all_metrics['service'] == "test-service"
        assert 'timestamp' in all_metrics
        assert 'uptime_seconds' in all_metrics

        # Counters
        assert all_metrics['counters']['requests'] == 100

        # Gauges
        assert all_metrics['gauges']['active_connections'] == 42

        # Timers with statistics
        response_timer = all_metrics['timers']['response_time']
        assert response_timer['count'] == 2
        assert response_timer['total_ms'] == 350.0
        assert response_timer['avg_ms'] == 175.0
        assert response_timer['min_ms'] == 150.0
        assert response_timer['max_ms'] == 200.0

        # System metrics
        assert 'system' in all_metrics

    def test_get_all_metrics_empty_collector(self, metrics_collector):
        """Test getting metrics from empty collector"""
        all_metrics = metrics_collector.get_all_metrics()

        assert all_metrics['counters'] == {}
        assert all_metrics['gauges'] == {}
        assert all_metrics['timers'] == {}


# ============================================================================
# Reset Metrics Tests
# ============================================================================

class TestMetricsCollectorReset:
    """Test metrics reset functionality"""

    def test_reset_metrics(self, metrics_collector):
        """Test resetting all metrics"""
        # Add metrics
        metrics_collector.increment_counter("requests", value=100)
        metrics_collector.set_gauge("temperature", 22.5)
        metrics_collector.record_timing("operation", 150.0)

        # Verify metrics exist
        assert len(metrics_collector.counters) > 0
        assert len(metrics_collector.gauges) > 0
        assert len(metrics_collector.timers) > 0

        # Reset
        metrics_collector.reset_metrics()

        # Verify all cleared
        assert len(metrics_collector.counters) == 0
        assert len(metrics_collector.gauges) == 0
        assert len(metrics_collector.timers) == 0


# ============================================================================
# Helper Method Tests
# ============================================================================

class TestMetricsCollectorHelpers:
    """Test helper methods"""

    def test_make_key_without_tags(self, metrics_collector):
        """Test key generation without tags"""
        key = metrics_collector._make_key("metric_name")

        assert key == "metric_name"

    def test_make_key_with_tags(self, metrics_collector):
        """Test key generation with tags"""
        key = metrics_collector._make_key(
            "metric_name",
            {"endpoint": "/api", "method": "GET"}
        )

        assert "metric_name" in key
        assert "endpoint=/api" in key
        assert "method=GET" in key

    def test_make_key_tags_sorted(self, metrics_collector):
        """Test tags are sorted for consistent keys"""
        key1 = metrics_collector._make_key(
            "metric",
            {"a": "1", "b": "2"}
        )
        key2 = metrics_collector._make_key(
            "metric",
            {"b": "2", "a": "1"}
        )

        # Keys should be identical regardless of tag order
        assert key1 == key2


# ============================================================================
# Global Collector Tests
# ============================================================================

class TestGetMetricsCollector:
    """Test global metrics collector function"""

    def test_get_metrics_collector_creates_new(self):
        """Test getting metrics collector creates new instance"""
        _metrics_collectors.clear()

        collector = get_metrics_collector("new-service")

        assert collector.service_name == "new-service"
        assert "new-service" in _metrics_collectors

    def test_get_metrics_collector_returns_existing(self):
        """Test getting existing collector returns same instance"""
        _metrics_collectors.clear()

        collector1 = get_metrics_collector("existing-service")
        collector2 = get_metrics_collector("existing-service")

        assert collector1 is collector2

    def test_get_metrics_collector_with_influxdb_client(self):
        """Test getting collector with InfluxDB client"""
        _metrics_collectors.clear()
        mock_client = Mock()

        collector = get_metrics_collector("service", influxdb_client=mock_client)

        assert collector.influxdb_client == mock_client


# ============================================================================
# Property-Based Tests
# ============================================================================

class TestMetricsCollectorProperties:
    """Property-based tests for metrics collector"""

    @given(
        counter_value=st.integers(min_value=1, max_value=1000),
        num_increments=st.integers(min_value=1, max_value=100)
    )
    @settings(max_examples=50)
    def test_counter_accumulates_correctly(self, counter_value, num_increments):
        """Property: Counter should accumulate all increments correctly"""
        collector = MetricsCollector(service_name="property-test")

        for _ in range(num_increments):
            collector.increment_counter("test_counter", value=counter_value)

        expected_total = counter_value * num_increments
        assert collector.counters["test_counter"] == expected_total

        collector.reset_metrics()

    @given(
        gauge_value=st.floats(min_value=-100.0, max_value=100.0, allow_nan=False)
    )
    @settings(max_examples=50)
    def test_gauge_stores_any_float(self, gauge_value):
        """Property: Gauge should store any valid float value"""
        collector = MetricsCollector(service_name="property-test")

        collector.set_gauge("test_gauge", gauge_value)

        assert collector.gauges["test_gauge"] == gauge_value

        collector.reset_metrics()

    @given(
        timing_values=st.lists(
            st.floats(min_value=0.1, max_value=1000.0, allow_nan=False),
            min_size=1,
            max_size=100
        )
    )
    @settings(max_examples=30)
    def test_timer_statistics_correct(self, timing_values):
        """Property: Timer statistics should always be mathematically correct"""
        collector = MetricsCollector(service_name="property-test")

        for value in timing_values:
            collector.record_timing("test_timer", value)

        timer = collector.timers["test_timer"]

        # Verify properties
        assert timer['count'] == len(timing_values)
        assert abs(timer['total'] - sum(timing_values)) < 0.01  # Floating point tolerance
        assert timer['min'] == min(timing_values)
        assert timer['max'] == max(timing_values)
        assert abs(timer['total'] / timer['count'] - sum(timing_values) / len(timing_values)) < 0.01

        collector.reset_metrics()


# ============================================================================
# Performance Tests
# ============================================================================

@pytest.mark.benchmark
class TestMetricsCollectorPerformance:
    """Performance benchmarks for metrics collector"""

    def test_counter_increment_performance(self, benchmark, metrics_collector):
        """Benchmark counter increment performance"""
        result = benchmark(metrics_collector.increment_counter, "bench_counter")
        assert result is None

    def test_gauge_set_performance(self, benchmark, metrics_collector):
        """Benchmark gauge set performance"""
        result = benchmark(metrics_collector.set_gauge, "bench_gauge", 42.0)
        assert result is None

    def test_timing_record_performance(self, benchmark, metrics_collector):
        """Benchmark timing record performance"""
        result = benchmark(metrics_collector.record_timing, "bench_timer", 123.45)
        assert result is None

    def test_get_all_metrics_performance(self, metrics_collector):
        """Test get_all_metrics performance with many metrics"""
        # Add many metrics
        for i in range(100):
            metrics_collector.increment_counter(f"counter_{i}")
            metrics_collector.set_gauge(f"gauge_{i}", float(i))
            metrics_collector.record_timing(f"timer_{i}", float(i) * 10.0)

        start = time.perf_counter()
        metrics = metrics_collector.get_all_metrics()
        duration_ms = (time.perf_counter() - start) * 1000

        # Should be fast even with many metrics
        assert duration_ms < 50  # <50ms
        assert len(metrics['counters']) == 100
        assert len(metrics['gauges']) == 100
        assert len(metrics['timers']) == 100
