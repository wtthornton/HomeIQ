"""Tests for metrics service."""


import pytest
from src.metrics_service import (
    Metric,
    MetricsCollector,
    MetricsService,
    MetricType,
    MetricValue,
    PerformanceTracker,
)


class TestMetricValue:
    """Test MetricValue class."""

    def test_metric_value_creation(self):
        """Test metric value creation."""
        value = MetricValue(
            timestamp="2024-01-01T00:00:00Z",
            value=42.5,
            labels={"service": "test"}
        )

        assert value.timestamp == "2024-01-01T00:00:00Z"
        assert value.value == 42.5
        assert value.labels == {"service": "test"}

    def test_metric_value_to_dict(self):
        """Test metric value to dictionary conversion."""
        value = MetricValue(
            timestamp="2024-01-01T00:00:00Z",
            value=42.5,
            labels={"service": "test"}
        )

        data = value.to_dict()

        assert data["timestamp"] == "2024-01-01T00:00:00Z"
        assert data["value"] == 42.5
        assert data["labels"] == {"service": "test"}


class TestMetric:
    """Test Metric class."""

    def test_metric_creation(self):
        """Test metric creation."""
        metric = Metric(
            name="test_metric",
            type=MetricType.GAUGE,
            description="Test metric",
            unit="count",
            values=[]
        )

        assert metric.name == "test_metric"
        assert metric.type == MetricType.GAUGE
        assert metric.description == "Test metric"
        assert metric.unit == "count"
        assert len(metric.values) == 0

    def test_metric_to_dict(self):
        """Test metric to dictionary conversion."""
        value = MetricValue("2024-01-01T00:00:00Z", 42.5)
        metric = Metric(
            name="test_metric",
            type=MetricType.GAUGE,
            description="Test metric",
            unit="count",
            values=[value],
            labels={"service": "test"}
        )

        data = metric.to_dict()

        assert data["name"] == "test_metric"
        assert data["type"] == "gauge"
        assert data["description"] == "Test metric"
        assert data["unit"] == "count"
        assert len(data["values"]) == 1
        assert data["labels"] == {"service": "test"}


