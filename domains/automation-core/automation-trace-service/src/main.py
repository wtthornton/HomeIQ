"""
Automation Trace Service — main entry point.

FastAPI app that connects to Home Assistant via WebSocket, polls
automation traces every 2 minutes, and stores them in InfluxDB +
data-api.
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import suppress

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import __version__, config
from .dedup_tracker import DedupTracker
from .ha_client import HATraceClient
from .health_check import HealthCheckHandler
from .influxdb_writer import InfluxDBTraceWriter
from .trace_poller import TracePoller

load_dotenv()

# Logging
try:
    from homeiq_observability.logging_config import setup_logging
    logger = setup_logging(config.SERVICE_NAME)
except ImportError:
    logging.basicConfig(level=config.LOG_LEVEL)
    logger = logging.getLogger(config.SERVICE_NAME)

# ---------------------------------------------------------------------------
# Global service components
# ---------------------------------------------------------------------------
ha_client: HATraceClient | None = None
influxdb_writer: InfluxDBTraceWriter | None = None
trace_poller: TracePoller | None = None
dedup: DedupTracker | None = None
health_handler = HealthCheckHandler()
_poller_task: asyncio.Task | None = None


async def startup():
    """Initialize all service components and start background poller."""
    global ha_client, influxdb_writer, trace_poller, dedup, _poller_task

    logger.info("Starting %s v%s", config.SERVICE_NAME, __version__)

    # HA WebSocket
    ha_client = HATraceClient()
    connected = await ha_client.connect()
    if not connected:
        logger.warning("Could not connect to HA — will retry in poller loop")

    # InfluxDB
    influxdb_writer = InfluxDBTraceWriter()
    await influxdb_writer.startup()

    # Dedup tracker
    dedup = DedupTracker()

    # Trace poller
    trace_poller = TracePoller(ha_client, influxdb_writer, dedup)

    # Start background polling task
    async def _run_poller():
        # If initial connection failed, keep retrying
        while not ha_client.is_connected:
            logger.info("Waiting for HA connection...")
            try:
                await ha_client.connect()
            except Exception:
                pass
            if not ha_client.is_connected:
                await asyncio.sleep(30)

        try:
            await trace_poller.run_continuous()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Trace poller background task crashed")

    _poller_task = asyncio.create_task(_run_poller(), name="trace-poller-loop")
    logger.info("Background trace poller started (interval=%ds)", config.TRACE_POLL_INTERVAL_SECONDS)


async def shutdown():
    """Graceful shutdown."""
    global _poller_task

    logger.info("Shutting down %s", config.SERVICE_NAME)

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
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Automation Trace Service",
    description="Ingests HA automation traces and stores to InfluxDB + data-api",
    version=__version__,
)

cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

app.add_event_handler("startup", startup)
app.add_event_handler("shutdown", shutdown)


@app.get("/")
async def root():
    return {
        "service": config.SERVICE_NAME,
        "version": __version__,
        "status": "running",
        "endpoints": ["/health", "/metrics"],
    }


@app.get("/health")
async def health():
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
    uvicorn.run(app, host="0.0.0.0", port=config.SERVICE_PORT, log_level="info")
