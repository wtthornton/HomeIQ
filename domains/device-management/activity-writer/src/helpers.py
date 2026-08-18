"""Pure helper functions for event parsing and feature extraction."""

from __future__ import annotations

import ast
import json
import re
from contextlib import suppress
from datetime import datetime
from typing import Any

from .models import SensorReading

# Pre-compiled patterns for entity classification
_MOTION_RE = re.compile(r"binary_sensor\.motion[\w_]*")
_DOOR_RE = re.compile(r"binary_sensor\.door[\w_]*")


def try_float(value: Any) -> float | None:
    """Attempt to convert *value* to float, returning ``None`` on failure."""
    if value is None:
        return None
    with suppress(TypeError, ValueError):
        return float(value)
    return None


def safe_float(s: str | None) -> float | None:
    """Parse a numeric-looking string to float, else ``None``."""
    if not s:
        return None
    digits = s.replace(".", "", 1).replace("-", "", 1).replace(" ", "")
    if not digits.isdigit():
        return None
    with suppress(ValueError):
        return float(s)
    return None


def extract_attrs(attrs: dict[str, Any]) -> tuple[float | None, float | None, float | None]:
    """Extract temperature, humidity and power from an HA attributes dict."""
    temp = try_float(attrs.get("temperature") or attrs.get("value"))
    humidity = try_float(attrs.get("humidity"))
    power = try_float(attrs.get("power") or attrs.get("current_power_w"))
    return temp, humidity, power


def parse_state_value(
    state_value: str | None,
    attributes: Any = None,
) -> tuple[str | None, float | None, float | None, float | None]:
    """Extract (state, temp, humidity, power) from an event's state and attributes.

    ``state_value`` is the bare HA state ("on", "21.5") since 2026-08-18; rows written
    before that hold the repr of the whole HA state object (state + attributes), which
    is still recognised. ``attributes`` is the event's separately-stored attributes field
    (JSON string or dict) and is where temp/humidity/power come from for new rows.
    """
    if not state_value:
        return None, None, None, None
    attrs: dict[str, Any] = _coerce_attributes(attributes)
    text = str(state_value)
    if text.startswith("{"):
        with suppress(Exception):
            obj = ast.literal_eval(text)
            if isinstance(obj, dict):
                if isinstance(obj.get("attributes"), dict) and not attrs:
                    attrs = obj["attributes"]
                temp, humidity, power = extract_attrs(attrs) if attrs else (None, None, None)
                return str(obj.get("state", "")), temp, humidity, power
    temp, humidity, power = extract_attrs(attrs) if attrs else (None, None, None)
    return text, temp, humidity, power


def _coerce_attributes(attributes: Any) -> dict[str, Any]:
    if isinstance(attributes, dict):
        return attributes
    if isinstance(attributes, str) and attributes.startswith("{"):
        with suppress(ValueError):
            parsed = json.loads(attributes)
            if isinstance(parsed, dict):
                return parsed
    return {}


def parse_event_timestamp(ts: Any) -> datetime | None:
    """Parse event timestamp to datetime or ``None``."""
    if ts is None:
        return None
    if isinstance(ts, str):
        with suppress(ValueError):
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return None
    if hasattr(ts, "timestamp"):
        return ts
    return None


def classify_entity(entity_id: str) -> str:
    """Return a category tag: motion/door/temp/hum/power/other."""
    ent = entity_id.lower()
    if "binary_sensor.motion" in ent or _MOTION_RE.match(ent):
        return "motion"
    if "binary_sensor.door" in ent or _DOOR_RE.match(ent):
        return "door"
    if "temperature" in ent or ent.startswith("climate."):
        return "temp"
    if "humidity" in ent and "sensor." in ent:
        return "hum"
    if "power" in ent and "sensor." in ent:
        return "power"
    return "other"


def append_value(
    bucket_list: list[float],
    parsed: float | None,
    state_str: str | None,
) -> None:
    """Append *parsed* (or fallback from *state_str*) to *bucket_list*."""
    if parsed is not None:
        bucket_list.append(parsed)
    else:
        val = safe_float(state_str)
        if val is not None:
            bucket_list.append(val)


def bucket_to_reading(b: dict[str, Any]) -> SensorReading:
    """Convert an accumulated bucket dict into a ``SensorReading``."""
    temp_avg = sum(b["temps"]) / len(b["temps"]) if b["temps"] else 20.0
    # HA may report Fahrenheit — convert if above 56 C (133 F)
    if temp_avg > 56:
        temp_avg = (temp_avg - 32) * 5 / 9
    hum_avg = sum(b["humidities"]) / len(b["humidities"]) if b["humidities"] else 50.0
    return SensorReading(
        motion=b["motion"],
        door=b["door"],
        temperature=temp_avg,
        humidity=hum_avg,
        power=sum(b["powers"]),
    )
