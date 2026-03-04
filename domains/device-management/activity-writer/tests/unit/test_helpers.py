"""Unit tests for activity-writer helpers module."""

from __future__ import annotations

from src.bucket_builder import build_readings
from src.helpers import (
    append_value,
    bucket_to_reading,
    classify_entity,
    extract_attrs,
    parse_event_timestamp,
    parse_state_value,
    safe_float,
    try_float,
)


# ---------------------------------------------------------------------------
# try_float
# ---------------------------------------------------------------------------


def test_try_float_none() -> None:
    assert try_float(None) is None


def test_try_float_valid() -> None:
    assert try_float("3.14") == 3.14
    assert try_float(42) == 42.0


def test_try_float_invalid() -> None:
    assert try_float("abc") is None


# ---------------------------------------------------------------------------
# safe_float
# ---------------------------------------------------------------------------


def test_safe_float_empty() -> None:
    assert safe_float(None) is None
    assert safe_float("") is None


def test_safe_float_valid() -> None:
    assert safe_float("21.5") == 21.5


def test_safe_float_non_numeric() -> None:
    assert safe_float("off") is None


# ---------------------------------------------------------------------------
# extract_attrs
# ---------------------------------------------------------------------------


def test_extract_attrs_all() -> None:
    attrs = {"temperature": 22.0, "humidity": 55.0, "power": 100.0}
    t, h, p = extract_attrs(attrs)
    assert t == 22.0
    assert h == 55.0
    assert p == 100.0


def test_extract_attrs_partial() -> None:
    attrs = {"humidity": 60.0}
    t, h, p = extract_attrs(attrs)
    assert t is None
    assert h == 60.0
    assert p is None


# ---------------------------------------------------------------------------
# parse_state_value
# ---------------------------------------------------------------------------


def test_parse_state_value_none() -> None:
    assert parse_state_value(None) == (None, None, None, None)


def test_parse_state_value_empty() -> None:
    assert parse_state_value("") == (None, None, None, None)


def test_parse_state_value_valid() -> None:
    s = "{'state': 'on', 'attributes': {}}"
    state, temp, hum, power = parse_state_value(s)
    assert state == "on"
    assert temp is None


def test_parse_state_value_with_attrs() -> None:
    s = "{'state': '21.5', 'attributes': {'temperature': 21.5, 'humidity': 45.0, 'power': 120.0}}"
    state, temp, hum, power = parse_state_value(s)
    assert state == "21.5"
    assert temp == 21.5
    assert hum == 45.0
    assert power == 120.0


# ---------------------------------------------------------------------------
# parse_event_timestamp
# ---------------------------------------------------------------------------


def test_parse_event_timestamp_none() -> None:
    assert parse_event_timestamp(None) is None


def test_parse_event_timestamp_valid_str() -> None:
    ts = parse_event_timestamp("2025-02-18T12:00:00Z")
    assert ts is not None


def test_parse_event_timestamp_invalid_str() -> None:
    assert parse_event_timestamp("not-a-date") is None


# ---------------------------------------------------------------------------
# classify_entity
# ---------------------------------------------------------------------------


def test_classify_motion() -> None:
    assert classify_entity("binary_sensor.motion_hall") == "motion"


def test_classify_door() -> None:
    assert classify_entity("binary_sensor.door_front") == "door"


def test_classify_temp() -> None:
    assert classify_entity("sensor.temperature_living") == "temp"
    assert classify_entity("climate.living_room") == "temp"


def test_classify_humidity() -> None:
    assert classify_entity("sensor.humidity_bath") == "hum"


def test_classify_power() -> None:
    assert classify_entity("sensor.power_meter") == "power"


def test_classify_other() -> None:
    assert classify_entity("light.office") == "other"


# ---------------------------------------------------------------------------
# append_value
# ---------------------------------------------------------------------------


def test_append_value_parsed() -> None:
    bucket: list[float] = []
    append_value(bucket, 10.0, None)
    assert bucket == [10.0]


def test_append_value_fallback() -> None:
    bucket: list[float] = []
    append_value(bucket, None, "7.5")
    assert bucket == [7.5]


def test_append_value_neither() -> None:
    bucket: list[float] = []
    append_value(bucket, None, "off")
    assert bucket == []


# ---------------------------------------------------------------------------
# bucket_to_reading
# ---------------------------------------------------------------------------


def test_bucket_to_reading_defaults() -> None:
    bucket = {"motion": 0.0, "door": 0.0, "temps": [], "humidities": [], "powers": []}
    reading = bucket_to_reading(bucket)
    assert reading.temperature == 20.0
    assert reading.humidity == 50.0


def test_bucket_to_reading_fahrenheit() -> None:
    bucket = {"motion": 1.0, "door": 0.0, "temps": [77.0], "humidities": [55.0], "powers": [100.0]}
    reading = bucket_to_reading(bucket)
    assert 24.0 < reading.temperature < 26.0


# ---------------------------------------------------------------------------
# build_readings
# ---------------------------------------------------------------------------


def test_build_readings_empty() -> None:
    assert build_readings([]) == []


def test_build_readings_motion() -> None:
    events = [
        {
            "entity_id": "binary_sensor.motion_living_room",
            "timestamp": "2025-02-18T12:00:30Z",
            "state_value": "{'state': 'on', 'attributes': {}}",
        }
    ]
    readings = build_readings(events)
    assert len(readings) == 1
    assert readings[0].motion == 1.0
