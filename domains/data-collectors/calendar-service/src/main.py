"""Calendar Service Main Entry Point.

Integrates with Home Assistant Calendar for occupancy prediction. Fetches calendar
events, predicts home occupancy status with confidence scoring, and stores
predictions as time-series data in InfluxDB.

Converted from aiohttp to FastAPI with homeiq-resilience shared library pattern.
"""

import asyncio
import contextlib
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import uvicorn
from aiohttp import ClientError
from config import settings
from event_parser import CalendarEventParser
from ha_client import HomeAssistantCalendarClient
from health_check import HealthCheckState
from homeiq_ha.enhanced_ha_connection_manager import ha_connection_manager
from homeiq_observability.logging_config import log_error_with_context, setup_logging
from homeiq_resilience import ServiceLifespan, StandardHealthCheck, create_app
from influxdb_client_3 import InfluxDBClient3, Point

logger = setup_logging("calendar-service")


class CalendarService:
    """Home Assistant Calendar integration for occupancy prediction."""

    def __init__(self) -> None:
        """Initialize the calendar service with HA connection and InfluxDB settings."""
        # Calendar configuration
        self.calendar_entities = settings.calendar_entities.split(',')

        # InfluxDB configuration
        self.influxdb_url = settings.influxdb_url
        self.influxdb_token = (
            settings.influxdb_token.get_secret_value()
            if settings.influxdb_token
            else ""
        )
        self.influxdb_org = settings.influxdb_org
        self.influxdb_bucket = settings.influxdb_bucket

        # Service configuration
        self.fetch_interval = settings.calendar_fetch_interval

        # Components
        self.ha_client: HomeAssistantCalendarClient | None = None
        self.event_parser = CalendarEventParser()
        self.influxdb_client: InfluxDBClient3 | None = None
        self.health_state = HealthCheckState()

        # Validate InfluxDB configuration
        if not self.influxdb_token:
            raise ValueError("INFLUXDB_TOKEN required (set via environment variable)")

        # Clean up calendar entity list
        self.calendar_entities = [cal.strip() for cal in self.calendar_entities]
        logger.info(
            "Configured for %d calendar(s): %s",
            len(self.calendar_entities),
            self.calendar_entities,
        )

    async def startup(self) -> None:
        """Initialize the calendar service, connecting to Home Assistant and InfluxDB."""
        logger.info("Initializing Calendar Service (Home Assistant Integration)...")

        # Get HA connection using the enhanced connection manager with circuit breaker
        connection_config = await ha_connection_manager.get_connection_with_circuit_breaker()

        if not connection_config:
            logger.error("No Home Assistant connections available")
            self.health_state.ha_connected = False
            raise ConnectionError(
                "No Home Assistant connections available. Configure "
                "HA_HTTP_URL/HA_WS_URL + HA_TOKEN or NABU_CASA_URL + NABU_CASA_TOKEN"
            )

        logger.info("Using HA connection: %s (%s)", connection_config.name, connection_config.url)

        # Convert WebSocket URL to HTTP URL for calendar client
        http_url = connection_config.url.replace('ws://', 'http://').replace('wss://', 'https://')
        if http_url.endswith('/api/websocket'):
            http_url = http_url.replace('/api/websocket', '')

        # Initialize Home Assistant client
        self.ha_client = HomeAssistantCalendarClient(
            base_url=http_url,
            token=connection_config.token,
        )

        await self.ha_client.connect()

        # Test connection
        connection_ok = await self.ha_client.test_connection()
        if not connection_ok:
            logger.error("Failed to connect to Home Assistant")
            self.health_state.ha_connected = False
            raise ConnectionError(f"Cannot connect to Home Assistant at {http_url}")

        self.health_state.ha_connected = True

        # Discover available calendars
        available_calendars = await self.ha_client.get_calendars()
        logger.info(
            "Found %d calendar(s) in Home Assistant: %s",
            len(available_calendars),
            available_calendars,
        )

        # Validate configured calendars exist
        for calendar_id in self.calendar_entities:
            if calendar_id not in available_calendars and f"calendar.{calendar_id}" not in available_calendars:
                logger.warning("Configured calendar '%s' not found in Home Assistant", calendar_id)

        self.health_state.calendar_count = len(self.calendar_entities)
        self.health_state.calendars_discovered = len(available_calendars)

        # Create InfluxDB client
        influxdb_url = self.influxdb_url
        parsed_url = urlparse(influxdb_url)
        if not parsed_url.scheme:
            influxdb_url = f"http://{influxdb_url}:8086"
        self.influxdb_client = InfluxDBClient3(
            host=influxdb_url,
            token=self.influxdb_token,
            database=self.influxdb_bucket,
            org=self.influxdb_org,
        )

        logger.info("Calendar Service initialized successfully")

    async def shutdown(self) -> None:
        """Shutdown service, closing HA and InfluxDB connections."""
        logger.info("Shutting down Calendar Service...")

        if self.ha_client:
            await self.ha_client.close()

        if self.influxdb_client:
            self.influxdb_client.close()

    async def get_today_events(self) -> list[dict[str, Any]]:
        """Fetch today's calendar events from all configured Home Assistant calendars.

        Returns:
            List of parsed and enriched calendar event dictionaries, sorted by start time.
        """
        try:
            # Define time range (today in local timezone)
            local_tz = ZoneInfo(settings.timezone)
            now = datetime.now(UTC)
            now_local = datetime.now(local_tz)
            end_of_day = now_local.replace(hour=23, minute=59, second=59, microsecond=999999)

            # Fetch events from all configured calendars
            all_events_raw = await self.ha_client.get_events_from_multiple_calendars(
                calendar_ids=self.calendar_entities,
                start=now,
                end=end_of_day,
            )

            # Combine events from all calendars with source tagging
            combined_events = [
                {**event, 'calendar_source': calendar_id}
                for calendar_id, events in all_events_raw.items()
                for event in events
            ]

            logger.info(
                "Fetched %d events from %d calendar(s)",
                len(combined_events),
                len(self.calendar_entities),
            )

            # Parse and enrich events
            parsed_events = self.event_parser.parse_multiple_events(combined_events)

            # Sort by start time
            parsed_events.sort(key=lambda e: e['start'] if e.get('start') else now)

            self.health_state.last_successful_fetch = datetime.now(UTC)
            self.health_state.total_fetches += 1

            return parsed_events

        except (ClientError, ConnectionError, TimeoutError) as e:
            log_error_with_context(
                logger,
                f"Network error fetching calendar events: {e}",
                service="calendar-service",
                error=str(e),
            )
            self.health_state.ha_connected = False
            self.health_state.failed_fetches += 1
            return []
        except Exception as e:
            log_error_with_context(
                logger,
                f"Error fetching calendar events: {e}",
                service="calendar-service",
                error=str(e),
            )
            self.health_state.failed_fetches += 1
            logger.debug("Exception context: %s: %s", type(e).__name__, e, exc_info=True)
            return []

    def _calculate_arrival_info(
        self, next_home_event: dict[str, Any] | None, now: datetime, wfh_today: bool,
    ) -> tuple[datetime | None, datetime | None, float | None, float]:
        """Calculate arrival time, prepare time, and confidence from the next home event."""
        if next_home_event:
            arrival_time = next_home_event['start']
            travel_time = timedelta(minutes=settings.default_travel_time_minutes)
            prepare_time = arrival_time - travel_time
            hours_until_arrival = (arrival_time - now).total_seconds() / 3600
            confidence = next_home_event.get('confidence', 0.75)
        else:
            arrival_time = None
            prepare_time = None
            hours_until_arrival = None
            confidence = 0.85 if wfh_today else 0.70
        return arrival_time, prepare_time, hours_until_arrival, confidence

    def _adjust_confidence(
        self,
        confidence: float,
        wfh_today: bool,
        currently_home: bool,
        current_events: list[dict[str, Any]],
    ) -> float:
        """Adjust occupancy confidence based on multiple contextual factors."""
        if wfh_today and currently_home:
            confidence = max(confidence, 0.90)
        elif currently_home and current_events:
            confidence = max(confidence, 0.85)
        return confidence

    async def predict_home_status(self) -> dict[str, Any] | None:
        """Predict home occupancy based on calendar events."""
        try:
            events = await self.get_today_events()
            now = datetime.now(UTC)

            if not events:
                logger.info("No calendar events found, assuming default status")
                return {
                    'currently_home': False,
                    'wfh_today': False,
                    'next_arrival': None,
                    'prepare_time': None,
                    'hours_until_arrival': None,
                    'confidence': 0.5,
                    'timestamp': datetime.now(UTC),
                    'event_count': 0,
                }

            wfh_today = any(e.get('is_wfh', False) for e in events)
            current_events = self.event_parser.get_current_events(events, now)
            currently_home = wfh_today or any(e.get('is_home', False) for e in current_events)
            future_events = self.event_parser.get_upcoming_events(events, now)
            next_home_event = next((e for e in future_events if e.get('is_home', False)), None)

            arrival_time, prepare_time, hours_until_arrival, confidence = (
                self._calculate_arrival_info(next_home_event, now, wfh_today)
            )
            confidence = self._adjust_confidence(confidence, wfh_today, currently_home, current_events)

            prediction = {
                'currently_home': currently_home,
                'wfh_today': wfh_today,
                'next_arrival': arrival_time,
                'prepare_time': prepare_time,
                'hours_until_arrival': hours_until_arrival,
                'confidence': confidence,
                'timestamp': datetime.now(UTC),
                'event_count': len(events),
                'current_event_count': len(current_events),
                'upcoming_event_count': len(future_events),
            }

            logger.info(
                "Occupancy prediction: Home=%s, WFH=%s, Events=%d, Confidence=%.2f",
                currently_home,
                wfh_today,
                len(events),
                confidence,
            )

            return prediction

        except (ClientError, ConnectionError, TimeoutError) as e:
            log_error_with_context(
                logger,
                f"Network error predicting occupancy: {e}",
                service="calendar-service",
                error=str(e),
            )
            self.health_state.failed_fetches += 1
            return None
        except Exception as e:
            log_error_with_context(
                logger,
                f"Error predicting occupancy: {e}",
                service="calendar-service",
                error=str(e),
            )
            self.health_state.failed_fetches += 1
            logger.debug("Exception context: %s: %s", type(e).__name__, e, exc_info=True)
            return None

    async def store_in_influxdb(self, prediction: dict[str, Any]) -> None:
        """Store occupancy prediction in InfluxDB as a time-series data point."""
        if not prediction:
            return

        if not self.influxdb_client:
            logger.error("InfluxDB client not initialized")
            return

        try:
            point = (
                Point("occupancy_prediction")
                .tag("source", "calendar")
                .tag("user", "primary")
                .field("currently_home", bool(prediction['currently_home']))
                .field("wfh_today", bool(prediction['wfh_today']))
                .field("confidence", float(prediction['confidence']))
                .field(
                    "hours_until_arrival",
                    float(prediction['hours_until_arrival'])
                    if prediction['hours_until_arrival'] is not None
                    else -1.0,
                )
                .field("event_count", int(prediction.get('event_count', 0)))
                .field("current_event_count", int(prediction.get('current_event_count', 0)))
                .field("upcoming_event_count", int(prediction.get('upcoming_event_count', 0)))
                .time(prediction['timestamp'])
            )

            await asyncio.to_thread(self.influxdb_client.write, point)

            logger.info("Occupancy prediction written to InfluxDB")

        except Exception as e:
            log_error_with_context(
                logger,
                f"Error writing to InfluxDB: {e}",
                service="calendar-service",
                error=str(e),
            )
            raise RuntimeError(f"Failed to write occupancy prediction to InfluxDB: {e}") from e

    async def run_continuous(self) -> None:
        """Run the continuous occupancy prediction loop."""
        logger.info("Starting continuous occupancy prediction (every %ds)", self.fetch_interval)

        while True:
            try:
                prediction = await self.predict_home_status()

                if prediction:
                    try:
                        await self.store_in_influxdb(prediction)
                    except Exception as e:
                        log_error_with_context(
                            logger,
                            f"Failed to store prediction in InfluxDB: {e}",
                            service="calendar-service",
                            error=str(e),
                        )
                        logger.debug("Exception context: %s: %s", type(e).__name__, e, exc_info=True)

                self.health_state.ha_connected = True
                await asyncio.sleep(self.fetch_interval)

            except Exception as e:
                log_error_with_context(
                    logger,
                    f"Error in continuous loop: {e}",
                    service="calendar-service",
                    error=str(e),
                )
                self.health_state.ha_connected = False
                logger.debug("Exception context: %s: %s", type(e).__name__, e, exc_info=True)
                await asyncio.sleep(300)


