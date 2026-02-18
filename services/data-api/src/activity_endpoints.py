"""
Activity Endpoints for Data API
Epic Activity Recognition Integration Phase 1 - Story 1.2

Exposes activity data (current and history) from home_activity measurement.
"""

import logging
import os

from fastapi import APIRouter, HTTPException, Query, status

from .cache import cache
from pydantic import BaseModel

logger = logging.getLogger(__name__)

_shared_influxdb_client = None


def _get_shared_influxdb_client():
    """Get or create shared InfluxDB client (same pattern as events_endpoints)."""
    global _shared_influxdb_client
    if _shared_influxdb_client is None:
        from influxdb_client import InfluxDBClient

        influxdb_url = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
        influxdb_token = os.getenv("INFLUXDB_TOKEN", "homeiq-token")
        influxdb_org = os.getenv("INFLUXDB_ORG", "homeiq")
        _shared_influxdb_client = InfluxDBClient(
            url=influxdb_url,
            token=influxdb_token,
            org=influxdb_org,
        )
    return _shared_influxdb_client


class CurrentActivityResponse(BaseModel):
    """Current activity response schema."""

    activity: str
    activity_id: int
    confidence: float
    timestamp: str


class ActivityHistoryItem(BaseModel):
    """Single activity history item."""

    activity: str
    activity_id: int
    confidence: float
    timestamp: str


router = APIRouter(prefix="/activity", tags=["Activity"])

# In-memory cache for current activity (1-2 min TTL)
# Uses data-api cache instance injected at route registration
_activity_cache_ttl = int(os.getenv("ACTIVITY_CACHE_TTL_SECONDS", "90"))  # 1.5 min


async def _query_activity_from_influxdb(
    hours: int | None = None,
    limit: int = 1,
) -> list[dict]:
    """
    Query home_activity measurement from InfluxDB.
    Returns list of {activity, activity_id, confidence, timestamp}.
    """
    client = _get_shared_influxdb_client()
    query_api = client.query_api()
    bucket = os.getenv("INFLUXDB_BUCKET", "home_assistant_events")

    if hours:
        range_clause = f'|> range(start: -{hours}h)'
    else:
        range_clause = "|> range(start: -24h)"

    # Each point has 3 fields; need ~3 records per point
    record_limit = max(limit * 4, 12)

    query = f'''
    from(bucket: "{bucket}")
      {range_clause}
      |> filter(fn: (r) => r._measurement == "home_activity")
      |> filter(fn: (r) => r._field == "activity" or r._field == "activity_id" or r._field == "confidence")
      |> sort(columns: ["_time"], desc: true)
      |> limit(n: {record_limit})
    '''

    try:
        result = query_api.query(query)
    except Exception as e:
        logger.warning("InfluxDB query failed for activity: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="InfluxDB unavailable",
        ) from e

    # Pivot: group by _time, collect activity, activity_id, confidence
    by_time: dict[str, dict] = {}
    for table in result:
        for record in table.records:
            t = record.get_time()
            key = t.isoformat()
            if key not in by_time:
                by_time[key] = {"timestamp": key}
            field = record.values.get("_field")
            value = record.values.get("_value")
            if field == "activity":
                by_time[key]["activity"] = str(value)
            elif field == "activity_id":
                by_time[key]["activity_id"] = int(value) if value is not None else 9
            elif field == "confidence":
                by_time[key]["confidence"] = float(value) if value is not None else 0.0

    # Sort by time desc, return as list
    items = []
    for ts in sorted(by_time.keys(), reverse=True):
        d = by_time[ts]
        if "activity" in d:
            items.append(d)
            if len(items) >= limit:
                break
    return items


@router.get("", response_model=CurrentActivityResponse)
async def get_current_activity():
    """
    Get current/latest activity from InfluxDB.
    Returns 404 if no activity data exists.
    Cache TTL: 1-2 min (configurable via ACTIVITY_CACHE_TTL_SECONDS).
    """
    cache_key = "activity:current"
    try:
        cached = await cache.get(cache_key)
        if cached is not None:
            return CurrentActivityResponse(**cached)
    except Exception:
        pass

    try:
        items = await _query_activity_from_influxdb(limit=1)
    except HTTPException:
        raise

    if not items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No activity data available",
        )

    d = items[0]
    response = CurrentActivityResponse(
        activity=d["activity"],
        activity_id=d["activity_id"],
        confidence=d["confidence"],
        timestamp=d["timestamp"],
    )

    try:
        await cache.set(
            cache_key,
            response.model_dump(),
            ttl=_activity_cache_ttl,
        )
    except Exception:
        pass

    return response


@router.get("/history", response_model=list[ActivityHistoryItem])
async def get_activity_history(
    hours: int = Query(24, description="Hours of history", ge=1, le=720),
    limit: int = Query(100, description="Max number of results", ge=1, le=500),
):
    """
    Get activity history.
    Supports ?hours=24 (default) or ?limit=100.
    Returns 503 when InfluxDB unavailable.
    """
    try:
        items = await _query_activity_from_influxdb(hours=hours, limit=limit)
    except HTTPException:
        raise

    return [
        ActivityHistoryItem(
            activity=d["activity"],
            activity_id=d["activity_id"],
            confidence=d["confidence"],
            timestamp=d["timestamp"],
        )
        for d in items
    ]
