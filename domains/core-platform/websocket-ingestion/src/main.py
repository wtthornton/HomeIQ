"""WebSocket Ingestion Service — main entry point.

Tier-1 critical service: all Home Assistant events flow through here.
Events are received via WebSocket, filtered, batched, and written to
InfluxDB for downstream consumption by data-api and other services.

Architecture:
    _service_config.py  — environment-based configuration
    _event_handlers.py  — HA event callback mixin
    _startup.py         — async startup phases
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from dotenv import load_dotenv
from homeiq_observability.logging_config import (
    generate_correlation_id,
    log_error_with_context,
    log_with_context,
    performance_monitor,
    set_correlation_id,
    setup_logging,
)

from ._event_handlers import EventHandlerMixin
from ._service_config import ServiceConfig
from ._startup import (
    start_ha_connection,
    start_influxdb_pipeline,
    start_processing_components,
)
from .async_event_processor import AsyncEventProcessor  # noqa: F401, TC001
from .batch_processor import BatchProcessor  # noqa: F401, TC001
from .connection_manager import ConnectionManager  # noqa: F401, TC001
from .entity_filter import EntityFilter
from .event_queue import EventQueue  # noqa: F401, TC001
from .health_check import HealthCheckHandler
from .historical_event_counter import HistoricalEventCounter  # noqa: F401, TC001
from .house_status import HouseStatusAggregator, StatusWebSocketPublisher  # noqa: TC001
from .influxdb_wrapper import InfluxDBConnectionManager  # noqa: F401, TC001
from .memory_manager import MemoryManager  # noqa: F401, TC001

if TYPE_CHECKING:
    from .http_client import SimpleHTTPClient

# Module-level initialisation
load_dotenv()
logger = setup_logging("websocket-ingestion")


# -- entity filter loader (pure function) ------------------------------------

def _load_entity_filter() -> EntityFilter | None:
    """Return an ``EntityFilter`` from env/file config, or ``None``."""
    env_json = os.getenv("ENTITY_FILTER_CONFIG")
    if env_json:
        return EntityFilter(json.loads(env_json))
    cfg_path = Path(os.getenv("ENTITY_FILTER_CONFIG_FILE", "config/entity_filter.json"))
    if cfg_path.exists():
        with cfg_path.open() as fh:
            return EntityFilter(json.load(fh))
    return None


# -- service class ------------------------------------------------------------

class WebSocketIngestionService(EventHandlerMixin):
    """Orchestrates WebSocket ingestion lifecycle.

    Event callbacks are provided by ``EventHandlerMixin``.
    Startup phases are delegated to ``_startup`` helpers.
    """

    def __init__(self, config: ServiceConfig | None = None) -> None:
        self.cfg = config or ServiceConfig()
        self.start_time = datetime.now(UTC)

        # Health handler (linked back for statistics)
        self.health_handler = HealthCheckHandler()
        self.health_handler.websocket_service = self

        # Runtime components (populated in start())
        self.connection_manager: ConnectionManager | None = None
        self.async_event_processor: AsyncEventProcessor | None = None
        self.event_queue: EventQueue | None = None
        self.batch_processor: BatchProcessor | None = None
        self.memory_manager: MemoryManager | None = None
        self.http_client: SimpleHTTPClient | None = None
        self.influxdb_manager: InfluxDBConnectionManager | None = None
        self.historical_counter: HistoricalEventCounter | None = None

        # House status aggregation (Epic 28 — optional layer)
        self.house_status_aggregator: HouseStatusAggregator | None = None
        self.house_status_publisher: StatusWebSocketPublisher | None = None

        # Proxied config for tests / health handler
        self.home_assistant_url = self.cfg.home_assistant_url
        self.home_assistant_ws_url = self.cfg.home_assistant_ws_url
        self.home_assistant_token = self.cfg.home_assistant_token
        self.home_assistant_enabled = self.cfg.home_assistant_enabled

        # Config proxies — keep tests and health handler working
        self.max_workers = self.cfg.max_workers
        self.processing_rate_limit = self.cfg.processing_rate_limit
        self.batch_size = self.cfg.batch_size
        self.batch_timeout = self.cfg.batch_timeout
        self.max_memory_mb = self.cfg.max_memory_mb
        self.influxdb_url = self.cfg.influxdb_url
        self.influxdb_token = self.cfg.influxdb_token
        self.influxdb_org = self.cfg.influxdb_org
        self.influxdb_bucket = self.cfg.influxdb_bucket

        # Entity filter (Epic 45.2)
        try:
            self.entity_filter: EntityFilter | None = _load_entity_filter()
        except Exception as exc:
            logger.warning("Entity filter init failed: %s", exc)
            self.entity_filter = None

    # -- lifecycle ------------------------------------------------------------

    @performance_monitor("service_startup")
    async def start(self) -> None:
        """Start all processing components and optionally connect to HA."""
        cid = generate_correlation_id()
        set_correlation_id(cid)
        log_with_context(logger, "INFO", "Starting WebSocket Ingestion Service",
                         operation="service_startup", correlation_id=cid)
        try:
            await start_processing_components(self, cid)
            await start_influxdb_pipeline(self, cid)
            await start_ha_connection(self, cid)
            self.health_handler.set_connection_manager(self.connection_manager)
            self.health_handler.set_historical_counter(self.historical_counter)
            log_with_context(logger, "INFO", "Service started successfully",
                             operation="service_startup_complete", correlation_id=cid)
        except Exception as exc:
            log_error_with_context(logger, "Startup failed", exc,
                                   operation="service_startup", correlation_id=cid)
            raise

    async def stop(self) -> None:
        """Stop all components; errors are logged, never re-raised."""
        logger.info("Stopping WebSocket Ingestion Service...")
        for name, comp in [
            ("house_status_publisher", self.house_status_publisher),
            ("async_event_processor", self.async_event_processor),
            ("batch_processor", self.batch_processor),
            ("memory_manager", self.memory_manager),
            ("influxdb_batch_writer", getattr(self, "influxdb_batch_writer", None)),
            ("influxdb_manager", self.influxdb_manager),
            ("connection_manager", self.connection_manager),
        ]:
            if comp is not None:
                try:
                    await comp.stop()
                except Exception as exc:
                    logger.error("Error stopping %s: %s", name, exc)
        logger.info("WebSocket Ingestion Service stopped")

    async def _check_connection_status(self) -> bool:
        """Return ``True`` only when the underlying WebSocket is open."""
        if not self.connection_manager or not self.connection_manager.client:
            return False
        client = self.connection_manager.client
        return (
            hasattr(client, "websocket")
            and client.websocket is not None
            and not client.websocket.closed
        )


# -- FastAPI app import -------------------------------------------------------
from .api.app import app  # noqa: E402


def main() -> None:
    """Run the FastAPI app via uvicorn."""
    import uvicorn

    port = int(os.getenv("WEBSOCKET_INGESTION_PORT", "8000"))
    host = os.getenv("WEBSOCKET_INGESTION_HOST", "0.0.0.0")  # noqa: S104  # nosec B104
    logger.info("Starting on %s:%s", host, port)
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