# ---------------------------------------------------------------------------
# Shared state
# ---------------------------------------------------------------------------

_service: CalendarService | None = None
_bg_task: asyncio.Task | None = None


# ---------------------------------------------------------------------------
# Lifespan hooks
# ---------------------------------------------------------------------------


async def _startup() -> None:
    global _service, _bg_task
    _service = CalendarService()
    await _service.startup()
    _bg_task = asyncio.create_task(_service.run_continuous())
    logger.info("Calendar Service started with background prediction loop")


async def _shutdown() -> None:
    global _bg_task
    if _bg_task:
        _bg_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _bg_task
    if _service:
        await _service.shutdown()
    logger.info("Calendar Service shut down")


lifespan = ServiceLifespan("calendar-service")
lifespan.on_startup(_startup, name="calendar-service-init")
lifespan.on_shutdown(_shutdown, name="calendar-service-cleanup")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


async def _check_ha_connected() -> bool:
    if _service is None:
        return False
    return await _service.health_state.check_ha_connected()


async def _check_calendars() -> bool:
    if _service is None:
        return True
    return await _service.health_state.check_calendars_discovered()


async def _check_recent_fetch() -> bool:
    if _service is None:
        return True
    return await _service.health_state.check_recent_fetch()


health = StandardHealthCheck(service_name="calendar-service", version="1.0.0")
health.register_check("ha-connection", _check_ha_connected)
health.register_check("calendars", _check_calendars)
health.register_check("recent-fetch", _check_recent_fetch)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = create_app(
    title="Calendar Service",
    version="1.0.0",
    description="Home Assistant Calendar integration for occupancy prediction",
    lifespan=lifespan.handler,
    health_check=health,
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/api/v1/prediction")
async def get_prediction() -> dict[str, Any]:
    """Get the latest occupancy prediction."""
    if _service is None:
        return {"error": "Service not initialized"}
    prediction = await _service.predict_home_status()
    if prediction is None:
        return {"error": "Failed to generate prediction"}
    # Serialize datetime fields for JSON
    result = dict(prediction)
    for key in ('next_arrival', 'prepare_time', 'timestamp'):
        if result.get(key) and isinstance(result[key], datetime):
            result[key] = result[key].isoformat()
    return result


@app.get("/api/v1/events")
async def get_events() -> dict[str, Any]:
    """Get today's calendar events."""
    if _service is None:
        return {"error": "Service not initialized", "events": []}
    events = await _service.get_today_events()
    # Serialize datetime fields
    serialized = []
    for event in events:
        entry = dict(event)
        for key in ('start', 'end'):
            if entry.get(key) and isinstance(entry[key], datetime):
                entry[key] = entry[key].isoformat()
        entry.pop('raw_event', None)
        serialized.append(entry)
    return {"events": serialized, "count": len(serialized)}


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",  # noqa: S104
        port=settings.service_port,
        log_level=settings.log_level.lower(),
    )
