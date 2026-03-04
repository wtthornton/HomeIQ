"""Data fetching from data-api and InfluxDB for activity-writer."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .helpers import parse_event_timestamp

logger = logging.getLogger("activity-writer")


async def fetch_from_data_api(
    session: aiohttp.ClientSession | None,
    data_api_url: str,
    data_api_key: str | None,
    events_limit: int,
) -> list[dict[str, Any]]:
    """Fetch events from data-api with auth."""
    if not session:
        return []
    url = f"{data_api_url.rstrip('/')}/api/v1/events"
    params: dict[str, Any] = {"event_type": "state_changed", "limit": events_limit}
    headers: dict[str, str] = {}
    if data_api_key:
        headers["Authorization"] = f"Bearer {data_api_key}"
    try:
        async with session.get(url, params=params, headers=headers or None) as resp:
            if resp.status != 200:
                logger.warning("Data-API returned %d", resp.status)
                return []
            data = await resp.json()
            if isinstance(data, list):
                return [
                    e if isinstance(e, dict) else e.model_dump() if hasattr(e, "model_dump") else {}
                    for e in data
                ]
            return []
    except Exception as e:
        logger.debug("Data-API fetch failed: %s", e)
        return []


def events_have_state(events: list[dict[str, Any]]) -> bool:
    """Check whether any of the first 10 events contain state info."""
    return any(e.get("new_state") or e.get("state_value") for e in events[:10])


def normalize_single_event(e: dict[str, Any]) -> dict[str, Any] | None:
    """Normalize a single data-api event. Returns ``None`` if no valid timestamp."""
    ns = e.get("new_state")
    state_value = e.get("state_value")
    if ns is not None and state_value is None:
        state_value = str(ns)
    ts = parse_event_timestamp(e.get("timestamp"))
    if ts is None:
        return None
    return {
        "entity_id": str(e.get("entity_id", "")),
        "timestamp": ts,
        "state_value": state_value,
        "event_type": e.get("event_type", "state_changed"),
    }


def normalize_data_api_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize data-api events to internal format."""
    return [n for e in events if (n := normalize_single_event(e)) is not None]


def group_influx_records(result: Any) -> list[dict[str, Any]]:
    """Group InfluxDB records by (entity_id, time)."""
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
            if record.values.get("_field") == "state_value" and record.values.get("_value"):
                by_key[key]["state_value"] = str(record.values["_value"])
    return list(by_key.values())