class TestMetricsCollector:
    """Test MetricsCollector class."""

    def test_metrics_collector_creation(self):
        """Test metrics collector creation."""
        collector = MetricsCollector()

        assert len(collector.metrics) == 0
        assert collector.max_values_per_metric == 1000
        assert collector.system_metrics_enabled is True
        assert collector.metrics_interval == 60.0

    def test_register_metric(self):
        """Test registering a metric."""
        collector = MetricsCollector()

        collector.register_metric(
            name="test_metric",
            metric_type=MetricType.GAUGE,
            description="Test metric",
            unit="count"
        )

        assert "test_metric" in collector.metrics
        metric = collector.metrics["test_metric"]
        assert metric.name == "test_metric"
        assert metric.type == MetricType.GAUGE
        assert metric.description == "Test metric"
        assert metric.unit == "count"

    def test_record_value(self):
        """Test recording a metric value."""
        collector = MetricsCollector()

        collector.register_metric(
            name="test_metric",
            metric_type=MetricType.GAUGE,
            description="Test metric",
            unit="count"
        )

        collector.record_value("test_metric", 42.5, {"service": "test"})

        metric = collector.metrics["test_metric"]
        assert len(metric.values) == 1
        assert metric.values[0].value == 42.5
        assert metric.values[0].labels == {"service": "test"}

    def test_increment_counter(self):
        """Test incrementing a counter."""
        collector = MetricsCollector()

        collector.register_metric(
            name="test_counter",
            metric_type=MetricType.COUNTER,
            description="Test counter",
            unit="count"
        )

        # First increment
        collector.increment_counter("test_counter", 1.0)
        assert collector.get_latest_value("test_counter") == 1.0

        # Second increment
        collector.increment_counter("test_counter", 2.0)
        assert collector.get_latest_value("test_counter") == 3.0

    def test_set_gauge(self):
        """Test setting a gauge value."""
        collector = MetricsCollector()

        collector.register_metric(
            name="test_gauge",
            metric_type=MetricType.GAUGE,
            description="Test gauge",
            unit="count"
        )

        collector.set_gauge("test_gauge", 42.5)
        assert collector.get_latest_value("test_gauge") == 42.5

        collector.set_gauge("test_gauge", 100.0)
        assert collector.get_latest_value("test_gauge") == 100.0

    def test_record_timer(self):
        """Test recording a timer value."""
        collector = MetricsCollector()

        collector.register_metric(
            name="test_timer",
            metric_type=MetricType.TIMER,
            description="Test timer",
            unit="seconds"
        )

        collector.record_timer("test_timer", 1.5, {"operation": "test"})

        metric = collector.metrics["test_timer"]
        assert len(metric.values) == 1
        assert metric.values[0].value == 1.5
        assert metric.values[0].labels == {"operation": "test"}

    def test_get_latest_value(self):
        """Test getting latest metric value."""
        collector = MetricsCollector()

        collector.register_metric(
            name="test_metric",
            metric_type=MetricType.GAUGE,
            description="Test metric",
            unit="count"
        )

        # No values yet
        assert collector.get_latest_value("test_metric") == 0.0

        # Add values
        collector.record_value("test_metric", 10.0)
        collector.record_value("test_metric", 20.0)
        collector.record_value("test_metric", 30.0)

        assert collector.get_latest_value("test_metric") == 30.0

    def test_get_latest_value_with_labels(self):
        """Test getting latest metric value with labels."""
        collector = MetricsCollector()

        collector.register_metric(
            name="test_metric",
            metric_type=MetricType.GAUGE,
            description="Test metric",
            unit="count"
        )

        # Add values with different labels
        collector.record_value("test_metric", 10.0, {"service": "service1"})
        collector.record_value("test_metric", 20.0, {"service": "service2"})
        collector.record_value("test_metric", 30.0, {"service": "service1"})

        assert collector.get_latest_value("test_metric", {"service": "service1"}) == 30.0
        assert collector.get_latest_value("test_metric", {"service": "service2"}) == 20.0

    def test_get_metric(self):
        """Test getting a metric by name."""
        collector = MetricsCollector()

        collector.register_metric(
            name="test_metric",
            metric_type=MetricType.GAUGE,
            description="Test metric",
            unit="count"
        )

        metric = collector.get_metric("test_metric")
        assert metric is not None
        assert metric.name == "test_metric"

        # Non-existent metric
        assert collector.get_metric("non_existent") is None

    def test_get_all_metrics(self):
        """Test getting all metrics."""
        collector = MetricsCollector()

        collector.register_metric("metric1", MetricType.GAUGE, "Metric 1", "count")
        collector.register_metric("metric2", MetricType.COUNTER, "Metric 2", "count")

        metrics = collector.get_all_metrics()
        assert len(metrics) == 2

        metric_names = [m.name for m in metrics]
        assert "metric1" in metric_names
        assert "metric2" in metric_names

    def test_get_metrics_summary(self):
        """Test getting metrics summary."""
        collector = MetricsCollector()

        collector.register_metric("metric1", MetricType.GAUGE, "Metric 1", "count")
        collector.register_metric("metric2", MetricType.COUNTER, "Metric 2", "count")

        collector.record_value("metric1", 10.0)
        collector.record_value("metric1", 20.0)
        collector.record_value("metric2", 5.0)

        summary = collector.get_metrics_summary()

        assert summary["total_metrics"] == 2
        assert summary["metric_types"]["gauge"] == 1
        assert summary["metric_types"]["counter"] == 1
        assert summary["total_values"] == 3

    @pytest.mark.asyncio
    async def test_start_stop_collection(self):
        """Test starting and stopping collection."""
        collector = MetricsCollector()

        # Start collection
        await collector.start_collection()
        assert collector.is_collecting

        # Stop collection
        await collector.stop_collection()
        assert not collector.is_collecting


