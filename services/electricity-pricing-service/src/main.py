"""
Electricity Pricing Service Main Entry Point
Fetches real-time electricity pricing from utility APIs
"""

import asyncio
import os
import sys
from datetime import datetime
from typing import Any

import aiohttp
from aiohttp import web
from dotenv import load_dotenv
from influxdb_client_3 import InfluxDBClient3, Point

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../../shared"))

from health_check import HealthCheckHandler
from providers import AwattarProvider

from shared.logging_config import log_error_with_context, log_with_context, setup_logging

# Load environment variables
load_dotenv()

# Configure logging
logger = setup_logging("electricity-pricing-service")


class ElectricityPricingService:
    """Fetch and store electricity pricing data"""

    def __init__(self):
        self.provider_name = os.getenv("PRICING_PROVIDER", "awattar")
        self.api_key = os.getenv("PRICING_API_KEY", "")

        # InfluxDB configuration
        self.influxdb_url = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
        self.influxdb_token = os.getenv("INFLUXDB_TOKEN")
        self.influxdb_org = os.getenv("INFLUXDB_ORG", "home_assistant")
        self.influxdb_bucket = os.getenv("INFLUXDB_BUCKET", "events")

        # Service configuration
        self.fetch_interval = 3600  # 1 hour in seconds
        self.cache_duration = 60  # minutes

        # Cache
        self.cached_data: dict[str, Any] | None = None
        self.last_fetch_time: datetime | None = None

        # HTTP session
        self.session: aiohttp.ClientSession | None = None

        # InfluxDB client
        self.influxdb_client: InfluxDBClient3 | None = None

        # Health check handler
        self.health_handler = HealthCheckHandler()

        # Provider
        self.provider = self._get_provider()

        # Validate configuration
        if not self.influxdb_token:
            msg = "INFLUXDB_TOKEN environment variable is required"
            raise ValueError(msg)

    def _get_provider(self):
        """Get pricing provider based on configuration"""

        providers = {
            "awattar": AwattarProvider(),
        }

        provider = providers.get(self.provider_name.lower())

        if not provider:
            logger.warning(f"Unknown provider {self.provider_name}, using Awattar")
            return AwattarProvider()

        return provider

    async def startup(self):
        """Initialize service components"""
        logger.info(f"Initializing Electricity Pricing Service (Provider: {self.provider_name})...")

        # Create HTTP session
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
        )

        # Create InfluxDB client
        self.influxdb_client = InfluxDBClient3(
            host=self.influxdb_url,
            token=self.influxdb_token,
            database=self.influxdb_bucket,
            org=self.influxdb_org,
        )

        logger.info("Electricity Pricing Service initialized successfully")

    async def shutdown(self):
        """Cleanup service components"""
        logger.info("Shutting down Electricity Pricing Service...")

        if self.session:
            await self.session.close()

        if self.influxdb_client:
            self.influxdb_client.close()

        logger.info("Electricity Pricing Service shut down successfully")

    async def fetch_pricing(self) -> dict[str, Any] | None:
        """Fetch electricity pricing from configured provider"""

        try:
            log_with_context(
                logger, "INFO",
                f"Fetching electricity pricing from {self.provider_name}",
                service="electricity-pricing-service",
                provider=self.provider_name,
            )

            data = await self.provider.fetch_pricing(self.session)

            # Add timestamp
            data["timestamp"] = datetime.now()
            data["provider"] = self.provider_name

            # Update cache
            self.cached_data = data
            self.last_fetch_time = datetime.now()

            # Update health check
            self.health_handler.last_successful_fetch = datetime.now()
            self.health_handler.total_fetches += 1

            logger.info(f"Current price: {data['current_price']:.3f} {data['currency']}/kWh")
            logger.info(f"Cheapest hours: {data['cheapest_hours']}")

            return data

        except Exception as e:
            log_error_with_context(
                logger,
                f"Error fetching pricing: {e}",
                service="electricity-pricing-service",
                error=str(e),
            )
            self.health_handler.failed_fetches += 1

            # Return cached data if available
            if self.cached_data:
                logger.warning("Using cached pricing data")
                return self.cached_data

            return None

    async def store_in_influxdb(self, data: dict[str, Any]):
        """Store pricing data in InfluxDB"""

        if not data:
            logger.warning("No data to store in InfluxDB")
            return

        try:
            # Store current pricing
            point = Point("electricity_pricing") \
                .tag("provider", data["provider"]) \
                .tag("currency", data["currency"]) \
                .field("current_price", float(data["current_price"])) \
                .field("peak_period", bool(data["peak_period"])) \
                .time(data["timestamp"])

            self.influxdb_client.write(point)

            # Store forecast
            for forecast in data.get("forecast_24h", []):
                forecast_point = Point("electricity_pricing_forecast") \
                    .tag("provider", data["provider"]) \
                    .field("price", float(forecast["price"])) \
                    .field("hour_offset", int(forecast["hour"])) \
                    .time(forecast["timestamp"])

                self.influxdb_client.write(forecast_point)

            logger.info("Electricity pricing data written to InfluxDB")

        except Exception as e:
            log_error_with_context(
                logger,
                f"Error writing to InfluxDB: {e}",
                service="electricity-pricing-service",
                error=str(e),
            )

    async def get_cheapest_hours(self, request):
        """API endpoint to get cheapest hours"""

        hours_needed = int(request.query.get("hours", 4))

        if self.cached_data and "cheapest_hours" in self.cached_data:
            cheapest = self.cached_data["cheapest_hours"][:hours_needed]
            return web.json_response({
                "cheapest_hours": cheapest,
                "provider": self.provider_name,
                "timestamp": self.last_fetch_time.isoformat() if self.last_fetch_time else None,
            })
        return web.json_response({
            "error": "No pricing data available",
        }, status=503)

    async def run_continuous(self):
        """Run continuous data collection loop"""

        logger.info(f"Starting continuous pricing monitoring (every {self.fetch_interval}s)")

        while True:
            try:
                # Fetch data
                data = await self.fetch_pricing()

                # Store in InfluxDB
                if data:
                    await self.store_in_influxdb(data)

                # Wait for next interval
                await asyncio.sleep(self.fetch_interval)

            except Exception as e:
                log_error_with_context(
                    logger,
                    f"Error in continuous loop: {e}",
                    service="electricity-pricing-service",
                    error=str(e),
                )
                # Wait before retrying
                await asyncio.sleep(300)  # 5 minutes


async def create_app(service: ElectricityPricingService):
    """Create the web application"""
    app = web.Application()

    # Add endpoints
    app.router.add_get("/health", service.health_handler.handle)
    app.router.add_get("/cheapest-hours", service.get_cheapest_hours)

    return app


async def main():
    """Main entry point"""
    logger.info("Starting Electricity Pricing Service...")

    # Create service
    service = ElectricityPricingService()
    await service.startup()

    # Create web application
    app = await create_app(service)
    runner = web.AppRunner(app)
    await runner.setup()

    # Start health check server
    port = int(os.getenv("SERVICE_PORT", "8011"))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    logger.info(f"API endpoints available on port {port}")

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

