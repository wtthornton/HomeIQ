"""Tests for Electricity Pricing Service main module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_env(monkeypatch):
    """Set required environment variables for service initialization."""
    monkeypatch.setenv("INFLUXDB_TOKEN", "test-token")
    monkeypatch.setenv("PRICING_PROVIDER", "awattar")
    monkeypatch.setenv("FETCH_INTERVAL", "60")
    monkeypatch.setenv("CACHE_DURATION", "5")


@pytest.fixture
def service(mock_env):
    """Create an ElectricityPricingService instance for testing."""
    with patch("main.AwattarProvider"):
        from main import ElectricityPricingService

        return ElectricityPricingService()


class TestElectricityPricingServiceInit:
    """Test service initialization and configuration."""

    def test_default_provider(self, service):
        """Service should default to 'awattar' provider."""
        assert service.provider_name == "awattar"

    def test_influxdb_config(self, service):
        """InfluxDB config should be loaded from environment."""
        assert service.influxdb_token == "test-token"
        assert service.influxdb_org == "home_assistant"

    def test_missing_influxdb_token_raises(self, monkeypatch):
        """Should raise ValueError when INFLUXDB_TOKEN is not set."""
        monkeypatch.delenv("INFLUXDB_TOKEN", raising=False)
        with patch("main.AwattarProvider"):
            from main import ElectricityPricingService

            with pytest.raises(ValueError, match="INFLUXDB_TOKEN"):
                ElectricityPricingService()

    def test_fetch_interval_from_env(self, service):
        """Fetch interval should be read from environment."""
        assert service.fetch_interval == 60


class TestFetchPricing:
    """Test pricing data fetching."""

    @pytest.mark.asyncio
    async def test_fetch_pricing_success(self, service):
        """Should return pricing data on successful provider fetch."""
        service.provider = AsyncMock()
        service.provider.fetch_pricing = AsyncMock(
            return_value={"current_price": 0.25, "currency": "EUR", "cheapest_hours": []}
        )
        service.session = MagicMock()
        service.health_handler = MagicMock()
        service.health_handler.total_fetches = 0

        result = await service.fetch_pricing()

        assert result is not None
        assert result["current_price"] == 0.25

    @pytest.mark.asyncio
    async def test_fetch_pricing_returns_cache_on_error(self, service):
        """Should return cached data when provider raises an exception."""
        service.provider = AsyncMock()
        service.provider.fetch_pricing = AsyncMock(side_effect=Exception("API down"))
        service.session = MagicMock()
        service.health_handler = MagicMock()
        service.health_handler.failed_fetches = 0
        service.cached_data = {"current_price": 0.20, "currency": "EUR"}
        from datetime import UTC, datetime

        service.last_fetch_time = datetime.now(UTC)

        result = await service.fetch_pricing()

        assert result == service.cached_data
