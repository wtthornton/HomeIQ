"""Sports adapter (former sports-api service) — HA Team Tracker integration.

Polls the Home Assistant REST API for Team Tracker sensor entities, parses game
states (PRE, IN, POST, BYE), extracts automation-relevant attributes (team colors,
winner flags, event names, last plays), and writes normalized time-series data to
InfluxDB with fallback hostname support and retry logic.

Former routes (unchanged): GET /, GET /sports-data, GET /stats.
"""

from __future__ import annotations

import asyncio
import os
import random
import time
from collections import defaultdict
from contextlib import suppress
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import aiohttp
from fastapi import APIRouter, Depends, Header, HTTPException
from homeiq_observability.logging_config import setup_logging
from influxdb_client_3 import InfluxDBClient3, Point
from pydantic import BaseModel

from ...config import settings
from ..base import CollectorAdapter, with_adapter_timeout

if TYPE_CHECKING:
    from homeiq_resilience import StandardHealthCheck

NAME = "sports"
ADAPTER_TIMEOUT_SECONDS = 15.0
SERVICE_NAME = "sports-api"

logger = setup_logging(f"{settings.service_name}.{NAME}")

SPORTS_API_KEY = settings.sports_api_key


async def verify_api_key(x_api_key: str = Header(...)) -> str:
    """Verify the X-API-Key header against the configured SPORTS_API_KEY."""
    if not SPORTS_API_KEY:
        return x_api_key
    if x_api_key != SPORTS_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


class RateLimiter:
    """In-memory sliding window rate limiter for API endpoint protection."""

    def __init__(self, max_requests: int = 30, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: defaultdict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str = "global") -> bool:
        """Check if a request is allowed under the sliding window rate limit."""
        now = time.monotonic()
        window_start = now - self.window_seconds
        self._requests[key] = [t for t in self._requests[key] if t > window_start]
        if len(self._requests[key]) >= self.max_requests:
            return False
        self._requests[key].append(now)
        return True


rate_limiter = RateLimiter()


class TeamTrackerSensor(BaseModel):
    """Team Tracker sensor data model from Home Assistant."""

    entity_id: str
    state: str
    attributes: dict[str, Any]
    last_updated: str
    last_changed: str


class SportsDataResponse(BaseModel):
    """Sports data API response containing parsed sensor data."""

    sensors: list[dict[str, Any]]
    count: int
    last_update: str | None = None


