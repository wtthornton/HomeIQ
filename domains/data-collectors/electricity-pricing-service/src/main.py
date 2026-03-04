"""Electricity Pricing Service Main Entry Point.

Fetches real-time electricity pricing from utility APIs.
Migrated from aiohttp to FastAPI with shared library pattern.
"""

import asyncio
from datetime import UTC, datetime
from typing import Any

import aiohttp
from config import settings
from fastapi import Query, Request
from health_check import HealthCheckHandler
from homeiq_observability.logging_config import (
    log_error_with_context,
    log_with_context,
    setup_logging,
)
from homeiq_resilience import ServiceLifespan, StandardHealthCheck, create_app
from influxdb_client_3 import InfluxDBClient3, Point
from providers import AwattarProvider
from security import require_internal_network, validate_hours_parameter

logger = setup_logging("electricity-pricing-service")


class ElectricityPricingService:
    """Fetch and store electricity pricing data."""

    def __init__(self) -> None:
        """Initialize the electricity pricing service with provider and InfluxDB config."""
        self.provider_name = settings.pricing_provider

        # InfluxDB configuration
        self.influxdb_url = settings.influxdb_url
        self.influxdb_token = (
            settings.influxdb_token.get_secret_value() if settings.influxdb_token else None
        )
        self.influxdb_org = settings.influxdb_org
        self.influxdb_bucket = settings.influxdb_bucket

        # Service configuration
        self.fetch_interval = settings.fetch_interval
        self.cache_duration = settings.cache_duration

        # Security configuration
        self.allowed_networks: list[str] | None = None
        if settings.allowed_networks:
            self.allowed_networks = [
                net.strip() for net in settings.allowed_networks.split(",") if net.strip()
            ]

        # Cache
        self.cached_data: dict[str, Any] | None = None
        self.last_fetch_time: datetime | None = None

        # Components
        self.session: aiohttp.ClientSession | None = None
        self.influxdb_client: InfluxDBClient3 | None = None
        self.health_handler = HealthCheckHandler()
        self.provider = self._get_provider()
        self._background_task: asyncio.Task | None = None

        if not self.influxdb_token:
            raise ValueError("INFLUXDB_TOKEN environment variable is required")

    def _get_provider(self) -> AwattarProvider:
        """Get pricing provider instance based on configuration."""
        providers = {"awattar": AwattarProvider()}
        provider = providers.get(self.provider_name.lower())

        if not provider:
            logger.warning("Unknown provider %s, using Awattar", self.provider_name)
            return AwattarProvider()

        return provider

    async def startup(self) -> None:
        """Initialize HTTP session and InfluxDB client."""
        logger.info(
            "Initializing Electricity Pricing Service (Provider: %s)...", self.provider_name
        )

        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))

        self.influxdb_client = InfluxDBClient3(
            host=self.influxdb_url,
            token=self.influxdb_token,
            database=self.influxdb_bucket,
            org=self.influxdb_org,
        )

        # Start background collection
        self._background_task = asyncio.create_task(self.run_continuous())

        logger.info("Electricity Pricing Service initialized successfully")

    async def shutdown(self) -> None:
        """Cleanup HTTP session and InfluxDB client."""
        logger.info("Shutting down Electricity Pricing Service...")

        if self._background_task and not self._background_task.done():
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass

        if self.session:
            await self.session.close()

        if self.influxdb_client:
            self.influxdb_client.close()

        logger.info("Electricity Pricing Service shut down successfully")

    async def fetch_pricing(self) -> dict[str, Any] | None:
        """Fetch electricity pricing from configured provider."""
        try:
            log_with_context(
                logger,
                "INFO",
                "Fetching electricity pricing from %s" % self.provider_name,
                service="electricity-pricing-service",
                provider=self.provider_name,
            )

            data = await self.provider.fetch_pricing(self.session)

            if data is None:
                logger.warning("Provider returned no data")
                return self.cached_data

            data["timestamp"] = datetime.now(UTC)
            data["provider"] = self.provider_name

            self.cached_data = data
            self.last_fetch_time = datetime.now(UTC)
            self.health_handler.last_successful_fetch = datetime.now(UTC)
            self.health_handler.total_fetches += 1

            logger.info("Current price: %.3f %s/kWh", data["current_price"], data["currency"])
            logger.info("Cheapest hours: %s", data["cheapest_hours"])

            return data

        except Exception as e:
            log_error_with_context(
                logger,
                f"Error fetching pricing: {e}",
                service="electricity-pricing-service",
                error=str(e),
            )
            self.health_handler.failed_fetches += 1

            if self.cached_data and self.last_fetch_time:
                age_min = (datetime.now(UTC) - self.last_fetch_time).total_seconds() / 60
                if age_min < self.cache_duration:
                    logger.warning("Using cached pricing data")
                    return self.cached_data
                logger.error("Cache expired (%.0fm > %dm)", age_min, self.cache_duration)

            return None

    async def store_in_influxdb(self, data: dict[str, Any]) -> None:
        """Store pricing data in InfluxDB using batch writes."""
        if not self.influxdb_client:
            logger.error("InfluxDB client not initialized, skipping write")
            return

        if not data:
            logger.warning("No data to store in InfluxDB")
            return

        try:
            required = ["provider", "currency", "current_price", "peak_period", "timestamp"]
            missing = [f for f in required if f not in data]
            if missing:
                logger.error("Missing required fields for InfluxDB write: %s", missing)
                return

            points = []

            current_point = (
                Point("electricity_pricing")
                .tag("provider", data["provider"])
                .tag("currency", data["currency"])
                .field("current_price", float(data["current_price"]))
                .field("peak_period", bool(data["peak_period"]))
                .time(data["timestamp"])
            )
            points.append(current_point)

            for forecast in data.get("forecast_24h", []):
                forecast_point = (
                    Point("electricity_pricing_forecast")
                    .tag("provider", data["provider"])
                    .field("price", float(forecast["price"]))
                    .field("hour_offset", int(forecast["hour"]))
                    .time(forecast["timestamp"])
                )
                points.append(forecast_point)

            if points:
                await asyncio.to_thread(self.influxdb_client.write, points)

            logger.info(
                "Electricity pricing data written to InfluxDB (%d points)", len(points)
            )

        except Exception as e:
            log_error_with_context(
                logger,
                f"Error writing to InfluxDB: {e}",
                service="electricity-pricing-service",
                error=str(e),
            )

    async def run_continuous(self) -> None:
        """Run the continuous pricing data collection and storage loop."""
        logger.info(
            "Starting continuous pricing monitoring (every %ds)", self.fetch_interval
        )

        while True:
            try:
                data = await self.fetch_pricing()
                if data:
                    await self.store_in_influxdb(data)
                await asyncio.sleep(self.fetch_interval)
            except asyncio.CancelledError:
                logger.info("Continuous pricing loop cancelled")
                raise
            except Exception as e:
                log_error_with_context(
                    logger,
                    f"Error in continuous loop: {e}",
                    service="electricity-pricing-service",
                    error=str(e),
                )
                await asyncio.sleep(300)


