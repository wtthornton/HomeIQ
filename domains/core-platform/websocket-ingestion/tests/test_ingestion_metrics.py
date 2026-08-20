"""
Unit tests for the Prometheus ingestion metrics collector.
"""

from prometheus_client import CollectorRegistry, generate_latest
from src.ingestion_metrics import IngestionMetricsCollector


class _FakeSubscription:
    def __init__(self, status):
        self._status = status

    def get_subscription_status(self):
        return self._status


class _FakeConnectionManager:
    def __init__(self, subscription, is_running=True):
        self.event_subscription = subscription
        self.is_running = is_running


class _FakeProcessor:
    def __init__(self, stats):
        self._stats = stats

    def get_processing_statistics(self):
        return self._stats


class _FakeService:
    def __init__(self, connection_manager=None, processor=None):
        self.connection_manager = connection_manager
        self.async_event_processor = processor


def _healthy_service(**status_overrides):
    status = {
        "is_subscribed": True,
        "total_events_received": 8217,
        "events_by_type": {"state_changed": 8212, "entity_registry_updated": 5},
        "last_event_time": "2026-08-20T18:03:30.630938+00:00",
    }
    status.update(status_overrides)
    return _FakeService(
        connection_manager=_FakeConnectionManager(_FakeSubscription(status)),
        processor=_FakeProcessor({"processed_events": 8210, "failed_events": 3}),
    )


def _scrape(service):
    registry = CollectorRegistry()
    registry.register(IngestionMetricsCollector(lambda: service))
    return generate_latest(registry).decode()


def test_exports_received_counts_per_event_type():
    output = _scrape(_healthy_service())

    assert 'ha_events_received_total{event_type="state_changed"} 8212.0' in output
    assert 'ha_events_received_total{event_type="entity_registry_updated"} 5.0' in output


def test_exports_last_event_timestamp_as_unix_seconds():
    output = _scrape(_healthy_service())

    # 2026-08-20T18:03:30.630938+00:00 -> 1787249010.630938
    assert "ha_last_event_timestamp_seconds 1.787249010630938e+09" in output


def test_exports_connection_and_subscription_state():
    output = _scrape(_healthy_service())

    assert "ha_connection_up 1.0" in output
    assert "ha_subscription_up 1.0" in output


def test_exports_processed_and_failed_counts():
    output = _scrape(_healthy_service())

    assert "ha_events_processed_total 8210.0" in output
    assert "ha_events_failed_total 3.0" in output


def test_disconnected_subscription_reports_down():
    service = _healthy_service(is_subscribed=False)
    service.connection_manager.is_running = False

    output = _scrape(service)

    assert "ha_connection_up 0.0" in output
    assert "ha_subscription_up 0.0" in output


def test_service_not_started_reports_down_rather_than_missing():
    """Before startup the series must exist and read 0, so alerts still fire."""
    output = _scrape(None)

    assert "ha_connection_up 0.0" in output
    assert "ha_subscription_up 0.0" in output
    assert "ha_events_processed_total 0.0" in output


def test_missing_last_event_omits_the_timestamp_sample():
    """No events yet means no timestamp -- never a misleading 0 (epoch 1970)."""
    output = _scrape(_healthy_service(last_event_time=None))

    assert "# TYPE ha_last_event_timestamp_seconds gauge" in output
    assert "\nha_last_event_timestamp_seconds " not in output


def test_unparseable_last_event_time_does_not_break_the_scrape():
    output = _scrape(_healthy_service(last_event_time="not-a-timestamp"))

    assert "ha_connection_up 1.0" in output
    assert "\nha_last_event_timestamp_seconds " not in output
