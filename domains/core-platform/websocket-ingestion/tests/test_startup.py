"""
Unit tests for websocket-ingestion startup helpers (_startup.py).

Covers the three startup phases:
  - start_processing_components
  - start_influxdb_pipeline
  - start_ha_connection

All external dependencies are mocked; these are pure unit tests.
"""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_svc(**extra_attrs: Any) -> MagicMock:
    """Return a minimal mock service object.

    The real service stores configuration under `svc.cfg`, so we build that
    as a simple MagicMock with sensible defaults for every attribute that
    _startup.py reads.
    """
    cfg = MagicMock()
    cfg.max_memory_mb = 512
    cfg.batch_size = 100
    cfg.batch_timeout = 5.0
    cfg.max_workers = 4
    cfg.processing_rate_limit = 500
    cfg.influxdb_url = "http://influxdb:8086"
    cfg.influxdb_token = "test-token"
    cfg.influxdb_org = "test-org"
    cfg.influxdb_bucket = "test-bucket"
    cfg.influxdb_max_pending_points = 50000
    cfg.influxdb_overflow_strategy = "drop_oldest"

    svc = MagicMock()
    svc.cfg = cfg
    svc._process_batch = AsyncMock()
    svc._write_event_to_influxdb = AsyncMock()
    svc._on_connect = AsyncMock()
    svc._on_disconnect = AsyncMock()
    svc._on_message = AsyncMock()
    svc._on_error = AsyncMock()
    svc._on_event = AsyncMock()
    svc._check_connection_status = AsyncMock(return_value=True)

    for key, value in extra_attrs.items():
        setattr(svc, key, value)

    return svc


# ---------------------------------------------------------------------------
# Module-level patches applied to the entire test module
# ---------------------------------------------------------------------------

MODULE = "src._startup"

# Shared patch targets
_MEMORY_MANAGER = f"{MODULE}.MemoryManager"
_EVENT_QUEUE = f"{MODULE}.EventQueue"
_BATCH_PROCESSOR = f"{MODULE}.BatchProcessor"
_ASYNC_EVENT_PROCESSOR = f"{MODULE}.AsyncEventProcessor"
_HOUSE_STATUS_AGGREGATOR = f"{MODULE}.HouseStatusAggregator"
_STATUS_WS_PUBLISHER = f"{MODULE}.StatusWebSocketPublisher"
_INFLUXDB_CONN_MANAGER = f"{MODULE}.InfluxDBConnectionManager"
_HISTORICAL_COUNTER = f"{MODULE}.HistoricalEventCounter"
_HA_CONN_MANAGER = f"{MODULE}.ha_connection_manager"
_CONNECTION_MANAGER = f"{MODULE}.ConnectionManager"
_LOG_WITH_CONTEXT = f"{MODULE}.log_with_context"
_ASYNCIO_SLEEP = f"{MODULE}.asyncio.sleep"
# InfluxDBBatchWriter is imported inline inside start_influxdb_pipeline, so
# we must patch at its definition module rather than the startup module.
_INFLUXDB_BATCH_WRITER = "src.influxdb_batch_writer.InfluxDBBatchWriter"


# ---------------------------------------------------------------------------
# Tests: start_processing_components
# ---------------------------------------------------------------------------

