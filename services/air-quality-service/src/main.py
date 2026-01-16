"""
Air Quality Service Main Entry Point
Fetches AQI data from OpenWeather API
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

from health_check import HealthCheckHandler

from shared.logging_config import log_error_with_context, log_with_context, setup_logging

load_dotenv()

logger = setup_logging("air-quality-service")


class AirQualityService:
    """Fetch and store air quality data from OpenWeather API"""

    def __init__(self) -> None:
        self.api_key = os.getenv('WEATHER_API_KEY')
        self.latitude = os.getenv('LATITUDE', '36.1699')  # Las Vegas default
        self.longitude = os.getenv('LONGITUDE', '-115.1398')
        self.base_url = "https://api.openweathermap.org/data/2.5/air_pollution"

        # Home Assistant configuration (for automatic location detection)
        self.ha_url = os.getenv('HOME_ASSISTANT_URL') or os.getenv('HA_HTTP_URL')
        self.ha_token = os.getenv('HOME_ASSISTANT_TOKEN') or os.getenv('HA_TOKEN')

        # InfluxDB configuration
        self.influxdb_url = os.getenv('INFLUXDB_URL', 'http://influxdb:8086')
        self.influxdb_token = os.getenv('INFLUXDB_TOKEN')
        self.influxdb_org = os.getenv('INFLUXDB_ORG', 'home_assistant')
        self.influxdb_bucket = os.getenv('INFLUXDB_BUCKET', 'events')

        # Service configuration
        self.fetch_interval = 3600  # 1 hour
        self.cache_duration = 60  # minutes

        # Cache
        self.cached_data: dict[str, Any] | None = None
        self.last_fetch_time: datetime | None = None
        self.last_category: str | None = None

        # Components
        self.session: aiohttp.ClientSession | None = None
        self.influxdb_client: InfluxDBClient3 | None = None
        self.health_handler = HealthCheckHandler()

        if not self.api_key:
            raise ValueError("WEATHER_API_KEY environment variable is required")
        if not self.influxdb_token:
            raise ValueError("INFLUXDB_TOKEN environment variable is required")

    async def fetch_location_from_ha(self) -> dict[str, float] | None:
        """Fetch location from Home Assistant configuration"""
        if not self.ha_url or not self.ha_token:
            logger.warning("Home Assistant URL or token not configured, using environment variables for location")
            return None

        try:
            headers = {"Authorization": f"Bearer {self.ha_token}"}
            url = f"{self.ha_url}/api/config"

            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    config = await response.json()
                    lat = config.get('latitude')
                    lon = config.get('longitude')

                    if lat and lon:
                        logger.info(f"Fetched location from Home Assistant: {lat},{lon}")
                        return {'latitude': float(lat), 'longitude': float(lon)}
                    else:
                        logger.warning("Home Assistant config missing latitude/longitude")
                        return None
                else:
                    logger.warning(f"Failed to fetch HA config: HTTP {response.status}")
                    return None

        except Exception as e:
            logger.warning(f"Could not fetch location from Home Assistant: {e}")
            return None

    async def startup(self) -> None:
        """Initialize service"""
        logger.info("Initializing Air Quality Service...")

        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10)
        )

        # Try to get location from Home Assistant first
        ha_location = await self.fetch_location_from_ha()
        if ha_location:
            self.latitude = str(ha_location['latitude'])
            self.longitude = str(ha_location['longitude'])
            logger.info(f"Using location from Home Assistant: {self.latitude}, {self.longitude}")
        else:
            logger.info(f"Using configured location: {self.latitude}, {self.longitude}")

        self.influxdb_client = InfluxDBClient3(
            host=self.influxdb_url,
            token=self.influxdb_token,
            database=self.influxdb_bucket,
            org=self.influxdb_org
        )

        logger.info("Air Quality Service initialized")

    async def shutdown(self) -> None:
        """Cleanup"""
        logger.info("Shutting down Air Quality Service...")

        if self.session:
            await self.session.close()

        if self.influxdb_client:
            self.influxdb_client.close()

    async def fetch_air_quality(self) -> dict[str, Any] | None:
        """Fetch AQI from OpenWeather API"""

        try:
            params = {
                "lat": self.latitude,
                "lon": self.longitude,
                "appid": self.api_key
            }

            log_with_context(
                logger, "INFO",
                f"Fetching AQI for location {self.latitude},{self.longitude}",
                service="air-quality-service"
            )

            async with self.session.get(self.base_url, params=params) as response:
                if response.status == 200:
                    raw_data = await response.json()

                    if not raw_data or 'list' not in raw_data or not raw_data['list']:
                        logger.warning("OpenWeather API returned empty data")
                        return self.cached_data

                    # OpenWeather returns data in a list
                    pollution_data = raw_data['list'][0]
                    main_data = pollution_data.get('main', {})
                    components = pollution_data.get('components', {})

                    # OpenWeather AQI is 1-5, convert to 0-500 scale
                    # 1=Good (0-50), 2=Fair (51-100), 3=Moderate (101-150),
                    # 4=Poor (151-200), 5=Very Poor (201-500)
                    ow_aqi = main_data.get('aqi', 1)

                    # Convert to 0-500 scale
                    aqi_map = {1: 25, 2: 75, 3: 125, 4: 175, 5: 250}
                    aqi_value = aqi_map.get(ow_aqi, 25)

                    # Category names
                    category_map = {
                        1: 'Good',
                        2: 'Fair',
                        3: 'Moderate',
                        4: 'Poor',
                        5: 'Very Poor'
                    }
                    category = category_map.get(ow_aqi, 'Unknown')

                    # Parse timestamp
                    timestamp = datetime.fromtimestamp(pollution_data.get('dt', datetime.now().timestamp()))

                    # Parse response
                    data = {
                        'aqi': aqi_value,
                        'category': category,
                        'parameter': 'Combined',
                        'pm25': int(components.get('pm2_5', 0)),
                        'pm10': int(components.get('pm10', 0)),
                        'ozone': int(components.get('o3', 0)),
                        'timestamp': timestamp,
                        'co': float(components.get('co', 0)),
                        'no2': float(components.get('no2', 0)),
                        'so2': float(components.get('so2', 0))
                    }

                    # Log category changes
                    if self.last_category and self.last_category != data['category']:
                        logger.warning(f"AQI category changed: {self.last_category} → {data['category']}")

                    self.last_category = data['category']
                    self.cached_data = data
                    self.last_fetch_time = datetime.now()

                    self.health_handler.last_successful_fetch = datetime.now()
                    self.health_handler.total_fetches += 1

                    logger.info(f"AQI: {data['aqi']} ({data['category']})")

                    return data

                else:
                    logger.error(f"OpenWeather API returned status {response.status}")
                    self.health_handler.failed_fetches += 1
                    return self.cached_data

        except Exception as e:
            log_error_with_context(
                logger,
                f"Error fetching AQI: {e}",
                service="air-quality-service",
                error=str(e)
            )
            self.health_handler.failed_fetches += 1
            return self.cached_data

    async def store_in_influxdb(self, data: dict[str, Any]) -> None:
        """Store AQI data in InfluxDB"""

        if not data:
            return

        if not self.influxdb_client:
            logger.error("InfluxDB client not initialized")
            return

        try:
            point = Point("air_quality") \
                .tag("location", f"{self.latitude},{self.longitude}") \
                .tag("category", data['category']) \
                .tag("parameter", data['parameter']) \
                .field("aqi", int(data['aqi'])) \
                .field("pm25", int(data['pm25'])) \
                .field("pm10", int(data['pm10'])) \
                .field("ozone", int(data['ozone'])) \
                .field("co", float(data.get('co', 0))) \
                .field("no2", float(data.get('no2', 0))) \
                .field("so2", float(data.get('so2', 0))) \
                .time(data['timestamp'])

            # CRITICAL FIX: Wrap blocking write() in asyncio.to_thread to prevent blocking event loop
            # InfluxDBClient3.write() is synchronous and blocks - must run in thread pool
            await asyncio.to_thread(self.influxdb_client.write, point)

            logger.info("AQI data written to InfluxDB")

        except Exception as e:
            log_error_with_context(
                logger,
                f"Error writing to InfluxDB: {e}",
                service="air-quality-service",
                error=str(e)
            )
            self.health_handler.failed_fetches += 1

    async def get_current_aqi(self, request: web.Request) -> web.Response:
        """API endpoint for current AQI"""

        if self.cached_data:
            return web.json_response({
                'aqi': self.cached_data['aqi'],
                'category': self.cached_data['category'],
                'pm25': self.cached_data.get('pm25', 0),
                'pm10': self.cached_data.get('pm10', 0),
                'ozone': self.cached_data.get('ozone', 0),
                'co': self.cached_data.get('co', 0),
                'no2': self.cached_data.get('no2', 0),
                'so2': self.cached_data.get('so2', 0),
                'timestamp': self.last_fetch_time.isoformat() if self.last_fetch_time else None
            })
        else:
            return web.json_response({'error': 'No data available'}, status=503)

    async def run_continuous(self) -> None:
        """Run continuous data collection loop"""

        logger.info(f"Starting continuous AQI monitoring (every {self.fetch_interval}s)")

        while True:
            try:
                data = await self.fetch_air_quality()

                if data:
                    await self.store_in_influxdb(data)

                await asyncio.sleep(self.fetch_interval)

            except Exception as e:
                log_error_with_context(
                    logger,
                    f"Error in continuous loop: {e}",
                    service="air-quality-service",
                    error=str(e)
                )
                await asyncio.sleep(300)


async def create_app(service: AirQualityService) -> web.Application:
    """Create web application"""
    app = web.Application()

    app.router.add_get('/health', service.health_handler.handle)
    app.router.add_get('/current-aqi', service.get_current_aqi)

    return app


async def main() -> None:
    """Main entry point"""
    logger.info("Starting Air Quality Service...")

    service = AirQualityService()
    await service.startup()

    app = await create_app(service)
    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.getenv('SERVICE_PORT', '8012'))
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