class SportsService:
    """Sports data service integrating Home Assistant Team Tracker with InfluxDB."""

    def __init__(self) -> None:
        """Initialize SportsService with configuration from environment variables."""
        self.ha_url = (os.getenv("HA_HTTP_URL") or os.getenv("HOME_ASSISTANT_URL") or "").rstrip(
            "/"
        )
        self.ha_token = os.getenv("HA_TOKEN") or os.getenv("HOME_ASSISTANT_TOKEN")
        if not self.ha_url:
            logger.error(
                "HA_HTTP_URL/HOME_ASSISTANT_URL not set — sports polling cannot reach Home Assistant"
            )
        self.poll_interval = int(os.getenv("SPORTS_POLL_INTERVAL", "60"))

        self._init_influxdb_config()
        self._init_cache()
        self._init_stats()

    def _init_influxdb_config(self) -> None:
        """Initialize InfluxDB configuration with fallback hostnames for DNS resilience."""
        influxdb_url = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
        parsed_url = self._parse_influxdb_url(influxdb_url)
        self.influxdb_host = parsed_url["host"]
        self.influxdb_port = parsed_url["port"]

        fallback_hosts = self._parse_fallback_hosts()
        self.influxdb_urls = self._build_influxdb_urls(influxdb_url, fallback_hosts)

        logger.info(f"InfluxDB fallback URLs configured: {len(self.influxdb_urls)} URLs")
        self.influxdb_url = influxdb_url
        self.influxdb_token = os.getenv("INFLUXDB_TOKEN")
        self.influxdb_org = os.getenv("INFLUXDB_ORG", "home_assistant")
        self.influxdb_bucket = os.getenv("INFLUXDB_BUCKET", "home_assistant_events")
        self.max_influx_retries = int(os.getenv("INFLUXDB_WRITE_RETRIES", "3"))
        self.working_influxdb_host: str | None = None

    def _parse_influxdb_url(self, url: str) -> dict[str, str]:
        """Parse InfluxDB URL to extract host and port components."""
        parsed = urlparse(url if "://" in url else f"http://{url}")
        return {
            "host": parsed.hostname or url.split(":")[0],
            "port": str(parsed.port) if parsed.port else "8086",
        }

    def _parse_fallback_hosts(self) -> list[str]:
        """Parse INFLUXDB_FALLBACK_HOSTS environment variable into a list."""
        fallback_hosts_env = os.getenv(
            "INFLUXDB_FALLBACK_HOSTS", "influxdb,homeiq-influxdb,localhost"
        )
        return [h.strip() for h in fallback_hosts_env.split(",") if h.strip()]

    def _build_influxdb_urls(self, primary_url: str, fallback_hosts: list[str]) -> list[str]:
        """Build URL list from primary and fallback hosts for DNS resilience."""
        urls = [primary_url]
        for host in fallback_hosts:
            if host != self.influxdb_host:
                urls.append(f"http://{host}:{self.influxdb_port}")
        return urls

    def _init_cache(self) -> None:
        """Initialize in-memory cache and service components."""
        self.cached_sensors: list[dict[str, Any]] | None = None
        self.cache_time: datetime | None = None
        self.session: aiohttp.ClientSession | None = None
        self.influxdb_client: InfluxDBClient3 | None = None
        self.background_task: asyncio.Task | None = None
        self.last_background_error: str | None = None
        self.last_successful_fetch: datetime | None = None
        self.last_influx_write: datetime | None = None
        self.last_influx_write_error: str | None = None
        self.influx_write_failure_count = 0
        self.influx_write_success_count = 0
        from .health_check import HealthCheckHandler

        self.health_handler = HealthCheckHandler(service_name=SERVICE_NAME, version="1.0.0")

    def _init_stats(self) -> None:
        """Initialize fetch count and sensors processed statistics counters."""
        self.fetch_count = 0
        self.sensors_processed = 0
        if not self.ha_token:
            logger.warning("HA_TOKEN not set - service will run in standby mode")
        if not self.influxdb_token:
            raise ValueError("INFLUXDB_TOKEN required")

    async def startup(self) -> None:
        """Initialize HTTP session and InfluxDB client for service operation."""
        logger.info("Initializing Sports adapter...")

        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        self.session = aiohttp.ClientSession(
            connector=connector, timeout=aiohttp.ClientTimeout(total=10)
        )

        self.influxdb_client = await self._initialize_influxdb()

        if not self.influxdb_client:
            logger.warning(
                "InfluxDB client initialization failed - adapter will continue but writes will fail"
            )

        logger.info("Sports adapter initialized")

    async def _initialize_influxdb(self) -> InfluxDBClient3 | None:
        """Initialize InfluxDB client, trying each fallback URL in order."""
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
                    org=self.influxdb_org,
                )

                self.working_influxdb_host = url
                logger.info(f"[OK] Successfully initialized InfluxDB client with URL: {url}")
                return client

            except Exception as e:
                logger.warning(f"Failed to connect to InfluxDB at {url}: {e}")
                continue

        logger.error(f"[FAIL] Failed to connect to InfluxDB with any URL: {self.influxdb_urls}")
        return None

    async def shutdown(self) -> None:
        """Cleanup service resources by stopping background task and closing connections."""
        logger.info("Shutting down Sports adapter...")
        await self.stop_background_task()

        if self.session and not self.session.closed:
            await self.session.close()

        if self.influxdb_client:
            self.influxdb_client.close()

    def _is_team_tracker_entity(self, state: dict[str, Any]) -> bool:
        """Check if a HA state entity is a Team Tracker sensor."""
        entity_id = state.get("entity_id", "")
        return entity_id.startswith("sensor.") and "team_tracker" in entity_id

    def _redact_token(self, message: str) -> str:
        """Redact HA bearer token from error messages for safe logging."""
        if self.ha_token and self.ha_token in message:
            return message.replace(self.ha_token, "[REDACTED]")
        return message

    async def _fetch_ha_states(self) -> list[dict[str, Any]]:
        """Fetch all entity states from Home Assistant REST API."""
        headers = {"Authorization": f"Bearer {self.ha_token}", "Content-Type": "application/json"}
        url = f"{self.ha_url}/api/states"
        async with self.session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            body = await response.text()
            logger.error(f"HA API error: {response.status} - {body[:500]}")
            return []

    def _filter_team_tracker_sensors(self, states: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Filter HA state list to only Team Tracker sensor entities."""
        return [s for s in states if self._is_team_tracker_entity(s)]

    async def fetch_team_tracker_sensors(self) -> list[dict[str, Any]]:
        """Fetch Team Tracker sensors from Home Assistant REST API."""
        if not self.ha_token:
            return []

        if not self.session or self.session.closed:
            raise RuntimeError("HTTP session not initialized")

        try:
            states = await self._fetch_ha_states()
            sensors = self._filter_team_tracker_sensors(states)
            logger.info(f"Fetched {len(sensors)} Team Tracker sensors from HA")
            return sensors

        except Exception as e:
            error_text = str(e) if str(e) else f"{type(e).__name__} (no message)"
            logger.error(f"Error fetching Team Tracker sensors: {self._redact_token(error_text)}")
            return []

    def parse_sensor_data(self, sensor: dict[str, Any]) -> dict[str, Any]:
        """Parse Team Tracker sensor data into normalized format."""
        entity_id = sensor.get("entity_id", "")
        state = sensor.get("state", "NOT_FOUND")
        attributes = sensor.get("attributes", {})

        parsed = self._extract_core_attributes(entity_id, state, attributes, sensor)
        parsed.update(self._extract_automation_attributes(attributes))
        return parsed

    def _extract_core_attributes(
        self, entity_id: str, state: str, attributes: dict[str, Any], sensor: dict[str, Any]
    ) -> dict[str, Any]:
        """Extract core game attributes: teams, scores, schedule, and timing."""
        return {
            "entity_id": entity_id,
            "state": state,
            "sport": attributes.get("sport", ""),
            "league": attributes.get("league", ""),
            "team_abbr": attributes.get("team_abbr", ""),
            "team_name": attributes.get("team_name", ""),
            "team_id": attributes.get("team_id", ""),
            "opponent_abbr": attributes.get("opponent_abbr", ""),
            "opponent_name": attributes.get("opponent_name", ""),
            "opponent_id": attributes.get("opponent_id", ""),
            "team_score": attributes.get("team_score"),
            "opponent_score": attributes.get("opponent_score"),
            "quarter": attributes.get("quarter"),
            "clock": attributes.get("clock"),
            "venue": attributes.get("venue", ""),
            "location": attributes.get("location", ""),
            "date": attributes.get("date", ""),
            "kickoff_in": attributes.get("kickoff_in", ""),
            "tv_network": attributes.get("tv_network", ""),
            "last_update": attributes.get("last_update", sensor.get("last_updated", "")),
            "last_updated": sensor.get("last_updated", ""),
            "last_changed": sensor.get("last_changed", ""),
        }

    def _extract_automation_attributes(self, attributes: dict[str, Any]) -> dict[str, Any]:
        """Extract automation-relevant attributes for smart home integration."""
        return {
            "team_homeaway": attributes.get("team_homeaway", ""),
            "team_colors": attributes.get("team_colors", []),
            "team_winner": attributes.get("team_winner"),
            "opponent_winner": attributes.get("opponent_winner"),
            "event_name": attributes.get("event_name", ""),
            "last_play": attributes.get("last_play", ""),
        }

    async def store_in_influxdb(self, sensors: list[dict[str, Any]]) -> None:
        """Store sports data in InfluxDB."""
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
        """Create InfluxDB Point objects from sensor data."""
        points: list[Point] = []
        timestamp = datetime.now(UTC)

        for sensor_data in sensors:
            point = self._create_point_from_sensor(sensor_data, timestamp)
            points.append(point)

        return points

    def _create_point_from_sensor(self, sensor_data: dict[str, Any], timestamp: datetime) -> Point:
        """Create a single InfluxDB Point from sensor data."""
        point = (
            Point("sports_data")
            .tag("entity_id", sensor_data["entity_id"])
            .tag("sport", sensor_data.get("sport", ""))
            .tag("league", sensor_data.get("league", ""))
            .tag("team_abbr", sensor_data.get("team_abbr", ""))
            .tag("team_id", str(sensor_data.get("team_id", "")))
            .tag("state", sensor_data["state"])
            .time(timestamp)
        )

        team_score = self._safe_int(sensor_data.get("team_score"))
        if team_score is not None:
            point = point.field("team_score", team_score)
        opponent_score = self._safe_int(sensor_data.get("opponent_score"))
        if opponent_score is not None:
            point = point.field("opponent_score", opponent_score)

        point = self._add_optional_fields(point, sensor_data)

        return point

    def _safe_int(self, value: Any) -> int | None:
        """Safely convert value to int, returning None if conversion fails."""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    def _add_game_state_fields(self, point: Point, sensor_data: dict[str, Any]) -> Point:
        """Add game state fields (quarter, clock, opponent) to InfluxDB Point."""
        if sensor_data.get("quarter"):
            point = point.field("quarter", str(sensor_data["quarter"]))
        if sensor_data.get("clock"):
            point = point.field("clock", str(sensor_data["clock"]))
        if sensor_data.get("opponent_abbr"):
            point = point.tag("opponent_abbr", sensor_data["opponent_abbr"])
        if sensor_data.get("opponent_id"):
            point = point.tag("opponent_id", str(sensor_data["opponent_id"]))
        if sensor_data.get("venue"):
            point = point.tag("venue", sensor_data["venue"])
        return point

    def _add_team_colors(self, point: Point, team_colors: list) -> Point:
        """Add team color fields (primary and secondary hex values) to InfluxDB Point."""
        if not team_colors or not isinstance(team_colors, list):
            return point
        point = point.field("team_color_primary", team_colors[0])
        if len(team_colors) >= 2:
            point = point.field("team_color_secondary", team_colors[1])
        return point

    def _add_automation_fields(self, point: Point, sensor_data: dict[str, Any]) -> Point:
        """Add automation-relevant fields (colors, winner, events) to InfluxDB Point."""
        if sensor_data.get("team_homeaway"):
            point = point.tag("team_homeaway", sensor_data["team_homeaway"])

        point = self._add_team_colors(point, sensor_data.get("team_colors", []))

        team_winner = sensor_data.get("team_winner")
        if team_winner is not None:
            point = point.field("team_winner", str(team_winner).lower())

        opponent_winner = sensor_data.get("opponent_winner")
        if opponent_winner is not None:
            point = point.field("opponent_winner", str(opponent_winner).lower())

        if sensor_data.get("event_name"):
            point = point.field("event_name", sensor_data["event_name"])

        if sensor_data.get("last_play"):
            point = point.field("last_play", sensor_data["last_play"])

        return point

    def _add_optional_fields(self, point: Point, sensor_data: dict[str, Any]) -> Point:
        """Add optional game state and automation fields to InfluxDB Point."""
        point = self._add_game_state_fields(point, sensor_data)
        return self._add_automation_fields(point, sensor_data)

    async def _write_points_with_retry(self, points: list[Point]) -> None:
        """Write points to InfluxDB with retry logic and DNS fallback."""
        for attempt in range(1, self.max_influx_retries + 1):
            try:
                await asyncio.to_thread(self.influxdb_client.write, points)
                self._record_successful_write(len(points))
                logger.info(f"Sports data written to InfluxDB ({len(points)} points)")
                return
            except Exception as e:
                self.last_influx_write_error = str(e)
                should_stop = await self._handle_write_error(attempt, e)
                if should_stop:
                    return

    async def _handle_write_error(self, attempt: int, error: Exception) -> bool:
        """Handle a write error, returning True if retries should stop."""
        error_str = str(error)
        is_final_attempt = attempt >= self.max_influx_retries

        if self._is_dns_error(error_str):
            await self._handle_dns_error(attempt, error)
            if is_final_attempt:
                self._record_failed_write()
                return True
            return False

        if is_final_attempt:
            self._record_failed_write()
            logger.error(f"Failed to write to InfluxDB after {attempt} attempts: {error}")
            return True

        backoff = 2 ** (attempt - 1)
        logger.warning(
            f"InfluxDB write failed (attempt {attempt}/{self.max_influx_retries}). Retrying in {backoff}s"
        )
        await asyncio.sleep(backoff)
        return False

    def _is_dns_error(self, error_str: str) -> bool:
        """Check if error is a DNS resolution error."""
        return "Name does not resolve" in error_str or "Failed to resolve" in error_str

    async def _handle_dns_error(self, attempt: int, _error: Exception) -> None:
        """Handle DNS resolution error by attempting to reconnect."""
        logger.warning(
            f"DNS resolution failed (attempt {attempt}/{self.max_influx_retries}), attempting to reconnect..."
        )
        self.influxdb_client = await self._initialize_influxdb()

    def _record_successful_write(self, point_count: int) -> None:
        """Record successful InfluxDB write metrics."""
        self.last_influx_write = datetime.now(UTC)
        self.last_influx_write_error = None
        self.influx_write_success_count += 1
        self.sensors_processed += point_count

    def _record_failed_write(self) -> None:
        """Record failed InfluxDB write metrics."""
        self.influx_write_failure_count += 1

    async def get_current_sports_data(self) -> list[dict[str, Any]]:
        """Fetch, parse, cache and store current Team Tracker sensor data."""
        sensors = await self.fetch_team_tracker_sensors()

        if not sensors:
            return self.cached_sensors or []

        parsed_sensors = [self.parse_sensor_data(sensor) for sensor in sensors]

        self.cached_sensors = parsed_sensors
        self.cache_time = datetime.now(UTC)
        self.last_successful_fetch = self.cache_time
        self.fetch_count += 1

        await self.store_in_influxdb(parsed_sensors)

        return parsed_sensors

    async def run_continuous(self) -> None:
        """Background fetch loop with exponential backoff and jitter on errors."""
        logger.info(f"Starting continuous fetch (every {self.poll_interval}s)")
        consecutive_errors = 0

        while True:
            try:
                await self.get_current_sports_data()
                consecutive_errors = 0
                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                logger.info("Continuous fetch loop cancelled")
                raise
            except Exception as e:
                consecutive_errors += 1
                self.last_background_error = str(e)
                logger.error(f"Error in continuous loop: {e}")
                backoff = min(300, (2**consecutive_errors) + random.uniform(0, 1))  # noqa: S311
                await asyncio.sleep(backoff)

    def start_background_task(self) -> asyncio.Task:
        """Start the guarded background fetch task, reusing existing if active."""
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
        """Stop background task gracefully, cancelling and awaiting completion."""
        if self.background_task and not self.background_task.done():
            self.background_task.cancel()
            with suppress(asyncio.CancelledError):
                await self.background_task
        self.background_task = None


sports_service: SportsService | None = None
_READY_START = time.monotonic()

router = APIRouter(tags=["sports"])


@router.get("/")
@with_adapter_timeout(NAME, ADAPTER_TIMEOUT_SECONDS)
async def root() -> dict[str, Any]:
    """Root endpoint providing sports adapter information."""
    return {
        "service": SERVICE_NAME,
        "version": "1.0.0",
        "status": "running",
        "endpoints": ["/health", "/sports-data", "/stats"],
    }


@router.get("/sports-data", response_model=SportsDataResponse)
@with_adapter_timeout(NAME, ADAPTER_TIMEOUT_SECONDS)
async def get_sports_data(_api_key: str = Depends(verify_api_key)) -> SportsDataResponse:
    """Get current sports data from cached Team Tracker sensors."""
    if not sports_service:
        raise HTTPException(status_code=503, detail="Adapter not initialized")

    if not rate_limiter.is_allowed("sports-data"):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    sensors = sports_service.cached_sensors or []

    return SportsDataResponse(
        sensors=sensors,
        count=len(sensors),
        last_update=sports_service.last_successful_fetch.isoformat()
        if sports_service.last_successful_fetch
        else None,
    )


@router.get("/stats")
@with_adapter_timeout(NAME, ADAPTER_TIMEOUT_SECONDS)
async def stats(_api_key: str = Depends(verify_api_key)) -> dict[str, Any]:
    """Adapter statistics endpoint returning fetch counts, write metrics, and cache info."""
    if not sports_service:
        raise HTTPException(status_code=503, detail="Adapter not initialized")

    return {
        "fetch_count": sports_service.fetch_count,
        "sensors_processed": sports_service.sensors_processed,
        "influx_write_success": sports_service.influx_write_success_count,
        "influx_write_failures": sports_service.influx_write_failure_count,
        "last_successful_fetch": sports_service.last_successful_fetch.isoformat()
        if sports_service.last_successful_fetch
        else None,
        "last_influx_write": sports_service.last_influx_write.isoformat()
        if sports_service.last_influx_write
        else None,
        "poll_interval_seconds": sports_service.poll_interval,
        "cached_sensors_count": len(sports_service.cached_sensors)
        if sports_service.cached_sensors
        else 0,
    }


async def _check_recent_fetch() -> dict[str, Any]:
    if sports_service is None:
        return {"ok": False, "reason": "service not started"}
    last = sports_service.last_successful_fetch
    interval = max(getattr(sports_service, "poll_interval", 60) * 2, 300)
    if last is None:
        in_grace = (time.monotonic() - _READY_START) <= max(interval, 300)
        return {"ok": in_grace, "last_successful_fetch": None, "startup_grace": in_grace}
    age = (datetime.now(UTC) - last).total_seconds()
    return {"ok": age <= interval * 2, "last_successful_fetch_age_s": round(age)}


class SportsAdapter(CollectorAdapter):
    """Adapter wrapping the former sports-api service."""

    name = NAME

    @property
    def router(self) -> APIRouter:
        return router

    async def startup(self) -> None:
        global sports_service
        service = SportsService()
        await service.startup()
        service.start_background_task()
        sports_service = service

    async def shutdown(self) -> None:
        global sports_service
        if sports_service:
            await sports_service.shutdown()
            sports_service = None

    def register_health(self, health: StandardHealthCheck) -> None:
        health.register_check(f"{NAME}_recent_fetch", _check_recent_fetch)


adapter = SportsAdapter()