class TestStartProcessingComponents:
    """Tests for the start_processing_components startup phase."""

    @pytest.fixture(autouse=True)
    def patch_log(self):
        with patch(_LOG_WITH_CONTEXT):
            yield

    async def test_creates_memory_manager(self):
        """MemoryManager is created with max_memory_mb from config."""
        svc = make_svc()
        mock_mm = AsyncMock()

        with patch(_MEMORY_MANAGER, return_value=mock_mm) as MockMM, \
             patch(_EVENT_QUEUE, return_value=MagicMock()), \
             patch(_BATCH_PROCESSOR, return_value=AsyncMock()), \
             patch(_ASYNC_EVENT_PROCESSOR, return_value=AsyncMock()), \
             patch(_HOUSE_STATUS_AGGREGATOR, return_value=MagicMock()), \
             patch(_STATUS_WS_PUBLISHER, return_value=AsyncMock()):

            from src._startup import start_processing_components
            await start_processing_components(svc, "corr-001")

        MockMM.assert_called_once_with(max_memory_mb=svc.cfg.max_memory_mb)
        assert svc.memory_manager is mock_mm

    async def test_creates_event_queue(self):
        """EventQueue is created with maxsize=10000."""
        svc = make_svc()
        mock_eq = MagicMock()

        with patch(_MEMORY_MANAGER, return_value=AsyncMock()), \
             patch(_EVENT_QUEUE, return_value=mock_eq) as MockEQ, \
             patch(_BATCH_PROCESSOR, return_value=AsyncMock()), \
             patch(_ASYNC_EVENT_PROCESSOR, return_value=AsyncMock()), \
             patch(_HOUSE_STATUS_AGGREGATOR, return_value=MagicMock()), \
             patch(_STATUS_WS_PUBLISHER, return_value=AsyncMock()):

            from src._startup import start_processing_components
            await start_processing_components(svc, "corr-001")

        MockEQ.assert_called_once_with(maxsize=10000)
        assert svc.event_queue is mock_eq

    async def test_creates_batch_processor(self):
        """BatchProcessor is created with batch_size and batch_timeout from config."""
        svc = make_svc()
        mock_bp = AsyncMock()

        with patch(_MEMORY_MANAGER, return_value=AsyncMock()), \
             patch(_EVENT_QUEUE, return_value=MagicMock()), \
             patch(_BATCH_PROCESSOR, return_value=mock_bp) as MockBP, \
             patch(_ASYNC_EVENT_PROCESSOR, return_value=AsyncMock()), \
             patch(_HOUSE_STATUS_AGGREGATOR, return_value=MagicMock()), \
             patch(_STATUS_WS_PUBLISHER, return_value=AsyncMock()):

            from src._startup import start_processing_components
            await start_processing_components(svc, "corr-001")

        MockBP.assert_called_once_with(
            batch_size=svc.cfg.batch_size,
            batch_timeout=svc.cfg.batch_timeout,
        )
        assert svc.batch_processor is mock_bp

    async def test_creates_async_event_processor(self):
        """AsyncEventProcessor is created with max_workers and processing_rate_limit."""
        svc = make_svc()
        mock_aep = AsyncMock()

        with patch(_MEMORY_MANAGER, return_value=AsyncMock()), \
             patch(_EVENT_QUEUE, return_value=MagicMock()), \
             patch(_BATCH_PROCESSOR, return_value=AsyncMock()), \
             patch(_ASYNC_EVENT_PROCESSOR, return_value=mock_aep) as MockAEP, \
             patch(_HOUSE_STATUS_AGGREGATOR, return_value=MagicMock()), \
             patch(_STATUS_WS_PUBLISHER, return_value=AsyncMock()):

            from src._startup import start_processing_components
            await start_processing_components(svc, "corr-001")

        MockAEP.assert_called_once_with(
            max_workers=svc.cfg.max_workers,
            processing_rate_limit=svc.cfg.processing_rate_limit,
        )
        assert svc.async_event_processor is mock_aep

    async def test_starts_all_components(self):
        """start() is called on memory_manager, batch_processor, and async_event_processor."""
        svc = make_svc()
        mock_mm = AsyncMock()
        mock_bp = AsyncMock()
        mock_aep = AsyncMock()

        with patch(_MEMORY_MANAGER, return_value=mock_mm), \
             patch(_EVENT_QUEUE), \
             patch(_BATCH_PROCESSOR, return_value=mock_bp), \
             patch(_ASYNC_EVENT_PROCESSOR, return_value=mock_aep), \
             patch(_HOUSE_STATUS_AGGREGATOR), \
             patch(_STATUS_WS_PUBLISHER):

            from src._startup import start_processing_components
            await start_processing_components(svc, "corr-001")

        mock_mm.start.assert_awaited_once()
        mock_bp.start.assert_awaited_once()
        mock_aep.start.assert_awaited_once()

    async def test_adds_batch_handler(self):
        """batch_processor.add_batch_handler is called with svc._process_batch."""
        svc = make_svc()
        mock_bp = AsyncMock()

        with patch(_MEMORY_MANAGER, return_value=AsyncMock()), \
             patch(_EVENT_QUEUE), \
             patch(_BATCH_PROCESSOR, return_value=mock_bp), \
             patch(_ASYNC_EVENT_PROCESSOR, return_value=AsyncMock()), \
             patch(_HOUSE_STATUS_AGGREGATOR), \
             patch(_STATUS_WS_PUBLISHER):

            from src._startup import start_processing_components
            await start_processing_components(svc, "corr-001")

        mock_bp.add_batch_handler.assert_called_once_with(svc._process_batch)

    async def test_creates_house_status_aggregator_and_publisher(self):
        """HouseStatusAggregator and StatusWebSocketPublisher are created and started."""
        svc = make_svc()
        mock_agg = MagicMock()
        mock_pub = AsyncMock()

        with patch(_MEMORY_MANAGER, return_value=AsyncMock()), \
             patch(_EVENT_QUEUE), \
             patch(_BATCH_PROCESSOR, return_value=AsyncMock()), \
             patch(_ASYNC_EVENT_PROCESSOR, return_value=AsyncMock()), \
             patch(_HOUSE_STATUS_AGGREGATOR, return_value=mock_agg), \
             patch(_STATUS_WS_PUBLISHER, return_value=mock_pub):

            from src._startup import start_processing_components
            await start_processing_components(svc, "corr-001")

        assert svc.house_status_aggregator is mock_agg
        assert svc.house_status_publisher is mock_pub
        mock_pub.start.assert_awaited_once()

    async def test_house_status_init_failure_is_non_fatal(self):
        """If HouseStatusAggregator raises, aggregator and publisher are set to None."""
        svc = make_svc()

        with patch(_MEMORY_MANAGER, return_value=AsyncMock()), \
             patch(_EVENT_QUEUE), \
             patch(_BATCH_PROCESSOR, return_value=AsyncMock()), \
             patch(_ASYNC_EVENT_PROCESSOR, return_value=AsyncMock()), \
             patch(_HOUSE_STATUS_AGGREGATOR, side_effect=RuntimeError("init failed")), \
             patch(_STATUS_WS_PUBLISHER):

            from src._startup import start_processing_components
            # Must not raise
            await start_processing_components(svc, "corr-001")

        assert svc.house_status_aggregator is None
        assert svc.house_status_publisher is None


