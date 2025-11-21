"""
Shared test fixtures for smart-meter-service
"""

import builtins
import contextlib
import os
import sys
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp ClientSession"""
    session = AsyncMock()
    session.get = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_influxdb_client():
    """Mock InfluxDB client"""
    client = MagicMock()
    client.write = MagicMock()
    client.close = MagicMock()
    return client


@pytest.fixture
def sample_meter_data() -> dict:
    """Sample power consumption data"""
    now = datetime.now()
    return {
        "total_power_w": 2450.0,
        "daily_kwh": 18.5,
        "circuits": [
            {"name": "HVAC", "power_w": 1200.0, "percentage": 49.0},
            {"name": "Kitchen", "power_w": 450.0, "percentage": 18.4},
            {"name": "Living Room", "power_w": 300.0, "percentage": 12.2},
        ],
        "timestamp": now,
    }


@pytest.fixture
def sample_low_power() -> dict:
    """Sample low power consumption (phantom load scenario)"""
    now = datetime.now()
    return {
        "total_power_w": 150.0,
        "daily_kwh": 2.5,
        "circuits": [
            {"name": "Standby", "power_w": 100.0, "percentage": 66.7},
            {"name": "Other", "power_w": 50.0, "percentage": 33.3},
        ],
        "timestamp": now,
    }


@pytest.fixture
def sample_high_power() -> dict:
    """Sample high power consumption (>10kW)"""
    now = datetime.now()
    return {
        "total_power_w": 12000.0,
        "daily_kwh": 85.0,
        "circuits": [
            {"name": "HVAC", "power_w": 5000.0, "percentage": 41.7},
            {"name": "Water Heater", "power_w": 4500.0, "percentage": 37.5},
            {"name": "Other", "power_w": 2500.0, "percentage": 20.8},
        ],
        "timestamp": now,
    }


@pytest.fixture
def sample_phantom_load() -> dict:
    """Sample 3am baseline (phantom load detection)"""
    now = datetime.now()
    return {
        "total_power_w": 250.0,  # High for 3am
        "daily_kwh": 1.0,
        "circuits": [
            {"name": "Standby Devices", "power_w": 150.0, "percentage": 60.0},
            {"name": "Always On", "power_w": 100.0, "percentage": 40.0},
        ],
        "timestamp": now,
    }


@pytest.fixture
async def service_instance():
    """Create service instance for testing"""
    from src.main import SmartMeterService

    # Set test environment
    os.environ["INFLUXDB_TOKEN"] = "test-token"
    os.environ["INFLUXDB_URL"] = "http://test-influxdb:8086"
    os.environ["INFLUXDB_ORG"] = "test-org"
    os.environ["INFLUXDB_BUCKET"] = "test-bucket"
    os.environ["METER_TYPE"] = "home_assistant"
    os.environ["HOME_ASSISTANT_URL"] = "http://test-ha:8123"
    os.environ["HOME_ASSISTANT_TOKEN"] = "test-ha-token"

    service = SmartMeterService()

    yield service

    # Cleanup
    with contextlib.suppress(builtins.BaseException):
        await service.shutdown()


@pytest.fixture
def mock_ha_adapter():
    """Mock Home Assistant adapter"""
    adapter = AsyncMock()
    adapter.test_connection = AsyncMock(return_value=True)
    adapter.fetch_consumption = AsyncMock()
    return adapter
