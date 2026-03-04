"""Air Quality Service Main Entry Point.

Fetches AQI data from OpenWeather API.
Migrated from aiohttp to FastAPI with shared library pattern.
"""

import asyncio
import logging
import time
from datetime import UTC, datetime
from typing import Any

import aiohttp
from config import settings
from health_check import HealthCheckHandler
from homeiq_observability.logging_config import (
    log_error_with_context,
    log_with_context,
    setup_logging,
)
from homeiq_resilience import ServiceLifespan, StandardHealthCheck, create_app
from influxdb_client_3 import InfluxDBClient3, Point

logger = setup_logging("air-quality-service")


class APIKeyFilter(logging.Filter):
    """Redact API keys from log output."""

    def __init__(self, api_key: str) -> None:
        super().__init__()
        self.api_key = api_key

    def filter(self, record: logging.LogRecord) -> bool:
        if self.api_key and self.api_key in record.getMessage():
            record.msg = record.msg.replace(self.api_key, "***REDACTED***")
            if record.args:
                record.args = tuple(
                    str(a).replace(self.api_key, "***REDACTED***") if isinstance(a, str) else a
                    for a in record.args
                )
        return True


_api_key = settings.weather_api_key
if _api_key:
    for handler in logging.root.handlers:
        handler.addFilter(APIKeyFilter(_api_key))
    logger.addFilter(APIKeyFilter(_api_key))


