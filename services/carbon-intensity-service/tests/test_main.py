"""
Tests for Carbon Intensity Service
"""

import os
import sys
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from main import CarbonIntensityService


@pytest.fixture
def mock_env(monkeypatch):
    """Mock environment variables"""
    monkeypatch.setenv("WATTTIME_API_TOKEN", "test_token")
    monkeypatch.setenv("GRID_REGION", "CAISO_NORTH")
    monkeypatch.setenv("INFLUXDB_TOKEN", "test_influx_token")
    monkeypatch.setenv("INFLUXDB_URL", "http://localhost:8086")


@pytest.fixture
async def service(mock_env):
    """Create service instance"""
    service = CarbonIntensityService()
    await service.startup()
    yield service
    await service.shutdown()


@pytest.mark.asyncio
async def test_service_initialization(mock_env):
    """Test service initializes correctly"""
    service = CarbonIntensityService()

    assert service.api_token == "test_token"
    assert service.region == "CAISO_NORTH"
    assert service.fetch_interval == 900
    assert service.cached_data is None


@pytest.mark.asyncio
async def test_fetch_carbon_intensity_success(service):
    """Test successful API fetch"""

    # Mock API response
    mock_response = {
        "moer": 250.5,
        "renewable_pct": 45.2,
        "forecast": [
            {"value": 210.0},  # 1 hour
            *[{"value": 0}] * 22,
            {"value": 180.0},  # 24 hours
        ],
    }

    # Mock aiohttp session
    with patch.object(service.session, "get") as mock_get:
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=mock_response)
        mock_get.return_value.__aenter__.return_value = mock_resp

        # Fetch data
        data = await service.fetch_carbon_intensity()

        # Verify
        assert data is not None
        assert data["carbon_intensity"] == 250.5
        assert data["renewable_percentage"] == 45.2
        assert data["fossil_percentage"] == 54.8
        assert data["forecast_1h"] == 210.0
        assert data["forecast_24h"] == 180.0
        assert service.cached_data == data
        assert service.health_handler.total_fetches == 1


@pytest.mark.asyncio
async def test_fetch_carbon_intensity_api_failure(service):
    """Test API failure with cache fallback"""

    # Set cached data
    service.cached_data = {
        "carbon_intensity": 200.0,
        "renewable_percentage": 50.0,
        "timestamp": datetime.now(),
    }

    # Mock API failure
    with patch.object(service.session, "get") as mock_get:
        mock_resp = AsyncMock()
        mock_resp.status = 503
        mock_get.return_value.__aenter__.return_value = mock_resp

        # Fetch data
        data = await service.fetch_carbon_intensity()

        # Should return cached data
        assert data == service.cached_data
        assert service.health_handler.failed_fetches == 1


@pytest.mark.asyncio
async def test_store_in_influxdb(service):
    """Test data storage in InfluxDB"""

    test_data = {
        "carbon_intensity": 250.5,
        "renewable_percentage": 45.2,
        "fossil_percentage": 54.8,
        "forecast_1h": 210.0,
        "forecast_24h": 180.0,
        "timestamp": datetime.now(),
    }

    # Mock InfluxDB client
    with patch.object(service.influxdb_client, "write") as mock_write:
        await service.store_in_influxdb(test_data)

        # Verify write was called
        assert mock_write.called

        # Verify Point data
        call_args = mock_write.call_args[0][0]
        assert call_args._name == "carbon_intensity"


@pytest.mark.asyncio
async def test_cache_functionality(service):
    """Test caching behavior"""

    mock_response = {
        "moer": 250.5,
        "renewable_pct": 45.2,
        "forecast": [{"value": 210.0}] * 24,
    }

    with patch.object(service.session, "get") as mock_get:
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=mock_response)
        mock_get.return_value.__aenter__.return_value = mock_resp

        # First fetch
        data1 = await service.fetch_carbon_intensity()
        assert service.cached_data == data1

        # Verify cache is populated
        assert service.cached_data["carbon_intensity"] == 250.5
        assert service.last_fetch_time is not None


@pytest.mark.asyncio
async def test_missing_env_variables():
    """Test service fails gracefully without required env vars"""

    with pytest.raises(ValueError, match="WATTTIME_API_TOKEN"):
        CarbonIntensityService()

