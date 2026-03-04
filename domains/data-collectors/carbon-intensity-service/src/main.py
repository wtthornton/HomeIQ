"""Carbon Intensity Service for Grid Emissions Monitoring.

Fetches real-time Marginal Operating Emissions Rate (MOER) data from the
WattTime v3 API, converts to gCO2/kWh, and stores time-series data in InfluxDB.
Migrated from aiohttp to FastAPI with shared library pattern.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlparse

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

logger = setup_logging("carbon-intensity-service")


class CarbonIntensityService:
    """Fetch and store grid carbon intensity data from the WattTime API."""

    def __init__(self) -> None:
        """Initialize the carbon intensity service with WattTime and InfluxDB config."""
        # WattTime authentication credentials
        self.username = settings.watttime_username
        self.password = settings.watttime_password
        self.api_token = settings.watttime_api_token

        # Token management
        self.token_expires_at: datetime | None = None
        self.token_refresh_buffer = 300  # Refresh 5 minutes before expiry

        # WattTime configuration
        self.region = settings.grid_region
        self.base_url = "https://api.watttime.org"

        # InfluxDB configuration
        self.influxdb_url = settings.influxdb_url
        parsed_influx = urlparse(self.influxdb_url)
        if not parsed_influx.scheme:
            self.influxdb_url = f"http://{self.influxdb_url}:8086"
        self.influxdb_token = (
            settings.influxdb_token.get_secret_value() if settings.influxdb_token else None
        )
        self.influxdb_org = settings.influxdb_org
        self.influxdb_bucket = settings.influxdb_bucket

        # Service configuration
        self.fetch_interval = settings.fetch_interval
        self.cache_duration = timedelta(minutes=15)

        # Cache
        self.cached_data: dict[str, Any] | None = None
        self.last_fetch_time: datetime | None = None

        # Components
        self.session: aiohttp.ClientSession | None = None
        self.influxdb_client: InfluxDBClient3 | None = None
        self.health_handler = HealthCheckHandler()
        self._background_task: asyncio.Task | None = None

        # Track configuration status
        self.credentials_configured = False

        # Validate configuration
        self._validate_credentials()

        if not self.influxdb_token:
            raise ValueError("INFLUXDB_TOKEN environment variable is required")

    def _validate_credentials(self) -> None:
        """Validate WattTime credentials and configure service accordingly."""
        placeholder_usernames = {"your_watttime_username", "your-username", ""}
        placeholder_passwords = {"your_watttime_password", "your-password", ""}

        is_placeholder_username = (
            self.username and self.username.lower() in placeholder_usernames
        )
        is_placeholder_password = (
            self.password and self.password.lower() in placeholder_passwords
        )

        if (
            not self.username
            or not self.password
            or is_placeholder_username
            or is_placeholder_password
        ):
            if not self.api_token:
                if is_placeholder_username or is_placeholder_password:
                    logger.error(
                        "[ERROR] WattTime credentials are placeholder values! "
                        "Please update WATTTIME_USERNAME and WATTTIME_PASSWORD in .env file. "
                        "Register at https://watttime.org if you don't have an account. "
                        "Service will run in standby mode until credentials are configured."
                    )
                else:
                    logger.warning(
                        "[WARN] No WattTime credentials configured! "
                        "Service will run in standby mode. "
                        "Add WATTTIME_USERNAME/PASSWORD to environment to enable data fetching."
                    )
                self.credentials_configured = False
                self.health_handler.credentials_missing = True
            else:
                logger.warning(
                    "Using static WATTTIME_API_TOKEN - token will expire in 30 minutes"
                )
                self.credentials_configured = True
                self.health_handler.credentials_missing = False
        else:
            self.credentials_configured = True
            self.health_handler.credentials_missing = False

    async def startup(self) -> None:
        """Initialize HTTP session, obtain WattTime token, and connect to InfluxDB."""
        logger.info("Initializing Carbon Intensity Service...")

        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))

        # If using username/password, get initial token
        if self.username and self.password:
            logger.info("Obtaining initial WattTime API token...")
            if not await self.refresh_token():
                logger.error(
                    "Failed to obtain initial WattTime API token - will run in standby mode"
                )
                self.credentials_configured = False
        elif self.api_token:
            logger.info("Using static API token (will expire in 30 minutes)")
        else:
            logger.warning("No WattTime credentials - service running in standby mode")

        # Create InfluxDB client
        logger.info("Connecting to InfluxDB at %s", self.influxdb_url)
        self.influxdb_client = InfluxDBClient3(
            host=self.influxdb_url,
            token=self.influxdb_token,
            database=self.influxdb_bucket,
            org=self.influxdb_org,
        )

        # Validate InfluxDB connection at startup
        try:
            test_point = (
                Point("service_startup")
                .tag("service", "carbon-intensity-service")
                .field("status", 1)
            )
            await asyncio.wait_for(
                asyncio.to_thread(self.influxdb_client.write, test_point), timeout=10.0
            )
            logger.info("InfluxDB connection validated successfully")
        except Exception as e:
            logger.warning(
                "InfluxDB startup validation failed (will retry on writes): %s", e
            )

        # Start background collection
        self._background_task = asyncio.create_task(self.run_continuous())

        logger.info("Carbon Intensity Service initialized successfully")

    async def shutdown(self) -> None:
        """Cleanup HTTP session and InfluxDB client on service shutdown."""
        logger.info("Shutting down Carbon Intensity Service...")

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

        logger.info("Carbon Intensity Service shut down successfully")

    async def refresh_token(self) -> bool:
        """Refresh WattTime API token using username/password authentication."""
        if not self.username or not self.password:
            logger.error("Cannot refresh token: username/password not configured")
            return False

        if not self.session:
            logger.error("HTTP session not initialized")
            return False

        try:
            url = f"{self.base_url}/login"
            auth = aiohttp.BasicAuth(self.username, self.password)

            log_with_context(
                logger,
                "INFO",
                "Refreshing WattTime API token",
                service="carbon-intensity-service",
            )

            async with self.session.post(url, auth=auth, allow_redirects=False) as response:
                if response.status == 200:
                    content_type = response.headers.get("Content-Type", "")
                    if "application/json" not in content_type:
                        error = ValueError(f"Unexpected content type: {content_type}")
                        log_error_with_context(
                            logger,
                            f"Unexpected content type: {content_type}",
                            error,
                            service="carbon-intensity-service",
                            status_code=response.status,
                        )
                        return False

                    data = await response.json()
                    self.api_token = data.get("token")
                    self.token_expires_at = datetime.now(UTC) + timedelta(minutes=30)
                    self.health_handler.last_token_refresh = datetime.now(UTC)
                    self.health_handler.token_refresh_count += 1

                    logger.info(
                        "Token refreshed successfully, expires at %s",
                        self.token_expires_at.isoformat(),
                    )
                    return True
                if response.status == 401:
                    logger.error(
                        "Authentication failed (401) - invalid credentials. "
                        "Please check WATTTIME_USERNAME and WATTTIME_PASSWORD in .env file",
                        extra={
                            "context": {
                                "service": "carbon-intensity-service",
                                "status_code": response.status,
                            }
                        },
                    )
                    self.credentials_configured = False
                    self.health_handler.credentials_missing = True
                    return False
                if response.status in (301, 302, 303, 307, 308):
                    location = response.headers.get("Location", "unknown")
                    error = ValueError(f"Unexpected redirect to {location}")
                    log_error_with_context(
                        logger,
                        f"Unexpected redirect to {location} - likely invalid API endpoint",
                        error,
                        service="carbon-intensity-service",
                        status_code=response.status,
                    )
                    self.credentials_configured = False
                    self.health_handler.credentials_missing = True
                    return False
                logger.error(
                    "Token refresh failed with status %d",
                    response.status,
                    extra={
                        "context": {
                            "service": "carbon-intensity-service",
                            "status_code": response.status,
                        }
                    },
                )
                return False

        except aiohttp.client_exceptions.ContentTypeError as e:
            log_error_with_context(
                logger,
                "API returned non-JSON response (likely HTML redirect). Check credentials.",
                e,
                service="carbon-intensity-service",
            )
            self.credentials_configured = False
            self.health_handler.credentials_missing = True
            return False
        except Exception as e:
            log_error_with_context(
                logger,
                "Error refreshing token",
                e,
                service="carbon-intensity-service",
            )
            return False

    async def ensure_valid_token(self) -> bool:
        """Ensure we have a valid API token, refreshing if expired or near expiry."""
        if not self.token_expires_at and self.username and self.password:
            logger.info("No token expiration set, refreshing token...")
            return await self.refresh_token()

        if self.token_expires_at:
            time_until_expiry = (self.token_expires_at - datetime.now(UTC)).total_seconds()
            if time_until_expiry < self.token_refresh_buffer:
                logger.info("Token expires in %.0fs, refreshing...", time_until_expiry)
                return await self.refresh_token()

        if not self.api_token:
            logger.error("No API token available")
            return False
        return True

    def _parse_watttime_response(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Parse WattTime v3 API response into standardized carbon intensity format."""
        entries = raw_data.get("data", [])
        current_moer = float(entries[0]["value"]) if entries else 0.0
        carbon_intensity = current_moer * 0.4536

        data: dict[str, Any] = {
            "carbon_intensity": carbon_intensity,
            "carbon_intensity_raw_moer": current_moer,
            "timestamp": datetime.now(UTC),
        }

        if len(entries) > 12:
            data["forecast_1h"] = float(entries[12]["value"]) * 0.4536
        else:
            data["forecast_1h"] = 0.0
        if len(entries) > 288:
            data["forecast_24h"] = float(entries[288]["value"]) * 0.4536
        else:
            data["forecast_24h"] = (
                float(entries[-1]["value"]) * 0.4536 if entries else 0.0
            )

        return data

    def _update_cache_and_health(self, data: dict[str, Any]) -> None:
        """Update the in-memory cache and health check metrics."""
        self.cached_data = data
        self.last_fetch_time = datetime.now(UTC)
        self.health_handler.last_successful_fetch = datetime.now(UTC)
        self.health_handler.total_fetches += 1

    async def _handle_auth_retry(
        self, url: str, params: dict[str, str]
    ) -> dict[str, Any] | None:
        """Handle 401 response by refreshing token and retrying once."""
        if not self.session:
            return None

        if await self.refresh_token():
            logger.info("Token refreshed, retrying request...")
            headers = {"Authorization": f"Bearer {self.api_token}"}
            async with self.session.get(url, headers=headers, params=params) as retry_response:
                if retry_response.status == 200:
                    raw_data = await retry_response.json()
                    data = self._parse_watttime_response(raw_data)
                    self._update_cache_and_health(data)
                    logger.info(
                        "Carbon intensity (retry): %.1f gCO2/kWh", data["carbon_intensity"]
                    )
                    return data
        return None

    async def _handle_transient_retry(
        self,
        url: str,
        headers: dict[str, str],
        params: dict[str, str],
        initial_status: int,
    ) -> dict[str, Any] | None:
        """Handle transient HTTP errors (429, 5xx) with exponential backoff."""
        if not self.session:
            return None

        last_status = initial_status
        retry_delays = [5, 10, 20]
        for attempt, delay in enumerate(retry_delays, 1):
            logger.warning(
                "Transient HTTP %d, retry %d/%d after %ds",
                last_status,
                attempt,
                len(retry_delays),
                delay,
            )
            await asyncio.sleep(delay)
            async with self.session.get(url, headers=headers, params=params) as retry_resp:
                if retry_resp.status == 200:
                    raw_data = await retry_resp.json()
                    data = self._parse_watttime_response(raw_data)
                    self._update_cache_and_health(data)
                    logger.info(
                        "Carbon intensity (retry %d): %.1f gCO2/kWh",
                        attempt,
                        data["carbon_intensity"],
                    )
                    return data
                last_status = retry_resp.status
                if retry_resp.status not in (429, 500, 502, 503):
                    break

        logger.error(
            "WattTime API returned status %d after %d retries",
            last_status,
            len(retry_delays),
        )
        return None

    def _is_cache_valid(self) -> bool:
        """Check if cached carbon intensity data is still within the TTL window."""
        if not self.cached_data or not self.last_fetch_time:
            return False
        cache_age = datetime.now(UTC) - self.last_fetch_time
        return cache_age < self.cache_duration

    async def fetch_carbon_intensity(self) -> dict[str, Any] | None:
        """Fetch carbon intensity from WattTime API with caching and retry logic."""
        if not self.credentials_configured:
            return None

        if self._is_cache_valid():
            return self.cached_data

        if not self.session:
            logger.error("HTTP session not initialized")
            self.health_handler.failed_fetches += 1
            return self.cached_data

        try:
            if not await self.ensure_valid_token():
                logger.error("No valid WattTime token available")
                self.health_handler.failed_fetches += 1
                return self.cached_data

            url = f"{self.base_url}/v3/forecast"
            headers = {"Authorization": f"Bearer {self.api_token}"}
            params = {"region": self.region, "signal_type": "co2_moer"}

            log_with_context(
                logger,
                "INFO",
                "Fetching carbon intensity for region %s" % self.region,
                service="carbon-intensity-service",
                region=self.region,
            )

            result = await self._dispatch_api_request(url, headers, params)
            if result is not None:
                return result

            self.health_handler.failed_fetches += 1
            return self.cached_data

        except aiohttp.ClientError as e:
            log_error_with_context(
                logger,
                f"Error fetching carbon intensity: {e}",
                e,
                service="carbon-intensity-service",
            )
            self.health_handler.failed_fetches += 1
            if self.cached_data:
                logger.warning("Using cached carbon intensity data")
                return self.cached_data
            return None

        except Exception as e:
            log_error_with_context(
                logger,
                f"Unexpected error: {e}",
                e,
                service="carbon-intensity-service",
            )
            self.health_handler.failed_fetches += 1
            return self.cached_data

    async def _dispatch_api_request(
        self, url: str, headers: dict[str, str], params: dict[str, str]
    ) -> dict[str, Any] | None:
        """Make the WattTime API request and dispatch based on status code."""
        if not self.session:
            return None

        async with self.session.get(url, headers=headers, params=params) as response:
            if response.status == 200:
                raw_data = await response.json()
                data = self._parse_watttime_response(raw_data)
                self._update_cache_and_health(data)
                logger.info(
                    "Carbon intensity: %.1f gCO2/kWh (MOER: %.1f lbs/MWh)",
                    data["carbon_intensity"],
                    data["carbon_intensity_raw_moer"],
                )
                return data

            if response.status == 401:
                error = aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=401,
                )
                log_error_with_context(
                    logger,
                    "Authentication failed (401), attempting token refresh",
                    error,
                    service="carbon-intensity-service",
                )
                return await self._handle_auth_retry(url, params)

            if response.status == 403:
                log_error_with_context(
                    logger,
                    f"WattTime API returned 403 Forbidden for region '{self.region}'. "
                    "This endpoint may require a paid subscription.",
                    aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=403,
                    ),
                    service="carbon-intensity-service",
                )
                return None

            if response.status in (429, 500, 502, 503):
                return await self._handle_transient_retry(
                    url, headers, params, response.status
                )

            log_error_with_context(
                logger,
                f"WattTime API returned status {response.status}",
                aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                ),
                service="carbon-intensity-service",
            )
            return None

    async def store_in_influxdb(self, data: dict[str, Any]) -> None:
        """Store carbon intensity data in InfluxDB."""
        if not data:
            logger.warning("No data to store in InfluxDB")
            return

        if not self.influxdb_client:
            logger.error("InfluxDB client not initialized")
            return

        try:
            point = (
                Point("carbon_intensity")
                .tag("region", self.region)
                .field("carbon_intensity_gco2_kwh", float(data["carbon_intensity"]))
                .field("moer_lbs_mwh", float(data.get("carbon_intensity_raw_moer", 0)))
                .field("forecast_1h", float(data["forecast_1h"]))
                .field("forecast_24h", float(data["forecast_24h"]))
                .time(data["timestamp"])
            )

            await asyncio.wait_for(
                asyncio.to_thread(self.influxdb_client.write, point), timeout=15.0
            )

            logger.info("Carbon intensity data written to InfluxDB")
            self.health_handler.last_successful_write = datetime.now(UTC)

        except TimeoutError:
            self.health_handler.influxdb_write_failures += 1
            log_error_with_context(
                logger,
                "InfluxDB write timed out after 15s",
                TimeoutError("InfluxDB write timed out after 15s"),
                service="carbon-intensity-service",
            )
        except Exception as e:
            self.health_handler.influxdb_write_failures += 1
            log_error_with_context(
                logger,
                f"Error writing to InfluxDB: {e}",
                e,
                service="carbon-intensity-service",
            )

    async def run_continuous(self) -> None:
        """Run the continuous carbon intensity monitoring loop."""
        logger.info(
            "Starting continuous carbon intensity monitoring (every %ds)", self.fetch_interval
        )

        while True:
            try:
                data = await self.fetch_carbon_intensity()
                if data:
                    await self.store_in_influxdb(data)
                await asyncio.sleep(self.fetch_interval)
            except asyncio.CancelledError:
                logger.info("Continuous monitoring loop cancelled")
                raise
            except Exception as e:
                log_error_with_context(
                    logger,
                    f"Error in continuous loop: {e}",
                    e,
                    service="carbon-intensity-service",
                )
                await asyncio.sleep(60)


# --- Global service instance ---
service: CarbonIntensityService | None = None

# --- Lifespan ---
lifespan = ServiceLifespan(service_name="carbon-intensity-service")


async def _startup() -> None:
    global service
    service = CarbonIntensityService()
    await service.startup()


async def _shutdown() -> None:
    if service:
        await service.shutdown()


lifespan.on_startup(_startup, name="carbon-intensity-init")
lifespan.on_shutdown(_shutdown, name="carbon-intensity-cleanup")

# --- Health check ---
health = StandardHealthCheck(service_name="carbon-intensity-service", version="1.0.0")

# --- App ---
app = create_app(
    title="Carbon Intensity Service",
    version="1.0.0",
    description="Grid emissions monitoring via WattTime API",
    lifespan=lifespan.handler,
    health_check=health,
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",  # noqa: S104 — Docker requires binding all interfaces
        port=settings.service_port,
        log_level="info",
    )
