"""Electricity-pricing adapter (former electricity-pricing-service).

Fetches real-time electricity pricing from utility APIs.

Former route (unchanged): GET /cheapest-hours.
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import aiohttp
from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from homeiq_observability.logging_config import (
    log_error_with_context,
    log_with_context,
    setup_logging,
)
from influxdb_client_3 import InfluxDBClient3, Point

from ...config import Settings, settings
from ..base import CollectorAdapter, with_adapter_timeout
from .health_check import HealthCheckHandler
from .providers import AwattarProvider
from .security import require_internal_network, validate_hours_parameter

if TYPE_CHECKING:
    from homeiq_resilience import StandardHealthCheck

NAME = "electricity_pricing"
ADAPTER_TIMEOUT_SECONDS = 15.0

logger = setup_logging(f"{settings.service_name}.{NAME}")


class ElectricityPricingService:
    """Fetch and store electricity pricing data."""

    def __init__(self) -> None:
        """Initialize the electricity pricing service with provider and InfluxDB config.

        Reads a *fresh* ``Settings()`` rather than the shared module-level
        ``settings`` singleton — that singleton snapshots first-import state,
        which is neither what CI exports at run time nor what tests patch
        (former electricity-pricing-service's TAP-6174 fix; preserved here).
        """
        local_settings = Settings()
        self.provider_name = local_settings.pricing_provider

        self.influxdb_url = local_settings.influxdb_url
        self.influxdb_token = (
            local_settings.influxdb_token.get_secret_value()
            if local_settings.influxdb_token
            else None
        )
        self.influxdb_org = local_settings.influxdb_org
        self.influxdb_bucket = local_settings.influxdb_bucket

        self.fetch_interval = local_settings.electricity_fetch_interval
        self.cache_duration = local_settings.electricity_cache_duration_minutes

        self.allowed_networks: list[str] | None = None
        if local_settings.allowed_networks:
            self.allowed_networks = [
                net.strip() for net in local_settings.allowed_networks.split(",") if net.strip()
            ]

        self.cached_data: dict[str, Any] | None = None
        self.last_fetch_time: datetime | None = None

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
            "Initializing Electricity Pricing adapter (Provider: %s)...", self.provider_name
        )

        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))

        self.influxdb_client = InfluxDBClient3(
            host=self.influxdb_url,
            token=self.influxdb_token,
            database=self.influxdb_bucket,
            org=self.influxdb_org,
        )

        self._background_task = asyncio.create_task(self.run_continuous())

        logger.info("Electricity Pricing adapter initialized successfully")

    async def shutdown(self) -> None:
        """Cleanup HTTP session and InfluxDB client."""
        logger.info("Shutting down Electricity Pricing adapter...")

        if self._background_task and not self._background_task.done():
            self._background_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._background_task

        if self.session:
            await self.session.close()

        if self.influxdb_client:
            self.influxdb_client.close()

        logger.info("Electricity Pricing adapter shut down successfully")

    async def fetch_pricing(self) -> dict[str, Any] | None:
        """Fetch electricity pricing from configured provider."""
        try:
            log_with_context(
                logger,
                "INFO",
                f"Fetching electricity pricing from {self.provider_name}",
                service="electricity-pricing-service",
                provider=self.provider_name,
            )

            data = await self.provider.fetch_pricing(self.session)

            if not data:
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

            logger.info("Electricity pricing data written to InfluxDB (%d points)", len(points))

        except Exception as e:
            log_error_with_context(
                logger,
                f"Error writing to InfluxDB: {e}",
                service="electricity-pricing-service",
                error=str(e),
            )

    async def run_continuous(self) -> None:
        """Run the continuous pricing data collection and storage loop."""
        logger.info("Starting continuous pricing monitoring (every %ds)", self.fetch_interval)

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


service: ElectricityPricingService | None = None
_READY_START = time.monotonic()

router = APIRouter(tags=["electricity_pricing"])


@router.get("/cheapest-hours")
@with_adapter_timeout(NAME, ADAPTER_TIMEOUT_SECONDS)
async def get_cheapest_hours(
    request: Request,
    hours: str | None = Query(default=None, description="Number of cheapest hours (1-24)"),
) -> dict:
    """API endpoint returning the cheapest electricity hours."""
    if not service:
        return JSONResponse(content={"error": "Adapter not initialized"}, status_code=503)

    try:
        hours_needed = validate_hours_parameter(hours, default=4)
    except ValueError as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)

    require_internal_network(request, service.allowed_networks)

    if service.cached_data and "cheapest_hours" in service.cached_data:
        cheapest = service.cached_data["cheapest_hours"][:hours_needed]
        return {
            "cheapest_hours": cheapest,
            "provider": service.provider_name,
            "timestamp": (service.last_fetch_time.isoformat() if service.last_fetch_time else None),
        }
    return JSONResponse(content={"error": "No pricing data available"}, status_code=503)


async def _check_recent_fetch() -> dict[str, Any]:
    if service is None:
        return {"ok": False, "reason": "service not started"}
    last = service.health_handler.last_successful_fetch
    interval = service.fetch_interval
    if last is None:
        in_grace = (time.monotonic() - _READY_START) <= max(interval, 300)
        return {"ok": in_grace, "last_successful_fetch": None, "startup_grace": in_grace}
    age = (datetime.now(UTC) - last).total_seconds()
    return {"ok": age <= interval * 2, "last_successful_fetch_age_s": round(age)}


class ElectricityPricingAdapter(CollectorAdapter):
    """Adapter wrapping the former electricity-pricing-service."""

    name = NAME

    @property
    def router(self) -> APIRouter:
        return router

    async def startup(self) -> None:
        global service
        service = ElectricityPricingService()
        await service.startup()

    async def shutdown(self) -> None:
        global service
        if service:
            await service.shutdown()
            service = None

    def register_health(self, health: StandardHealthCheck) -> None:
        health.register_check(f"{NAME}_recent_fetch", _check_recent_fetch)


adapter = ElectricityPricingAdapter()
