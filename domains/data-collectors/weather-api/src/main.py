"""Weather API Service for OpenWeatherMap Integration.

Fetches current weather data from the OpenWeatherMap API, caches results with
thundering herd protection, and stores time-series data in InfluxDB. Supports
header and query auth modes, InfluxDB fallback hostnames for DNS resilience,
and exponential backoff on consecutive background fetch failures.
"""

from __future__ import annotations

import asyncio
import re
from contextlib import suppress
from datetime import UTC, datetime
from typing import Any

import aiohttp
from fastapi import HTTPException
from homeiq_observability.logging_config import setup_logging
from homeiq_resilience import ServiceLifespan, StandardHealthCheck, create_app
from influxdb_client_3 import InfluxDBClient3, Point
from pydantic import BaseModel

from . import __version__
from .config import settings

SERVICE_NAME = settings.service_name
SERVICE_VERSION = __version__

# Configure logging
logger = setup_logging(SERVICE_NAME)


# Pydantic Models
class WeatherResponse(BaseModel):
    """Current weather response"""
    temperature: float
    feels_like: float
    humidity: int
    pressure: int
    condition: str
    description: str
    wind_speed: float
    cloudiness: int
    location: str
    timestamp: str


class WeatherService:
    """Weather data service that fetches from OpenWeatherMap and stores in InfluxDB.

    Implements cache-first fetching with thundering herd protection, InfluxDB fallback
    hostnames, and continuous background polling with exponential backoff on failures.
    """

    def __init__(self) -> None:
        """Initialize the weather service with OpenWeatherMap and InfluxDB config."""
        self._init_weather_config()
        self._init_influxdb_config()
        self._init_cache_and_components()

        if not self.api_key:
            logger.warning("WEATHER_API_KEY not set - service will run in standby mode")
        if not self.influxdb_token:
            raise ValueError("INFLUXDB_TOKEN required")

    def _init_weather_config(self) -> None:
        """Initialize OpenWeatherMap API configuration."""
        self.api_key = settings.weather_api_key
        location = settings.weather_location
        if not re.match(r'^[a-zA-Z\s,.\-]{1,100}$', location):
            raise ValueError(f"Invalid WEATHER_LOCATION: must be alphanumeric with spaces/commas, got '{location}'")
        self.location = location
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.auth_mode = settings.weather_api_auth_mode
        if self.auth_mode == "query":
            logger.warning(
                "SECURITY: WEATHER_API_AUTH_MODE=query sends API key in URL parameters. "
                "This exposes the key in logs and proxy caches. Use 'header' mode unless "
                "your API plan does not support header authentication."
            )

    def _init_influxdb_config(self) -> None:
        """Initialize InfluxDB configuration with fallback hostname logic."""
        influxdb_url = settings.influxdb_url
        if '://' in influxdb_url:
            self.influxdb_host = influxdb_url.split('://')[1].split(':')[0]
            self.influxdb_port = influxdb_url.split(':')[-1] if ':' in influxdb_url.split('://')[1] else '8086'
        else:
            self.influxdb_host = influxdb_url.split(':')[0]
            self.influxdb_port = influxdb_url.split(':')[1] if ':' in influxdb_url else '8086'

        fallback_hosts = [h.strip() for h in settings.influxdb_fallback_hosts.split(',') if h.strip()]

        self.influxdb_urls = [influxdb_url]
        for host in fallback_hosts:
            if host != self.influxdb_host:
                self.influxdb_urls.append(f'http://{host}:{self.influxdb_port}')

        logger.info("InfluxDB fallback URLs configured: %d URLs (original + %d fallbacks)", len(self.influxdb_urls), len(fallback_hosts))
        self.influxdb_url = influxdb_url
        self.influxdb_token = settings.influxdb_token.get_secret_value() if settings.influxdb_token else None
        self.influxdb_org = settings.influxdb_org
        self.influxdb_bucket = settings.influxdb_bucket
        self.max_influx_retries = settings.influxdb_write_retries
        self.working_influxdb_host = None

    def _init_cache_and_components(self) -> None:
        """Initialize cache, service components, and stats counters."""
        self.cached_weather: dict[str, Any] | None = None
        self.cache_time: datetime | None = None
        self.cache_ttl = settings.cache_ttl_seconds

        self.session: aiohttp.ClientSession | None = None
        self.influxdb_client: InfluxDBClient3 | None = None
        self.background_task: asyncio.Task | None = None
        self.last_background_error: str | None = None
        self.last_successful_fetch: datetime | None = None
        self.last_influx_write: datetime | None = None
        self.last_influx_write_error: str | None = None
        self.influx_write_failure_count = 0
        self.influx_write_success_count = 0
        self._fetch_lock = asyncio.Lock()
        self.fetch_count = 0
        self.cache_hits = 0
        self.cache_misses = 0

    async def startup(self) -> None:
        """Initialize HTTP session and InfluxDB client with fallback hostname logic."""
        logger.info("Initializing Weather API Service...")

        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))

        # Try to connect to InfluxDB with fallback hostnames
        self.influxdb_client = await self._initialize_influxdb()

        if not self.influxdb_client:
            logger.warning("InfluxDB client initialization failed - service will continue but writes will fail")

        logger.info("Weather API Service initialized")

    async def _initialize_influxdb(self) -> InfluxDBClient3 | None:
        """Initialize InfluxDB client, trying each fallback URL in order.

        Returns:
            Connected InfluxDB client on success, None if all URLs fail.
        """
        if not self.influxdb_token:
            logger.error("INFLUXDB_TOKEN not set - cannot initialize InfluxDB client")
            return None

        # Try each URL in order
        for url in self.influxdb_urls:
            try:
                logger.info("Attempting to connect to InfluxDB at %s", url)

                # InfluxDBClient3 expects full URL with protocol
                client = InfluxDBClient3(
                    host=url,
                    token=self.influxdb_token,
                    database=self.influxdb_bucket,
                    org=self.influxdb_org
                )

                # Actually test the connection with a lightweight query
                await asyncio.to_thread(client.query, "SELECT 1")
                self.working_influxdb_host = url
                logger.info("[OK] Successfully verified InfluxDB connection at: %s", url)
                return client

            except Exception as e:
                logger.warning("Failed to connect to InfluxDB at %s: %s", url, e)
                continue

        logger.error("[FAIL] Failed to connect to InfluxDB with any URL: %s", self.influxdb_urls)
        return None

    async def shutdown(self) -> None:
        """Shutdown service, stopping background task and closing connections."""
        logger.info("Shutting down Weather API Service...")
        await self.stop_background_task()

        if self.session and not self.session.closed:
            await self.session.close()

        if self.influxdb_client:
            self.influxdb_client.close()

    async def fetch_weather(self) -> dict[str, Any] | None:
        """Fetch current weather data from OpenWeatherMap API.

        Returns:
            Weather data dictionary with temperature, humidity, etc., or cached data on failure.
        """
        if not self.api_key:
            return self.cached_weather

        if not self.session or self.session.closed:
            raise RuntimeError("HTTP session not initialized")

        try:
            url = f"{self.base_url}/weather"
            params = {
                "q": self.location,
                "units": "metric"
            }
            headers = {
                "Accept": "application/json"
            }
            if self.auth_mode == "header":
                headers["X-API-Key"] = self.api_key
            else:
                params["appid"] = self.api_key

            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()

                    timestamp = datetime.now(UTC).isoformat()
                    weather = {
                        'temperature': data.get("main", {}).get("temp", 0),
                        'feels_like': data.get("main", {}).get("feels_like", 0),
                        'humidity': data.get("main", {}).get("humidity", 0),
                        'pressure': data.get("main", {}).get("pressure", 0),
                        'condition': data.get("weather", [{}])[0].get("main", "Unknown"),
                        'description': data.get("weather", [{}])[0].get("description", ""),
                        'wind_speed': data.get("wind", {}).get("speed", 0),
                        'cloudiness': data.get("clouds", {}).get("all", 0),
                        'location': data.get("name", self.location),
                        'timestamp': timestamp
                    }

                    self.fetch_count += 1
                    logger.info("Fetched weather: %s°C, %s", weather['temperature'], weather['condition'])
                    return weather
                else:
                    if response.status == 401 and self.auth_mode == "header":
                        logger.error("OpenWeatherMap API authentication failed with header mode. "
                                     "Set WEATHER_API_AUTH_MODE=query if your API key does not support headers.")
                    else:
                        logger.error("OpenWeatherMap API error: %s", response.status)
                    return self.cached_weather

        except Exception as e:
            logger.error("Error fetching weather: %s", e)
            return self.cached_weather

    async def get_current_weather(self) -> dict[str, Any] | None:
        """Get current weather using cache-first strategy with thundering herd protection.

        Returns:
            Weather data dictionary from cache or fresh API fetch.
        """
        # Check cache first (no lock needed for reads)
        now = datetime.now(UTC)
        if self.cached_weather and self.cache_time:
            age = (now - self.cache_time).total_seconds()
            if age < self.cache_ttl:
                self.cache_hits += 1
                return self.cached_weather

        # Lock to prevent thundering herd on cache miss
        async with self._fetch_lock:
            # Double-check cache after acquiring lock
            if self.cached_weather and self.cache_time:
                age = (datetime.now(UTC) - self.cache_time).total_seconds()
                if age < self.cache_ttl:
                    self.cache_hits += 1
                    return self.cached_weather

            # Cache miss - fetch
            self.cache_misses += 1
            weather = await self.fetch_weather()

            if weather:
                self.cached_weather = weather
                self.cache_time = datetime.now(UTC)
                self.last_successful_fetch = self.cache_time

                # Write to InfluxDB
                await self.store_in_influxdb(weather)

            return weather

    async def store_in_influxdb(self, weather: dict[str, Any]) -> None:
        """Store weather data in InfluxDB with retry and fallback hostname logic.

        Args:
            weather: Weather data dictionary with temperature, humidity, etc.
        """
        if not weather:
            return

        if not self.influxdb_client:
            logger.warning("InfluxDB client not available, attempting to reinitialize...")
            self.influxdb_client = await self._initialize_influxdb()
            if not self.influxdb_client:
                logger.error("Cannot write to InfluxDB - client unavailable after reinit attempt")
                return

        timestamp = datetime.fromisoformat(weather['timestamp'])

        point = Point("weather") \
            .tag("location", weather['location']) \
            .tag("condition", weather['condition']) \
            .tag("description", weather.get('description', '')) \
            .field("temperature", float(weather['temperature'])) \
            .field("feels_like", float(weather.get('feels_like', 0))) \
            .field("humidity", int(weather['humidity'])) \
            .field("pressure", int(weather['pressure'])) \
            .field("wind_speed", float(weather['wind_speed'])) \
            .field("cloudiness", int(weather['cloudiness'])) \
            .time(timestamp)

        await self._write_point_with_retry(point)

    async def _handle_dns_write_error(self, attempt: int, error: Exception) -> bool:
        """Handle DNS resolution error during InfluxDB write by reconnecting.

        Args:
            attempt: Current retry attempt number.
            error: The exception that occurred.

        Returns:
            True if reconnection succeeded and retry should continue, False to give up.
        """
        logger.warning("DNS resolution failed (attempt %d/%d), reconnecting...", attempt, self.max_influx_retries)
        old_client = self.influxdb_client
        self.influxdb_client = await self._initialize_influxdb()
        if not self.influxdb_client:
            logger.error("Failed to reconnect to InfluxDB with fallback - all URLs exhausted")
            if attempt >= self.max_influx_retries:
                self.influx_write_failure_count += 1
                logger.error("Failed to write to InfluxDB after %s attempts: %s", attempt, error)
            return False
        if old_client != self.influxdb_client:
            logger.info("Reconnected to InfluxDB using fallback URL: %s", self.working_influxdb_host)
        return True

    async def _write_point_with_retry(self, point: Point) -> None:
        """Write a single InfluxDB point with retry and DNS fallback logic.

        Args:
            point: InfluxDB Point object to write.
        """
        for attempt in range(1, self.max_influx_retries + 1):
            try:
                await asyncio.to_thread(self.influxdb_client.write, point)
                self.last_influx_write = datetime.now(UTC)
                self.last_influx_write_error = None
                self.influx_write_success_count += 1
                logger.info("Weather data written to InfluxDB")
                return
            except Exception as e:
                error_str = str(e)
                self.last_influx_write_error = error_str

                is_dns_error = "Name does not resolve" in error_str or "Failed to resolve" in error_str
                if is_dns_error and not await self._handle_dns_write_error(attempt, e):
                    if attempt >= self.max_influx_retries:
                        return
                    continue

                if attempt >= self.max_influx_retries:
                    self.influx_write_failure_count += 1
                    logger.error("Failed to write to InfluxDB after %s attempts: %s", attempt, e)
                else:
                    backoff = 2 ** (attempt - 1)
                    logger.warning("InfluxDB write failed (attempt %s/%s). Retrying in %ss",
                                   attempt, self.max_influx_retries, backoff)
                    await asyncio.sleep(backoff)

    async def run_continuous(self) -> None:
        """Background fetch loop with exponential backoff on consecutive failures.

        Fetches weather data on each cache TTL interval. On error, applies
        linear backoff (max 30 minutes) based on consecutive failure count.
        """
        logger.info("Starting continuous fetch (every %ds)", self.cache_ttl)
        consecutive_failures = 0

        while True:
            try:
                await self.get_current_weather()
                consecutive_failures = 0  # Reset on success
                await asyncio.sleep(self.cache_ttl)
            except asyncio.CancelledError:
                logger.info("Continuous fetch loop cancelled")
                raise
            except Exception as e:
                consecutive_failures += 1
                self.last_background_error = str(e)
                backoff = min(300 * consecutive_failures, 1800)  # Max 30 minutes
                logger.error("Error in continuous loop (failure #%d): %s. Retrying in %ds",
                             consecutive_failures, e, backoff)
                await asyncio.sleep(backoff)

    def start_background_task(self) -> asyncio.Task:
        """Start the guarded background fetch task, reusing existing if active.

        Returns:
            The background asyncio.Task running the continuous fetch loop.
        """
        if self.background_task and not self.background_task.done():
            return self.background_task

        async def _run():
            try:
                await self.run_continuous()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.last_background_error = str(exc)
                logger.exception("Weather background task failed")

        self.background_task = asyncio.create_task(_run(), name="weather-fetch-loop")
        return self.background_task

    async def stop_background_task(self) -> None:
        """Stop background task gracefully, cancelling and awaiting completion."""
        if self.background_task and not self.background_task.done():
            self.background_task.cancel()
            with suppress(asyncio.CancelledError):
                await self.background_task
        self.background_task = None


