"""Tests for Air Quality Service main module."""

from datetime import UTC, datetime

import pytest


@pytest.fixture
def mock_env(monkeypatch):
    """Set required environment variables for service initialization.

    Open-Meteo needs no API key, so InfluxDB is the only credential.
    """
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
        assert service.influxdb_token == "test-token"
        assert service.base_url.startswith("https://air-quality-api.open-meteo.com")

    def test_missing_influxdb_token_raises(self, mock_env, monkeypatch):
        """Should raise ValueError when INFLUXDB_TOKEN is not set."""
        monkeypatch.delenv("INFLUXDB_TOKEN", raising=False)
        from main import AirQualityService

        with pytest.raises(ValueError, match="INFLUXDB_TOKEN"):
            AirQualityService()

    def test_invalid_latitude_raises(self, mock_env, monkeypatch):
        """Should raise ValueError for out-of-range latitude."""
        monkeypatch.setenv("LATITUDE", "999")
        from main import AirQualityService

        with pytest.raises(ValueError, match="LATITUDE"):
            AirQualityService()


class TestParsePollutionResponse:
    """Test Open-Meteo air-quality response parsing."""

    def test_parse_valid_response(self, service):
        """Should parse a valid Open-Meteo air-quality response."""
        raw = {
            "current": {
                "time": "2026-08-11T17:00",
                "us_aqi": 34,
                "pm2_5": 12.5,
                "pm10": 25.0,
                "ozone": 40.0,
                "carbon_monoxide": 200.0,
                "nitrogen_dioxide": 10.0,
                "sulphur_dioxide": 5.0,
            }
        }

        result = service._parse_pollution_response(raw)

        assert result is not None
        assert result["aqi"] == 34
        assert result["category"] == "Good"
        assert result["pm25"] == 12.5
        assert result["ozone"] == 40.0
        assert result["timestamp"] == datetime(2026, 8, 11, 17, 0, tzinfo=UTC)

    def test_parse_uses_reported_aqi_not_a_bucket_midpoint(self, service):
        """The reported US AQI is used verbatim, not mapped to a synthetic value."""
        raw = {"current": {"time": "2026-08-11T17:00", "us_aqi": 157}}

        result = service._parse_pollution_response(raw)

        assert result["aqi"] == 157
        assert result["category"] == "Unhealthy"

    @pytest.mark.parametrize(
        ("aqi", "category"),
        [
            (0, "Good"),
            (50, "Good"),
            (51, "Moderate"),
            (100, "Moderate"),
            (101, "Unhealthy for Sensitive Groups"),
            (150, "Unhealthy for Sensitive Groups"),
            (151, "Unhealthy"),
            (200, "Unhealthy"),
            (201, "Very Unhealthy"),
            (300, "Very Unhealthy"),
            (301, "Hazardous"),
            (500, "Hazardous"),
        ],
    )
    def test_aqi_category_boundaries(self, service, aqi, category):
        """EPA category boundaries are inclusive of their upper bound."""
        assert service._aqi_category(aqi) == category

    def test_parse_null_aqi_is_no_data_not_good(self, service):
        """A null us_aqi must not be published as AQI 0 / "Good"."""
        assert service._parse_pollution_response({"current": {"time": "x", "us_aqi": None}}) is None
        assert service._parse_pollution_response({"current": {"time": "x"}}) is None

    def test_parse_zero_aqi_is_a_real_reading(self, service):
        """AQI 0 is a valid measurement and must survive the null check."""
        result = service._parse_pollution_response({"current": {"time": "x", "us_aqi": 0}})

        assert result is not None
        assert result["aqi"] == 0
        assert result["category"] == "Good"

    def test_parse_missing_pollutants_default_to_zero(self, service):
        """Absent pollutant fields yield zeros rather than raising."""
        result = service._parse_pollution_response({"current": {"time": "x", "us_aqi": 42}})

        assert result["aqi"] == 42
        assert result["pm25"] == 0
        assert result["co"] == 0

    def test_parse_bad_timestamp_falls_back_to_now(self, service):
        """An unparseable time still produces a timezone-aware timestamp."""
        result = service._parse_pollution_response({"current": {"time": "not-a-time", "us_aqi": 1}})

        assert result["timestamp"].tzinfo is not None

    def test_parse_empty_response_returns_none(self, service):
        """Should return None when the response carries no `current` block."""
        assert service._parse_pollution_response({}) is None
        assert service._parse_pollution_response({"current": {}}) is None


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
