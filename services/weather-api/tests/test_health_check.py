"""
Tests for Health Check Handler
Epic 31, Story 31.1
"""

import pytest
from datetime import datetime, timedelta
from src.health_check import HealthCheckHandler


@pytest.mark.asyncio
async def test_health_check_returns_healthy_status():
    """Test that health check returns healthy status"""
    handler = HealthCheckHandler()
    
    result = await handler.handle()
    
    assert result["status"] == "healthy"
    assert result["service"] == "weather-api"
    assert result["version"] == "1.0.0"
    assert "uptime" in result
    assert "timestamp" in result


@pytest.mark.asyncio
async def test_health_check_includes_component_status():
    """Test that health check includes component status"""
    handler = HealthCheckHandler()
    
    result = await handler.handle()
    
    assert "components" in result
    assert result["components"]["api"] == "healthy"
    # Other components not initialized in Story 31.1
    assert result["components"]["weather_client"] == "not_initialized"
    assert result["components"]["cache"] == "not_initialized"
    assert result["components"]["influxdb"] == "not_initialized"


@pytest.mark.asyncio
async def test_health_check_tracks_uptime():
    """Test that health check tracks service uptime"""
    handler = HealthCheckHandler()
    
    # Wait a moment
    import asyncio
    await asyncio.sleep(0.1)
    
    result = await handler.handle()
    
    assert result["uptime_seconds"] >= 0
    assert isinstance(result["uptime_seconds"], int)


def test_get_uptime_seconds():
    """Test uptime calculation"""
    handler = HealthCheckHandler()
    handler.start_time = datetime.utcnow() - timedelta(seconds=100)
    
    uptime = handler.get_uptime_seconds()
    
    assert uptime >= 100
    assert uptime < 101  # Allow for small timing variations

