"""Startup helpers for WebSocketIngestionService.

Houses the three startup phases so that ``main.py`` stays concise.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from homeiq_ha.enhanced_ha_connection_manager import ha_connection_manager
from homeiq_observability.logging_config import (
    log_with_context,
    setup_logging,
)

from .async_event_processor import AsyncEventProcessor
from .batch_processor import BatchProcessor
from .connection_manager import ConnectionManager
from .event_queue import EventQueue
from .historical_event_counter import HistoricalEventCounter
from .house_status import HouseStatusAggregator, StatusWebSocketPublisher
from .influxdb_wrapper import InfluxDBConnectionManager
from .memory_manager import MemoryManager

if TYPE_CHECKING:
    from ._service_config import ServiceConfig

logger = setup_logging("websocket-ingestion")


async def start_processing_components(
    svc: Any,
    corr_id: str,
) -> None:
    """Initialize and start high-volume processing components."""
    cfg: ServiceConfig = svc.cfg
    svc.memory_manager = MemoryManager(max_memory_mb=cfg.max_memory_mb)
    svc.event_queue = EventQueue(maxsize=10000)
    svc.batch_processor = BatchProcessor(
        batch_size=cfg.batch_size,
        batch_timeout=cfg.batch_timeout,
    )
    svc.async_event_processor = AsyncEventProcessor(
        max_workers=cfg.max_workers,
        processing_rate_limit=cfg.processing_rate_limit,
    )

    await svc.memory_manager.start()
    await svc.batch_processor.start()
    await svc.async_event_processor.start()

    log_with_context(
        logger, "INFO", "High-volume processing components started",
        operation="component_startup",
        correlation_id=corr_id,
    )

    svc.batch_processor.add_batch_handler(svc._process_batch)

    # Epic 28: House status aggregation (optional layer — never blocks startup)
    try:
        svc.house_status_aggregator = HouseStatusAggregator()
        svc.house_status_publisher = StatusWebSocketPublisher()
        await svc.house_status_publisher.start()
        log_with_context(
            logger, "INFO", "House status aggregator + publisher started",
            operation="house_status_startup",
            correlation_id=corr_id,
        )
    except Exception as exc:
        logger.warning("House status aggregation init failed (non-fatal): %s", exc)
        svc.house_status_aggregator = None
        svc.house_status_publisher = None


async def start_influxdb_pipeline(
    svc: Any,
    corr_id: str,
) -> None:
    """Initialize InfluxDB manager, historical counter, and batch writer."""
    cfg: ServiceConfig = svc.cfg
    svc.influxdb_manager = InfluxDBConnectionManager(
        url=cfg.influxdb_url,
        token=cfg.influxdb_token,
        org=cfg.influxdb_org,
        bucket=cfg.influxdb_bucket,
    )
    await svc.influxdb_manager.start()
    log_with_context(
        logger, "INFO", "InfluxDB manager started",
        operation="influxdb_connection",
        correlation_id=corr_id,
    )

    svc.historical_counter = HistoricalEventCounter(svc.influxdb_manager)
    historical_totals = await svc.historical_counter.initialize_historical_totals()
    log_with_context(
        logger, "INFO", "Historical event totals initialized",
        operation="historical_counter_init",
        correlation_id=corr_id,
        total_events=historical_totals.get("total_events_received", 0),
    )

    from .influxdb_batch_writer import InfluxDBBatchWriter

    svc.influxdb_batch_writer = InfluxDBBatchWriter(
        connection_manager=svc.influxdb_manager,
        batch_size=1000,
        batch_timeout=5.0,
        max_pending_points=cfg.influxdb_max_pending_points,
        overflow_strategy=cfg.influxdb_overflow_strategy,
    )
    await svc.influxdb_batch_writer.start()
    log_with_context(
        logger, "INFO", "InfluxDB batch writer started",
        operation="influxdb_batch_writer_startup",
        correlation_id=corr_id,
    )

    svc.async_event_processor.add_event_handler(svc._write_event_to_influxdb)


async def start_ha_connection(
    svc: Any,
    corr_id: str,
) -> None:
    """Connect to Home Assistant if enabled, otherwise log standalone mode."""
    if not svc.home_assistant_enabled:
        log_with_context(
            logger, "INFO",
            "Home Assistant connection disabled - running in standalone mode",
            operation="ha_connection_startup",
            correlation_id=corr_id,
            mode="standalone",
        )
        return

    connection_config = await ha_connection_manager.get_connection_with_circuit_breaker()
    if not connection_config:
        raise ValueError(
            "No Home Assistant connections available. "
            "Configure HA_HTTP_URL/HA_WS_URL + HA_TOKEN or NABU_CASA_URL + NABU_CASA_TOKEN"
        )

    logger.info(
        "Using HA connection: %s (%s)",
        connection_config.name,
        connection_config.url,
        extra={"correlation_id": corr_id},
    )

    svc.connection_manager = ConnectionManager(
        connection_config.url,
        connection_config.token,
        influxdb_manager=svc.influxdb_manager,
    )

    svc.connection_manager.on_connect = svc._on_connect
    svc.connection_manager.on_disconnect = svc._on_disconnect
    svc.connection_manager.on_message = svc._on_message
    svc.connection_manager.on_error = svc._on_error
    svc.connection_manager.on_event = svc._on_event

    await svc.connection_manager.start()
    await asyncio.sleep(2)

    if not await svc._check_connection_status():
        logger.error(
            "Failed to establish Home Assistant connection",
            extra={"correlation_id": corr_id},
        )
        raise ConnectionError("Could not connect to Home Assistant")

    # Epic 28: Wire discovery service into house status aggregator for area lookups.
    if svc.house_status_aggregator and svc.connection_manager:
        svc.house_status_aggregator._discovery = (
            svc.connection_manager.discovery_service
        )

    log_with_context(
        logger, "INFO", "Home Assistant connection manager started",
        operation="ha_connection_startup",
        correlation_id=corr_id,
        connection_name=connection_config.name,
        url=connection_config.url,
    )
