"""Unit tests for activity-writer main module."""

from datetime import UTC, datetime

import pytest
from src.main import SERVICE_NAME, SERVICE_VERSION, app
from src.service import ActivityWriterService
from src.helpers import (
    bucket_to_reading,
    classify_entity,
    parse_event_timestamp,
    parse_state_value,
    safe_float,
    try_float,
)


@pytest.fixture
def service() -> ActivityWriterService:
    """Create ActivityWriterService instance (no startup)."""
    return ActivityWriterService()


# ---------------------------------------------------------------------------
# _events_have_state (static method)
# ---------------------------------------------------------------------------


def test_events_have_state_empty() -> None:
    """Empty events returns False."""
    assert ActivityWriterService._events_have_state([]) is False


def test_events_have_state_no_state() -> None:
    """Events without state info return False."""
    events = [{"entity_id": "sensor.foo"}, {"event_type": "state_changed"}]
    assert ActivityWriterService._events_have_state(events) is False


def test_events_have_state_with_state_value() -> None:
    """Events with state_value return True."""
    events = [{"entity_id": "sensor.foo", "state_value": "{'state':'on'}"}]
    assert ActivityWriterService._events_have_state(events) is True


def test_events_have_state_with_new_state() -> None:
    """Events with new_state return True."""
    events = [{"entity_id": "sensor.foo", "new_state": {"state": "on"}}]
    assert ActivityWriterService._events_have_state(events) is True


# ---------------------------------------------------------------------------
# parse_state_value
# ---------------------------------------------------------------------------


def test_parse_state_from_value_none() -> None:
    """None state_value returns all None."""
    assert parse_state_value(None) == (None, None, None, None)


def test_parse_state_from_value_empty() -> None:
    """Empty string returns all None."""
    assert parse_state_value("") == (None, None, None, None)


def test_parse_state_from_value_valid_state() -> None:
    """Valid state_value dict extracts state."""
    s = "{'state': 'on', 'attributes': {}}"
    state, temp, hum, power = parse_state_value(s)
    assert state == "on"
    assert temp is None
    assert hum is None
    assert power is None


def test_parse_state_from_value_with_attrs() -> None:
    """state_value with attributes extracts temp, humidity, power."""
    s = "{'state': '21.5', 'attributes': {'temperature': 21.5, 'humidity': 45.0, 'power': 120.0}}"
    state, temp, hum, power = parse_state_value(s)
    assert state == "21.5"
    assert temp == 21.5
    assert hum == 45.0
    assert power == 120.0


def test_parse_state_from_value_invalid() -> None:
    """Invalid string returns all None."""
    assert parse_state_value("not valid python") == (None, None, None, None)


# ---------------------------------------------------------------------------
# parse_event_timestamp
# ---------------------------------------------------------------------------


def test_parse_event_timestamp_none() -> None:
    """None returns None."""
    assert parse_event_timestamp(None) is None


def test_parse_event_timestamp_str_valid() -> None:
    """ISO string returns datetime."""
    ts = parse_event_timestamp("2025-02-18T12:00:00Z")
    assert ts is not None
    assert hasattr(ts, "timestamp")


def test_parse_event_timestamp_str_invalid() -> None:
    """Invalid string returns None."""
    assert parse_event_timestamp("not-a-date") is None


def test_parse_event_timestamp_datetime() -> None:
    """Datetime object returns as-is."""
    dt = datetime.now(UTC)
    assert parse_event_timestamp(dt) is dt


# ---------------------------------------------------------------------------
# classify_entity
# ---------------------------------------------------------------------------


def test_classify_entity_motion() -> None:
    """Motion sensor classified correctly."""
    assert classify_entity("binary_sensor.motion_hall") == "motion"


def test_classify_entity_door() -> None:
    """Door sensor classified correctly."""
    assert classify_entity("binary_sensor.door_front") == "door"


def test_classify_entity_temperature() -> None:
    """Temperature sensor classified correctly."""
    assert classify_entity("sensor.temperature_living") == "temp"
    assert classify_entity("climate.living_room") == "temp"


def test_classify_entity_other() -> None:
    """Unrecognized entity classified as other."""
    assert classify_entity("light.office") == "other"


# ---------------------------------------------------------------------------
# build_readings
# ---------------------------------------------------------------------------


def test_build_readings_empty() -> None:
    """Empty events yields empty readings."""
    assert ActivityWriterService.build_readings([]) == []


def test_build_readings_motion() -> None:
    """Motion event sets motion=1.0 in bucket."""
    events = [
        {
            "entity_id": "binary_sensor.motion_living_room",
            "timestamp": "2025-02-18T12:00:30Z",
            "state_value": "{'state': 'on', 'attributes': {}}",
        }
    ]
    readings = ActivityWriterService.build_readings(events)
    assert len(readings) == 1
    assert readings[0].motion == 1.0


def test_build_readings_door() -> None:
    """Door event sets door=1.0 in bucket."""
    events = [
        {
            "entity_id": "binary_sensor.door_front",
            "timestamp": "2025-02-18T12:00:30Z",
            "state_value": "{'state': 'on', 'attributes': {}}",
        }
    ]
    readings = ActivityWriterService.build_readings(events)
    assert len(readings) == 1
    assert readings[0].door == 1.0


