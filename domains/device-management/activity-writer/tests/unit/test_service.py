"""Unit tests for activity-writer service module."""

from datetime import UTC, datetime

import pytest
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
from src.service import ActivityWriterService


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
# classify_entity
# ---------------------------------------------------------------------------


def test_classify_motion() -> None:
    assert classify_entity("binary_sensor.motion_hall") == "motion"


def test_classify_door() -> None:
    assert classify_entity("binary_sensor.door_front") == "door"


def test_classify_temp() -> None:
    assert classify_entity("sensor.temperature_living") == "temp"


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
# get_metrics
# ---------------------------------------------------------------------------


def test_get_metrics_default() -> None:
    svc = ActivityWriterService()
    m = svc.get_metrics()
    assert m["cycles_succeeded"] == 0
    assert m["last_error"] is None