class AirQualityService:
    """Fetch and store air quality data from OpenWeather API."""

    def __init__(self) -> None:
        """Initialize the air quality service with API keys and InfluxDB config."""
        self.api_key = settings.weather_api_key
        self.latitude = settings.latitude
        self.longitude = settings.longitude
        self.base_url = "https://api.openweathermap.org/data/2.5/air_pollution"

        # Home Assistant configuration (for automatic location detection)
        self.ha_url = settings.home_assistant_url or settings.ha_http_url
        self.ha_token = settings.home_assistant_token or settings.ha_token

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
        self.retry_delays = [30, 120, 300]

        # Rate limiting for /current-aqi (60 requests per minute)
        self._rate_limit_max = 60
        self._rate_limit_window = 60.0
        self._rate_limit_requests: list[float] = []

        # Cache
        self.cached_data: dict[str, Any] | None = None
        self.last_fetch_time: datetime | None = None
        self.last_category: str | None = None

        # Components
        self.session: aiohttp.ClientSession | None = None
        self.influxdb_client: InfluxDBClient3 | None = None
        self.health_handler = HealthCheckHandler()
        self._background_task: asyncio.Task | None = None

        if not self.api_key:
            raise ValueError("WEATHER_API_KEY environment variable is required")
        if not self.influxdb_token:
            raise ValueError("INFLUXDB_TOKEN environment variable is required")

        self._validate_coordinate(self.latitude, "LATITUDE", -90, 90)
        self._validate_coordinate(self.longitude, "LONGITUDE", -180, 180)

    @staticmethod
    def _validate_coordinate(value: str, name: str, min_val: float, max_val: float) -> None:
        try:
            num = float(value)
        except (TypeError, ValueError) as err:
            msg = f"{name} must be a valid number, got {value!r}"
            raise ValueError(msg) from err
        if not (min_val <= num <= max_val):
            msg = f"{name} must be between {min_val} and {max_val}, got {num}"
            raise ValueError(msg)

    async def fetch_location_from_ha(self) -> dict[str, float] | None:
        """Fetch latitude/longitude from Home Assistant configuration API."""
        if not self.ha_url or not self.ha_token:
            logger.warning(
                "Home Assistant URL or token not configured, "
                "using environment variables for location"
            )
            return None

        try:
            headers = {"Authorization": f"Bearer {self.ha_token}"}
            url = f"{self.ha_url}/api/config"

            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    config = await response.json()
                    lat = config.get("latitude")
                    lon = config.get("longitude")

                    if lat is not None and lon is not None:
                        logger.info("Fetched location from Home Assistant: %s,%s", lat, lon)
                        return {"latitude": float(lat), "longitude": float(lon)}
                    logger.warning("Home Assistant config missing latitude/longitude")
                    return None
                logger.warning("Failed to fetch HA config: HTTP %d", response.status)
                return None

        except Exception as e:
            logger.warning("Could not fetch location from Home Assistant: %s", e)
            return None

    async def startup(self) -> None:
        """Initialize HTTP session, fetch HA location, and connect to InfluxDB."""
        logger.info("Initializing Air Quality Service...")

        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))

        # Try to get location from Home Assistant first
        ha_location = await self.fetch_location_from_ha()
        if ha_location:
            self.latitude = str(ha_location["latitude"])
            self.longitude = str(ha_location["longitude"])
            logger.info("Using location from Home Assistant: %s, %s", self.latitude, self.longitude)
        else:
            logger.info("Using configured location: %s, %s", self.latitude, self.longitude)

        self.influxdb_client = InfluxDBClient3(
            host=self.influxdb_url,
            token=self.influxdb_token,
            database=self.influxdb_bucket,
            org=self.influxdb_org,
        )

        # Start background collection
        self._background_task = asyncio.create_task(self.run_continuous())

        logger.info("Air Quality Service initialized")

    async def shutdown(self) -> None:
        """Shutdown service."""
        logger.info("Shutting down Air Quality Service...")

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

    def _parse_pollution_response(self, raw_data: dict[str, Any]) -> dict[str, Any] | None:
        """Parse OpenWeather air pollution API response into normalized format."""
        if not raw_data or "list" not in raw_data or not raw_data["list"]:
            logger.warning("OpenWeather API returned empty data")
            return None

        pollution_data = raw_data["list"][0]
        main_data = pollution_data.get("main", {})
        components = pollution_data.get("components", {})

        ow_aqi = main_data.get("aqi", 1)
        aqi_map = {1: 25, 2: 75, 3: 125, 4: 175, 5: 250}
        category_map = {1: "Good", 2: "Fair", 3: "Moderate", 4: "Poor", 5: "Very Poor"}

        timestamp = datetime.fromtimestamp(
            pollution_data.get("dt", datetime.now(UTC).timestamp()), tz=UTC
        )

        return {
            "aqi": aqi_map.get(ow_aqi, 25),
            "category": category_map.get(ow_aqi, "Unknown"),
            "parameter": "Combined",
            "pm25": round(float(components.get("pm2_5", 0)), 2),
            "pm10": round(float(components.get("pm10", 0)), 2),
            "ozone": round(float(components.get("o3", 0)), 2),
            "timestamp": timestamp,
            "co": float(components.get("co", 0)),
            "no2": float(components.get("no2", 0)),
            "so2": float(components.get("so2", 0)),
        }

    def _update_aqi_cache(self, data: dict[str, Any]) -> None:
        """Update cache and health metrics after a successful AQI fetch."""
        if self.last_category and self.last_category != data["category"]:
            logger.warning(
                "AQI category changed: %s -> %s", self.last_category, data["category"]
            )
        self.last_category = data["category"]
        self.cached_data = data
        self.last_fetch_time = datetime.now(UTC)
        self.health_handler.last_successful_fetch = datetime.now(UTC)
        self.health_handler.total_fetches += 1
        self.health_handler.last_api_success = True

    async def fetch_air_quality(self) -> dict[str, Any] | None:
        """Fetch AQI from OpenWeather API with retry logic."""
        for attempt in range(len(self.retry_delays) + 1):
            try:
                params = {"lat": self.latitude, "lon": self.longitude, "appid": self.api_key}

                log_with_context(
                    logger,
                    "INFO",
                    "Fetching AQI for location %s,%s" % (self.latitude, self.longitude),
                    service="air-quality-service",
                )

                async with self.session.get(self.base_url, params=params) as response:
                    if response.status == 200:
                        raw_data = await response.json()
                        data = self._parse_pollution_response(raw_data)
                        if data is None:
                            return self.cached_data
                        self._update_aqi_cache(data)
                        logger.info("AQI: %d (%s)", data["aqi"], data["category"])
                        return data

                    logger.error("OpenWeather API returned status %d", response.status)
                    if attempt < len(self.retry_delays):
                        logger.info(
                            "Retrying in %ds (attempt %d/%d)",
                            self.retry_delays[attempt],
                            attempt + 1,
                            len(self.retry_delays),
                        )
                        await asyncio.sleep(self.retry_delays[attempt])
                        continue
                    self.health_handler.last_api_success = False
                    self.health_handler.failed_fetches += 1
                    return self.cached_data

            except Exception as e:
                if attempt < len(self.retry_delays):
                    logger.warning(
                        "Fetch attempt %d failed: %s. Retrying in %ds",
                        attempt + 1,
                        e,
                        self.retry_delays[attempt],
                    )
                    await asyncio.sleep(self.retry_delays[attempt])
                    continue
                self.health_handler.last_api_success = False
                log_error_with_context(
                    logger, f"Error fetching AQI: {e}", e, service="air-quality-service"
                )
                self.health_handler.failed_fetches += 1
                return self.cached_data
        return self.cached_data  # pragma: no cover — unreachable but satisfies type checker

    async def store_in_influxdb(self, data: dict[str, Any]) -> None:
        """Store AQI data in InfluxDB."""
        if not data:
            return

        if not self.influxdb_client:
            logger.error("InfluxDB client not initialized")
            return

        try:
            point = (
                Point("air_quality")
                .tag("location", f"{self.latitude},{self.longitude}")
                .tag("category", data["category"])
                .tag("parameter", data["parameter"])
                .field("aqi", int(data["aqi"]))
                .field("pm25", round(float(data["pm25"]), 2))
                .field("pm10", round(float(data["pm10"]), 2))
                .field("ozone", round(float(data["ozone"]), 2))
                .field("co", float(data.get("co", 0)))
                .field("no2", float(data.get("no2", 0)))
                .field("so2", float(data.get("so2", 0)))
                .time(data["timestamp"])
            )

            await asyncio.to_thread(self.influxdb_client.write, point)

            self.health_handler.total_writes += 1
            self.health_handler.last_influxdb_success = True
            logger.info("AQI data written to InfluxDB")

        except Exception as e:
            log_error_with_context(
                logger,
                f"Error writing to InfluxDB: {e}",
                e,
                service="air-quality-service",
            )
            self.health_handler.last_influxdb_success = False
            self.health_handler.failed_writes += 1

    def _is_cache_valid(self) -> bool:
        """Check if cached AQI data is still fresh."""
        if not self.cached_data or not self.last_fetch_time:
            return False
        age_minutes = (datetime.now(UTC) - self.last_fetch_time).total_seconds() / 60
        return age_minutes < self.cache_duration

    def _check_rate_limit(self) -> bool:
        """Check if the current request is within the rate limit window."""
        now = time.monotonic()
        self._rate_limit_requests = [
            t for t in self._rate_limit_requests if now - t < self._rate_limit_window
        ]
        if len(self._rate_limit_requests) >= self._rate_limit_max:
            return False
        self._rate_limit_requests.append(now)
        return True

    async def run_continuous(self, stop_event: asyncio.Event | None = None) -> None:
        """Run the continuous AQI data collection and storage loop."""
        logger.info("Starting continuous AQI monitoring (every %ds)", self.fetch_interval)

        while not (stop_event and stop_event.is_set()):
            try:
                data = await self.fetch_air_quality()
                if data:
                    await self.store_in_influxdb(data)

                if stop_event:
                    try:
                        await asyncio.wait_for(stop_event.wait(), timeout=self.fetch_interval)
                        break
                    except TimeoutError:
                        pass
                else:
                    await asyncio.sleep(self.fetch_interval)

            except asyncio.CancelledError:
                logger.info("Continuous loop cancelled")
                break
            except Exception as e:
                log_error_with_context(
                    logger,
                    f"Error in continuous loop: {e}",
                    e,
                    service="air-quality-service",
                )
                if stop_event:
                    try:
                        await asyncio.wait_for(stop_event.wait(), timeout=300)
                        break
                    except TimeoutError:
                        pass
                else:
                    await asyncio.sleep(300)


