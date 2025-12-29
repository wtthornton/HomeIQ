"""
Sports API Service - Home Assistant Team Tracker Integration
Epic 31 Architecture Pattern: Standalone service that writes directly to InfluxDB

This service:
1. Polls Home Assistant REST API for Team Tracker sensors
2. Parses sensor states and attributes (PRE, IN, POST, BYE states)
3. Writes normalized sports data to InfluxDB
4. Supports all Team Tracker features and leagues
"""

from __future__ import annotations

import asyncio
import os
import sys
from contextlib import suppress
from datetime import datetime, timezone
from typing import Any, Literal
from urllib.parse import urlparse

import aiohttp
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from influxdb_client_3 import InfluxDBClient3, Point
from pydantic import BaseModel

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))

from shared.logging_config import setup_logging

from .health_check import HealthCheckHandler

# Load environment variables
load_dotenv()

SERVICE_NAME = "sports-api"
SERVICE_VERSION = "1.0.0"

# Configure logging
logger = setup_logging(SERVICE_NAME)


# Pydantic Models
class TeamTrackerSensor(BaseModel):
    """Team Tracker sensor data model"""
    entity_id: str
    state: str  # PRE, IN, POST, BYE, NOT_FOUND
    attributes: dict[str, Any]
    last_updated: str
    last_changed: str


class SportsDataResponse(BaseModel):
    """Sports data response"""
    sensors: list[dict[str, Any]]
    count: int
    last_update: str


