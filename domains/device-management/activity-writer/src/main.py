"""
Activity Writer Service - Epic Activity Recognition Integration Phase 1

Periodically fetches state_changed events, builds feature windows,
calls activity-recognition for prediction, and writes results to InfluxDB.
"""

from __future__ import annotations

import ast
import asyncio
import os
import re
from contextlib import suppress
from datetime import UTC, datetime
from typing import Any

import aiohttp
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from homeiq_observability.logging_config import setup_logging
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from . import __version__

load_dotenv()

SERVICE_NAME = "activity-writer"
SERVICE_VERSION = __version__

logger = setup_logging(SERVICE_NAME)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class SensorReading(BaseModel):
    """Single 1-min bucket feature vector."""

    motion: float = 0.0  # binary_sensor.motion* on=1
    door: float = 0.0  # binary_sensor.door* on=1
    temperature: float = 20.0  # avg of climate/sensor.temp
    humidity: float = 50.0  # avg
    power: float = 0.0  # sum


class PredictResponse(BaseModel):
    """Activity recognition predict response."""

    activity: str
    activity_id: int
    confidence: float
    probabilities: dict[str, float] | None = None


# ---------------------------------------------------------------------------
# Activity Writer Service
# ---------------------------------------------------------------------------


class ActivityWriterService:
    """Fetches events, builds windows, calls activity-recognition, writes to InfluxDB."""

    def __init__(self) -> None:
        self.interval_seconds = int(os.getenv("ACTIVITY_WRITER_INTERVAL_SECONDS", "300"))  # 5 min default
        self.data_api_url = os.getenv("DATA_API_URL", "http://data-api:8006")
        self.data_api_key = os.getenv("DATA_API_API_KEY") or os.getenv("DATA_API_KEY") or os.getenv("API_KEY")
        self.activity_recognition_url = os.getenv(
            "ACTIVITY_RECOGNITION_URL", "http://activity-recognition:8036"
        )
        self.activity_recognition_timeout = int(os.getenv("ACTIVITY_RECOGNITION_TIMEOUT", "30"))
        self.home_id = os.getenv("HOME_ID", "default")
        self.events_limit = int(os.getenv("ACTIVITY_WRITER_EVENTS_LIMIT", "500"))
        self.min_readings = 10

        # InfluxDB (v2 client)
        self.influxdb_url = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
        self.influxdb_token = os.getenv("INFLUXDB_TOKEN")
        self.influxdb_org = os.getenv("INFLUXDB_ORG", "homeiq")
        self.influxdb_bucket = os.getenv("INFLUXDB_BUCKET", "home_assistant_events")

        self._influx_client: InfluxDBClient | None = None
        self._session: aiohttp.ClientSession | None = None
        self._background_task: asyncio.Task | None = None

        # Metrics
        self.last_successful_run: datetime | None = None
        self.last_error: str | None = None
        self.cycles_succeeded = 0
        self.cycles_failed = 0

    async def startup(self) -> None:
        """Initialize clients and start background scheduler."""
        logger.info("Starting Activity Writer Service...")
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        if self.influxdb_token:
            self._influx_client = InfluxDBClient(
                url=self.influxdb_url,
                token=self.influxdb_token,
                org=self.influxdb_org,
                timeout=30_000,
            )
        else:
            logger.warning("INFLUXDB_TOKEN not set - InfluxDB writes disabled")
        self._background_task = asyncio.create_task(
            self._run_loop(),
            name="activity-writer-loop",
        )
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
        """Single cycle: fetch events -> build windows -> predict -> write."""
        # 1. Fetch state_changed events (try data-api, fallback to InfluxDB)
        events = await self._fetch_events()
        if not events:
            logger.debug("No state_changed events - skipping cycle")
            return

        # 2. Build 1-min rolling windows with 5 features
        readings = self._build_readings(events)
        if len(readings) < self.min_readings:
            logger.debug("Insufficient readings (%d < %d) - skipping cycle", len(readings), self.min_readings)
            return

        # 3. POST to activity-recognition
        try:
            prediction = await self._call_activity_recognition(readings)
        except (TimeoutError, aiohttp.ClientError) as e:
            logger.warning("Activity-recognition timeout/unavailable: %s - skipping cycle", e)
            return

        # 4. Write to InfluxDB
        await self._write_to_influxdb(prediction)
        self.last_successful_run = datetime.now(UTC)
        self.last_error = None
        self.cycles_succeeded += 1
        logger.info(
            "Cycle complete: activity=%s confidence=%.2f",
            prediction.activity,
            prediction.confidence,
        )

    async def _fetch_events(self) -> list[dict[str, Any]]:
        """Fetch state_changed events. Prefer data-api when it has state; else InfluxDB for state_value."""
        events = await self._fetch_from_data_api()
        if events and self._events_have_state(events):
            return self._normalize_data_api_events(events)
        # Data-api lacks state_value or returned empty; use InfluxDB for full event data
        return await self._fetch_from_influxdb()

    async def _fetch_from_data_api(self) -> list[dict[str, Any]]:
        """Fetch events from data-api with auth."""
        if not self._session:
            return []
        url = f"{self.data_api_url.rstrip('/')}/api/v1/events"
        params = {"event_type": "state_changed", "limit": self.events_limit}
        headers = {}
        if self.data_api_key:
            headers["Authorization"] = f"Bearer {self.data_api_key}"
        try:
            async with self._session.get(url, params=params, headers=headers or None) as resp:
                if resp.status != 200:
                    logger.warning("Data-API returned %d", resp.status)
                    return []
                data = await resp.json()
                if isinstance(data, list):
                    return [e if isinstance(e, dict) else e.model_dump() if hasattr(e, "model_dump") else {} for e in data]
                return []
        except Exception as e:
            logger.debug("Data-API fetch failed: %s", e)
            return []

    def _events_have_state(self, events: list[dict[str, Any]]) -> bool:
        """Check if events contain state info for feature extraction."""
        return any(e.get("new_state") or e.get("state_value") for e in events[:10])

    def _normalize_data_api_events(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Normalize data-api EventData to our internal format."""
        out: list[dict[str, Any]] = []
        for e in events:
            ns = e.get("new_state")
            state_value = e.get("state_value")
            if ns is not None and state_value is None:
                state_value = str(ns) if isinstance(ns, dict) else str(ns)
            ts = self._parse_event_timestamp(e.get("timestamp"))
            if ts is None:
                continue
            out.append({
                "entity_id": str(e.get("entity_id", "")),
                "timestamp": ts,
                "state_value": state_value,
                "event_type": e.get("event_type", "state_changed"),
            })
        return out

    async def _fetch_from_influxdb(self) -> list[dict[str, Any]]:
        """Query InfluxDB directly for state_changed events with state_value."""
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
            # Group by (entity_id, _time) - each event can have multiple field records
            by_key: dict[tuple[str, str], dict[str, Any]] = {}
            for table in result:
                for record in table.records:
                    entity_id = str(record.values.get("entity_id", ""))
                    if not entity_id:
                        continue
                    t = record.get_time()
                    key = (entity_id, t.isoformat())
                    if key not in by_key:
                        by_key[key] = {"entity_id": entity_id, "timestamp": t, "state_value": None}
                    value = record.values.get("_value")
                    field_name = record.values.get("_field")
                    if field_name == "state_value" and value:
                        by_key[key]["state_value"] = str(value)
            return list(by_key.values())
        except Exception as e:
            logger.warning("InfluxDB query failed: %s", e)
            return []

    def _parse_state_from_value(self, state_value: str | None) -> tuple[str | None, float | None, float | None, float | None]:
        """Parse state_value string to extract state, temp, humidity, power."""
        if not state_value:
            return None, None, None, None
        state_str = None
        temp = None
        humidity = None
        power = None
        with suppress(Exception):
            obj = ast.literal_eval(state_value)
            if isinstance(obj, dict):
                state_str = str(obj.get("state", ""))
                attrs = obj.get("attributes") or {}
                if isinstance(attrs, dict):
                    t = attrs.get("temperature") or attrs.get("value")
                    if t is not None:
                        with suppress(TypeError, ValueError):
                            temp = float(t)
                    h = attrs.get("humidity")
                    if h is not None:
                        with suppress(TypeError, ValueError):
                            humidity = float(h)
                    p = attrs.get("power") or attrs.get("current_power_w")
                    if p is not None:
                        with suppress(TypeError, ValueError):
                            power = float(p)
        return state_str, temp, humidity, power

    def _parse_event_timestamp(self, ts: Any) -> datetime | None:
        """Parse event timestamp to datetime or None if invalid."""
        if ts is None:
            return None
        if isinstance(ts, str):
            with suppress(ValueError):
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return None
        if hasattr(ts, "timestamp"):
            return ts
        return None

    def _apply_event_to_bucket(
        self,
        b: dict[str, Any],
        entity_id: str,
        state_str: str | None,
        temp: float | None,
        humidity: float | None,
        power: float | None,
    ) -> None:
        """Classify entity and update bucket features."""
        ent = entity_id.lower()
        on_states = {"on", "1", "true"}
        is_on = (state_str or "").lower() in on_states

        def safe_float(s: str | None) -> float | None:
            if not s:
                return None
            digits = s.replace(".", "", 1).replace("-", "", 1).replace(" ", "")
            if not digits.isdigit():
                return None
            with suppress(ValueError):
                return float(s)
            return None

        if "binary_sensor.motion" in ent or re.match(r"binary_sensor\.motion[\w_]*", ent):
            b["motion"] = 1.0 if is_on else max(b["motion"], 0.0)
        elif "binary_sensor.door" in ent or re.match(r"binary_sensor\.door[\w_]*", ent):
            b["door"] = 1.0 if is_on else max(b["door"], 0.0)
        elif "temperature" in ent or ent.startswith("climate."):
            if temp is not None:
                b["temps"].append(temp)
            elif (val := safe_float(state_str)) is not None:
                b["temps"].append(val)
        elif "humidity" in ent and "sensor." in ent:
            if humidity is not None:
                b["humidities"].append(humidity)
            elif (val := safe_float(state_str)) is not None:
                b["humidities"].append(val)
        elif "power" in ent and "sensor." in ent:
            if power is not None:
                b["powers"].append(power)
            elif (val := safe_float(state_str)) is not None:
                b["powers"].append(val)

    def _build_readings(self, events: list[dict[str, Any]]) -> list[SensorReading]:
        """Build 1-min buckets and extract 5 features per bucket."""
        buckets: dict[int, dict[str, Any]] = {}

        for ev in events:
            ts = self._parse_event_timestamp(ev.get("timestamp"))
            if ts is None:
                continue
            bucket_key = int(ts.timestamp()) // 60
            if bucket_key not in buckets:
                buckets[bucket_key] = {
                    "motion": 0.0,
                    "door": 0.0,
                    "temps": [],
                    "humidities": [],
                    "powers": [],
                }
            b = buckets[bucket_key]
            entity_id = str(ev.get("entity_id", ""))
            state_value = ev.get("state_value")
            state_str, temp, humidity, power = self._parse_state_from_value(state_value)
            self._apply_event_to_bucket(b, entity_id, state_str, temp, humidity, power)

        # Convert buckets to SensorReading list, sorted by time
        readings: list[SensorReading] = []
        for k in sorted(buckets.keys()):
            b = buckets[k]
            temp_avg = sum(b["temps"]) / len(b["temps"]) if b["temps"] else 20.0
            # HA may report in Fahrenheit - convert to Celsius if above 56°C (133°F)
            # threshold: any reading >56°C is almost certainly Fahrenheit
            if temp_avg > 56:
                temp_avg = (temp_avg - 32) * 5 / 9
            hum_avg = sum(b["humidities"]) / len(b["humidities"]) if b["humidities"] else 50.0
            power_sum = sum(b["powers"])
            readings.append(
                SensorReading(
                    motion=b["motion"],
                    door=b["door"],
                    temperature=temp_avg,
                    humidity=hum_avg,
                    power=power_sum,
                )
            )
        return readings

    # Activity-recognition ONNX model expects exactly 30 timesteps
    MAX_READINGS = 30

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
        # Truncate to most recent MAX_READINGS (model window limit)
        if len(readings) > self.MAX_READINGS:
            readings = readings[-self.MAX_READINGS:]
        url = f"{self.activity_recognition_url.rstrip('/')}/api/v1/predict"
        payload = {
            "readings": [
                {"motion": r.motion, "door": r.door, "temperature": r.temperature, "humidity": r.humidity, "power": r.power}
                for r in readings
            ]
        }
        async with self._session.post(
            url,
            json=payload,
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
            write_api.write,
            bucket=self.influxdb_bucket,
            org=self.influxdb_org,
            record=point,
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


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

activity_writer: ActivityWriterService | None = None


async def startup() -> None:
    global activity_writer
    activity_writer = ActivityWriterService()
    await activity_writer.startup()


async def shutdown() -> None:
    if activity_writer:
        await activity_writer.shutdown()


app = FastAPI(
    title="Activity Writer Service",
    description="Periodic activity recognition pipeline",
    version=SERVICE_VERSION,
)

cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

app.add_event_handler("startup", startup)
app.add_event_handler("shutdown", shutdown)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "status": "running",
        "endpoints": ["/health", "/metrics"],
    }


@app.get("/health")
async def health() -> JSONResponse:
    if not activity_writer:
        raise HTTPException(status_code=503, detail="Service not initialized")
    healthy = activity_writer.cycles_failed == 0 or activity_writer.last_successful_run is not None
    status = "healthy" if healthy else "degraded"
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={
            "status": status,
            "service": SERVICE_NAME,
            "version": SERVICE_VERSION,
            **activity_writer.get_metrics(),
        },
    )


@app.get("/metrics")
async def metrics() -> dict[str, Any]:
    if not activity_writer:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return activity_writer.get_metrics()


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("SERVICE_PORT", "8035"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")  # noqa: S104
