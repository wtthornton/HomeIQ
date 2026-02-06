"""
Air Quality Service Main Entry Point
Fetches AQI data from OpenWeather API
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any

import aiohttp
from aiohttp import web
from dotenv import load_dotenv
from influxdb_client_3 import InfluxDBClient3, Point

from health_check import HealthCheckHandler

from shared.logging_config import log_error_with_context, log_with_context, setup_logging

load_dotenv()

logger = setup_logging("air-quality-service")


class APIKeyFilter(logging.Filter):
    """Redact API keys from log output"""

    def __init__(self, api_key: str):
        super().__init__()
        self.api_key = api_key

    def filter(self, record: logging.LogRecord) -> bool:
        if self.api_key and self.api_key in record.getMessage():
            record.msg = record.msg.replace(self.api_key, '***REDACTED***')
            if record.args:
                record.args = tuple(
                    str(a).replace(self.api_key, '***REDACTED***') if isinstance(a, str) else a
                    for a in record.args
                )
        return True


_api_key = os.getenv('WEATHER_API_KEY')
if _api_key:
    for handler in logging.root.handlers:
        handler.addFilter(APIKeyFilter(_api_key))
    logger.addFilter(APIKeyFilter(_api_key))


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
        self.fetch_interval = int(os.getenv('FETCH_INTERVAL', '3600'))  # seconds
        self.cache_duration = int(os.getenv('CACHE_DURATION', '60'))  # minutes
        self.retry_delays = [30, 120, 300]  # seconds between retry attempts

        # Rate limiting for /current-aqi (60 requests per minute)
        self._rate_limit_max = 60
        self._rate_limit_window = 60.0  # seconds
        self._rate_limit_requests: list[float] = []

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

        self._validate_coordinate(self.latitude, "LATITUDE", -90, 90)
        self._validate_coordinate(self.longitude, "LONGITUDE", -180, 180)

    @staticmethod
    def _validate_coordinate(value: str, name: str, min_val: float, max_val: float) -> None:
        try:
            num = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"{name} must be a valid number, got {value!r}")
        if not (min_val <= num <= max_val):
            raise ValueError(f"{name} must be between {min_val} and {max_val}, got {num}")

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

                    if lat is not None and lon is not None:
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

        for attempt in range(len(self.retry_delays) + 1):
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
                        timestamp = datetime.fromtimestamp(pollution_data.get('dt', datetime.now(timezone.utc).timestamp()), tz=timezone.utc)

                        # Parse response
                        data = {
                            'aqi': aqi_value,
                            'category': category,
                            'parameter': 'Combined',
                            'pm25': round(float(components.get('pm2_5', 0)), 2),
                            'pm10': round(float(components.get('pm10', 0)), 2),
                            'ozone': round(float(components.get('o3', 0)), 2),
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
                        self.last_fetch_time = datetime.now(timezone.utc)

                        self.health_handler.last_successful_fetch = datetime.now(timezone.utc)
                        self.health_handler.total_fetches += 1
                        self.health_handler.last_api_success = True

                        logger.info(f"AQI: {data['aqi']} ({data['category']})")

                        return data

                    else:
                        logger.error(f"OpenWeather API returned status {response.status}")
                        if attempt < len(self.retry_delays):
                            logger.info(f"Retrying in {self.retry_delays[attempt]}s (attempt {attempt + 1}/{len(self.retry_delays)})")
                            await asyncio.sleep(self.retry_delays[attempt])
                            continue
                        self.health_handler.last_api_success = False
                        self.health_handler.failed_fetches += 1
                        return self.cached_data

            except Exception as e:
                if attempt < len(self.retry_delays):
                    logger.warning(f"Fetch attempt {attempt + 1} failed: {e}. Retrying in {self.retry_delays[attempt]}s")
                    await asyncio.sleep(self.retry_delays[attempt])
                    continue
                self.health_handler.last_api_success = False
                log_error_with_context(
                    logger,
                    f"Error fetching AQI: {e}",
                    e,
                    service="air-quality-service"
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
                .field("pm25", round(float(data['pm25']), 2)) \
                .field("pm10", round(float(data['pm10']), 2)) \
                .field("ozone", round(float(data['ozone']), 2)) \
                .field("co", float(data.get('co', 0))) \
                .field("no2", float(data.get('no2', 0))) \
                .field("so2", float(data.get('so2', 0))) \
                .time(data['timestamp'])

            # CRITICAL FIX: Wrap blocking write() in asyncio.to_thread to prevent blocking event loop
            # InfluxDBClient3.write() is synchronous and blocks - must run in thread pool
            await asyncio.to_thread(self.influxdb_client.write, point)

            self.health_handler.total_writes += 1
            self.health_handler.last_influxdb_success = True
            logger.info("AQI data written to InfluxDB")

        except Exception as e:
            log_error_with_context(
                logger,
                f"Error writing to InfluxDB: {e}",
                e,
                service="air-quality-service"
            )
            self.health_handler.last_influxdb_success = False
            self.health_handler.failed_writes += 1

    def _is_cache_valid(self) -> bool:
        if not self.cached_data or not self.last_fetch_time:
            return False
        age_minutes = (datetime.now(timezone.utc) - self.last_fetch_time).total_seconds() / 60
        return age_minutes < self.cache_duration

    def _check_rate_limit(self) -> bool:
        import time
        now = time.monotonic()
        self._rate_limit_requests = [t for t in self._rate_limit_requests if now - t < self._rate_limit_window]
        if len(self._rate_limit_requests) >= self._rate_limit_max:
            return False
        self._rate_limit_requests.append(now)
        return True

    async def get_current_aqi(self, request: web.Request) -> web.Response:
        """API endpoint for current AQI"""

        if not self._check_rate_limit():
            return web.json_response({'error': 'Rate limit exceeded'}, status=429)

        if self._is_cache_valid():
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

    async def run_continuous(self, stop_event: asyncio.Event | None = None) -> None:
        """Run continuous data collection loop"""

        logger.info(f"Starting continuous AQI monitoring (every {self.fetch_interval}s)")

        while not (stop_event and stop_event.is_set()):
            try:
                data = await self.fetch_air_quality()

                if data:
                    await self.store_in_influxdb(data)

                if stop_event:
                    try:
                        await asyncio.wait_for(stop_event.wait(), timeout=self.fetch_interval)
                        break
                    except asyncio.TimeoutError:
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
                    service="air-quality-service"
                )
                if stop_event:
                    try:
                        await asyncio.wait_for(stop_event.wait(), timeout=300)
                        break
                    except asyncio.TimeoutError:
                        pass
                else:
                    await asyncio.sleep(300)


async def create_app(service: AirQualityService) -> web.Application:
    """Create web application"""
    app = web.Application()

    app.router.add_get('/health', service.health_handler.handle)
    app.router.add_get('/current-aqi', service.get_current_aqi)

    return app


async def main() -> None:
    """Main entry point"""
    import signal

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

    stop_event = asyncio.Event()
    loop = asyncio.get_event_loop()

    try:
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, stop_event.set)
    except NotImplementedError:
        pass

    try:
        await service.run_continuous(stop_event)
    except asyncio.CancelledError:
        logger.info("Received shutdown signal")
    finally:
        logger.info("Shutting down...")
        await service.shutdown()
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

