"""
Carbon Intensity Service Main Entry Point
Fetches grid carbon intensity from WattTime API
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from typing import Any

import aiohttp
from aiohttp import web
from dotenv import load_dotenv
from influxdb_client_3 import InfluxDBClient3, Point

# Add shared directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))

from health_check import HealthCheckHandler

from shared.logging_config import log_error_with_context, log_with_context, setup_logging

# Load environment variables
load_dotenv()

# Configure logging
logger = setup_logging("carbon-intensity-service")


class CarbonIntensityService:
    """Fetch and store carbon intensity data from WattTime API"""

    def __init__(self):
        # WattTime authentication credentials
        self.username = os.getenv('WATTTIME_USERNAME')
        self.password = os.getenv('WATTTIME_PASSWORD')
        self.api_token = os.getenv('WATTTIME_API_TOKEN')  # Optional fallback for manual token

        # Token management
        self.token_expires_at: datetime | None = None
        self.token_refresh_buffer = 300  # Refresh 5 minutes before expiry (seconds)

        # WattTime configuration
        self.region = os.getenv('GRID_REGION', 'CAISO_NORTH')
        self.base_url = "https://api.watttime.org/v3"

        # InfluxDB configuration
        self.influxdb_url = os.getenv('INFLUXDB_URL', 'http://influxdb:8086')
        self.influxdb_token = os.getenv('INFLUXDB_TOKEN')
        self.influxdb_org = os.getenv('INFLUXDB_ORG', 'home_assistant')
        self.influxdb_bucket = os.getenv('INFLUXDB_BUCKET', 'events')

        # Service configuration
        self.fetch_interval = 900  # 15 minutes in seconds
        self.cache_duration = 15  # minutes

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
        if not self.username or not self.password:
            if not self.api_token:
                logger.warning(
                    "⚠️  No WattTime credentials configured! "
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

        if not self.influxdb_token:
            raise ValueError("INFLUXDB_TOKEN environment variable is required")

    async def startup(self):
        """Initialize service components"""
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

        # Create InfluxDB client
        self.influxdb_client = InfluxDBClient3(
            host=self.influxdb_url,
            token=self.influxdb_token,
            database=self.influxdb_bucket,
            org=self.influxdb_org
        )

        logger.info("Carbon Intensity Service initialized successfully")

    async def shutdown(self):
        """Cleanup service components"""
        logger.info("Shutting down Carbon Intensity Service...")

        if self.session:
            await self.session.close()

        if self.influxdb_client:
            self.influxdb_client.close()

        logger.info("Carbon Intensity Service shut down successfully")

    async def refresh_token(self) -> bool:
        """
        Refresh WattTime API token using username/password
        
        Returns:
            bool: True if refresh successful, False otherwise
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

            async with self.session.post(url, auth=auth) as response:
                if response.status == 200:
                    data = await response.json()
                    self.api_token = data.get('token')

                    # WattTime tokens expire in 30 minutes
                    self.token_expires_at = datetime.now() + timedelta(minutes=30)

                    # Update health check
                    self.health_handler.last_token_refresh = datetime.now()
                    self.health_handler.token_refresh_count += 1

                    logger.info(f"Token refreshed successfully, expires at {self.token_expires_at.isoformat()}")
                    return True
                else:
                    log_error_with_context(
                        logger,
                        f"Token refresh failed with status {response.status}",
                        service="carbon-intensity-service",
                        status_code=response.status
                    )
                    return False

        except Exception as e:
            log_error_with_context(
                logger,
                f"Error refreshing token: {e}",
                service="carbon-intensity-service",
                error=str(e)
            )
            return False

    async def ensure_valid_token(self) -> bool:
        """
        Ensure we have a valid token, refresh if needed
        
        Returns:
            bool: True if we have a valid token, False otherwise
        """
        # If no expiration time set and we have username/password, refresh now
        if not self.token_expires_at and self.username and self.password:
            logger.info("No token expiration set, refreshing token...")
            return await self.refresh_token()

        # If token expires soon (within buffer time), refresh now
        if self.token_expires_at:
            time_until_expiry = (self.token_expires_at - datetime.now()).total_seconds()
            if time_until_expiry < self.token_refresh_buffer:
                logger.info(f"Token expires in {time_until_expiry:.0f}s, refreshing...")
                return await self.refresh_token()

        return True  # Token still valid

    async def fetch_carbon_intensity(self) -> dict[str, Any] | None:
        """Fetch carbon intensity from WattTime API"""

        # If no credentials configured, skip fetch silently
        if not self.credentials_configured:
            # Don't log error every time, just return None quietly
            return None

        if not self.session:
            logger.error("HTTP session not initialized")
            self.health_handler.failed_fetches += 1
            return self.cached_data

        try:
            # Ensure we have a valid token before making request
            if not await self.ensure_valid_token():
                logger.error("No valid WattTime token available")
                self.health_handler.failed_fetches += 1
                return self.cached_data

            url = f"{self.base_url}/forecast"
            headers = {"Authorization": f"Bearer {self.api_token}"}
            params = {"region": self.region}

            log_with_context(
                logger, "INFO",
                f"Fetching carbon intensity for region {self.region}",
                service="carbon-intensity-service",
                region=self.region
            )

            async with self.session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    raw_data = await response.json()

                    # Parse WattTime response
                    data = {
                        'carbon_intensity': raw_data.get('moer', 0),  # Marginal emissions rate
                        'renewable_percentage': raw_data.get('renewable_pct', 0),
                        'fossil_percentage': 100 - raw_data.get('renewable_pct', 0),
                        'timestamp': datetime.now()
                    }

                    # Extract forecasts if available
                    forecast = raw_data.get('forecast', [])
                    if forecast:
                        data['forecast_1h'] = forecast[0].get('value', 0) if len(forecast) > 0 else 0
                        data['forecast_24h'] = forecast[23].get('value', 0) if len(forecast) > 23 else 0
                    else:
                        data['forecast_1h'] = 0
                        data['forecast_24h'] = 0

                    # Update cache
                    self.cached_data = data
                    self.last_fetch_time = datetime.now()

                    # Update health check
                    self.health_handler.last_successful_fetch = datetime.now()
                    self.health_handler.total_fetches += 1

                    logger.info(f"Carbon intensity: {data['carbon_intensity']:.1f} gCO2/kWh, Renewable: {data['renewable_percentage']:.1f}%")

                    return data

                elif response.status == 401:
                    # Token expired mid-request, try refresh and retry once
                    log_error_with_context(
                        logger,
                        "Authentication failed (401), attempting token refresh",
                        service="carbon-intensity-service"
                    )

                    if await self.refresh_token():
                        logger.info("Token refreshed, retrying request...")
                        # Retry once with new token
                        headers = {"Authorization": f"Bearer {self.api_token}"}
                        async with self.session.get(url, headers=headers, params=params) as retry_response:
                            if retry_response.status == 200:
                                raw_data = await retry_response.json()

                                # Parse WattTime response
                                data = {
                                    'carbon_intensity': raw_data.get('moer', 0),
                                    'renewable_percentage': raw_data.get('renewable_pct', 0),
                                    'fossil_percentage': 100 - raw_data.get('renewable_pct', 0),
                                    'timestamp': datetime.now()
                                }

                                # Extract forecasts
                                forecast = raw_data.get('forecast', [])
                                if forecast:
                                    data['forecast_1h'] = forecast[0].get('value', 0) if len(forecast) > 0 else 0
                                    data['forecast_24h'] = forecast[23].get('value', 0) if len(forecast) > 23 else 0
                                else:
                                    data['forecast_1h'] = 0
                                    data['forecast_24h'] = 0

                                # Update cache and health
                                self.cached_data = data
                                self.last_fetch_time = datetime.now()
                                self.health_handler.last_successful_fetch = datetime.now()
                                self.health_handler.total_fetches += 1

                                logger.info(f"Carbon intensity (retry): {data['carbon_intensity']:.1f} gCO2/kWh")
                                return data

                    # Token refresh failed or retry failed
                    self.health_handler.failed_fetches += 1
                    return self.cached_data

                else:
                    log_error_with_context(
                        logger,
                        f"WattTime API returned status {response.status}",
                        service="carbon-intensity-service",
                        status_code=response.status
                    )
                    self.health_handler.failed_fetches += 1
                    return self.cached_data

        except aiohttp.ClientError as e:
            log_error_with_context(
                logger,
                f"Error fetching carbon intensity: {e}",
                service="carbon-intensity-service",
                error=str(e)
            )
            self.health_handler.failed_fetches += 1

            # Return cached data if available
            if self.cached_data:
                logger.warning("Using cached carbon intensity data")
                return self.cached_data

            return None

        except Exception as e:
            log_error_with_context(
                logger,
                f"Unexpected error: {e}",
                service="carbon-intensity-service",
                error=str(e)
            )
            self.health_handler.failed_fetches += 1
            return self.cached_data

    async def store_in_influxdb(self, data: dict[str, Any]) -> None:
        """Store carbon intensity data in InfluxDB"""

        if not data:
            logger.warning("No data to store in InfluxDB")
            return

        if not self.influxdb_client:
            logger.error("InfluxDB client not initialized")
            return

        try:
            point = Point("carbon_intensity") \
                .tag("region", self.region) \
                .tag("grid_operator", self.region.split('_')[0]) \
                .field("carbon_intensity_gco2_kwh", float(data['carbon_intensity'])) \
                .field("renewable_percentage", float(data['renewable_percentage'])) \
                .field("fossil_percentage", float(data['fossil_percentage'])) \
                .field("forecast_1h", float(data['forecast_1h'])) \
                .field("forecast_24h", float(data['forecast_24h'])) \
                .time(data['timestamp'])

            # CRITICAL FIX: Use asyncio.to_thread to avoid blocking the event loop
            # InfluxDBClient3.write() is synchronous and blocks the async event loop
            await asyncio.to_thread(self.influxdb_client.write, point)

            logger.info("Carbon intensity data written to InfluxDB")

        except Exception as e:
            log_error_with_context(
                logger,
                f"Error writing to InfluxDB: {e}",
                service="carbon-intensity-service",
                error=str(e)
            )
            # Don't re-raise - allow loop to continue with next fetch interval
            # InfluxDB write failures shouldn't stop data collection

    async def run_continuous(self):
        """Run continuous data collection loop"""

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
                    service="carbon-intensity-service",
                    error=str(e)
                )
                # Wait before retrying
                await asyncio.sleep(60)


async def create_app(service: CarbonIntensityService):
    """Create the web application"""
    app = web.Application()

    # Add health check endpoint
    app.router.add_get('/health', service.health_handler.handle)

    return app


async def main():
    """Main entry point"""
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
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

    logger.info(f"Health check endpoint available on port {port}")

    try:
        # Run continuous data collection
        await service.run_continuous()

    except KeyboardInterrupt:
        logger.info("Received shutdown signal")

    finally:
        await service.shutdown()
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

