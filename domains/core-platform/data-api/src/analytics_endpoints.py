"""
Analytics Endpoints for Data API
Story 21.4: Analytics Tab with Real Data

Provides aggregated analytics data for dashboard visualization.
- eventsPerMinute: real InfluxDB query
- apiResponseTime: real in-memory metrics (per-request timing middleware)
- databaseLatency: real in-memory metrics (per-query InfluxDB callback)
- errorRate: real in-memory metrics (HTTP status tracking middleware)
"""

import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from .metrics_state import metrics_buffer

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------

class TimeSeriesPoint(BaseModel):
    """Time series data point"""
    timestamp: str
    value: float


class MetricData(BaseModel):
    """Metric data with statistics"""
    current: float
    peak: float
    average: float
    min: float
    trend: str  # 'up', 'down', 'stable'
    data: list[TimeSeriesPoint]


class AnalyticsSummary(BaseModel):
    """Analytics summary statistics"""
    totalEvents: int
    successRate: float
    avgLatency: float
    uptime: float


class AnalyticsResponse(BaseModel):
    """Analytics response model"""
    eventsPerMinute: MetricData
    apiResponseTime: MetricData
    databaseLatency: MetricData
    errorRate: MetricData
    summary: AnalyticsSummary
    timeRange: str
    lastUpdate: str


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(tags=["Analytics"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def calculate_trend(data: list[float], window: int = 5) -> str:
    """Calculate trend from time series data."""
    if len(data) < window:
        return 'stable'

    recent = data[-window:]
    older = data[-window * 2:-window] if len(data) >= window * 2 else data[:-window]

    if not older:
        return 'stable'

    recent_avg = sum(recent) / len(recent)
    older_avg = sum(older) / len(older)

    threshold = abs(older_avg) * 0.1 if older_avg != 0 else 0.1

    if recent_avg > older_avg + threshold:
        return 'up'
    elif recent_avg < older_avg - threshold:
        return 'down'
    return 'stable'


def get_time_range_params(time_range: str) -> tuple:
    """Return (start_time_iso, interval_str, num_points) for *time_range*."""
    now = datetime.now(UTC)

    if time_range == '1h':
        start = now - timedelta(hours=1)
        return (start.strftime('%Y-%m-%dT%H:%M:%SZ'), '1m', 60)
    if time_range == '6h':
        start = now - timedelta(hours=6)
        return (start.strftime('%Y-%m-%dT%H:%M:%SZ'), '5m', 72)
    if time_range == '24h':
        start = now - timedelta(hours=24)
        return (start.strftime('%Y-%m-%dT%H:%M:%SZ'), '15m', 96)
    if time_range == '7d':
        start = now - timedelta(days=7)
        return (start.strftime('%Y-%m-%dT%H:%M:%SZ'), '2h', 84)

    # Default 1h
    start = now - timedelta(hours=1)
    return (start.strftime('%Y-%m-%dT%H:%M:%SZ'), '1m', 60)


def _build_metric(series: list[dict[str, Any]]) -> MetricData:
    """Build a MetricData from a raw series list."""
    values = [p['value'] for p in series]
    return MetricData(
        current=values[-1] if values else 0.0,
        peak=max(values) if values else 0.0,
        average=sum(values) / len(values) if values else 0.0,
        min=min(values) if values else 0.0,
        trend=calculate_trend(values),
        data=[TimeSeriesPoint(**p) for p in series],
    )


def calculate_service_uptime() -> float:
    """Return service uptime as percentage (always 100 while running)."""
    try:
        from .main import SERVICE_START_TIME
        uptime_seconds = (datetime.now(UTC) - SERVICE_START_TIME).total_seconds()
        # Service is running → 100 %.
        # A more advanced version would track restart windows.
        return 100.0 if uptime_seconds > 0 else 0.0
    except Exception as e:
        logger.error(f"Error calculating uptime: {e}")
        return 100.0


_INTERVAL_RE = re.compile(r'(\d+)([mhd])')


def _generate_empty_series(start_time: str, interval: str, num_points: int) -> list[dict[str, Any]]:
    """Generate zero-filled time series (used when InfluxDB has no data)."""
    m = _INTERVAL_RE.match(interval)
    if not m:
        delta = timedelta(minutes=1)
    else:
        v, u = int(m.group(1)), m.group(2)
        delta = timedelta(minutes=v) if u == 'm' else timedelta(hours=v) if u == 'h' else timedelta(days=v)

    start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
    return [
        {'timestamp': (start + delta * i).isoformat() + 'Z', 'value': 0.0}
        for i in range(num_points)
    ]


# ---------------------------------------------------------------------------
# Data Queries
# ---------------------------------------------------------------------------

async def query_events_per_minute(
    influxdb_client,
    start_time: str,
    interval: str,
    num_points: int,
) -> list[dict[str, Any]]:
    """Query real event counts from InfluxDB."""
    try:
        query = f'''
        from(bucket: "home_assistant_events")
          |> range(start: {start_time})
          |> filter(fn: (r) => r._measurement == "home_assistant_events")
          |> aggregateWindow(every: {interval}, fn: count)
          |> keep(columns: ["_time", "_value"])
        '''
        result = await influxdb_client._execute_query(query)

        data = []
        for record in result:
            time_val = record.get('_time')
            ts = time_val.isoformat() + 'Z' if hasattr(time_val, 'isoformat') else str(time_val)
            data.append({
                'timestamp': ts,
                'value': float(record.get('_value') or 0),
            })

        if len(data) < num_points:
            if not data:
                return _generate_empty_series(start_time, interval, num_points)
            return data

        return data[:num_points]
    except Exception as e:
        logger.error(f"Error querying events per minute: {e}")
        return _generate_empty_series(start_time, interval, num_points)


def query_api_response_time(start_time: str, interval: str, num_points: int) -> list[dict[str, Any]]:
    """Real API response time from in-memory MetricsBuffer."""
    return metrics_buffer.get_series('response_time', start_time, interval, num_points)


def query_database_latency(start_time: str, interval: str, num_points: int) -> list[dict[str, Any]]:
    """Real InfluxDB query latency from in-memory MetricsBuffer."""
    return metrics_buffer.get_series('db_latency', start_time, interval, num_points)


def query_error_rate(start_time: str, interval: str, num_points: int) -> list[dict[str, Any]]:
    """Real error rate from in-memory MetricsBuffer."""
    return metrics_buffer.get_series('error_rate', start_time, interval, num_points)


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    range: Literal['1h', '6h', '24h', '7d'] = Query(
        '1h',
        description="Time range: 1h, 6h, 24h, 7d"
    ),
    _metrics: str | None = Query(None, description="Comma-separated list of metrics to include"),
):
    """Get analytics data for the specified time range."""
    try:
        # Lazy-import to access the shared InfluxDB client from the service
        from .main import data_api_service
        influxdb_client = data_api_service.influxdb_client

        if not influxdb_client.is_connected:
            await influxdb_client.connect()

        start_time, interval, num_points = get_time_range_params(range)

        # Events — real InfluxDB query
        events_data = await query_events_per_minute(influxdb_client, start_time, interval, num_points)

        # Response time, DB latency, error rate — real in-memory buffer
        api_response_data = query_api_response_time(start_time, interval, num_points)
        db_latency_data = query_database_latency(start_time, interval, num_points)
        error_rate_data = query_error_rate(start_time, interval, num_points)

        # Summary
        total_events = sum(p['value'] for p in events_data)
        current_error_rate = error_rate_data[-1]['value'] if error_rate_data else 0.0
        avg_latency = (
            sum(p['value'] for p in db_latency_data) / len(db_latency_data)
            if db_latency_data else 0.0
        )

        return AnalyticsResponse(
            eventsPerMinute=_build_metric(events_data),
            apiResponseTime=_build_metric(api_response_data),
            databaseLatency=_build_metric(db_latency_data),
            errorRate=_build_metric(error_rate_data),
            summary=AnalyticsSummary(
                totalEvents=int(total_events),
                successRate=round(100.0 - current_error_rate, 2),
                avgLatency=round(avg_latency, 2),
                uptime=calculate_service_uptime(),
            ),
            timeRange=range,
            lastUpdate=datetime.now(UTC).isoformat() + 'Z',
        )

    except Exception as e:
        logger.error(f"Error getting analytics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get analytics: {str(e)}",
        ) from e


def create_analytics_router() -> APIRouter:
    """Create analytics router (for compatibility)."""
    return router
