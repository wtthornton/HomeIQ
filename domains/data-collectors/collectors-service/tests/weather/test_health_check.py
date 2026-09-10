"""
Tests for Weather Health Check Handler (former weather-api/tests/test_health_check.py)
"""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from src.adapters.weather.health_check import HealthCheckHandler


def _healthy_service_stub():
    now = datetime.now(UTC).replace(tzinfo=UTC)
    task = SimpleNamespace(done=lambda: False, cancelled=lambda: False)
    return SimpleNamespace(
        session=SimpleNamespace(closed=False),
        cached_weather={"temperature": 20},
        cache_time=now,
        cache_ttl=900,
        cache_hits=1,
        cache_misses=0,
        fetch_count=1,
        influxdb_client=object(),
        background_task=task,
        last_successful_fetch=now,
        last_influx_write=now,
        last_influx_write_error=None,
        last_background_error=None,
    )


@pytest.mark.asyncio
async def test_health_check_returns_healthy_status():
    handler = HealthCheckHandler(service_name="weather-api", version="test")

    result = await handler.handle(_healthy_service_stub())

    assert result["status"] == "healthy"
    assert result["service"] == "weather-api"
    assert result["version"] == "test"
    assert "uptime" in result
    assert "timestamp" in result


@pytest.mark.asyncio
async def test_health_check_includes_component_status():
    handler = HealthCheckHandler(service_name="weather-api", version="test")

    result = await handler.handle(_healthy_service_stub())

    assert "components" in result
    assert result["components"]["api"] == "healthy"
    assert result["components"]["weather_client"] == "healthy"
    assert result["components"]["cache"] in {"healthy", "empty"}
    assert result["components"]["influxdb"] == "healthy"
    assert result["components"]["background_task"] == "running"


@pytest.mark.asyncio
async def test_health_check_tracks_uptime():
    handler = HealthCheckHandler(service_name="weather-api", version="test")

    import asyncio

    await asyncio.sleep(0.1)

    result = await handler.handle(_healthy_service_stub())

    assert result["uptime_seconds"] >= 0
    assert isinstance(result["uptime_seconds"], int)


def test_get_uptime_seconds():
    handler = HealthCheckHandler(service_name="weather-api", version="test")
    handler.start_time = datetime.now(UTC).replace(tzinfo=UTC) - timedelta(seconds=100)

    uptime = handler.get_uptime_seconds()

    assert uptime >= 100
    assert uptime < 101
