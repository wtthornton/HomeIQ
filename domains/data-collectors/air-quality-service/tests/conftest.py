"""
Shared test fixtures for air-quality-service
"""

import contextlib
import os
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Add service root and src/ directory to sys.path for imports
_service_root = str(Path(__file__).resolve().parent.parent)
_service_src = str(Path(__file__).resolve().parent.parent / "src")
if _service_root not in sys.path:
    sys.path.insert(0, _service_root)
if _service_src not in sys.path:
    sys.path.insert(0, _service_src)


@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp ClientSession"""
    session = MagicMock()
    session.close = AsyncMock()
    # Don't pre-define session.get - let tests set it up as async context manager
    return session


@pytest.fixture
def mock_influxdb_client():
    """Mock InfluxDB client"""
    client = MagicMock()
    client.write = MagicMock()
    client.close = MagicMock()
    return client


@pytest.fixture
def sample_open_meteo_response() -> dict:
    """Sample Open-Meteo air-quality response (good air quality)"""
    return {
        "latitude": 36.0,
        "longitude": -115.2,
        "current": {
            "time": "2026-08-11T17:00",
            "us_aqi": 34,
            "carbon_monoxide": 230.31,
            "nitrogen_dioxide": 1.15,
            "ozone": 68.66,
            "sulphur_dioxide": 0.38,
            "pm2_5": 3.41,
            "pm10": 3.78,
        },
    }


@pytest.fixture
def sample_poor_aqi_response() -> dict:
    """Sample Open-Meteo response with poor AQI"""
    return {
        "current": {
            "time": "2026-08-11T17:00",
            "us_aqi": 175,
            "carbon_monoxide": 450.0,
            "nitrogen_dioxide": 45.0,
            "ozone": 150.0,
            "sulphur_dioxide": 25.0,
            "pm2_5": 75.0,
            "pm10": 120.0,
        }
    }


@pytest.fixture
def sample_ha_config_response() -> dict:
    """Sample Home Assistant config response"""
    return {
        "latitude": 36.1699,
        "longitude": -115.1398,
        "elevation": 610,
        "unit_system": {"length": "km", "mass": "g", "temperature": "C", "volume": "L"},
        "location_name": "Home",
        "time_zone": "America/Los_Angeles",
    }


@pytest.fixture
def sample_aqi_data() -> dict:
    """Sample processed AQI data"""
    now = datetime.now()
    return {
        "aqi": 34,  # US AQI as reported by Open-Meteo
        "category": "Good",
        "parameter": "Combined",
        "pm25": 3,
        "pm10": 4,
        "ozone": 69,
        "co": 230.31,
        "no2": 1.15,
        "so2": 0.38,
        "timestamp": now,
    }


@pytest.fixture
async def service_instance():
    """Create service instance for testing"""
    from src.main import AirQualityService

    # Set test environment
    os.environ["INFLUXDB_TOKEN"] = "test-token"
    os.environ["INFLUXDB_URL"] = "http://test-influxdb:8086"
    os.environ["INFLUXDB_ORG"] = "test-org"
    os.environ["INFLUXDB_BUCKET"] = "test-bucket"
    os.environ["LATITUDE"] = "36.1699"
    os.environ["LONGITUDE"] = "-115.1398"

    service = AirQualityService()
    service.retry_delays = []  # Disable retries in tests

    yield service

    # Cleanup
    with contextlib.suppress(BaseException):
        await service.shutdown()
