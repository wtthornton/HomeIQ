"""Shared test fixtures for the smart-meter adapter (former smart-meter-service)."""

import contextlib
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest


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
def mock_ha_adapter():
    """Mock Home Assistant meter adapter"""
    adapter = AsyncMock()
    adapter.test_connection = AsyncMock(return_value=True)
    adapter.fetch_consumption = AsyncMock()
    return adapter


@pytest.fixture
async def service_instance(monkeypatch):
    """Create a SmartMeterService instance for testing.

    Uses monkeypatch (not raw os.environ mutation) so these env vars don't
    leak into other adapters' tests running in the same process — all six
    adapters' suites share one pytest session now that they're one service.
    """
    from src.adapters.smart_meter import SmartMeterService

    monkeypatch.setenv("INFLUXDB_TOKEN", "test-token")
    monkeypatch.setenv("INFLUXDB_URL", "http://test-influxdb:8086")
    monkeypatch.setenv("INFLUXDB_ORG", "test-org")
    monkeypatch.setenv("INFLUXDB_BUCKET", "test-bucket")
    monkeypatch.setenv("METER_TYPE", "home_assistant")
    monkeypatch.setenv("HOME_ASSISTANT_URL", "http://test-ha:8123")
    monkeypatch.setenv("HOME_ASSISTANT_TOKEN", "test-ha-token")

    service = SmartMeterService()

    yield service

    with contextlib.suppress(BaseException):
        await service.shutdown()