class SportsService:
    """Sports service - fetch from HA, parse, store in InfluxDB"""

    def __init__(self) -> None:
        """Initialize SportsService with configuration from environment variables."""
        self._init_home_assistant_config()
        self._init_influxdb_config()
        self._init_cache()
        self._init_components()
        self._init_stats()
        self._validate_config()

    def _init_home_assistant_config(self) -> None:
        """Initialize Home Assistant configuration."""
        self.ha_url = os.getenv('HA_HTTP_URL') or os.getenv('HOME_ASSISTANT_URL', 'http://192.168.1.86:8123')
        self.ha_token = os.getenv('HA_TOKEN') or os.getenv('HOME_ASSISTANT_TOKEN')
        self.ha_url = self.ha_url.rstrip('/')
        self.poll_interval = int(os.getenv('SPORTS_POLL_INTERVAL', '60'))

    def _init_influxdb_config(self) -> None:
        """Initialize InfluxDB configuration with fallback hostnames."""
        influxdb_url = os.getenv('INFLUXDB_URL', 'http://influxdb:8086')
        parsed_url = self._parse_influxdb_url(influxdb_url)
        self.influxdb_host = parsed_url['host']
        self.influxdb_port = parsed_url['port']
        
        fallback_hosts = self._parse_fallback_hosts()
        self.influxdb_urls = self._build_influxdb_urls(influxdb_url, fallback_hosts)
        
        logger.info(f"InfluxDB fallback URLs configured: {len(self.influxdb_urls)} URLs")
        self.influxdb_url = influxdb_url
        self.influxdb_token = os.getenv('INFLUXDB_TOKEN')
        self.influxdb_org = os.getenv('INFLUXDB_ORG', 'home_assistant')
        self.influxdb_bucket = os.getenv('INFLUXDB_BUCKET', 'home_assistant_events')
        self.max_influx_retries = int(os.getenv('INFLUXDB_WRITE_RETRIES', '3'))
        self.working_influxdb_host: str | None = None

    def _parse_influxdb_url(self, url: str) -> dict[str, str]:
        """Parse InfluxDB URL to extract host and port.
        
        Args:
            url: InfluxDB URL (e.g., 'http://influxdb:8086')
            
        Returns:
            Dictionary with 'host' and 'port' keys
        """
        parsed = urlparse(url if '://' in url else f'http://{url}')
        return {
            'host': parsed.hostname or url.split(':')[0],
            'port': str(parsed.port) if parsed.port else '8086'
        }

    def _parse_fallback_hosts(self) -> list[str]:
        """Parse fallback hosts from environment variable.
        
        Returns:
            List of fallback hostnames
        """
        fallback_hosts_env = os.getenv('INFLUXDB_FALLBACK_HOSTS', 'influxdb,homeiq-influxdb,localhost')
        return [h.strip() for h in fallback_hosts_env.split(',') if h.strip()]

    def _build_influxdb_urls(self, primary_url: str, fallback_hosts: list[str]) -> list[str]:
        """Build list of InfluxDB URLs including primary and fallback hosts.
        
        Args:
            primary_url: Primary InfluxDB URL
            fallback_hosts: List of fallback hostnames
            
        Returns:
            List of InfluxDB URLs
        """
        urls = [primary_url]
        for host in fallback_hosts:
            if host != self.influxdb_host:
                urls.append(f'http://{host}:{self.influxdb_port}')
        return urls

    def _init_cache(self) -> None:
        """Initialize cache variables."""
        self.cached_sensors: list[dict[str, Any]] | None = None
        self.cache_time: datetime | None = None

    def _init_components(self) -> None:
        """Initialize service components."""
        self.session: aiohttp.ClientSession | None = None
        self.influxdb_client: InfluxDBClient3 | None = None
        self.background_task: asyncio.Task | None = None
        self.last_background_error: str | None = None
        self.last_successful_fetch: datetime | None = None
        self.last_influx_write: datetime | None = None
        self.last_influx_write_error: str | None = None
        self.influx_write_failure_count = 0
        self.influx_write_success_count = 0
        self.health_handler = HealthCheckHandler(service_name=SERVICE_NAME, version=SERVICE_VERSION)

    def _init_stats(self) -> None:
        """Initialize statistics counters."""
        self.fetch_count = 0
        self.sensors_processed = 0

    def _validate_config(self) -> None:
        """Validate required configuration."""
        if not self.ha_token:
            logger.warning("HA_TOKEN not set - service will run in standby mode")
        if not self.influxdb_token:
            raise ValueError("INFLUXDB_TOKEN required")

    async def startup(self) -> None:
        """Initialize service components."""
        logger.info("Initializing Sports API Service...")
        
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
        
        # Try to connect to InfluxDB with fallback hostnames
        self.influxdb_client = await self._initialize_influxdb()
        
        if not self.influxdb_client:
            logger.warning("InfluxDB client initialization failed - service will continue but writes will fail")
        
        logger.info("Sports API Service initialized")

    async def _initialize_influxdb(self) -> InfluxDBClient3 | None:
        """Initialize InfluxDB client with fallback hostname logic"""
        if not self.influxdb_token:
            logger.error("INFLUXDB_TOKEN not set - cannot initialize InfluxDB client")
            return None
        
        for url in self.influxdb_urls:
            try:
                logger.info(f"Attempting to connect to InfluxDB at {url}")
                
                client = InfluxDBClient3(
                    host=url,
                    token=self.influxdb_token,
                    database=self.influxdb_bucket,
                    org=self.influxdb_org
                )
                
                self.working_influxdb_host = url
                logger.info(f"✅ Successfully initialized InfluxDB client with URL: {url}")
                return client
                
            except Exception as e:
                logger.warning(f"Failed to connect to InfluxDB at {url}: {e}")
                continue
        
        logger.error(f"❌ Failed to connect to InfluxDB with any URL: {self.influxdb_urls}")
        return None

    async def shutdown(self) -> None:
        """Cleanup service resources."""
        logger.info("Shutting down Sports API Service...")
        await self.stop_background_task()
        
        if self.session and not self.session.closed:
            await self.session.close()
        
        if self.influxdb_client:
            self.influxdb_client.close()

    async def fetch_team_tracker_sensors(self) -> list[dict[str, Any]]:
        """Fetch Team Tracker sensors from Home Assistant"""
        if not self.ha_token:
            return []
        
        if not self.session or self.session.closed:
            raise RuntimeError("HTTP session not initialized")
        
        try:
            headers = {
                "Authorization": f"Bearer {self.ha_token}",
                "Content-Type": "application/json"
            }
            
            # Fetch all states and filter for Team Tracker sensors
            url = f"{self.ha_url}/api/states"
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    states = await response.json()
                    
                    # Filter for Team Tracker sensors (entity_id starts with sensor.team_tracker_)
                    team_tracker_sensors = [
                        state for state in states
                        if state.get('entity_id', '').startswith('sensor.team_tracker_')
                    ]
                    
                    logger.info(f"Fetched {len(team_tracker_sensors)} Team Tracker sensors from HA")
                    return team_tracker_sensors
                else:
                    logger.error(f"HA API error: {response.status}")
                    return []
        
        except Exception as e:
            logger.error(f"Error fetching Team Tracker sensors: {e}")
            return []

    def parse_sensor_data(self, sensor: dict[str, Any]) -> dict[str, Any]:
        """Parse Team Tracker sensor data into normalized format"""
        entity_id = sensor.get('entity_id', '')
        state = sensor.get('state', 'NOT_FOUND')
        attributes = sensor.get('attributes', {})
        
        # Extract key attributes
        parsed = {
            'entity_id': entity_id,
            'state': state,
            'sport': attributes.get('sport', ''),
            'league': attributes.get('league', ''),
            'team_abbr': attributes.get('team_abbr', ''),
            'team_name': attributes.get('team_name', ''),
            'team_id': attributes.get('team_id', ''),
            'opponent_abbr': attributes.get('opponent_abbr', ''),
            'opponent_name': attributes.get('opponent_name', ''),
            'opponent_id': attributes.get('opponent_id', ''),
            'team_score': attributes.get('team_score'),
            'opponent_score': attributes.get('opponent_score'),
            'quarter': attributes.get('quarter'),
            'clock': attributes.get('clock'),
            'venue': attributes.get('venue', ''),
            'location': attributes.get('location', ''),
            'date': attributes.get('date', ''),
            'kickoff_in': attributes.get('kickoff_in', ''),
            'tv_network': attributes.get('tv_network', ''),
            'last_update': attributes.get('last_update', sensor.get('last_updated', '')),
            'last_updated': sensor.get('last_updated', ''),
            'last_changed': sensor.get('last_changed', ''),
            # Include all other attributes for completeness
            'all_attributes': attributes
        }
        
        return parsed

    async def store_in_influxdb(self, sensors: list[dict[str, Any]]) -> None:
        """Store sports data in InfluxDB.
        
        Args:
            sensors: List of parsed sensor data dictionaries
        """
        if not sensors:
            return
        
        if not self.influxdb_client:
            logger.warning("InfluxDB client not initialized, skipping write")
            return
        
        try:
            points = self._create_influxdb_points(sensors)
            if points:
                await self._write_points_with_retry(points)
        except Exception as e:
            logger.error(f"Error storing sports data in InfluxDB: {e}")

    def _create_influxdb_points(self, sensors: list[dict[str, Any]]) -> list[Point]:
        """Create InfluxDB Point objects from sensor data.
        
        Args:
            sensors: List of parsed sensor data dictionaries
            
        Returns:
            List of InfluxDB Point objects
        """
        points: list[Point] = []
        timestamp = datetime.utcnow().replace(tzinfo=timezone.utc)
        
        for sensor_data in sensors:
            point = self._create_point_from_sensor(sensor_data, timestamp)
            points.append(point)
        
        return points

    def _create_point_from_sensor(self, sensor_data: dict[str, Any], timestamp: datetime) -> Point:
        """Create a single InfluxDB Point from sensor data.
        
        Args:
            sensor_data: Parsed sensor data dictionary
            timestamp: Timestamp for the data point
            
        Returns:
            InfluxDB Point object
        """
        point = Point("sports_data") \
            .tag("entity_id", sensor_data['entity_id']) \
            .tag("sport", sensor_data.get('sport', '')) \
            .tag("league", sensor_data.get('league', '')) \
            .tag("team_abbr", sensor_data.get('team_abbr', '')) \
            .tag("team_id", str(sensor_data.get('team_id', ''))) \
            .tag("state", sensor_data['state']) \
            .field("team_score", self._safe_int(sensor_data.get('team_score'))) \
            .field("opponent_score", self._safe_int(sensor_data.get('opponent_score'))) \
            .time(timestamp)
        
        # Add optional fields
        point = self._add_optional_fields(point, sensor_data)
        
        return point

    def _safe_int(self, value: Any) -> int | None:
        """Safely convert value to int, returning None if conversion fails.
        
        Args:
            value: Value to convert
            
        Returns:
            Integer value or None
        """
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    def _add_optional_fields(self, point: Point, sensor_data: dict[str, Any]) -> Point:
        """Add optional fields and tags to InfluxDB Point.
        
        Args:
            point: InfluxDB Point object
            sensor_data: Parsed sensor data dictionary
            
        Returns:
            Updated InfluxDB Point object
        """
        if sensor_data.get('quarter'):
            point = point.field("quarter", str(sensor_data['quarter']))
        if sensor_data.get('clock'):
            point = point.field("clock", str(sensor_data['clock']))
        if sensor_data.get('opponent_abbr'):
            point = point.tag("opponent_abbr", sensor_data['opponent_abbr'])
        if sensor_data.get('opponent_id'):
            point = point.tag("opponent_id", str(sensor_data['opponent_id']))
        if sensor_data.get('venue'):
            point = point.tag("venue", sensor_data['venue'])
        
        return point

    async def _write_points_with_retry(self, points: list[Point]) -> None:
        """Write points to InfluxDB with retry logic.
        
        Args:
            points: List of InfluxDB Point objects to write
        """
        for attempt in range(1, self.max_influx_retries + 1):
            try:
                await asyncio.to_thread(self.influxdb_client.write, points)
                self._record_successful_write(len(points))
                logger.info(f"Sports data written to InfluxDB ({len(points)} points)")
                return
            except Exception as e:
                error_str = str(e)
                self.last_influx_write_error = error_str
                
                if self._is_dns_error(error_str):
                    await self._handle_dns_error(attempt, e)
                    if attempt >= self.max_influx_retries:
                        self._record_failed_write()
                        return
                    continue
                
                if attempt >= self.max_influx_retries:
                    self._record_failed_write()
                    logger.error(f"Failed to write to InfluxDB after {attempt} attempts: {e}")
                else:
                    backoff = 2 ** (attempt - 1)
                    logger.warning(f"InfluxDB write failed (attempt {attempt}/{self.max_influx_retries}). Retrying in {backoff}s")
                    await asyncio.sleep(backoff)

    def _is_dns_error(self, error_str: str) -> bool:
        """Check if error is a DNS resolution error.
        
        Args:
            error_str: Error message string
            
        Returns:
            True if error is DNS-related
        """
        return "Name does not resolve" in error_str or "Failed to resolve" in error_str

    async def _handle_dns_error(self, attempt: int, error: Exception) -> None:
        """Handle DNS resolution error by attempting to reconnect.
        
        Args:
            attempt: Current retry attempt number
            error: The exception that occurred
        """
        logger.warning(f"DNS resolution failed (attempt {attempt}/{self.max_influx_retries}), attempting to reconnect...")
        self.influxdb_client = await self._initialize_influxdb()

    def _record_successful_write(self, point_count: int) -> None:
        """Record successful InfluxDB write.
        
        Args:
            point_count: Number of points written
        """
        self.last_influx_write = datetime.utcnow().replace(tzinfo=timezone.utc)
        self.last_influx_write_error = None
        self.influx_write_success_count += 1
        self.sensors_processed += point_count

    def _record_failed_write(self) -> None:
        """Record failed InfluxDB write."""
        self.influx_write_failure_count += 1

    async def get_current_sports_data(self) -> list[dict[str, Any]]:
        """Get current sports data (fetch from HA, parse, store)"""
        sensors = await self.fetch_team_tracker_sensors()
        
        if not sensors:
            return self.cached_sensors or []
        
        # Parse sensor data
        parsed_sensors = [self.parse_sensor_data(sensor) for sensor in sensors]
        
        # Update cache
        self.cached_sensors = parsed_sensors
        self.cache_time = datetime.utcnow().replace(tzinfo=timezone.utc)
        self.last_successful_fetch = self.cache_time
        self.fetch_count += 1
        
        # Write to InfluxDB
        await self.store_in_influxdb(parsed_sensors)
        
        return parsed_sensors

    async def run_continuous(self):
        """Background fetch loop"""
        logger.info(f"Starting continuous fetch (every {self.poll_interval}s)")
        
        while True:
            try:
                await self.get_current_sports_data()
                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                logger.info("Continuous fetch loop cancelled")
                raise
            except Exception as e:
                self.last_background_error = str(e)
                logger.error(f"Error in continuous loop: {e}")
                await asyncio.sleep(300)

    def start_background_task(self) -> asyncio.Task:
        """Start guarded background task"""
        if self.background_task and not self.background_task.done():
            return self.background_task
        
        async def _run():
            try:
                await self.run_continuous()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.last_background_error = str(exc)
                logger.exception("Sports background task failed")
        
        self.background_task = asyncio.create_task(_run(), name="sports-fetch-loop")
        return self.background_task

    async def stop_background_task(self) -> None:
        """Stop background task gracefully."""
        if self.background_task and not self.background_task.done():
            self.background_task.cancel()
            with suppress(asyncio.CancelledError):
                await self.background_task
        self.background_task = None


