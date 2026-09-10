"""Smart-meter adapter (former smart-meter-service; already adapter-shaped).

Generic smart meter integration with a meter-adapter pattern (`meters/`) —
this is the ABC-based adapter shape the whole collectors process extends
(see `..base.CollectorAdapter`).

Former route (unchanged): GET /consumption.
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from datetime import UTC, datetime
from typing import Any

import aiohttp
from fastapi import APIRouter
from homeiq_observability.logging_config import log_error_with_context, setup_logging
from homeiq_resilience import StandardHealthCheck
from influxdb_client_3 import InfluxDBClient3, Point

from ...config import settings
from ..base import CollectorAdapter, with_adapter_timeout
from .health_check import HealthCheckHandler
from .meters.base import MeterAdapter
from .meters.home_assistant import HomeAssistantAdapter

NAME = "smart_meter"
ADAPTER_TIMEOUT_SECONDS = 15.0

logger = setup_logging(f"{settings.service_name}.{NAME}")


class SmartMeterService:
    """Generic smart meter integration with meter-adapter support."""

    def __init__(self) -> None:
        """Initialize the smart meter service with adapter and InfluxDB configuration."""
        self.meter_type = settings.meter_type
        self.api_token = settings.meter_api_token
        self.device_id = settings.meter_device_id

        self.ha_url = settings.home_assistant_url
        self.ha_token = settings.home_assistant_token

        self.influxdb_url = settings.influxdb_url
        self.influxdb_token = (
            settings.influxdb_token.get_secret_value() if settings.influxdb_token else None
        )
        self.influxdb_org = settings.influxdb_org
        self.influxdb_bucket = settings.influxdb_bucket

        self.fetch_interval = settings.fetch_interval_seconds
        if self.fetch_interval < 10:
            logger.warning(
                "Fetch interval %ds too low, setting to 10s minimum", self.fetch_interval
            )
            self.fetch_interval = 10

        self.cached_data: dict[str, Any] | None = None
        self.last_fetch_time: datetime | None = None
        self.baseline_3am: float | None = None
        self.CACHE_MAX_AGE_SECONDS = 900  # noqa: N815 — 15 minutes

        self.session: aiohttp.ClientSession | None = None
        self.influxdb_client: InfluxDBClient3 | None = None
        self.health_handler = HealthCheckHandler()
        self.adapter: MeterAdapter | None = None
        self._background_task: asyncio.Task | None = None

        if not self.influxdb_token:
            raise ValueError("INFLUXDB_TOKEN required")

    async def startup(self) -> None:
        """Initialize service."""
        logger.info("Initializing Smart Meter adapter (Type: %s)...", self.meter_type)

        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))

        self.influxdb_client = InfluxDBClient3(
            host=self.influxdb_url,
            token=self.influxdb_token,
            database=self.influxdb_bucket,
            org=self.influxdb_org,
        )

        self.adapter = self._create_adapter()

        if self.adapter:
            connected = await self.adapter.test_connection(self.session)
            if not connected:
                logger.warning("Failed to connect to meter - will use mock data")

        self._background_task = asyncio.create_task(self.run_continuous())

        logger.info("Smart Meter adapter initialized")

    def _create_adapter(self) -> MeterAdapter | None:
        """Create meter adapter based on meter type."""
        if self.meter_type == "home_assistant":
            if not self.ha_url or not self.ha_token:
                logger.warning(
                    "HOME_ASSISTANT_URL and HOME_ASSISTANT_TOKEN not configured - using mock data"
                )
                return None
            return HomeAssistantAdapter(self.ha_url, self.ha_token)
        if self.meter_type == "emporia":
            logger.warning("Emporia adapter not yet implemented - using mock data")
            return None
        if self.meter_type == "sense":
            logger.warning("Sense adapter not yet implemented - using mock data")
            return None
        logger.warning("Unknown meter type: %s - using mock data", self.meter_type)
        return None

    async def shutdown(self) -> None:
        """Cleanup."""
        if self._background_task and not self._background_task.done():
            self._background_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._background_task
        if self.session:
            await self.session.close()
        if self.influxdb_client:
            self.influxdb_client.close()

    def _enrich_consumption_data(self, data: dict[str, Any]) -> None:
        """Enrich consumption data with percentages, phantom load detection, and logging."""
        if "timestamp" not in data:
            data["timestamp"] = datetime.now(UTC)

        for circuit in data.get("circuits", []):
            if "percentage" not in circuit:
                total = data.get("total_power_w", 0)
                power = circuit.get("power_w", 0)
                circuit["percentage"] = (power / total) * 100 if total > 0 else 0

        current_hour = datetime.now(UTC).hour
        if current_hour == 3:
            self.baseline_3am = data["total_power_w"]
            if self.baseline_3am > 200:
                logger.warning("High phantom load detected: %.0fW at 3am", self.baseline_3am)

        if data["total_power_w"] > 10000:
            logger.warning("High power consumption: %.0fW", data["total_power_w"])

    def _get_cached_or_none(self) -> dict[str, Any] | None:
        """Return cached data if fresh enough, otherwise None."""
        if self.cached_data and self.last_fetch_time:
            cache_age = (datetime.now(UTC) - self.last_fetch_time).total_seconds()
            if cache_age < self.CACHE_MAX_AGE_SECONDS:
                logger.warning("Using cached data (age: %.0fs) after adapter failure", cache_age)
                return self.cached_data
            logger.warning(
                "Cached data too old (%.0fs > %ds), falling back to mock data",
                cache_age,
                self.CACHE_MAX_AGE_SECONDS,
            )
        return None

    async def fetch_consumption(self) -> dict[str, Any] | None:
        """Fetch power consumption from configured meter adapter, cache, or mock data."""
        if self.adapter:
            try:
                data = await self.adapter.fetch_consumption(
                    self.session, self.api_token, self.device_id
                )
                self._enrich_consumption_data(data)

                self.cached_data = data
                self.last_fetch_time = datetime.now(UTC)
                self.health_handler.last_successful_fetch = datetime.now(UTC)
                self.health_handler.total_fetches += 1

                logger.info(
                    "Power: %.0fW, Daily: %.1fkWh, Circuits: %d",
                    data["total_power_w"],
                    data.get("daily_kwh", 0),
                    len(data.get("circuits", [])),
                )
                return data

            except Exception as e:
                log_error_with_context(
                    logger,
                    f"Error fetching from adapter: {e}",
                    error=e,
                    service="smart-meter-service",
                )
                self.health_handler.failed_fetches += 1
                cached = self._get_cached_or_none()
                if cached:
                    return cached
                logger.warning("No cached data available, using mock data")

        return self._get_mock_data()

    def _get_mock_data(self) -> dict[str, Any]:
        """Return mock consumption data for testing."""
        data = {
            "total_power_w": 2450.0,
            "daily_kwh": 18.5,
            "circuits": [
                {"name": "HVAC", "power_w": 1200.0, "percentage": 49.0},
                {"name": "Kitchen", "power_w": 450.0, "percentage": 18.4},
                {"name": "Living Room", "power_w": 300.0, "percentage": 12.2},
                {"name": "Office", "power_w": 250.0, "percentage": 10.2},
                {"name": "Bedrooms", "power_w": 150.0, "percentage": 6.1},
                {"name": "Other", "power_w": 100.0, "percentage": 4.1},
            ],
            "timestamp": datetime.now(UTC),
        }

        self.cached_data = data
        self.last_fetch_time = datetime.now(UTC)
        self.health_handler.total_fetches += 1

        logger.debug("Using mock data")
        return data

    async def store_in_influxdb(self, data: dict[str, Any], max_retries: int = 3) -> None:
        """Store consumption data in InfluxDB with exponential backoff retry."""
        if not data:
            return

        points = []

        point = (
            Point("smart_meter")
            .tag("meter_type", self.meter_type)
            .field("total_power_w", float(data["total_power_w"]))
            .field("daily_kwh", float(data["daily_kwh"]))
            .time(data["timestamp"])
        )
        points.append(point)

        for circuit in data.get("circuits", []):
            circuit_point = (
                Point("smart_meter_circuit")
                .tag("circuit_name", circuit["name"])
                .field("power_w", float(circuit["power_w"]))
                .field("percentage", float(circuit["percentage"]))
                .time(data["timestamp"])
            )
            points.append(circuit_point)

        for attempt in range(max_retries):
            try:
                self.influxdb_client.write(points)
                logger.info("Wrote %d points to InfluxDB", len(points))
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    wait = 2**attempt
                    logger.warning(
                        "InfluxDB write attempt %d failed, retrying in %ds: %s",
                        attempt + 1,
                        wait,
                        e,
                    )
                    await asyncio.sleep(wait)
                else:
                    log_error_with_context(
                        logger,
                        f"InfluxDB write failed after {max_retries} attempts: {e}",
                        error=e,
                        service="smart-meter-service",
                    )

    async def run_continuous(self) -> None:
        """Run continuous data collection loop."""
        logger.info("Starting continuous power monitoring (every %ds)", self.fetch_interval)

        while True:
            try:
                data = await self.fetch_consumption()
                if data:
                    await self.store_in_influxdb(data)
                await asyncio.sleep(self.fetch_interval)
            except asyncio.CancelledError:
                logger.info("Continuous collection loop cancelled")
                raise
            except Exception as e:
                log_error_with_context(
                    logger,
                    f"Error in continuous loop: {e}",
                    error=e,
                    service="smart-meter-service",
                )
                await asyncio.sleep(60)


service: SmartMeterService | None = None
_READY_START = time.monotonic()

router = APIRouter(tags=["smart_meter"])


@router.get("/consumption")
@with_adapter_timeout(NAME, ADAPTER_TIMEOUT_SECONDS)
async def get_consumption() -> dict:
    """Get current power consumption data."""
    if not service:
        return {"error": "Adapter not initialized"}
    if service.cached_data:
        data = dict(service.cached_data)
        if "timestamp" in data and isinstance(data["timestamp"], datetime):
            data["timestamp"] = data["timestamp"].isoformat()
        return data
    return {"error": "No data available"}


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


class SmartMeterAdapter(CollectorAdapter):
    """Adapter wrapping the former smart-meter-service."""

    name = NAME

    @property
    def router(self) -> APIRouter:
        return router

    async def startup(self) -> None:
        global service
        service = SmartMeterService()
        await service.startup()

    async def shutdown(self) -> None:
        global service
        if service:
            await service.shutdown()
            service = None

    def register_health(self, health: StandardHealthCheck) -> None:
        health.register_check(f"{NAME}_recent_fetch", _check_recent_fetch)


adapter = SmartMeterAdapter()
