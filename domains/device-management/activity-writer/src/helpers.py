"""Pure helper functions for event parsing and feature extraction."""

from __future__ import annotations

import ast
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
) -> tuple[str | None, float | None, float | None, float | None]:
    """Parse a state_value string to extract state, temp, humidity, power."""
    if not state_value:
        return None, None, None, None
    with suppress(Exception):
        obj = ast.literal_eval(state_value)
        if isinstance(obj, dict):
            state_str = str(obj.get("state", ""))
            attrs = obj.get("attributes") or {}
            if isinstance(attrs, dict):
                temp, humidity, power = extract_attrs(attrs)
                return state_str, temp, humidity, power
            return state_str, None, None, None
    return None, None, None, None


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
    bucket_list: list[float], parsed: float | None, state_str: str | None,
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
        motion=b["motion"], door=b["door"],
        temperature=temp_avg, humidity=hum_avg, power=sum(b["powers"]),
    )
