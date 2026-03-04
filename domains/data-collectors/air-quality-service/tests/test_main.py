"""Tests for Air Quality Service main module."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_env(monkeypatch):
    """Set required environment variables for service initialization."""
    monkeypatch.setenv("WEATHER_API_KEY", "test-api-key")
    monkeypatch.setenv("INFLUXDB_TOKEN", "test-token")
    monkeypatch.setenv("LATITUDE", "36.17")
    monkeypatch.setenv("LONGITUDE", "-115.14")


@pytest.fixture
def service(mock_env):
    """Create an AirQualityService instance for testing."""
    from main import AirQualityService

    return AirQualityService()


class TestAirQualityServiceInit:
    """Test service initialization and configuration."""

    def test_default_config(self, service):
        """Service should have expected default configuration."""
        assert service.api_key == "test-api-key"
        assert service.influxdb_token == "test-token"

    def test_missing_api_key_raises(self, monkeypatch):
        """Should raise ValueError when WEATHER_API_KEY is not set."""
        monkeypatch.setenv("INFLUXDB_TOKEN", "test-token")
        monkeypatch.delenv("WEATHER_API_KEY", raising=False)
        from main import AirQualityService

        with pytest.raises(ValueError, match="WEATHER_API_KEY"):
            AirQualityService()

    def test_invalid_latitude_raises(self, mock_env, monkeypatch):
        """Should raise ValueError for out-of-range latitude."""
        monkeypatch.setenv("LATITUDE", "999")
        from main import AirQualityService

        with pytest.raises(ValueError, match="LATITUDE"):
            AirQualityService()


class TestParsePollutionResponse:
    """Test OpenWeather API response parsing."""

    def test_parse_valid_response(self, service):
        """Should parse a valid OpenWeather pollution response."""
        raw = {
            "list": [
                {
                    "main": {"aqi": 2},
                    "components": {
                        "pm2_5": 12.5,
                        "pm10": 25.0,
                        "o3": 40.0,
                        "co": 200.0,
                        "no2": 10.0,
                        "so2": 5.0,
                    },
                    "dt": 1709500000,
                }
            ]
        }

        result = service._parse_pollution_response(raw)

        assert result is not None
        assert result["category"] == "Fair"
        assert result["aqi"] == 75
        assert result["pm25"] == 12.5

    def test_parse_empty_response_returns_none(self, service):
        """Should return None for empty response."""
        assert service._parse_pollution_response({}) is None
        assert service._parse_pollution_response({"list": []}) is None


class TestCacheValidation:
    """Test cache validity checking."""

    def test_cache_invalid_when_empty(self, service):
        """Cache should be invalid when no data is cached."""
        assert service._is_cache_valid() is False

    def test_cache_valid_when_fresh(self, service):
        """Cache should be valid when data is fresh."""
        service.cached_data = {"aqi": 50}
        service.last_fetch_time = datetime.now(UTC)
        assert service._is_cache_valid() is True
