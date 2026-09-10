"""Unit tests for edge cases in the electricity-pricing adapter.

Tests boundary conditions, edge cases, and unusual scenarios.
"""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestBoundaryConditions:
    """Test boundary conditions and limits"""

    def test_hours_parameter_minimum(self, api_client, service_instance, sample_pricing_data):
        """GIVEN: Hours at minimum (1) | WHEN: Request | THEN: 200"""
        service_instance.cached_data = sample_pricing_data
        service_instance.last_fetch_time = datetime.now(UTC)

        response = api_client.get("/cheapest-hours", params={"hours": "1"})

        assert response.status_code == 200

    def test_hours_parameter_maximum(self, api_client, service_instance, sample_pricing_data):
        """GIVEN: Hours at maximum (24) | WHEN: Request | THEN: 200"""
        service_instance.cached_data = sample_pricing_data
        service_instance.last_fetch_time = datetime.now(UTC)

        response = api_client.get("/cheapest-hours", params={"hours": "24"})

        assert response.status_code == 200

    def test_hours_parameter_zero(self, api_client, service_instance):
        """GIVEN: Hours is zero | WHEN: Request | THEN: 400"""
        service_instance.cached_data = {"cheapest_hours": [1, 2, 3, 4]}

        response = api_client.get("/cheapest-hours", params={"hours": "0"})

        assert response.status_code == 400

    def test_hours_parameter_negative(self, api_client, service_instance):
        """GIVEN: Hours is negative | WHEN: Request | THEN: 400"""
        service_instance.cached_data = {"cheapest_hours": [1, 2, 3, 4]}

        response = api_client.get("/cheapest-hours", params={"hours": "-1"})

        assert response.status_code == 400

    def test_hours_parameter_exceeds_max(self, api_client, service_instance):
        """GIVEN: Hours exceeds maximum (25) | WHEN: Request | THEN: 400"""
        service_instance.cached_data = {"cheapest_hours": [1, 2, 3, 4]}

        response = api_client.get("/cheapest-hours", params={"hours": "25"})

        assert response.status_code == 400


class TestEmptyDataScenarios:
    """Test scenarios with empty or missing data"""

    @pytest.mark.asyncio
    async def test_empty_forecast_data(self, service_instance):
        """GIVEN: Pricing data with empty forecast | WHEN: Store | THEN: Handle gracefully"""
        empty_data = {
            "current_price": 0.25,
            "currency": "EUR",
            "peak_period": False,
            "cheapest_hours": [],
            "most_expensive_hours": [],
            "forecast_24h": [],
            "timestamp": datetime.now(UTC),
            "provider": "awattar",
        }

        mock_client = MagicMock()
        service_instance.influxdb_client = mock_client

        await service_instance.store_in_influxdb(empty_data)

        assert mock_client.write.called

    def test_missing_cheapest_hours_in_cache(self, api_client, service_instance):
        """GIVEN: Cache missing cheapest_hours key | WHEN: Request | THEN: 503"""
        service_instance.cached_data = {"current_price": 0.25, "currency": "EUR"}

        response = api_client.get("/cheapest-hours", params={"hours": "4"})

        assert response.status_code == 503

    def test_empty_cheapest_hours_list(self, api_client, service_instance):
        """GIVEN: Cache with empty cheapest_hours list | WHEN: Request | THEN: Empty list"""
        service_instance.cached_data = {"cheapest_hours": [], "current_price": 0.25}
        service_instance.last_fetch_time = datetime.now(UTC)

        response = api_client.get("/cheapest-hours", params={"hours": "4"})

        assert response.status_code == 200
        assert response.json()["cheapest_hours"] == []