# --- Global service instance ---
service: ElectricityPricingService | None = None

# --- Lifespan ---
lifespan = ServiceLifespan(service_name="electricity-pricing-service")


async def _startup() -> None:
    global service
    service = ElectricityPricingService()
    await service.startup()


async def _shutdown() -> None:
    if service:
        await service.shutdown()


lifespan.on_startup(_startup, name="electricity-pricing-init")
lifespan.on_shutdown(_shutdown, name="electricity-pricing-cleanup")

# --- Health check ---
health = StandardHealthCheck(service_name="electricity-pricing-service", version="1.0.0")

# --- App ---
app = create_app(
    title="Electricity Pricing Service",
    version="1.0.0",
    description="Real-time electricity pricing from utility APIs",
    lifespan=lifespan.handler,
    health_check=health,
)


@app.get("/cheapest-hours")
async def get_cheapest_hours(
    request: Request,
    hours: str | None = Query(default=None, description="Number of cheapest hours (1-24)"),
) -> dict:
    """API endpoint returning the cheapest electricity hours."""
    if not service:
        from fastapi.responses import JSONResponse

        return JSONResponse(content={"error": "Service not initialized"}, status_code=503)

    # Validate hours parameter
    try:
        hours_needed = validate_hours_parameter(hours, default=4)
    except ValueError as e:
        from fastapi.responses import JSONResponse

        return JSONResponse(content={"error": str(e)}, status_code=400)

    # Require internal network access (if configured)
    require_internal_network(request, service.allowed_networks)

    if service.cached_data and "cheapest_hours" in service.cached_data:
        cheapest = service.cached_data["cheapest_hours"][:hours_needed]
        return {
            "cheapest_hours": cheapest,
            "provider": service.provider_name,
            "timestamp": (
                service.last_fetch_time.isoformat() if service.last_fetch_time else None
            ),
        }
    from fastapi.responses import JSONResponse

    return JSONResponse(content={"error": "No pricing data available"}, status_code=503)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",  # noqa: S104 — Docker requires binding all interfaces
        port=settings.service_port,
        log_level="info",
    )
