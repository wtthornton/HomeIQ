"""Carbon Intensity Service for Grid Emissions Monitoring.

Fetches real-time Marginal Operating Emissions Rate (MOER) data from the
WattTime v3 API, converts to gCO2/kWh, and stores time-series data in InfluxDB.
Supports automatic token refresh, transient error retry with exponential backoff,
and configurable cache TTL for rate-limit compliance.
"""

import asyncio
import contextlib
import os
import re
import signal
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlparse

import aiohttp
from aiohttp import web
from dotenv import load_dotenv
from health_check import HealthCheckHandler
from homeiq_observability.logging_config import (
    log_error_with_context,
    log_with_context,
    setup_logging,
)
from influxdb_client_3 import InfluxDBClient3, Point

# Load environment variables
load_dotenv()

# Configure logging
logger = setup_logging("carbon-intensity-service")


class CarbonIntensityService:
    """Fetch and store grid carbon intensity data from the WattTime API.

    Monitors MOER (Marginal Operating Emissions Rate) for a configurable grid region,
    converts to gCO2/kWh, and stores time-series data in InfluxDB. Supports automatic
    token refresh with WattTime username/password authentication.
    """

    def __init__(self) -> None:
        """Initialize the carbon intensity service with WattTime and InfluxDB config."""
        # WattTime authentication credentials
        self.username = os.getenv('WATTTIME_USERNAME')
        self.password = os.getenv('WATTTIME_PASSWORD')
        self.api_token = os.getenv('WATTTIME_API_TOKEN')  # Optional fallback for manual token

        # Token management
        self.token_expires_at: datetime | None = None
        self.token_refresh_buffer = 300  # Refresh 5 minutes before expiry (seconds)

        # WattTime configuration
        grid_region = os.getenv('GRID_REGION', 'CAISO_NORTH')
        if not re.match(r'^[A-Za-z0-9_]+$', grid_region):
            raise ValueError(f"Invalid GRID_REGION '{grid_region}': must be alphanumeric and underscores only")
        self.region = grid_region
        self.base_url = "https://api.watttime.org"

        # InfluxDB configuration
        # InfluxDBClient3 accepts a full URL as the `host` param and internally
        # parses scheme/hostname/port.  A bare hostname defaults to https:443,
        # so always include scheme + port (e.g. http://influxdb:8086).
        self.influxdb_url = os.getenv('INFLUXDB_URL', 'http://influxdb:8086')
        parsed_influx = urlparse(self.influxdb_url)
        if not parsed_influx.scheme:
            # Bare hostname — assume http on default port
            self.influxdb_url = f"http://{self.influxdb_url}:8086"
        self.influxdb_token = os.getenv('INFLUXDB_TOKEN')
        self.influxdb_org = os.getenv('INFLUXDB_ORG', 'home_assistant')
        self.influxdb_bucket = os.getenv('INFLUXDB_BUCKET', 'events')

        # Service configuration
        self.fetch_interval = int(os.getenv('FETCH_INTERVAL', '900'))
        self.cache_duration = timedelta(minutes=15)

        # Cache
        self.cached_data: dict[str, Any] | None = None
        self.last_fetch_time: datetime | None = None

        # HTTP session
        self.session: aiohttp.ClientSession | None = None

        # InfluxDB client
        self.influxdb_client: InfluxDBClient3 | None = None

        # Health check handler
        self.health_handler = HealthCheckHandler()

        # Track configuration status
        self.credentials_configured = False

        # Validate configuration
        self._validate_credentials()

        if not self.influxdb_token:
            raise ValueError("INFLUXDB_TOKEN environment variable is required")

    def _validate_credentials(self) -> None:
        """Validate WattTime credentials and configure service accordingly.

        Checks for placeholder values, missing credentials, and static token fallback.
        Sets credentials_configured flag and updates health handler status.
        """
        # Check if credentials are placeholder values
        is_placeholder_username = self.username and self.username.lower() in ['your_watttime_username', 'your-username', '']
        is_placeholder_password = self.password and self.password.lower() in ['your_watttime_password', 'your-password', '']

        if not self.username or not self.password or is_placeholder_username or is_placeholder_password:
            if not self.api_token:
                if is_placeholder_username or is_placeholder_password:
                    logger.error(
                        "[ERROR] WattTime credentials are placeholder values! "
                        "Please update WATTTIME_USERNAME and WATTTIME_PASSWORD in .env file with your actual credentials. "
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
                logger.warning("Using static WATTTIME_API_TOKEN - token will expire in 30 minutes")
                self.credentials_configured = True
                self.health_handler.credentials_missing = False
        else:
            self.credentials_configured = True
            self.health_handler.credentials_missing = False

    async def startup(self) -> None:
        """Initialize HTTP session, obtain WattTime token, and connect to InfluxDB.

        Creates an aiohttp session with 10-second timeout, obtains an initial WattTime
        API token (or falls back to static token), and validates the InfluxDB connection
        with a test write.
        """
        logger.info("Initializing Carbon Intensity Service...")

        # Create HTTP session
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10)
        )

        # If using username/password, get initial token
        if self.username and self.password:
            logger.info("Obtaining initial WattTime API token...")
            if not await self.refresh_token():
                logger.error("Failed to obtain initial WattTime API token - will run in standby mode")
                self.credentials_configured = False
        elif self.api_token:
            logger.info("Using static API token (will expire in 30 minutes)")
        else:
            logger.warning("No WattTime credentials - service running in standby mode")

        # Create InfluxDB client — pass full URL (library parses scheme/host/port)
        logger.info(f"Connecting to InfluxDB at {self.influxdb_url}")
        self.influxdb_client = InfluxDBClient3(
            host=self.influxdb_url,
            token=self.influxdb_token,
            database=self.influxdb_bucket,
            org=self.influxdb_org,
        )

        # Validate InfluxDB connection at startup
        try:
            test_point = Point("service_startup").tag("service", "carbon-intensity-service").field("status", 1)
            await asyncio.wait_for(asyncio.to_thread(self.influxdb_client.write, test_point), timeout=10.0)
            logger.info("InfluxDB connection validated successfully")
        except Exception as e:
            logger.warning(f"InfluxDB startup validation failed (will retry on writes): {e}")

        logger.info("Carbon Intensity Service initialized successfully")

    async def shutdown(self) -> None:
        """Cleanup HTTP session and InfluxDB client on service shutdown."""
        logger.info("Shutting down Carbon Intensity Service...")

        if self.session:
            await self.session.close()

        if self.influxdb_client:
            self.influxdb_client.close()

        logger.info("Carbon Intensity Service shut down successfully")

    async def refresh_token(self) -> bool:
        """Refresh WattTime API token using username/password authentication.

        Posts to the WattTime login endpoint with Basic Auth credentials. Handles
        redirect detection, content-type validation, and 401/403 error reporting.
        Tokens expire after 30 minutes; refresh is called proactively by ensure_valid_token.

        Returns:
            True if token refresh was successful, False otherwise.
        """
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
                logger, "INFO",
                "Refreshing WattTime API token",
                service="carbon-intensity-service"
            )

            # Disable redirects to prevent following redirects to docs page on auth failure
            async with self.session.post(url, auth=auth, allow_redirects=False) as response:
                if response.status == 200:
                    # Check content type before parsing JSON
                    content_type = response.headers.get('Content-Type', '')
                    if 'application/json' not in content_type:
                        error = ValueError(f"Unexpected content type: {content_type}")
                        log_error_with_context(
                            logger,
                            f"Unexpected content type: {content_type}",
                            error,
                            service="carbon-intensity-service",
                            status_code=response.status
                        )
                        return False

                    data = await response.json()
                    self.api_token = data.get('token')

                    # WattTime tokens expire in 30 minutes
                    self.token_expires_at = datetime.now(UTC) + timedelta(minutes=30)

                    # Update health check
                    self.health_handler.last_token_refresh = datetime.now(UTC)
                    self.health_handler.token_refresh_count += 1

                    logger.info(f"Token refreshed successfully, expires at {self.token_expires_at.isoformat()}")
                    return True
                elif response.status == 401:
                    error_msg = "Authentication failed (401) - invalid credentials. Please check WATTTIME_USERNAME and WATTTIME_PASSWORD in .env file"
                    logger.error(
                        error_msg,
                        extra={
                            "context": {
                                "service": "carbon-intensity-service",
                                "status_code": response.status
                            }
                        }
                    )
                    # Mark credentials as invalid
                    self.credentials_configured = False
                    self.health_handler.credentials_missing = True
                    return False
                elif response.status in (301, 302, 303, 307, 308):
                    # Handle redirects (shouldn't happen with allow_redirects=False, but just in case)
                    location = response.headers.get('Location', 'unknown')
                    error = ValueError(f"Unexpected redirect to {location}")
                    log_error_with_context(
                        logger,
                        f"Unexpected redirect to {location} - likely invalid API endpoint or credentials",
                        error,
                        service="carbon-intensity-service",
                        status_code=response.status
                    )
                    self.credentials_configured = False
                    self.health_handler.credentials_missing = True
                    return False
                else:
                    error_msg = f"Token refresh failed with status {response.status}"
                    logger.error(
                        error_msg,
                        extra={
                            "context": {
                                "service": "carbon-intensity-service",
                                "status_code": response.status
                            }
                        }
                    )
                    return False

        except aiohttp.client_exceptions.ContentTypeError as e:
            # Handle case where API returns HTML instead of JSON (e.g., redirect to docs page)
            log_error_with_context(
                logger,
                "API returned non-JSON response (likely HTML redirect). Check credentials.",
                e,
                service="carbon-intensity-service"
            )
            self.credentials_configured = False
            self.health_handler.credentials_missing = True
            return False
        except Exception as e:
            log_error_with_context(
                logger,
                "Error refreshing token",
                e,
                service="carbon-intensity-service"
            )
            return False

    async def ensure_valid_token(self) -> bool:
        """Ensure we have a valid API token, refreshing if expired or near expiry.

        Checks token expiration against the configured buffer time and triggers
        a refresh when needed. Falls back to checking for a static token.

        Returns:
            True if a valid token is available, False otherwise.
        """
        # If no expiration time set and we have username/password, refresh now
        if not self.token_expires_at and self.username and self.password:
            logger.info("No token expiration set, refreshing token...")
            return await self.refresh_token()

        # If token expires soon (within buffer time), refresh now
        if self.token_expires_at:
            time_until_expiry = (self.token_expires_at - datetime.now(UTC)).total_seconds()
            if time_until_expiry < self.token_refresh_buffer:
                logger.info(f"Token expires in {time_until_expiry:.0f}s, refreshing...")
                return await self.refresh_token()

        if not self.api_token:
            logger.error("No API token available")
            return False
        return True  # Token still valid

    def _parse_watttime_response(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Parse WattTime v3 API response into standardized carbon intensity format.

        Converts the v3 response format ({data: [{point_time, value}, ...], meta: ...})
        into a normalized dictionary with current intensity, MOER value, and forecasts.
        The 'value' field is MOER in lbs CO2/MWh; conversion factor: 1 lb/MWh = 0.4536 g/kWh.
        Data points arrive at 5-minute intervals (12 per hour, 288 per day).

        Args:
            raw_data: Raw JSON response from WattTime v3 forecast endpoint.

        Returns:
            Dictionary with carbon_intensity (gCO2/kWh), raw MOER, and forecast values.
        """
        entries = raw_data.get('data', [])
        # Current MOER value is the first entry
        current_moer = float(entries[0]['value']) if entries else 0.0
        # Convert lbs/MWh to gCO2/kWh: 1 lb/MWh = 0.4536 g/kWh
        carbon_intensity = current_moer * 0.4536

        data: dict[str, Any] = {
            'carbon_intensity': carbon_intensity,
            'carbon_intensity_raw_moer': current_moer,
            'timestamp': datetime.now(UTC),
        }

        # Extract forecast points (5-min intervals: 12 per hour)
        if len(entries) > 12:
            data['forecast_1h'] = float(entries[12]['value']) * 0.4536
        else:
            data['forecast_1h'] = 0.0
        if len(entries) > 288:
            data['forecast_24h'] = float(entries[288]['value']) * 0.4536
        else:
            data['forecast_24h'] = float(entries[-1]['value']) * 0.4536 if entries else 0.0

        return data

    def _update_cache_and_health(self, data: dict[str, Any]) -> None:
        """Update the in-memory cache and health check metrics after a successful fetch.

        Args:
            data: Parsed carbon intensity data dictionary.
        """
        self.cached_data = data
        self.last_fetch_time = datetime.now(UTC)
        self.health_handler.last_successful_fetch = datetime.now(UTC)
        self.health_handler.total_fetches += 1

    async def _handle_auth_retry(self, url: str, params: dict[str, str]) -> dict[str, Any] | None:
        """Handle 401 response by refreshing token and retrying once.

        Returns parsed data on success, None on failure.
        """
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
                    logger.info(f"Carbon intensity (retry): {data['carbon_intensity']:.1f} gCO2/kWh")
                    return data
        return None

    async def _handle_transient_retry(
        self, url: str, headers: dict[str, str], params: dict[str, str], initial_status: int
    ) -> dict[str, Any] | None:
        """Handle transient HTTP errors (429, 5xx) with exponential backoff.

        Returns parsed data on success, None after all retries exhausted.
        """
        if not self.session:
            return None

        last_status = initial_status
        retry_delays = [5, 10, 20]
        for attempt, delay in enumerate(retry_delays, 1):
            logger.warning(f"Transient HTTP {last_status}, retry {attempt}/{len(retry_delays)} after {delay}s")
            await asyncio.sleep(delay)
            async with self.session.get(url, headers=headers, params=params) as retry_resp:
                if retry_resp.status == 200:
                    raw_data = await retry_resp.json()
                    data = self._parse_watttime_response(raw_data)
                    self._update_cache_and_health(data)
                    logger.info(f"Carbon intensity (retry {attempt}): {data['carbon_intensity']:.1f} gCO2/kWh")
                    return data
                last_status = retry_resp.status
                if retry_resp.status not in (429, 500, 502, 503):
                    break

        logger.error(f"WattTime API returned status {last_status} after {len(retry_delays)} retries")
        return None

    def _is_cache_valid(self) -> bool:
        """Check if cached carbon intensity data is still within the TTL window."""
        if not self.cached_data or not self.last_fetch_time:
            return False
        cache_age = datetime.now(UTC) - self.last_fetch_time
        return cache_age < self.cache_duration

    async def fetch_carbon_intensity(self) -> dict[str, Any] | None:
        """Fetch carbon intensity from WattTime API with caching and retry logic.

        Returns:
            Carbon intensity data dictionary, cached data on failure, or None.
        """
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
                logger, "INFO",
                f"Fetching carbon intensity for region {self.region}",
                service="carbon-intensity-service",
                region=self.region,
            )

            result = await self._dispatch_api_request(url, headers, params)
            if result is not None:
                return result

            self.health_handler.failed_fetches += 1
            return self.cached_data

        except aiohttp.ClientError as e:
            log_error_with_context(logger, f"Error fetching carbon intensity: {e}", e, service="carbon-intensity-service")
            self.health_handler.failed_fetches += 1
            if self.cached_data:
                logger.warning("Using cached carbon intensity data")
                return self.cached_data
            return None

        except Exception as e:
            log_error_with_context(logger, f"Unexpected error: {e}", e, service="carbon-intensity-service")
            self.health_handler.failed_fetches += 1
            return self.cached_data

    async def _dispatch_api_request(
        self, url: str, headers: dict[str, str], params: dict[str, str]
    ) -> dict[str, Any] | None:
        """Make the WattTime API request and dispatch based on status code.

        Returns parsed data on success, None on failure (caller should handle fallback).
        """
        if not self.session:
            return None

        async with self.session.get(url, headers=headers, params=params) as response:
            if response.status == 200:
                raw_data = await response.json()
                data = self._parse_watttime_response(raw_data)
                self._update_cache_and_health(data)
                logger.info(
                    f"Carbon intensity: {data['carbon_intensity']:.1f} gCO2/kWh "
                    f"(MOER: {data['carbon_intensity_raw_moer']:.1f} lbs/MWh)"
                )
                return data

            if response.status == 401:
                error = aiohttp.ClientResponseError(
                    request_info=response.request_info, history=response.history, status=401
                )
                log_error_with_context(
                    logger, "Authentication failed (401), attempting token refresh", error, service="carbon-intensity-service"
                )
                return await self._handle_auth_retry(url, params)

            if response.status == 403:
                log_error_with_context(
                    logger,
                    f"WattTime API returned 403 Forbidden for region '{self.region}'. "
                    "This endpoint may require a paid subscription. "
                    "Free tier access is limited to CAISO_NORTH preview only.",
                    aiohttp.ClientResponseError(
                        request_info=response.request_info, history=response.history, status=403
                    ),
                    service="carbon-intensity-service",
                )
                return None

            if response.status in (429, 500, 502, 503):
                return await self._handle_transient_retry(url, headers, params, response.status)

            log_error_with_context(
                logger,
                f"WattTime API returned status {response.status}",
                aiohttp.ClientResponseError(
                    request_info=response.request_info, history=response.history, status=response.status
                ),
                service="carbon-intensity-service",
            )
            return None

    async def store_in_influxdb(self, data: dict[str, Any]) -> None:
        """Store carbon intensity data in InfluxDB as a time-series point.

        Args:
            data: Carbon intensity data with carbon_intensity, moer, and forecast values.
        """

        if not data:
            logger.warning("No data to store in InfluxDB")
            return

        if not self.influxdb_client:
            logger.error("InfluxDB client not initialized")
            return

        try:
            point = Point("carbon_intensity") \
                .tag("region", self.region) \
                .field("carbon_intensity_gco2_kwh", float(data['carbon_intensity'])) \
                .field("moer_lbs_mwh", float(data.get('carbon_intensity_raw_moer', 0))) \
                .field("forecast_1h", float(data['forecast_1h'])) \
                .field("forecast_24h", float(data['forecast_24h'])) \
                .time(data['timestamp'])

            # CRITICAL FIX: Use asyncio.to_thread to avoid blocking the event loop
            # InfluxDBClient3.write() is synchronous and blocks the async event loop
            await asyncio.wait_for(asyncio.to_thread(self.influxdb_client.write, point), timeout=15.0)

            logger.info("Carbon intensity data written to InfluxDB")
            self.health_handler.last_successful_write = datetime.now(UTC)

        except TimeoutError:
            self.health_handler.influxdb_write_failures += 1
            log_error_with_context(
                logger,
                "InfluxDB write timed out after 15s",
                TimeoutError("InfluxDB write timed out after 15s"),
                service="carbon-intensity-service"
            )
        except Exception as e:
            self.health_handler.influxdb_write_failures += 1
            log_error_with_context(
                logger,
                f"Error writing to InfluxDB: {e}",
                e,
                service="carbon-intensity-service"
            )
            # Don't re-raise - allow loop to continue with next fetch interval
            # InfluxDB write failures shouldn't stop data collection

    async def run_continuous(self) -> None:
        """Run the continuous carbon intensity monitoring loop.

        Fetches carbon intensity data and writes to InfluxDB on each interval.
        On error, waits 60 seconds before retrying to avoid tight failure loops.
        """

        logger.info(f"Starting continuous carbon intensity monitoring (every {self.fetch_interval}s)")

        while True:
            try:
                # Fetch data
                data = await self.fetch_carbon_intensity()

                # Store in InfluxDB
                if data:
                    await self.store_in_influxdb(data)

                # Wait for next interval
                await asyncio.sleep(self.fetch_interval)

            except Exception as e:
                log_error_with_context(
                    logger,
                    f"Error in continuous loop: {e}",
                    e,
                    service="carbon-intensity-service"
                )
                # Wait before retrying
                await asyncio.sleep(60)


async def create_app(service: CarbonIntensityService) -> web.Application:
    """Create the aiohttp web application with health check endpoint."""
    app = web.Application()

    # Add health check endpoint
    app.router.add_get('/health', service.health_handler.handle)

    return app


async def main() -> None:
    """Main entry point: starts the carbon intensity service with graceful signal handling.

    Initializes the service, starts the health check web server, registers SIGTERM/SIGINT
    handlers for clean Docker shutdown, and runs the continuous monitoring loop.
    """
    logger.info("Starting Carbon Intensity Service...")

    # Create service
    service = CarbonIntensityService()
    await service.startup()

    # Create web application for health check
    app = await create_app(service)
    runner = web.AppRunner(app)
    await runner.setup()

    # Start health check server
    port = int(os.getenv('SERVICE_PORT', '8010'))
    bind_host = os.getenv("BIND_HOST", "0.0.0.0")  # noqa: S104 — Docker container requires binding to all interfaces
    site = web.TCPSite(runner, bind_host, port)
    await site.start()

    logger.info(f"Health check endpoint available on port {port}")

    # Register signal handlers for graceful Docker shutdown
    loop = asyncio.get_running_loop()
    shutdown_event = asyncio.Event()

    def _signal_handler():
        logger.info("Received shutdown signal")
        shutdown_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        with contextlib.suppress(NotImplementedError):
            # Windows does not support add_signal_handler
            loop.add_signal_handler(sig, _signal_handler)

    try:
        # Run continuous data collection until shutdown
        continuous_task = asyncio.create_task(service.run_continuous())
        shutdown_task = asyncio.create_task(shutdown_event.wait())
        done, pending = await asyncio.wait(
            [continuous_task, shutdown_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")

    finally:
        await service.shutdown()
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

