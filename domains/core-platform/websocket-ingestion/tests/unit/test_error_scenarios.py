"""
Unit tests for error scenarios in websocket-ingestion service
Epic 50 Story 50.4: Error Scenario Testing

Tests connection failures, InfluxDB write failures, discovery service failures,
network timeouts, and queue overflow scenarios.

Each test drives the real production code path and asserts on observable
behaviour (return value, counters, callbacks) — never on a mock of the very
method under test.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

# 32+ alphanumeric characters, so TokenValidator accepts it
VALID_TOKEN = "a" * 40


def _stub_schema(valid=True):
    """Schema stand-in returning plain dicts instead of InfluxDB Points."""
    schema = MagicMock()
    schema.create_event_point.side_effect = lambda event: dict(event)
    schema.validate_point.return_value = (valid, [] if valid else ["bad point"])
    return schema


class TestWebSocketConnectionFailures:
    """Test WebSocket connection failure scenarios"""

    @pytest.mark.asyncio
    async def test_connect_rejects_invalid_token(self):
        """
        GIVEN: A token that fails format validation
        WHEN: connect() is called
        THEN: It returns False and reports the error without opening a session
        """
        from src.websocket_client import HomeAssistantWebSocketClient

        client = HomeAssistantWebSocketClient("http://localhost:8123", "short")
        client.on_error = AsyncMock()

        assert await client.connect() is False
        client.on_error.assert_awaited_once()
        assert "Token validation failed" in client.on_error.await_args[0][0]
        assert client.is_connected is False
        assert client.session is None

    @pytest.mark.asyncio
    async def test_connect_handles_transport_failure(self, monkeypatch):
        """
        GIVEN: The WebSocket handshake raises
        WHEN: connect() is called
        THEN: It returns False, reports the error, and leaves the client disconnected
        """
        from src.websocket_client import HomeAssistantWebSocketClient

        client = HomeAssistantWebSocketClient("http://localhost:8123", VALID_TOKEN)
        client.on_error = AsyncMock()

        session = MagicMock()
        session.ws_connect = AsyncMock(side_effect=ConnectionError("Connection refused"))
        session.close = AsyncMock()
        session.closed = False
        monkeypatch.setattr(client, "_ensure_single_session", AsyncMock(return_value=session))
        client.session = session

        assert await client.connect() is False
        assert client.is_connected is False
        client.on_error.assert_awaited_once()
        assert "Connection refused" in client.on_error.await_args[0][0]

    @pytest.mark.asyncio
    async def test_connect_returns_false_when_authentication_fails(self, monkeypatch):
        """
        GIVEN: The handshake succeeds but authentication does not
        WHEN: connect() is called
        THEN: It returns False and does not fire the on_connect callback
        """
        from src.websocket_client import HomeAssistantWebSocketClient

        client = HomeAssistantWebSocketClient("http://localhost:8123", VALID_TOKEN)
        client.on_connect = AsyncMock()

        session = MagicMock()
        session.ws_connect = AsyncMock(return_value=MagicMock())
        session.close = AsyncMock()
        session.closed = False
        monkeypatch.setattr(client, "_ensure_single_session", AsyncMock(return_value=session))
        client.session = session

        # Authentication runs but never flips is_authenticated
        monkeypatch.setattr(client, "_handle_authentication", AsyncMock())

        assert await client.connect() is False
        client.on_connect.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_send_message_refused_when_not_authenticated(self):
        """
        GIVEN: A connected but unauthenticated client
        WHEN: send_message() is called
        THEN: It refuses to send
        """
        from src.websocket_client import HomeAssistantWebSocketClient

        client = HomeAssistantWebSocketClient("http://localhost:8123", VALID_TOKEN)
        client.is_connected = True
        client.is_authenticated = False

        assert await client.send_message({"type": "ping"}) is False

    @pytest.mark.asyncio
    async def test_connection_manager_records_failed_connection(self):
        """
        GIVEN: The underlying client reports a failed connection
        WHEN: ConnectionManager._connect() runs
        THEN: The failure is counted and the attempt counter advances by exactly one
        """
        from src.connection_manager import ConnectionManager

        manager = ConnectionManager(base_url="http://localhost:8123", token=VALID_TOKEN)
        manager.client = MagicMock()
        manager.client.connect = AsyncMock(return_value=False)

        assert await manager._connect() is False
        assert manager.connection_attempts == 1
        assert manager.failed_connections == 1
        assert manager.successful_connections == 0

    @pytest.mark.asyncio
    async def test_connection_manager_records_connection_exception(self):
        """
        GIVEN: The underlying client raises
        WHEN: ConnectionManager._connect() runs
        THEN: The error is captured and logged against the current attempt number
        """
        from src.connection_manager import ConnectionManager

        manager = ConnectionManager(base_url="http://localhost:8123", token=VALID_TOKEN)
        manager.client = MagicMock()
        manager.client.connect = AsyncMock(side_effect=ConnectionError("boom"))
        manager.error_handler = MagicMock()

        assert await manager._connect() is False
        assert manager.last_error == "boom"
        assert manager.failed_connections == 1

        _, context = manager.error_handler.log_error.call_args[0]
        assert context["connection_attempt"] == manager.connection_attempts


class TestInfluxDBWriteFailures:
    """Test InfluxDB write failure scenarios"""

    def _writer(self, **kwargs):
        from src.influxdb_batch_writer import InfluxDBBatchWriter

        manager = MagicMock()
        manager.write_points = AsyncMock(return_value=True)
        writer = InfluxDBBatchWriter(
            connection_manager=manager,
            retry_delay=0,
            **kwargs,
        )
        writer.schema = _stub_schema()
        return writer, manager

    @pytest.mark.asyncio
    async def test_influxdb_connection_failure_is_retried_then_reported(self):
        """
        GIVEN: InfluxDB is unreachable
        WHEN: A batch is written
        THEN: The write is retried max_retries times and reported as failed
        """
        writer, manager = self._writer(max_retries=3)
        manager.write_points = AsyncMock(side_effect=ConnectionError("Connection refused"))

        assert await writer._write_batch([{"id": 1}]) is False
        assert manager.write_points.await_count == 3

    @pytest.mark.asyncio
    async def test_influxdb_write_timeout_is_handled(self):
        """
        GIVEN: An InfluxDB write times out
        WHEN: A batch is written
        THEN: The timeout is swallowed into a False result, not propagated
        """
        writer, manager = self._writer(max_retries=2)
        manager.write_points = AsyncMock(side_effect=TimeoutError("Write timeout"))

        assert await writer._write_batch([{"id": 1}]) is False
        assert manager.write_points.await_count == 2

    @pytest.mark.asyncio
    async def test_failed_batch_counts_points_as_failed(self):
        """
        GIVEN: A batch that InfluxDB rejects
        WHEN: The batch is processed
        THEN: Every point is counted against total_points_failed
        """
        writer, manager = self._writer(max_retries=1)
        manager.write_points = AsyncMock(return_value=False)

        await writer._process_batch_with_metrics([{"id": 1}, {"id": 2}])

        assert writer.total_points_failed == 2
        assert writer.total_batches_written == 0

    @pytest.mark.asyncio
    async def test_batch_of_invalid_points_is_not_written(self):
        """
        GIVEN: Every point in a batch fails schema validation
        WHEN: The batch is written
        THEN: Nothing is sent to InfluxDB and the write reports failure
        """
        writer, manager = self._writer(max_retries=1)
        writer.schema = _stub_schema(valid=False)

        assert await writer._write_batch([{"id": 1}]) is False
        manager.write_points.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_unserializable_event_is_rejected_not_raised(self):
        """
        GIVEN: Point creation raises for a malformed event
        WHEN: write_event() is called
        THEN: It returns False instead of propagating
        """
        writer, _ = self._writer()
        writer.schema.create_event_point.side_effect = ValueError("bad event")

        assert await writer.write_event({"id": 1}) is False


class TestDiscoveryServiceFailures:
    """Test discovery service failure scenarios"""

    @pytest.mark.asyncio
    async def test_discovery_http_api_failure_returns_empty(self, monkeypatch):
        """
        GIVEN: The HTTP discovery fallback fails
        WHEN: Devices are discovered with no transport available
        THEN: An empty list is returned rather than an exception
        """
        from src.discovery_service import DiscoveryService

        discovery = DiscoveryService()
        monkeypatch.setattr(
            discovery,
            "_discover_devices_http",
            AsyncMock(side_effect=ConnectionError("API unavailable")),
        )

        assert await discovery.discover_devices() == []

    @pytest.mark.asyncio
    async def test_discovery_failure_leaves_existing_cache_intact(self, monkeypatch):
        """
        GIVEN: A populated device/area cache and a failing discovery
        WHEN: Discovery runs again and fails
        THEN: The previously cached mappings survive
        """
        from src.discovery_service import DiscoveryService

        discovery = DiscoveryService()
        discovery.device_to_area["dev1"] = "kitchen"
        discovery.entity_to_device["light.kitchen"] = "dev1"

        monkeypatch.setattr(discovery, "_discover_devices_http", AsyncMock(return_value=[]))

        assert await discovery.discover_devices() == []
        assert discovery.device_to_area["dev1"] == "kitchen"
        assert discovery.get_device_id("light.kitchen") == "dev1"


class TestNetworkTimeoutScenarios:
    """Test network timeout scenarios"""

    @pytest.mark.asyncio
    async def test_http_client_timeout_returns_false(self, monkeypatch):
        """
        GIVEN: Every HTTP attempt times out
        WHEN: An event is sent
        THEN: send_event reports failure and counts it
        """
        from src.http_client import SimpleHTTPClient

        client = SimpleHTTPClient(enrichment_url="http://localhost:8123")
        client.session = MagicMock()
        client.session.post = MagicMock(side_effect=TimeoutError("Request timeout"))
        monkeypatch.setattr(asyncio, "sleep", AsyncMock())

        assert await client.send_event({"event": "test"}) is False
        assert client.failed_requests == 1
        assert client.consecutive_failures == 1

    @pytest.mark.asyncio
    async def test_http_client_opens_circuit_after_repeated_failures(self, monkeypatch):
        """
        GIVEN: Failures reach max_consecutive_failures
        WHEN: A further event is sent
        THEN: The circuit is open and the request fails fast without a network call
        """
        from src.http_client import SimpleHTTPClient

        client = SimpleHTTPClient(enrichment_url="http://localhost:8123")
        client.session = MagicMock()
        client.session.post = MagicMock(side_effect=ConnectionError("down"))
        monkeypatch.setattr(asyncio, "sleep", AsyncMock())

        for _ in range(client.max_consecutive_failures):
            await client.send_event({"event": "test"})

        assert client.circuit_open is True

        client.session.post.reset_mock()
        assert await client.send_event({"event": "test"}) is False
        client.session.post.assert_not_called()


class TestQueueOverflowScenarios:
    """Test queue overflow scenarios"""

    @pytest.mark.asyncio
    async def test_event_queue_at_capacity_diverts_to_overflow(self):
        """
        GIVEN: An event queue filled to capacity
        WHEN: Another event is enqueued
        THEN: put() reports False and the event lands in the overflow buffer
        """
        from src.event_queue import EventQueue

        queue = EventQueue(maxsize=10)

        for i in range(10):
            assert await queue.put({"event_id": i}) is True

        assert queue.queue.qsize() == 10

        assert await queue.put({"event_id": 10}) is False
        assert queue.overflow_events == 1
        assert len(queue.overflow_queue) == 1
        assert queue.overflow_queue[0]["data"]["event_id"] == 10

    @pytest.mark.asyncio
    async def test_event_queue_statistics_report_overflow(self):
        """
        GIVEN: A queue that has overflowed
        WHEN: Statistics are read
        THEN: Received and overflow counts are reflected
        """
        from src.event_queue import EventQueue

        queue = EventQueue(maxsize=2)
        for i in range(4):
            await queue.put({"event_id": i})

        stats = queue.get_queue_statistics()
        assert stats["total_events_received"] == 4
        assert stats["overflow_events"] == 2

    @pytest.mark.asyncio
    async def test_batch_processor_flushes_at_batch_size(self):
        """
        GIVEN: A batch processor with a registered handler
        WHEN: Enough events arrive to fill a batch
        THEN: The handler receives exactly one full batch and the remainder is held
        """
        from src.batch_processor import BatchProcessor

        processor = BatchProcessor(batch_size=10, batch_timeout=5.0)
        batches = []
        processor.add_batch_handler(AsyncMock(side_effect=lambda b: batches.append(list(b))))

        for i in range(12):
            assert await processor.add_event({"event_id": i}) is True

        assert len(batches) == 1
        assert len(batches[0]) == 10
        assert len(processor.current_batch) == 2
        assert processor.total_events_processed == 10

    @pytest.mark.asyncio
    async def test_batch_processor_counts_handler_failures(self):
        """
        GIVEN: A batch handler that always raises
        WHEN: A batch is flushed
        THEN: Retries are exhausted and the events are counted as failed
        """
        from src.batch_processor import BatchProcessor

        processor = BatchProcessor(batch_size=2, batch_timeout=5.0)
        processor.retry_delay = 0
        handler = AsyncMock(side_effect=RuntimeError("handler down"))
        processor.add_batch_handler(handler)

        for i in range(2):
            await processor.add_event({"event_id": i})

        assert handler.await_count == processor.retry_attempts
        assert processor.total_events_failed == 2
        assert processor.total_batches_processed == 0


class TestRetryLogic:
    """Test retry logic scenarios"""

    def test_reconnect_delay_grows_exponentially(self):
        """
        GIVEN: Consecutive reconnection attempts
        WHEN: The backoff delay is computed
        THEN: It grows with each retry and is capped at max_delay
        """
        from src.connection_manager import ConnectionManager

        manager = ConnectionManager(base_url="http://localhost:8123", token=VALID_TOKEN)
        manager.base_delay = 1.0
        manager.max_delay = 10.0
        manager.jitter_range = 0.0  # deterministic for the growth assertion

        manager.current_retry_count = 1
        first = manager._calculate_delay()
        manager.current_retry_count = 2
        second = manager._calculate_delay()

        assert second > first

        # max_delay is a hard ceiling even once jitter is applied
        manager.jitter_range = 0.1
        manager.current_retry_count = 20
        assert all(manager._calculate_delay() <= manager.max_delay for _ in range(50))

    @pytest.mark.asyncio
    async def test_reconnect_loop_stops_at_max_retries(self, monkeypatch):
        """
        GIVEN: Every reconnection attempt fails
        WHEN: The reconnect loop runs
        THEN: It gives up after max_retries attempts instead of looping forever
        """
        from src.connection_manager import ConnectionManager
        from src.state_machine import ConnectionState

        manager = ConnectionManager(base_url="http://localhost:8123", token=VALID_TOKEN)
        manager.max_retries = 3
        # FAILED is a legal source state for RECONNECTING
        manager.state_machine.transition(ConnectionState.FAILED, force=True)
        monkeypatch.setattr(manager, "_calculate_delay", lambda: 0)
        connect = AsyncMock(return_value=False)
        monkeypatch.setattr(manager, "_connect", connect)

        await manager._reconnect_loop()

        assert connect.await_count == 3
        assert manager.current_retry_count == 3