# ---------------------------------------------------------------------------
# Tests: start_influxdb_pipeline
# ---------------------------------------------------------------------------

class TestStartInfluxdbPipeline:
    """Tests for the start_influxdb_pipeline startup phase."""

    @pytest.fixture(autouse=True)
    def patch_log(self):
        with patch(_LOG_WITH_CONTEXT):
            yield

    def _make_mock_batch_writer(self) -> MagicMock:
        mock = AsyncMock()
        return mock

    async def test_creates_influxdb_connection_manager_with_correct_params(self):
        """InfluxDBConnectionManager is constructed with URL/token/org/bucket from config."""
        svc = make_svc()
        mock_mgr = AsyncMock()

        batch_writer_mock = AsyncMock()
        historical_mock = AsyncMock()
        historical_mock.initialize_historical_totals = AsyncMock(
            return_value={"total_events_received": 0}
        )

        with patch(_INFLUXDB_CONN_MANAGER, return_value=mock_mgr) as MockMgr, \
             patch(_HISTORICAL_COUNTER, return_value=historical_mock), \
             patch(_INFLUXDB_BATCH_WRITER, return_value=batch_writer_mock):

            from src._startup import start_influxdb_pipeline
            await start_influxdb_pipeline(svc, "corr-002")

        MockMgr.assert_called_once_with(
            url=svc.cfg.influxdb_url,
            token=svc.cfg.influxdb_token,
            org=svc.cfg.influxdb_org,
            bucket=svc.cfg.influxdb_bucket,
        )
        assert svc.influxdb_manager is mock_mgr

    async def test_starts_influxdb_manager_and_initializes_historical_counter(self):
        """influxdb_manager.start() is awaited and historical totals are initialized."""
        svc = make_svc()
        mock_mgr = AsyncMock()
        historical_mock = AsyncMock()
        historical_mock.initialize_historical_totals = AsyncMock(
            return_value={"total_events_received": 42}
        )
        batch_writer_mock = AsyncMock()

        with patch(_INFLUXDB_CONN_MANAGER, return_value=mock_mgr), \
             patch(_HISTORICAL_COUNTER, return_value=historical_mock) as MockHC, \
             patch(_INFLUXDB_BATCH_WRITER, return_value=batch_writer_mock):

            from src._startup import start_influxdb_pipeline
            await start_influxdb_pipeline(svc, "corr-002")

        mock_mgr.start.assert_awaited_once()
        MockHC.assert_called_once_with(mock_mgr)
        historical_mock.initialize_historical_totals.assert_awaited_once()
        assert svc.historical_counter is historical_mock

    async def test_creates_and_starts_influxdb_batch_writer(self):
        """InfluxDBBatchWriter is created with expected params and started."""
        svc = make_svc()
        mock_mgr = AsyncMock()
        historical_mock = AsyncMock()
        historical_mock.initialize_historical_totals = AsyncMock(
            return_value={"total_events_received": 0}
        )
        batch_writer_mock = AsyncMock()

        with patch(_INFLUXDB_CONN_MANAGER, return_value=mock_mgr), \
             patch(_HISTORICAL_COUNTER, return_value=historical_mock), \
             patch(_INFLUXDB_BATCH_WRITER, return_value=batch_writer_mock) as MockBW:

            from src._startup import start_influxdb_pipeline
            await start_influxdb_pipeline(svc, "corr-002")

        MockBW.assert_called_once_with(
            connection_manager=mock_mgr,
            batch_size=1000,
            batch_timeout=5.0,
            max_pending_points=svc.cfg.influxdb_max_pending_points,
            overflow_strategy=svc.cfg.influxdb_overflow_strategy,
        )
        batch_writer_mock.start.assert_awaited_once()
        assert svc.influxdb_batch_writer is batch_writer_mock

    async def test_adds_event_handler(self):
        """async_event_processor.add_event_handler is called with the influxdb write handler."""
        svc = make_svc()
        mock_aep = MagicMock()
        svc.async_event_processor = mock_aep

        mock_mgr = AsyncMock()
        historical_mock = AsyncMock()
        historical_mock.initialize_historical_totals = AsyncMock(
            return_value={"total_events_received": 0}
        )
        batch_writer_mock = AsyncMock()

        with patch(_INFLUXDB_CONN_MANAGER, return_value=mock_mgr), \
             patch(_HISTORICAL_COUNTER, return_value=historical_mock), \
             patch(_INFLUXDB_BATCH_WRITER, return_value=batch_writer_mock):

            from src._startup import start_influxdb_pipeline
            await start_influxdb_pipeline(svc, "corr-002")

        mock_aep.add_event_handler.assert_called_once_with(svc._write_event_to_influxdb)