class TestPerformanceTracker:
    """Test PerformanceTracker class."""

    def test_performance_tracker_creation(self):
        """Test performance tracker creation."""
        collector = MetricsCollector()
        tracker = PerformanceTracker(collector)

        assert tracker.metrics_collector is collector
        assert len(tracker.operation_timers) == 0

    def test_start_end_operation(self):
        """Test starting and ending an operation."""
        collector = MetricsCollector()
        tracker = PerformanceTracker(collector)

        # Register timer metric
        collector.register_metric(
            name="operation_duration_seconds",
            metric_type=MetricType.TIMER,
            description="Operation duration",
            unit="seconds"
        )

        # Start operation
        timer_id = tracker.start_operation("test_operation")
        assert timer_id.startswith("test_operation_")
        assert timer_id in tracker.operation_timers

        # End operation
        tracker.end_operation(timer_id, {"service": "test"})
        assert timer_id not in tracker.operation_timers

        # Check that metric was recorded
        metric = collector.get_metric("operation_duration_seconds")
        assert len(metric.values) == 1
        assert metric.values[0].labels == {"operation": "test_operation", "service": "test"}

    def test_record_event_processed(self):
        """Test recording event processing."""
        collector = MetricsCollector()
        tracker = PerformanceTracker(collector)

        # Register metrics
        collector.register_metric("event_processing_duration_seconds", MetricType.TIMER, "Event processing duration", "seconds")
        collector.register_metric("events_processed_total", MetricType.COUNTER, "Total events processed", "count")

        tracker.record_event_processed("state_changed", 150.0, "sensor.temperature")

        # Check timer metric
        timer_metric = collector.get_metric("event_processing_duration_seconds")
        assert len(timer_metric.values) == 1
        assert timer_metric.values[0].value == 0.15  # 150ms = 0.15s
        assert timer_metric.values[0].labels == {"event_type": "state_changed", "entity_id": "sensor.temperature"}

        # Check counter metric
        counter_metric = collector.get_metric("events_processed_total")
        assert len(counter_metric.values) == 1
        assert counter_metric.values[0].value == 1.0
        assert counter_metric.values[0].labels == {"event_type": "state_changed", "entity_id": "sensor.temperature"}

    def test_record_error(self):
        """Test recording error metrics."""
        collector = MetricsCollector()
        tracker = PerformanceTracker(collector)

        collector.register_metric("errors_total", MetricType.COUNTER, "Total errors", "count")

        tracker.record_error("validation_error", "websocket-service")

        metric = collector.get_metric("errors_total")
        assert len(metric.values) == 1
        assert metric.values[0].value == 1.0
        assert metric.values[0].labels == {"error_type": "validation_error", "service": "websocket-service"}

    def test_record_api_request(self):
        """Test recording API request metrics."""
        collector = MetricsCollector()
        tracker = PerformanceTracker(collector)

        collector.register_metric("api_request_duration_seconds", MetricType.TIMER, "API request duration", "seconds")
        collector.register_metric("api_requests_total", MetricType.COUNTER, "Total API requests", "count")

        tracker.record_api_request("/api/v1/health", "GET", 200, 50.0)

        # Check timer metric
        timer_metric = collector.get_metric("api_request_duration_seconds")
        assert len(timer_metric.values) == 1
        assert timer_metric.values[0].value == 0.05  # 50ms = 0.05s
        assert timer_metric.values[0].labels == {"endpoint": "/api/v1/health", "method": "GET", "status_code": "200"}

        # Check counter metric
        counter_metric = collector.get_metric("api_requests_total")
        assert len(counter_metric.values) == 1
        assert counter_metric.values[0].value == 1.0
        assert counter_metric.values[0].labels == {"endpoint": "/api/v1/health", "method": "GET", "status_code": "200"}


class TestMetricsService:
    """Test MetricsService class."""

    def test_metrics_service_creation(self):
        """Test metrics service creation."""
        service = MetricsService()

        assert isinstance(service.collector, MetricsCollector)
        assert isinstance(service.performance_tracker, PerformanceTracker)
        assert not service.is_running

        # Check that application metrics are registered
        assert "events_processed_total" in service.collector.metrics
        assert "api_requests_total" in service.collector.metrics
        assert "errors_total" in service.collector.metrics

    def test_get_collector(self):
        """Test getting metrics collector."""
        service = MetricsService()
        collector = service.get_collector()

        assert collector is service.collector

    def test_get_performance_tracker(self):
        """Test getting performance tracker."""
        service = MetricsService()
        tracker = service.get_performance_tracker()

        assert tracker is service.performance_tracker

    def test_get_metrics(self):
        """Test getting metrics."""
        service = MetricsService()

        # Get all metrics
        all_metrics = service.get_metrics()
        assert len(all_metrics) > 0

        # Get specific metrics
        specific_metrics = service.get_metrics(["events_processed_total", "api_requests_total"])
        assert len(specific_metrics) == 2

    def test_get_metrics_summary(self):
        """Test getting metrics summary."""
        service = MetricsService()

        summary = service.get_metrics_summary()

        assert "total_metrics" in summary
        assert "metric_types" in summary
        assert "total_values" in summary

    def test_get_current_metrics(self):
        """Test getting current metric values."""
        service = MetricsService()

        # Add some values
        service.collector.record_value("events_processed_total", 100.0)
        service.collector.record_value("api_requests_total", 50.0)

        current_metrics = service.get_current_metrics()

        assert "events_processed_total" in current_metrics
        assert "api_requests_total" in current_metrics
        assert current_metrics["events_processed_total"]["value"] == 100.0
        assert current_metrics["api_requests_total"]["value"] == 50.0

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test starting and stopping service."""
        service = MetricsService()

        # Start service
        await service.start()
        assert service.is_running

        # Stop service
        await service.stop()
        assert not service.is_running
