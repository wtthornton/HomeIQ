"""
Smart Meter Service Main Entry Point
Generic smart meter integration with adapter pattern
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

sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))

from adapters.home_assistant import HomeAssistantAdapter
from health_check import HealthCheckHandler

from shared.logging_config import log_error_with_context, setup_logging

load_dotenv()

logger = setup_logging("smart-meter-service")


class SmartMeterService:
    """Generic smart meter integration with adapter support"""

    def __init__(self):
        self.meter_type = os.getenv('METER_TYPE', 'home_assistant')
        self.api_token = os.getenv('METER_API_TOKEN', '')
        self.device_id = os.getenv('METER_DEVICE_ID', '')

        # Home Assistant configuration
        self.ha_url = os.getenv('HOME_ASSISTANT_URL')
        self.ha_token = os.getenv('HOME_ASSISTANT_TOKEN')

        # InfluxDB configuration
        self.influxdb_url = os.getenv('INFLUXDB_URL', 'http://influxdb:8086')
        self.influxdb_token = os.getenv('INFLUXDB_TOKEN')
        self.influxdb_org = os.getenv('INFLUXDB_ORG', 'home_assistant')
        self.influxdb_bucket = os.getenv('INFLUXDB_BUCKET', 'events')

        # Service configuration
        self.fetch_interval = 300  # 5 minutes

        # Cache
        self.cached_data: dict[str, Any] | None = None
        self.last_fetch_time: datetime | None = None
        self.baseline_3am: float | None = None

        # Components
        self.session: aiohttp.ClientSession | None = None
        self.influxdb_client: InfluxDBClient3 | None = None
        self.health_handler = HealthCheckHandler()
        self.adapter = None  # Will be initialized in startup

        if not self.influxdb_token:
            raise ValueError("INFLUXDB_TOKEN required")

    async def startup(self) -> None:
        """Initialize service"""
        logger.info(f"Initializing Smart Meter Service (Type: {self.meter_type})...")

        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10)
        )

        self.influxdb_client = InfluxDBClient3(
            host=self.influxdb_url,
            token=self.influxdb_token,
            database=self.influxdb_bucket,
            org=self.influxdb_org
        )

        # Initialize adapter based on meter type
        self.adapter = self._create_adapter()

        # Test connection if using Home Assistant adapter
        if isinstance(self.adapter, HomeAssistantAdapter):
            connected = await self.adapter.test_connection()
            if not connected:
                logger.warning("Failed to connect to Home Assistant - will use mock data")

        logger.info("Smart Meter Service initialized")

    def _create_adapter(self) -> Any:
        """Create adapter based on meter type"""
        if self.meter_type == 'home_assistant':
            if not self.ha_url or not self.ha_token:
                logger.warning(
                    "HOME_ASSISTANT_URL and HOME_ASSISTANT_TOKEN not configured - using mock data"
                )
                return None
            return HomeAssistantAdapter(self.ha_url, self.ha_token)
        elif self.meter_type == 'emporia':
            logger.warning("Emporia adapter not yet implemented - using mock data")
            return None
        elif self.meter_type == 'sense':
            logger.warning("Sense adapter not yet implemented - using mock data")
            return None
        else:
            logger.warning(f"Unknown meter type: {self.meter_type} - using mock data")
            return None

    async def shutdown(self) -> None:
        """Cleanup"""
        if self.session:
            await self.session.close()
        if self.influxdb_client:
            self.influxdb_client.close()

    async def fetch_consumption(self) -> dict[str, Any] | None:
        """Fetch power consumption from configured adapter or mock data"""

        # Use adapter if configured
        if self.adapter:
            try:
                data = await self.adapter.fetch_consumption(
                    self.session,
                    self.api_token,
                    self.device_id
                )

                # Add timestamp if not present
                if 'timestamp' not in data:
                    data['timestamp'] = datetime.now()

                # Ensure percentages are calculated
                for circuit in data.get('circuits', []):
                    if 'percentage' not in circuit:
                        circuit['percentage'] = (
                            (circuit['power_w'] / data['total_power_w']) * 100
                            if data['total_power_w'] > 0 else 0
                        )

                # Detect phantom loads (high 3am baseline)
                current_hour = datetime.now().hour
                if current_hour == 3:
                    self.baseline_3am = data['total_power_w']
                    if self.baseline_3am > 200:
                        logger.warning(f"High phantom load detected: {self.baseline_3am:.0f}W at 3am")

                # Log high consumption
                if data['total_power_w'] > 10000:
                    logger.warning(f"High power consumption: {data['total_power_w']:.0f}W")

                # Update cache and stats
                self.cached_data = data
                self.last_fetch_time = datetime.now()
                self.health_handler.last_successful_fetch = datetime.now()
                self.health_handler.total_fetches += 1

                logger.info(
                    f"Power: {data['total_power_w']:.0f}W, "
                    f"Daily: {data.get('daily_kwh', 0):.1f}kWh, "
                    f"Circuits: {len(data.get('circuits', []))}"
                )

                return data

            except Exception as e:
                log_error_with_context(
                    logger,
                    f"Error fetching from adapter: {e}",
                    service="smart-meter-service",
                    error=str(e)
                )
                self.health_handler.failed_fetches += 1

                # Return cached data if available
                if self.cached_data:
                    logger.warning("Using cached data after adapter failure")
                    return self.cached_data

                # Fall through to mock data
                logger.warning("No cached data available, using mock data")

        # Use mock data if no adapter or adapter failed
        return self._get_mock_data()

    def _get_mock_data(self) -> dict[str, Any]:
        """Return mock data for testing when no adapter is configured"""

        data = {
            'total_power_w': 2450.0,
            'daily_kwh': 18.5,
            'circuits': [
                {'name': 'HVAC', 'power_w': 1200.0, 'percentage': 49.0},
                {'name': 'Kitchen', 'power_w': 450.0, 'percentage': 18.4},
                {'name': 'Living Room', 'power_w': 300.0, 'percentage': 12.2},
                {'name': 'Office', 'power_w': 250.0, 'percentage': 10.2},
                {'name': 'Bedrooms', 'power_w': 150.0, 'percentage': 6.1},
                {'name': 'Other', 'power_w': 100.0, 'percentage': 4.1}
            ],
            'timestamp': datetime.now()
        }

        # Update stats
        self.cached_data = data
        self.last_fetch_time = datetime.now()
        self.health_handler.last_successful_fetch = datetime.now()
        self.health_handler.total_fetches += 1

        logger.debug("Using mock data")

        return data

    async def store_in_influxdb(self, data: dict[str, Any]) -> None:
        """Store consumption data in InfluxDB"""

        if not data:
            return

        try:
            # Store whole-home consumption
            point = Point("smart_meter") \
                .tag("meter_type", self.meter_type) \
                .field("total_power_w", float(data['total_power_w'])) \
                .field("daily_kwh", float(data['daily_kwh'])) \
                .time(data['timestamp'])

            self.influxdb_client.write(point)

            # Store circuit-level data
            for circuit in data.get('circuits', []):
                circuit_point = Point("smart_meter_circuit") \
                    .tag("circuit_name", circuit['name']) \
                    .field("power_w", float(circuit['power_w'])) \
                    .field("percentage", float(circuit['percentage'])) \
                    .time(data['timestamp'])

                self.influxdb_client.write(circuit_point)

            logger.info("Smart meter data written to InfluxDB")

        except Exception as e:
            log_error_with_context(
                logger,
                f"Error writing to InfluxDB: {e}",
                service="smart-meter-service",
                error=str(e)
            )

    async def run_continuous(self) -> None:
        """Run continuous data collection loop"""

        logger.info(f"Starting continuous power monitoring (every {self.fetch_interval}s)")

        while True:
            try:
                data = await self.fetch_consumption()

                if data:
                    await self.store_in_influxdb(data)

                await asyncio.sleep(self.fetch_interval)

            except Exception as e:
                log_error_with_context(
                    logger,
                    f"Error in continuous loop: {e}",
                    service="smart-meter-service",
                    error=str(e)
                )
                await asyncio.sleep(60)


async def create_app(service: SmartMeterService) -> web.Application:
    """Create web application"""
    app = web.Application()
    app.router.add_get('/health', service.health_handler.handle)
    return app


async def main() -> None:
    """Main entry point"""
    logger.info("Starting Smart Meter Service...")

    service = SmartMeterService()
    await service.startup()

    app = await create_app(service)
    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.getenv('SERVICE_PORT', '8014'))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

    logger.info(f"API endpoints available on port {port}")

    try:
        await service.run_continuous()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        await service.shutdown()
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