# ---------------------------------------------------------------------------
# Tests: start_ha_connection
# ---------------------------------------------------------------------------

class TestStartHaConnection:
    """Tests for the start_ha_connection startup phase."""

    @pytest.fixture(autouse=True)
    def patch_log(self):
        with patch(_LOG_WITH_CONTEXT):
            yield

    async def test_standalone_mode_returns_early(self):
        """When home_assistant_enabled is False, function returns without connecting."""
        svc = make_svc(home_assistant_enabled=False)

        with patch(_HA_CONN_MANAGER) as mock_ha_mgr, \
             patch(_CONNECTION_MANAGER) as MockCM:

            from src._startup import start_ha_connection
            await start_ha_connection(svc, "corr-003")

        mock_ha_mgr.get_connection_with_circuit_breaker.assert_not_called()
        MockCM.assert_not_called()

    async def test_raises_value_error_when_no_ha_connections(self):
        """ValueError is raised when ha_connection_manager returns None/falsy."""
        svc = make_svc(home_assistant_enabled=True)

        mock_ha_mgr = AsyncMock()
        mock_ha_mgr.get_connection_with_circuit_breaker = AsyncMock(return_value=None)

        with patch(_HA_CONN_MANAGER, mock_ha_mgr):
            from src._startup import start_ha_connection
            with pytest.raises(ValueError, match="No Home Assistant connections available"):
                await start_ha_connection(svc, "corr-003")

    async def test_successful_connection_sets_up_callbacks(self):
        """On a successful connection, callbacks and connection_manager are wired up."""
        svc = make_svc(
            home_assistant_enabled=True,
            house_status_aggregator=None,
        )

        connection_config = MagicMock()
        connection_config.name = "local"
        connection_config.url = "ws://ha:8123/api/websocket"
        connection_config.token = "secret"

        mock_ha_mgr = AsyncMock()
        mock_ha_mgr.get_connection_with_circuit_breaker = AsyncMock(
            return_value=connection_config
        )

        mock_cm = AsyncMock()
        mock_cm.start = AsyncMock()

        with patch(_HA_CONN_MANAGER, mock_ha_mgr), \
             patch(_CONNECTION_MANAGER, return_value=mock_cm) as MockCM, \
             patch(_ASYNCIO_SLEEP):

            from src._startup import start_ha_connection
            await start_ha_connection(svc, "corr-003")

        MockCM.assert_called_once_with(
            connection_config.url,
            connection_config.token,
            influxdb_manager=svc.influxdb_manager,
        )
        mock_cm.start.assert_awaited_once()

        # Verify all five callbacks are wired
        assert svc.connection_manager.on_connect is svc._on_connect
        assert svc.connection_manager.on_disconnect is svc._on_disconnect
        assert svc.connection_manager.on_message is svc._on_message
        assert svc.connection_manager.on_error is svc._on_error
        assert svc.connection_manager.on_event is svc._on_event

    async def test_raises_connection_error_when_connection_check_fails(self):
        """ConnectionError is raised when _check_connection_status returns False."""
        svc = make_svc(
            home_assistant_enabled=True,
            house_status_aggregator=None,
        )
        svc._check_connection_status = AsyncMock(return_value=False)

        connection_config = MagicMock()
        connection_config.name = "local"
        connection_config.url = "ws://ha:8123/api/websocket"
        connection_config.token = "secret"

        mock_ha_mgr = AsyncMock()
        mock_ha_mgr.get_connection_with_circuit_breaker = AsyncMock(
            return_value=connection_config
        )

        mock_cm = AsyncMock()
        mock_cm.start = AsyncMock()

        with patch(_HA_CONN_MANAGER, mock_ha_mgr), \
             patch(_CONNECTION_MANAGER, return_value=mock_cm), \
             patch(_ASYNCIO_SLEEP):

            from src._startup import start_ha_connection
            with pytest.raises(ConnectionError, match="Could not connect to Home Assistant"):
                await start_ha_connection(svc, "corr-003")