def test_build_readings_temperature_from_attrs() -> None:
    """Temperature from attributes populates bucket."""
    events = [
        {
            "entity_id": "climate.living_room",
            "timestamp": "2025-02-18T12:00:30Z",
            "state_value": "{'state': 'heat', 'attributes': {'temperature': 22.0}}",
        }
    ]
    readings = ActivityWriterService.build_readings(events)
    assert len(readings) == 1
    assert readings[0].temperature == 22.0


def test_build_readings_buckets_by_minute() -> None:
    """Events in same minute go to same bucket."""
    events = [
        {"entity_id": "binary_sensor.motion_1", "timestamp": "2025-02-18T12:00:10Z", "state_value": "{'state': 'on'}"},
        {"entity_id": "binary_sensor.door_1", "timestamp": "2025-02-18T12:00:50Z", "state_value": "{'state': 'on'}"},
    ]
    readings = ActivityWriterService.build_readings(events)
    assert len(readings) == 1
    assert readings[0].motion == 1.0
    assert readings[0].door == 1.0


# ---------------------------------------------------------------------------
# normalize events
# ---------------------------------------------------------------------------


def test_normalize_data_api_events_basic() -> None:
    """Normalize data-api events with new_state."""
    events = [
        {"entity_id": "sensor.temp", "new_state": {"state": "21.5"}, "timestamp": "2025-02-18T12:00:00Z"}
    ]
    out = ActivityWriterService._normalize_data_api_events(events)
    assert len(out) == 1
    assert out[0]["entity_id"] == "sensor.temp"
    assert out[0]["state_value"] is not None


def test_normalize_data_api_events_skips_no_timestamp() -> None:
    """Events without timestamp are skipped."""
    events = [{"entity_id": "sensor.foo", "timestamp": None}]
    assert ActivityWriterService._normalize_data_api_events(events) == []


def test_normalize_single_event_valid() -> None:
    """Valid event normalizes correctly."""
    ev = {"entity_id": "sensor.x", "new_state": "on", "timestamp": "2025-02-18T12:00:00Z"}
    result = ActivityWriterService._normalize_single_event(ev)
    assert result is not None
    assert result["entity_id"] == "sensor.x"
    assert result["state_value"] == "on"


def test_normalize_single_event_no_timestamp() -> None:
    """Event without timestamp returns None."""
    ev = {"entity_id": "sensor.x", "timestamp": None}
    assert ActivityWriterService._normalize_single_event(ev) is None


# ---------------------------------------------------------------------------
# bucket_to_reading
# ---------------------------------------------------------------------------


def test_bucket_to_reading_defaults() -> None:
    """Bucket with no sensor data uses defaults."""
    bucket = {"motion": 0.0, "door": 0.0, "temps": [], "humidities": [], "powers": []}
    reading = bucket_to_reading(bucket)
    assert reading.temperature == 20.0
    assert reading.humidity == 50.0
    assert reading.power == 0.0


def test_bucket_to_reading_fahrenheit_conversion() -> None:
    """Bucket with Fahrenheit temps converts to Celsius."""
    bucket = {"motion": 1.0, "door": 0.0, "temps": [77.0], "humidities": [55.0], "powers": [100.0]}
    reading = bucket_to_reading(bucket)
    assert 24.0 < reading.temperature < 26.0  # 77F = 25C


# ---------------------------------------------------------------------------
# get_metrics
# ---------------------------------------------------------------------------


def test_get_metrics_initial(service: ActivityWriterService) -> None:
    """Metrics reflect initial state."""
    m = service.get_metrics()
    assert m["last_successful_run"] is None
    assert m["last_error"] is None
    assert m["cycles_succeeded"] == 0
    assert m["cycles_failed"] == 0


# ---------------------------------------------------------------------------
# FastAPI endpoint smoke tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_endpoint_not_initialized() -> None:
    """Health endpoint returns 503 when service not started."""
    from httpx import ASGITransport, AsyncClient

    import src.main as mod
    old = mod.activity_writer
    mod.activity_writer = None
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            assert resp.status_code == 503
    finally:
        mod.activity_writer = old


@pytest.mark.asyncio
async def test_health_endpoint_healthy() -> None:
    """Health endpoint returns 200 when service is running."""
    from httpx import ASGITransport, AsyncClient

    import src.main as mod
    svc = ActivityWriterService()
    svc.cycles_succeeded = 1
    svc.last_successful_run = datetime.now(UTC)
    old = mod.activity_writer
    mod.activity_writer = svc
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "healthy"
    finally:
        mod.activity_writer = old


@pytest.mark.asyncio
async def test_root_endpoint() -> None:
    """Root endpoint returns service info."""
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["service"] == "activity-writer"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


def test_service_constants() -> None:
    """Service name and version are set."""
    assert SERVICE_NAME == "activity-writer"
    assert isinstance(SERVICE_VERSION, str)
