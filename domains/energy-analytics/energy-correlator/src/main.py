"""
Energy-Event Correlation Service
Post-processes HA events and power data to find causality relationships.

Converted from aiohttp to FastAPI with shared library pattern.
"""

import asyncio
import logging
import sys
from datetime import UTC, datetime

from fastapi import Request
from fastapi.responses import JSONResponse
from homeiq_observability.logging_config import (
    log_error_with_context,
    log_with_context,
    setup_logging,
)
from homeiq_resilience import ServiceLifespan, StandardHealthCheck, create_app

from .config import settings
from .correlator import EnergyEventCorrelator
from .security import validate_bucket_name, validate_internal_request

logger = setup_logging("energy-correlator")


# ---------------------------------------------------------------------------
# Service class (retained for correlation logic)
# ---------------------------------------------------------------------------

class EnergyCorrelatorService:
    """Main service for energy-event correlation."""

    def __init__(self) -> None:
        # Validate bucket name on startup
        influxdb_token = settings.influxdb_token.get_secret_value() if settings.influxdb_token else None
        validate_bucket_name(settings.influxdb_bucket)

        # Derive retry_window_minutes
        retry_window = settings.retry_window_minutes or settings.lookback_minutes

        # Components
        data_api_url = settings.data_api_url.strip() or None
        self.correlator = EnergyEventCorrelator(
            settings.influxdb_url,
            influxdb_token,
            settings.influxdb_org,
            settings.influxdb_bucket,
            correlation_window_seconds=settings.correlation_window_seconds,
            min_power_delta=settings.min_power_delta,
            max_events_per_interval=settings.max_events_per_interval,
            power_lookup_padding_seconds=settings.power_lookup_padding_seconds,
            max_retry_queue_size=settings.max_retry_queue_size,
            retry_window_minutes=retry_window,
            data_api_url=data_api_url,
        )

        # Validate required configuration
        if not influxdb_token:
            raise ValueError("INFLUXDB_TOKEN environment variable is required")

        # Parse allowed networks
        raw_networks = settings.allowed_networks
        self.allowed_networks: list[str] | None = (
            [net.strip() for net in raw_networks.split(",") if net.strip()]
            if raw_networks else None
        )

        # Health tracking
        self.last_successful_fetch: datetime | None = None
        self.total_fetches: int = 0
        self.failed_fetches: int = 0

        logger.info(
            "Service configured: interval=%ds, lookback=%dm",
            settings.processing_interval,
            settings.lookback_minutes,
        )

    async def startup(self) -> None:
        """Initialize service."""
        logger.info("Initializing Energy Correlator Service...")
        try:
            await self.correlator.startup()
            logger.info("Energy Correlator Service initialized successfully")
        except Exception as e:
            log_error_with_context(
                logger,
                "Failed to initialize service",
                service="energy-correlator",
                error=str(e),
            )
            raise

    async def shutdown(self) -> None:
        """Cleanup."""
        logger.info("Shutting down Energy Correlator Service...")
        try:
            await self.correlator.shutdown()
            logger.info("Energy Correlator Service shut down successfully")
        except Exception as e:
            logger.error("Error during shutdown: %s", e)

    async def run_continuous(self) -> None:
        """Run continuous correlation processing."""
        log_with_context(
            logger, "INFO",
            f"Starting correlation loop (every {settings.processing_interval}s)",
            service="energy-correlator",
            interval=settings.processing_interval,
            lookback_minutes=settings.lookback_minutes,
        )

        while True:
            try:
                await self.correlator.process_recent_events(
                    lookback_minutes=settings.lookback_minutes,
                )
                self.last_successful_fetch = datetime.now(UTC)
                self.total_fetches += 1
                await asyncio.sleep(settings.processing_interval)
            except Exception as e:
                log_error_with_context(
                    logger,
                    "Error in correlation loop",
                    service="energy-correlator",
                    error=str(e),
                )
                self.failed_fetches += 1
                await asyncio.sleep(settings.error_retry_interval)


# Global service instance
_service: EnergyCorrelatorService | None = None
_background_task: asyncio.Task | None = None


# ---------------------------------------------------------------------------
# Startup / Shutdown
# ---------------------------------------------------------------------------

async def _startup_service() -> None:
    """Create and start the correlator service + background loop."""
    global _service, _background_task
    _service = EnergyCorrelatorService()
    await _service.startup()
    _background_task = asyncio.create_task(
        _service.run_continuous(), name="correlator-loop",
    )


async def _shutdown_service() -> None:
    """Stop background loop and shut down the correlator service."""
    global _service, _background_task
    if _background_task and not _background_task.done():
        _background_task.cancel()
        try:
            await _background_task
        except asyncio.CancelledError:
            pass
    _background_task = None
    if _service:
        await _service.shutdown()
        _service = None


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

lifespan = ServiceLifespan(settings.service_name)
lifespan.on_startup(_startup_service, name="correlator")
lifespan.on_shutdown(_shutdown_service, name="correlator")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

health = StandardHealthCheck(
    service_name=settings.service_name,
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = create_app(
    title="Energy Correlator Service",
    version="1.0.0",
    description="Post-processes HA events and power data to find causality relationships",
    lifespan=lifespan.handler,
    health_check=health,
    cors_origins=settings.get_cors_origins_list(),
)


# ---------------------------------------------------------------------------
# Routes (migrated from aiohttp handlers)
# ---------------------------------------------------------------------------

@app.get("/statistics")
async def get_statistics() -> dict:
    """Get correlation statistics."""
    if not _service:
        return JSONResponse({"error": "Service not initialized"}, status_code=503)
    try:
        stats = _service.correlator.get_statistics()
        return stats
    except Exception as e:
        logger.error("Error getting statistics: %s", e)
        return JSONResponse(
            {"error": "Failed to retrieve statistics"},
            status_code=500,
        )


@app.post("/statistics/reset")
async def reset_statistics(request: Request) -> dict:
    """Reset correlation statistics (requires internal network access)."""
    if not _service:
        return JSONResponse({"error": "Service not initialized"}, status_code=503)

    if not validate_internal_request(request, _service.allowed_networks):
        client_host = request.client.host if request.client else "unknown"
        logger.warning(
            "Unauthorized reset attempt from %s",
            client_host,
            extra={"service": "energy-correlator", "endpoint": "/statistics/reset"},
        )
        return JSONResponse(
            {"error": "Forbidden: This endpoint is only accessible from internal networks"},
            status_code=403,
        )

    _service.correlator.reset_statistics()
    return {"message": "Statistics reset"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",  # noqa: S104
        port=settings.service_port,
        reload=True,
    )