# Global service instance
sports_service = None


async def startup() -> None:
    """Startup handler for FastAPI application."""
    global sports_service
    sports_service = SportsService()
    await sports_service.startup()
    sports_service.start_background_task()


async def shutdown() -> None:
    """Shutdown handler for FastAPI application."""
    if sports_service:
        await sports_service.shutdown()


# FastAPI app
app = FastAPI(
    title="Sports API Service",
    description="Home Assistant Team Tracker integration service",
    version=SERVICE_VERSION
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lifecycle
app.add_event_handler("startup", startup)
app.add_event_handler("shutdown", shutdown)


@app.get("/")
async def root() -> dict[str, Any]:
    """Root endpoint providing service information."""
    return {
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "status": "running",
        "endpoints": ["/health", "/metrics", "/sports-data", "/stats"]
    }


@app.get("/health")
async def health() -> dict[str, Any]:
    """Health check endpoint."""
    if not sports_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    return await sports_service.health_handler.handle(sports_service)


@app.get("/metrics")
async def metrics() -> dict[str, Any]:
    """Lightweight metrics endpoint (JSON)."""
    if not sports_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    return await sports_service.health_handler.handle(sports_service)


@app.get("/sports-data", response_model=SportsDataResponse)
async def get_sports_data() -> SportsDataResponse:
    """Get current sports data from Team Tracker sensors."""
    if not sports_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    sensors = await sports_service.get_current_sports_data()
    
    return SportsDataResponse(
        sensors=sensors,
        count=len(sensors),
        last_update=sports_service.last_successful_fetch.isoformat() if sports_service.last_successful_fetch else None
    )


@app.get("/stats")
async def stats() -> dict[str, Any]:
    """Service statistics endpoint."""
    if not sports_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    return {
        "fetch_count": sports_service.fetch_count,
        "sensors_processed": sports_service.sensors_processed,
        "influx_write_success": sports_service.influx_write_success_count,
        "influx_write_failures": sports_service.influx_write_failure_count,
        "last_successful_fetch": sports_service.last_successful_fetch.isoformat() if sports_service.last_successful_fetch else None,
        "last_influx_write": sports_service.last_influx_write.isoformat() if sports_service.last_influx_write else None,
        "poll_interval_seconds": sports_service.poll_interval,
        "cached_sensors_count": len(sports_service.cached_sensors) if sports_service.cached_sensors else 0
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('SERVICE_PORT', '8005'))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

