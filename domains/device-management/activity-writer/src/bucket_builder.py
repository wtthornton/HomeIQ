"""Bucket aggregation — groups events into 1-minute windows."""

from __future__ import annotations

from typing import Any

from .helpers import (
    append_value,
    bucket_to_reading,
    classify_entity,
    parse_event_timestamp,
    parse_state_value,
)
from .models import SensorReading

_ON_STATES: frozenset[str] = frozenset({"on", "1", "true"})


def _apply_event_to_bucket(
    b: dict[str, Any], category: str, is_on: bool,
    state_str: str | None, temp: float | None,
    humidity: float | None, power: float | None,
) -> None:
    """Apply a single parsed event to its bucket."""
    if category == "motion":
        b["motion"] = 1.0 if is_on else max(b["motion"], 0.0)
    elif category == "door":
        b["door"] = 1.0 if is_on else max(b["door"], 0.0)
    elif category == "temp":
        append_value(b["temps"], temp, state_str)
    elif category == "hum":
        append_value(b["humidities"], humidity, state_str)
    elif category == "power":
        append_value(b["powers"], power, state_str)


def _new_bucket() -> dict[str, Any]:
    """Create an empty sensor bucket."""
    return {"motion": 0.0, "door": 0.0, "temps": [], "humidities": [], "powers": []}


def build_readings(events: list[dict[str, Any]]) -> list[SensorReading]:
    """Build 1-min buckets and extract 5 features per bucket."""
    buckets: dict[int, dict[str, Any]] = {}
    for ev in events:
        ts = parse_event_timestamp(ev.get("timestamp"))
        if ts is None:
            continue
        bucket_key = int(ts.timestamp()) // 60
        if bucket_key not in buckets:
            buckets[bucket_key] = _new_bucket()
        b = buckets[bucket_key]
        entity_id = str(ev.get("entity_id", ""))
        state_str, temp, humidity, power = parse_state_value(ev.get("state_value"))
        category = classify_entity(entity_id)
        is_on = (state_str or "").lower() in _ON_STATES
        _apply_event_to_bucket(b, category, is_on, state_str, temp, humidity, power)
    return [bucket_to_reading(buckets[k]) for k in sorted(buckets)]