class TestProviderEdgeCases:
    """Test provider-specific edge cases"""

    def test_unknown_provider_fallback(self, monkeypatch):
        """GIVEN: Unknown provider | WHEN: Init | THEN: Keep name, fall back to Awattar"""
        from src.adapters.electricity_pricing import ElectricityPricingService

        monkeypatch.setenv("INFLUXDB_TOKEN", "test-token")
        monkeypatch.setenv("PRICING_PROVIDER", "unknown-provider")

        service = ElectricityPricingService()

        assert service.provider_name == "unknown-provider"
        assert service.provider is not None

    @pytest.mark.asyncio
    async def test_provider_fetch_returns_empty_data(self, service_instance):
        """GIVEN: Provider returns empty payload | WHEN: Fetch | THEN: Nothing cached"""
        service_instance.session = AsyncMock()

        with patch.object(
            service_instance.provider, "fetch_pricing", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = {}

            result = await service_instance.fetch_pricing()

        assert result is None
        assert service_instance.cached_data is None


class TestConfigurationEdgeCases:
    """Test configuration edge cases"""

    def test_missing_influxdb_token(self, monkeypatch):
        """GIVEN: INFLUXDB_TOKEN not set | WHEN: Init | THEN: Raise ValueError"""
        from src.adapters.electricity_pricing import ElectricityPricingService

        monkeypatch.delenv("INFLUXDB_TOKEN", raising=False)

        with pytest.raises(ValueError, match="INFLUXDB_TOKEN"):
            ElectricityPricingService()

    def test_custom_allowed_networks(self, monkeypatch):
        """GIVEN: Custom allowed networks | WHEN: Init | THEN: Parse correctly"""
        from src.adapters.electricity_pricing import ElectricityPricingService

        monkeypatch.setenv("INFLUXDB_TOKEN", "test-token")
        monkeypatch.setenv("ALLOWED_NETWORKS", "192.168.1.0/24,10.0.0.0/8")

        service = ElectricityPricingService()

        assert service.allowed_networks == ["192.168.1.0/24", "10.0.0.0/8"]

    def test_empty_allowed_networks(self, monkeypatch):
        """GIVEN: Empty allowed-networks string | WHEN: Init | THEN: None"""
        from src.adapters.electricity_pricing import ElectricityPricingService

        monkeypatch.setenv("INFLUXDB_TOKEN", "test-token")
        monkeypatch.setenv("ALLOWED_NETWORKS", "")

        service = ElectricityPricingService()

        assert service.allowed_networks is None or len(service.allowed_networks) == 0


class TestDataFormatEdgeCases:
    """Test data format edge cases"""

    @pytest.mark.asyncio
    async def test_store_with_missing_fields(self, service_instance):
        """GIVEN: Data missing optional fields | WHEN: Store | THEN: Handle gracefully"""
        incomplete_data = {
            "current_price": 0.25,
            "currency": "EUR",
            "timestamp": datetime.now(UTC),
            "provider": "awattar",
        }

        mock_client = MagicMock()
        service_instance.influxdb_client = mock_client

        await service_instance.store_in_influxdb(incomplete_data)

    @pytest.mark.asyncio
    async def test_store_with_extra_fields(self, service_instance):
        """GIVEN: Data with extra unexpected fields | WHEN: Store | THEN: Handle gracefully"""
        extra_data = {
            "current_price": 0.25,
            "currency": "EUR",
            "peak_period": False,
            "cheapest_hours": [1, 2, 3, 4],
            "forecast_24h": [],
            "timestamp": datetime.now(UTC),
            "provider": "awattar",
            "extra_field": "should be ignored",
        }

        mock_client = MagicMock()
        service_instance.influxdb_client = mock_client

        await service_instance.store_in_influxdb(extra_data)

        assert mock_client.write.called


class TestConcurrentOperations:
    """Test concurrent operation scenarios"""

    @pytest.mark.asyncio
    async def test_concurrent_fetches(self, service_instance, sample_pricing_data):
        """GIVEN: Multiple concurrent fetches | WHEN: Fetch simultaneously | THEN: All succeed"""
        service_instance.session = AsyncMock()

        with patch.object(
            service_instance.provider, "fetch_pricing", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = sample_pricing_data.copy()

            results = await asyncio.gather(
                service_instance.fetch_pricing(),
                service_instance.fetch_pricing(),
                service_instance.fetch_pricing(),
            )

            assert all(r is not None for r in results)
            assert mock_fetch.call_count == 3

    @pytest.mark.asyncio
    async def test_fetch_while_storing(self, service_instance, sample_pricing_data):
        """GIVEN: Fetch and store concurrent | WHEN: Both run | THEN: Both complete"""
        service_instance.session = AsyncMock()
        mock_client = MagicMock()
        service_instance.influxdb_client = mock_client

        with patch.object(
            service_instance.provider, "fetch_pricing", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = sample_pricing_data.copy()

            fetch_task = service_instance.fetch_pricing()
            store_task = service_instance.store_in_influxdb(sample_pricing_data)

            await asyncio.gather(fetch_task, store_task)

            assert mock_fetch.called
            assert mock_client.write.called


class TestHealthCheckEdgeCases:
    """Test health check edge cases"""

    def test_health_check_with_no_fetches(self, service_instance):
        """GIVEN: No fetch attempts | WHEN: Check health | THEN: Healthy with zero counters"""
        status = service_instance.health_handler.get_status()

        assert status["status"] == "healthy"
        assert status["total_fetches"] == 0
        assert status["failed_fetches"] == 0
        assert status["last_successful_fetch"] is None

    def test_health_check_after_failures(self, service_instance):
        """GIVEN: Failed fetches | WHEN: Check health | THEN: Reflect failure count/success rate"""
        service_instance.health_handler.failed_fetches = 5
        service_instance.health_handler.total_fetches = 10

        status = service_instance.health_handler.get_status()

        assert status["failed_fetches"] == 5
        assert status["total_fetches"] == 10
        assert status["success_rate"] == pytest.approx(10 / 15)
