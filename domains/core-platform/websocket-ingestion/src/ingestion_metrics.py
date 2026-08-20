"""
Prometheus ingestion metrics for the WebSocket Ingestion Service.

The service already tracks every number needed to answer "is HA data still
flowing?" -- ``EventSubscription`` counts events off the wire, and
``AsyncEventProcessor`` counts what it managed to process. Those live only on
``/api/v1/event-rate``, so ``/metrics`` could not distinguish a healthy service
from one whose websocket had silently died.

This module exposes that existing state as Prometheus metrics via a custom
collector that reads the service at scrape time. Nothing is added to the event
hot path, and the subscription counters stay the single source of truth.
"""

from datetime import datetime

from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily

from .utils.logger import logger


def _event_timestamp(raw: str | None) -> float | None:
    """Parse an ISO-8601 event time into a Unix timestamp."""
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw).timestamp()
    except ValueError:
        logger.warning("Unparseable last_event_time for metrics: %r", raw)
        return None


class IngestionMetricsCollector:
    """Exports Home Assistant ingestion state on every ``/metrics`` scrape.

    Args:
        get_service: Callable returning the live ``WebSocketIngestionService``,
            or ``None`` before startup finishes. Resolved per scrape so the
            collector can be registered before the service exists.
    """

    def __init__(self, get_service):
        self._get_service = get_service

    def collect(self):
        subscription_status, processing_stats = self._read_service_state()

        yield self._received_counter(subscription_status)
        yield self._last_event_gauge(subscription_status)
        yield self._up_gauge(
            "ha_connection_up",
            "1 if the Home Assistant websocket connection is established, 0 otherwise",
            subscription_status.get("is_connected"),
        )
        yield self._up_gauge(
            "ha_subscription_up",
            "1 if the service is subscribed to Home Assistant events, 0 otherwise",
            subscription_status.get("is_subscribed"),
        )
        yield self._processed_counter(
            "ha_events_processed",
            "Total Home Assistant events successfully processed",
            processing_stats.get("processed_events"),
        )
        yield self._processed_counter(
            "ha_events_failed",
            "Total Home Assistant events that failed processing",
            processing_stats.get("failed_events"),
        )
        yield self._dropped_counter(processing_stats)
        yield self._gauge(
            "ha_event_queue_size",
            "Events waiting in the processing queue",
            processing_stats.get("queue_size"),
        )
        yield self._gauge(
            "ha_event_queue_max_size",
            "Capacity of the processing queue; events are dropped when it fills",
            processing_stats.get("queue_maxsize"),
        )

    def _read_service_state(self) -> tuple[dict, dict]:
        """Pull subscription and processing stats off the running service.

        Returns empty dicts when the service has not started yet, which
        renders as ``ha_connection_up 0`` rather than a missing series.
        """
        service = self._get_service()
        if service is None:
            return {}, {}

        subscription_status: dict = {}
        connection_manager = getattr(service, "connection_manager", None)
        subscription = getattr(connection_manager, "event_subscription", None)
        if subscription is not None:
            subscription_status = subscription.get_subscription_status()
            subscription_status["is_connected"] = getattr(connection_manager, "is_running", False)

        processor = getattr(service, "async_event_processor", None)
        processing_stats = processor.get_processing_statistics() if processor else {}

        return subscription_status, processing_stats

    @staticmethod
    def _received_counter(status: dict) -> CounterMetricFamily:
        """Events received off the websocket, broken down by HA event type."""
        counter = CounterMetricFamily(
            "ha_events_received",
            "Total events received from the Home Assistant websocket",
            labels=["event_type"],
        )
        for event_type, count in sorted(status.get("events_by_type", {}).items()):
            counter.add_metric([event_type], count)
        return counter

    @staticmethod
    def _last_event_gauge(status: dict) -> GaugeMetricFamily:
        """Unix time of the most recent event; alert on staleness against this."""
        gauge = GaugeMetricFamily(
            "ha_last_event_timestamp_seconds",
            "Unix timestamp of the most recent Home Assistant event received",
        )
        timestamp = _event_timestamp(status.get("last_event_time"))
        if timestamp is not None:
            gauge.add_metric([], timestamp)
        return gauge

    @staticmethod
    def _up_gauge(name: str, documentation: str, value) -> GaugeMetricFamily:
        gauge = GaugeMetricFamily(name, documentation)
        gauge.add_metric([], 1 if value else 0)
        return gauge

    @staticmethod
    def _processed_counter(name: str, documentation: str, value) -> CounterMetricFamily:
        counter = CounterMetricFamily(name, documentation)
        counter.add_metric([], value or 0)
        return counter

    @staticmethod
    def _dropped_counter(processing_stats: dict) -> CounterMetricFamily:
        """Events rejected before reaching a worker, by reason.

        These never appear in processed or failed -- the caller discards
        process_event's False return -- so this is the only signal that the
        rate limiter or a full queue is shedding load.
        """
        counter = CounterMetricFamily(
            "ha_events_dropped",
            "Total Home Assistant events dropped before processing",
            labels=["reason"],
        )
        for reason, count in sorted(processing_stats.get("dropped_events", {}).items()):
            counter.add_metric([reason], count)
        return counter

    @staticmethod
    def _gauge(name: str, documentation: str, value) -> GaugeMetricFamily:
        gauge = GaugeMetricFamily(name, documentation)
        if value is not None:
            gauge.add_metric([], value)
        return gauge