# Global service instance
weather_service = None


async def _startup_weather() -> None:
    """Start weather service and background task."""
    global weather_service
    weather_service = WeatherService()
    await weather_service.startup()
    weather_service.start_background_task()


async def _shutdown_weather() -> None:
    """Shut down weather service."""
    global weather_service
    if weather_service:
        await weather_service.shutdown()
        weather_service = None


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

_lifespan = ServiceLifespan(settings.service_name)
_lifespan.on_startup(_startup_weather, name="weather")
_lifespan.on_shutdown(_shutdown_weather, name="weather")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

_health = StandardHealthCheck(
    service_name=settings.service_name,
    version=SERVICE_VERSION,
)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = create_app(
    title="Weather API Service",
    version=SERVICE_VERSION,
    description="Standalone weather data service",
    lifespan=_lifespan.handler,
    health_check=_health,
    cors_origins=settings.get_cors_origins_list(),
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "status": "running",
        "endpoints": ["/health", "/metrics", "/current-weather", "/cache/stats"]
    }


@app.get("/metrics")
async def metrics():
    """Lightweight numeric metrics endpoint (JSON)"""
    if not weather_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return {
        "fetch_count": weather_service.fetch_count,
        "cache_hits": weather_service.cache_hits,
        "cache_misses": weather_service.cache_misses,
        "influx_write_success_count": weather_service.influx_write_success_count,
        "influx_write_failure_count": weather_service.influx_write_failure_count,
    }


@app.get("/current-weather", response_model=WeatherResponse)
async def get_current_weather():
    """Get current weather (Story 31.3)"""
    if not weather_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    weather = await weather_service.get_current_weather()

    if not weather:
        raise HTTPException(status_code=503, detail="Weather data unavailable")

    return WeatherResponse(**weather)


@app.get("/cache/stats")
async def cache_stats():
    """Cache statistics"""
    if not weather_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    total = weather_service.cache_hits + weather_service.cache_misses
    hit_rate = (weather_service.cache_hits / total * 100) if total > 0 else 0

    return {
        "hits": weather_service.cache_hits,
        "misses": weather_service.cache_misses,
        "hit_rate": round(hit_rate, 2),
        "fetch_count": weather_service.fetch_count,
        "ttl_seconds": weather_service.cache_ttl,
        "last_cache_time": weather_service.cache_time.isoformat() if weather_service.cache_time else None
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",  # noqa: S104
        port=settings.service_port,
        reload=True,
    )
