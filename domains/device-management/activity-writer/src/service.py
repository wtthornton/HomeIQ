"""Core ActivityWriterService — orchestrates event cycle, prediction, and InfluxDB writes."""

from __future__ import annotations

import asyncio
import os
from contextlib import suppress
from datetime import UTC, datetime
from typing import Any

import aiohttp
from homeiq_observability.logging_config import setup_logging
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .bucket_builder import build_readings
from .data_fetcher import (
    events_have_state,
    fetch_from_data_api,
    group_influx_records,
    normalize_data_api_events,
)
from .models import PredictResponse, SensorReading

logger = setup_logging("activity-writer")


class ActivityWriterService:
    """Fetches events, builds windows, calls activity-recognition, writes to InfluxDB."""

    MAX_READINGS: int = 30

    def __init__(self) -> None:
        self.interval_seconds: int = int(os.getenv("ACTIVITY_WRITER_INTERVAL_SECONDS", "300"))
        self.data_api_url: str = os.getenv("DATA_API_URL", "http://data-api:8006")
        self.data_api_key: str | None = (
            os.getenv("DATA_API_API_KEY") or os.getenv("DATA_API_KEY") or os.getenv("API_KEY")
        )
        self.activity_recognition_url: str = os.getenv(
            "ACTIVITY_RECOGNITION_URL", "http://activity-recognition:8036",
        )
        self.activity_recognition_timeout: int = int(os.getenv("ACTIVITY_RECOGNITION_TIMEOUT", "30"))
        self.home_id: str = os.getenv("HOME_ID", "default")
        self.events_limit: int = int(os.getenv("ACTIVITY_WRITER_EVENTS_LIMIT", "500"))
        self.min_readings: int = 10

        self.influxdb_url: str = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
        self.influxdb_token: str | None = os.getenv("INFLUXDB_TOKEN")
        self.influxdb_org: str = os.getenv("INFLUXDB_ORG", "homeiq")
        self.influxdb_bucket: str = os.getenv("INFLUXDB_BUCKET", "home_assistant_events")

        self._influx_client: InfluxDBClient | None = None
        self._session: aiohttp.ClientSession | None = None
        self._background_task: asyncio.Task[None] | None = None

        self.last_successful_run: datetime | None = None
        self.last_error: str | None = None
        self.cycles_succeeded: int = 0
        self.cycles_failed: int = 0

    async def startup(self) -> None:
        """Initialize clients and start background scheduler."""
        logger.info("Starting Activity Writer Service...")
        self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        if self.influxdb_token:
            self._influx_client = InfluxDBClient(
                url=self.influxdb_url, token=self.influxdb_token,
                org=self.influxdb_org, timeout=30_000,
            )
        else:
            logger.warning("INFLUXDB_TOKEN not set - InfluxDB writes disabled")
        self._background_task = asyncio.create_task(self._run_loop(), name="activity-writer-loop")
        logger.info("Activity Writer Service started (interval=%ss)", self.interval_seconds)

    async def shutdown(self) -> None:
        """Stop background task and close clients."""
        if self._background_task and not self._background_task.done():
            self._background_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._background_task
        self._background_task = None
        if self._session and not self._session.closed:
            await self._session.close()
        if self._influx_client:
            self._influx_client.close()
            self._influx_client = None

    async def _run_loop(self) -> None:
        """Background loop: run cycle every interval."""
        while True:
            try:
                await self._run_cycle()
                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self.last_error = str(e)
                self.cycles_failed += 1
                logger.exception("Activity writer cycle failed: %s", e)
                await asyncio.sleep(min(60, self.interval_seconds))

    async def _run_cycle(self) -> None:
        """Single cycle: fetch -> build -> predict -> write."""
        events = await self._fetch_events()
        if not events:
            logger.debug("No state_changed events - skipping cycle")
            return
        readings = build_readings(events)
        if len(readings) < self.min_readings:
            logger.debug("Insufficient readings (%d < %d)", len(readings), self.min_readings)
            return
        try:
            prediction = await self._call_activity_recognition(readings)
        except (TimeoutError, aiohttp.ClientError) as e:
            logger.warning("Activity-recognition unavailable: %s", e)
            return
        await self._write_to_influxdb(prediction)
        self.last_successful_run = datetime.now(UTC)
        self.last_error = None
        self.cycles_succeeded += 1
        logger.info("Cycle complete: activity=%s confidence=%.2f", prediction.activity, prediction.confidence)

    async def _fetch_events(self) -> list[dict[str, Any]]:
        """Fetch state_changed events, preferring data-api over InfluxDB."""
        events = await fetch_from_data_api(
            self._session, self.data_api_url, self.data_api_key, self.events_limit,
        )
        if events and events_have_state(events):
            return normalize_data_api_events(events)
        return await self._fetch_from_influxdb()

    async def _fetch_from_influxdb(self) -> list[dict[str, Any]]:
        """Query InfluxDB for state_changed events."""
        if not self._influx_client or not self.influxdb_token:
            return []
        query_api = self._influx_client.query_api()
        query = f'''
        from(bucket: "{self.influxdb_bucket}")
          |> range(start: -2h)
          |> filter(fn: (r) => r._measurement == "home_assistant_events")
          |> filter(fn: (r) => r.event_type == "state_changed")
          |> filter(fn: (r) => r._field == "state_value" or r._field == "attributes")
          |> sort(columns: ["_time"], desc: false)
          |> limit(n: {self.events_limit})
        '''
        try:
            result = query_api.query(query)
            return group_influx_records(result)
        except Exception as e:
            logger.warning("InfluxDB query failed: %s", e)
            return []

    @retry(
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError, ConnectionError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _call_activity_recognition(self, readings: list[SensorReading]) -> PredictResponse:
        """POST to activity-recognition predict with tenacity retry."""
        if not self._session:
            raise RuntimeError("HTTP session not initialized")
        if len(readings) > self.MAX_READINGS:
            readings = readings[-self.MAX_READINGS:]
        url = f"{self.activity_recognition_url.rstrip('/')}/api/v1/predict"
        payload = {
            "readings": [
                {"motion": r.motion, "door": r.door, "temperature": r.temperature,
                 "humidity": r.humidity, "power": r.power}
                for r in readings
            ],
        }
        async with self._session.post(
            url, json=payload,
            timeout=aiohttp.ClientTimeout(total=self.activity_recognition_timeout),
        ) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise aiohttp.ClientError(f"Activity-recognition returned {resp.status}: {text[:200]}")
            data = await resp.json()
            return PredictResponse(
                activity=data.get("activity", "unknown"),
                activity_id=int(data.get("activity_id", 9)),
                confidence=float(data.get("confidence", 0.0)),
                probabilities=data.get("probabilities"),
            )

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _write_to_influxdb(self, prediction: PredictResponse) -> None:
        """Write activity point to InfluxDB with tenacity retry."""
        if not self._influx_client or not self.influxdb_token:
            logger.warning("InfluxDB client not available - skip write")
            return
        point = (
            Point("home_activity")
            .tag("home_id", self.home_id)
            .field("activity", prediction.activity)
            .field("activity_id", prediction.activity_id)
            .field("confidence", prediction.confidence)
            .time(datetime.now(UTC), WritePrecision.NS)
        )
        write_api = self._influx_client.write_api(write_options=SYNCHRONOUS)
        await asyncio.to_thread(
            write_api.write, bucket=self.influxdb_bucket,
            org=self.influxdb_org, record=point,
        )
        write_api.close()

    def get_metrics(self) -> dict[str, Any]:
        """Return health/metrics dict."""
        return {
            "last_successful_run": self.last_successful_run.isoformat() if self.last_successful_run else None,
            "last_error": self.last_error,
            "cycles_succeeded": self.cycles_succeeded,
            "cycles_failed": self.cycles_failed,
        }

    # Backward-compatible static methods for tests
    @staticmethod
    def _events_have_state(events: list[dict[str, Any]]) -> bool:
        return events_have_state(events)

    @staticmethod
    def _normalize_single_event(e: dict[str, Any]) -> dict[str, Any] | None:
        from .data_fetcher import normalize_single_event
        return normalize_single_event(e)

    @staticmethod
    def _normalize_data_api_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return normalize_data_api_events(events)

    @staticmethod
    def build_readings(events: list[dict[str, Any]]) -> list[SensorReading]:
        return build_readings(events)

    @staticmethod
    def _group_influx_records(result: Any) -> list[dict[str, Any]]:
        return group_influx_records(result)
