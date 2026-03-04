"""Tests for Smart Meter Service main module."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_env(monkeypatch):
    """Set required environment variables for service initialization."""
    monkeypatch.setenv("INFLUXDB_TOKEN", "test-token")
    monkeypatch.setenv("METER_TYPE", "home_assistant")
    monkeypatch.setenv("FETCH_INTERVAL_SECONDS", "30")


@pytest.fixture
def service(mock_env):
    """Create a SmartMeterService instance for testing."""
    with patch("main.HomeAssistantAdapter"):
        from main import SmartMeterService

        return SmartMeterService()


class TestSmartMeterServiceInit:
    """Test service initialization and configuration."""

    def test_default_meter_type(self, service):
        """Service should default to 'home_assistant' meter type."""
        assert service.meter_type == "home_assistant"

    def test_influxdb_config(self, service):
        """InfluxDB config should be loaded from environment."""
        assert service.influxdb_token == "test-token"

    def test_missing_influxdb_token_raises(self, monkeypatch):
        """Should raise ValueError when INFLUXDB_TOKEN is not set."""
        monkeypatch.delenv("INFLUXDB_TOKEN", raising=False)
        with patch("main.HomeAssistantAdapter"):
            from main import SmartMeterService

            with pytest.raises(ValueError, match="INFLUXDB_TOKEN"):
                SmartMeterService()

    def test_fetch_interval_minimum(self, mock_env, monkeypatch):
        """Fetch interval below 10s should be clamped to 10s."""
        monkeypatch.setenv("FETCH_INTERVAL_SECONDS", "5")
        with patch("main.HomeAssistantAdapter"):
            from main import SmartMeterService

            svc = SmartMeterService()
            assert svc.fetch_interval == 10


class TestMockData:
    """Test mock data generation."""

    def test_get_mock_data_returns_valid_structure(self, service):
        """Mock data should contain expected fields."""
        data = service._get_mock_data()

        assert "total_power_w" in data
        assert "daily_kwh" in data
        assert "circuits" in data
        assert isinstance(data["circuits"], list)
        assert len(data["circuits"]) > 0

    def test_mock_data_has_timestamp(self, service):
        """Mock data should include a UTC timestamp."""
        data = service._get_mock_data()
        assert "timestamp" in data
        assert data["timestamp"].tzinfo is not None


class TestEnrichConsumptionData:
    """Test consumption data enrichment."""

    def test_adds_timestamp_if_missing(self, service):
        """Should add timestamp when not present in data."""
        data = {"total_power_w": 1000, "circuits": []}
        service._enrich_consumption_data(data)
        assert "timestamp" in data

    def test_calculates_circuit_percentages(self, service):
        """Should calculate percentage for circuits missing it."""
        data = {
            "total_power_w": 1000,
            "circuits": [{"name": "HVAC", "power_w": 500}],
        }
        service._enrich_consumption_data(data)
        assert data["circuits"][0]["percentage"] == 50.0