# --- Global service instance ---
service: AirQualityService | None = None

# --- Lifespan ---
lifespan = ServiceLifespan(service_name="air-quality-service")


async def _startup() -> None:
    global service
    service = AirQualityService()
    await service.startup()


async def _shutdown() -> None:
    if service:
        await service.shutdown()


lifespan.on_startup(_startup, name="air-quality-init")
lifespan.on_shutdown(_shutdown, name="air-quality-cleanup")

# --- Health check ---
health = StandardHealthCheck(service_name="air-quality-service", version="1.0.0")

# --- App ---
app = create_app(
    title="Air Quality Service",
    version="1.0.0",
    description="Fetches AQI data from OpenWeather API",
    lifespan=lifespan.handler,
    health_check=health,
)


@app.get("/current-aqi")
async def get_current_aqi() -> dict:
    """API endpoint returning current AQI data with rate limiting."""
    if not service:
        return {"error": "Service not initialized"}

    if not service._check_rate_limit():
        from fastapi.responses import JSONResponse

        return JSONResponse(content={"error": "Rate limit exceeded"}, status_code=429)

    if service._is_cache_valid():
        return {
            "aqi": service.cached_data["aqi"],
            "category": service.cached_data["category"],
            "pm25": service.cached_data.get("pm25", 0),
            "pm10": service.cached_data.get("pm10", 0),
            "ozone": service.cached_data.get("ozone", 0),
            "co": service.cached_data.get("co", 0),
            "no2": service.cached_data.get("no2", 0),
            "so2": service.cached_data.get("so2", 0),
            "timestamp": (
                service.last_fetch_time.isoformat() if service.last_fetch_time else None
            ),
        }
    from fastapi.responses import JSONResponse

    return JSONResponse(content={"error": "No data available"}, status_code=503)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",  # noqa: S104 — Docker requires binding all interfaces
        port=settings.service_port,
        log_level="info",
    )
