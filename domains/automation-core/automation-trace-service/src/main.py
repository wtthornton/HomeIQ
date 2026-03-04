"""Automation Trace Service -- main entry point.

FastAPI app that connects to Home Assistant via WebSocket, polls
automation traces every 2 minutes, and stores them in InfluxDB +
data-api.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import suppress

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from homeiq_resilience import ServiceLifespan, StandardHealthCheck, create_app

from . import __version__
from .config import settings
from .dedup_tracker import DedupTracker
from .ha_client import HATraceClient
from .health_check import HealthCheckHandler
from .influxdb_writer import InfluxDBTraceWriter
from .trace_poller import TracePoller


def _configure_logging() -> None:
    """Configure logging for the service."""
    try:
        from homeiq_observability.logging_config import setup_logging

        setup_logging(settings.service_name)
    except ImportError:
        logging.basicConfig(
            level=getattr(logging, settings.log_level.upper()),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)],
        )


_configure_logging()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Global service components
# ---------------------------------------------------------------------------
ha_client: HATraceClient | None = None
influxdb_writer: InfluxDBTraceWriter | None = None
trace_poller: TracePoller | None = None
dedup: DedupTracker | None = None
health_handler = HealthCheckHandler()
_poller_task: asyncio.Task | None = None


async def _startup() -> None:
    """Initialize all service components and start background poller."""
    global ha_client, influxdb_writer, trace_poller, dedup, _poller_task  # noqa: PLW0603

    logger.info("Starting %s v%s", settings.service_name, __version__)

    # HA WebSocket
    ha_client = HATraceClient()
    connected = await ha_client.connect()
    if not connected:
        logger.warning("Could not connect to HA -- will retry in poller loop")

    # InfluxDB
    influxdb_writer = InfluxDBTraceWriter()
    await influxdb_writer.startup()

    # Dedup tracker
    dedup = DedupTracker()

    # Trace poller
    trace_poller = TracePoller(ha_client, influxdb_writer, dedup)

    # Start background polling task
    async def _run_poller() -> None:
        assert ha_client is not None  # noqa: S101
        # If initial connection failed, keep retrying
        while not ha_client.is_connected:
            logger.info("Waiting for HA connection...")
            with suppress(Exception):
                await ha_client.connect()
            if not ha_client.is_connected:
                await asyncio.sleep(30)

        try:
            assert trace_poller is not None  # noqa: S101
            await trace_poller.run_continuous()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Trace poller background task crashed")

    _poller_task = asyncio.create_task(_run_poller(), name="trace-poller-loop")
    logger.info(
        "Background trace poller started (interval=%ds)",
        settings.trace_poll_interval_seconds,
    )


async def _shutdown() -> None:
    """Graceful shutdown."""
    global _poller_task  # noqa: PLW0603

    logger.info("Shutting down %s", settings.service_name)

    if _poller_task and not _poller_task.done():
        _poller_task.cancel()
        with suppress(asyncio.CancelledError):
            await _poller_task
        _poller_task = None

    if trace_poller:
        await trace_poller.cleanup()
    if ha_client:
        await ha_client.disconnect()
    if influxdb_writer:
        influxdb_writer.shutdown()


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

lifespan = ServiceLifespan(settings.service_name)
lifespan.on_startup(_startup, name="trace_components")
lifespan.on_shutdown(_shutdown, name="trace_components")

# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

health = StandardHealthCheck(
    service_name=settings.service_name,
    version=__version__,
)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = create_app(
    title="Automation Trace Service",
    version=__version__,
    description="Ingests HA automation traces and stores to InfluxDB + data-api",
    lifespan=lifespan.handler,
    health_check=health,
    cors_origins=settings.get_cors_origins_list(),
)


# ---------------------------------------------------------------------------
# Custom health endpoint (preserves detailed component status)
# ---------------------------------------------------------------------------


@app.get("/health/details")
async def health_details():
    """Detailed health check with component-level status."""
    if not trace_poller:
        raise HTTPException(status_code=503, detail="Service not initialized")

    result = health_handler.build(
        ha_connected=ha_client.is_connected if ha_client else False,
        influxdb_ok=influxdb_writer.client is not None if influxdb_writer else False,
        poller_stats={
            "poll_count": trace_poller.poll_count,
            "traces_captured": trace_poller.traces_captured,
            "automations_found": trace_poller.automations_found,
            "poller_errors": trace_poller.errors,
            "last_poll": trace_poller.last_poll.isoformat() if trace_poller.last_poll else None,
        },
        dedup_stats={
            "tracked_automations": dedup.tracked_automation_count if dedup else 0,
            "tracked_runs": dedup.total_tracked_runs if dedup else 0,
            "total_deduped": dedup.total_deduped if dedup else 0,
        },
    )
    status_code = 200 if result.get("status") == "healthy" else 503
    return JSONResponse(content=result, status_code=status_code)


@app.get("/metrics")
async def metrics():
    """Service metrics endpoint."""
    if not trace_poller or not influxdb_writer:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return {
        "poll_count": trace_poller.poll_count,
        "traces_captured": trace_poller.traces_captured,
        "automations_found": trace_poller.automations_found,
        "poller_errors": trace_poller.errors,
        "influx_write_success": influxdb_writer.write_success_count,
        "influx_write_failure": influxdb_writer.write_failure_count,
        "dedup_tracked_automations": dedup.tracked_automation_count if dedup else 0,
        "dedup_total_runs": dedup.total_tracked_runs if dedup else 0,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",  # noqa: S104
        port=settings.service_port,
        log_level="info",
    )
