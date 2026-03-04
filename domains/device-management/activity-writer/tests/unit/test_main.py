"""Unit tests for activity-writer main module."""

from datetime import UTC, datetime

import pytest
from src.main import SERVICE_NAME, SERVICE_VERSION, ActivityWriterService


@pytest.fixture
def service() -> ActivityWriterService:
    """Create ActivityWriterService instance (no startup)."""
    return ActivityWriterService()


# ---------------------------------------------------------------------------
# _events_have_state
# ---------------------------------------------------------------------------


def test_events_have_state_empty(service: ActivityWriterService) -> None:
    """Empty events returns False."""
    assert service._events_have_state([]) is False


def test_events_have_state_no_state(service: ActivityWriterService) -> None:
    """Events without state info return False."""
    events = [{"entity_id": "sensor.foo"}, {"event_type": "state_changed"}]
    assert service._events_have_state(events) is False


def test_events_have_state_with_state_value(service: ActivityWriterService) -> None:
    """Events with state_value return True."""
    events = [{"entity_id": "sensor.foo", "state_value": "{'state':'on'}"}]
    assert service._events_have_state(events) is True


def test_events_have_state_with_new_state(service: ActivityWriterService) -> None:
    """Events with new_state return True."""
    events = [{"entity_id": "sensor.foo", "new_state": {"state": "on"}}]
    assert service._events_have_state(events) is True


# ---------------------------------------------------------------------------
# _parse_state_from_value
# ---------------------------------------------------------------------------


def test_parse_state_from_value_none(service: ActivityWriterService) -> None:
    """None state_value returns all None."""
    assert service._parse_state_from_value(None) == (None, None, None, None)


def test_parse_state_from_value_empty(service: ActivityWriterService) -> None:
    """Empty string returns all None."""
    assert service._parse_state_from_value("") == (None, None, None, None)


def test_parse_state_from_value_valid_state(service: ActivityWriterService) -> None:
    """Valid state_value dict extracts state."""
    s = "{'state': 'on', 'attributes': {}}"
    state, temp, hum, power = service._parse_state_from_value(s)
    assert state == "on"
    assert temp is None
    assert hum is None
    assert power is None


def test_parse_state_from_value_with_attrs(service: ActivityWriterService) -> None:
    """state_value with attributes extracts temp, humidity, power."""
    s = "{'state': '21.5', 'attributes': {'temperature': 21.5, 'humidity': 45.0, 'power': 120.0}}"
    state, temp, hum, power = service._parse_state_from_value(s)
    assert state == "21.5"
    assert temp == 21.5
    assert hum == 45.0
    assert power == 120.0


def test_parse_state_from_value_invalid(service: ActivityWriterService) -> None:
    """Invalid string returns all None."""
    assert service._parse_state_from_value("not valid python") == (None, None, None, None)


# ---------------------------------------------------------------------------
# _parse_event_timestamp
# ---------------------------------------------------------------------------


def test_parse_event_timestamp_none(service: ActivityWriterService) -> None:
    """None returns None."""
    assert service._parse_event_timestamp(None) is None


def test_parse_event_timestamp_str_valid(service: ActivityWriterService) -> None:
    """ISO string returns datetime."""
    ts = service._parse_event_timestamp("2025-02-18T12:00:00Z")
    assert ts is not None
    assert hasattr(ts, "timestamp")


def test_parse_event_timestamp_str_invalid(service: ActivityWriterService) -> None:
    """Invalid string returns None."""
    assert service._parse_event_timestamp("not-a-date") is None


def test_parse_event_timestamp_datetime(service: ActivityWriterService) -> None:
    """Datetime object returns as-is."""
    dt = datetime.now(UTC)
    assert service._parse_event_timestamp(dt) is dt


# ---------------------------------------------------------------------------
# _apply_event_to_bucket / _build_readings
# ---------------------------------------------------------------------------


def test_build_readings_empty(service: ActivityWriterService) -> None:
    """Empty events yields empty readings."""
    assert service._build_readings([]) == []


def test_build_readings_motion(service: ActivityWriterService) -> None:
    """Motion event sets motion=1.0 in bucket."""
    events = [
        {
            "entity_id": "binary_sensor.motion_living_room",
            "timestamp": "2025-02-18T12:00:30Z",
            "state_value": "{'state': 'on', 'attributes': {}}",
        }
    ]
    readings = service._build_readings(events)
    assert len(readings) == 1
    assert readings[0].motion == 1.0


def test_build_readings_door(service: ActivityWriterService) -> None:
    """Door event sets door=1.0 in bucket."""
    events = [
        {
            "entity_id": "binary_sensor.door_front",
            "timestamp": "2025-02-18T12:00:30Z",
            "state_value": "{'state': 'on', 'attributes': {}}",
        }
    ]
    readings = service._build_readings(events)
    assert len(readings) == 1
    assert readings[0].door == 1.0


def test_build_readings_temperature_from_attrs(service: ActivityWriterService) -> None:
    """Temperature from attributes populates bucket."""
    events = [
        {
            "entity_id": "climate.living_room",
            "timestamp": "2025-02-18T12:00:30Z",
            "state_value": "{'state': 'heat', 'attributes': {'temperature': 22.0}}",
        }
    ]
    readings = service._build_readings(events)
    assert len(readings) == 1
    assert readings[0].temperature == 22.0


def test_build_readings_buckets_by_minute(service: ActivityWriterService) -> None:
    """Events in same minute go to same bucket."""
    events = [
        {"entity_id": "binary_sensor.motion_1", "timestamp": "2025-02-18T12:00:10Z", "state_value": "{'state': 'on'}"},
        {"entity_id": "binary_sensor.door_1", "timestamp": "2025-02-18T12:00:50Z", "state_value": "{'state': 'on'}"},
    ]
    readings = service._build_readings(events)
    assert len(readings) == 1
    assert readings[0].motion == 1.0
    assert readings[0].door == 1.0


# ---------------------------------------------------------------------------
# _normalize_data_api_events
# ---------------------------------------------------------------------------


def test_normalize_data_api_events_basic(service: ActivityWriterService) -> None:
    """Normalize data-api events with new_state."""
    events = [
        {"entity_id": "sensor.temp", "new_state": {"state": "21.5"}, "timestamp": "2025-02-18T12:00:00Z"}
    ]
    out = service._normalize_data_api_events(events)
    assert len(out) == 1
    assert out[0]["entity_id"] == "sensor.temp"
    assert out[0]["state_value"] is not None


def test_normalize_data_api_events_skips_no_timestamp(service: ActivityWriterService) -> None:
    """Events without timestamp are skipped."""
    events = [{"entity_id": "sensor.foo", "timestamp": None}]
    assert service._normalize_data_api_events(events) == []


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


def test_service_constants() -> None:
    """Service name and version are set."""
    assert SERVICE_NAME == "activity-writer"
    assert isinstance(SERVICE_VERSION, str)
