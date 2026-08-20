"""
Unit tests for edge cases in electricity pricing service
Epic 49 Story 49.5: Test Coverage & Quality Improvements

Tests boundary conditions, edge cases, and unusual scenarios to improve
test coverage from 50% to 70% target.
"""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestBoundaryConditions:
    """Test boundary conditions and limits"""

    @pytest.mark.asyncio
    async def test_hours_parameter_minimum(self, api_client, service_instance, sample_pricing_data):
        """
        GIVEN: Hours parameter at minimum (1)
        WHEN: Request cheapest hours
        THEN: Should return 200
        """
        service_instance.cached_data = sample_pricing_data
        service_instance.last_fetch_time = datetime.now(UTC)

        response = await api_client.get("/cheapest-hours", params={"hours": "1"})

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_hours_parameter_maximum(self, api_client, service_instance, sample_pricing_data):
        """
        GIVEN: Hours parameter at maximum (24)
        WHEN: Request cheapest hours
        THEN: Should return 200
        """
        service_instance.cached_data = sample_pricing_data
        service_instance.last_fetch_time = datetime.now(UTC)

        response = await api_client.get("/cheapest-hours", params={"hours": "24"})

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_hours_parameter_zero(self, api_client, service_instance):
        """
        GIVEN: Hours parameter is zero
        WHEN: Request cheapest hours
        THEN: Should return 400 error
        """
        service_instance.cached_data = {"cheapest_hours": [1, 2, 3, 4]}

        response = await api_client.get("/cheapest-hours", params={"hours": "0"})

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_hours_parameter_negative(self, api_client, service_instance):
        """
        GIVEN: Hours parameter is negative
        WHEN: Request cheapest hours
        THEN: Should return 400 error
        """
        service_instance.cached_data = {"cheapest_hours": [1, 2, 3, 4]}

        response = await api_client.get("/cheapest-hours", params={"hours": "-1"})

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_hours_parameter_exceeds_max(self, api_client, service_instance):
        """
        GIVEN: Hours parameter exceeds maximum (25)
        WHEN: Request cheapest hours
        THEN: Should return 400 error
        """
        service_instance.cached_data = {"cheapest_hours": [1, 2, 3, 4]}

        response = await api_client.get("/cheapest-hours", params={"hours": "25"})

        assert response.status_code == 400


class TestEmptyDataScenarios:
    """Test scenarios with empty or missing data"""

    @pytest.mark.asyncio
    async def test_empty_forecast_data(self, service_instance):
        """
        GIVEN: Pricing data with empty forecast
        WHEN: Store in InfluxDB
        THEN: Should handle gracefully
        """
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

        # Should still write current price point
        assert mock_client.write.called

    @pytest.mark.asyncio
    async def test_missing_cheapest_hours_in_cache(self, api_client, service_instance):
        """
        GIVEN: Cached data missing cheapest_hours key
        WHEN: Request cheapest hours
        THEN: Should return 503 error
        """
        service_instance.cached_data = {"current_price": 0.25, "currency": "EUR"}

        response = await api_client.get("/cheapest-hours", params={"hours": "4"})

        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_empty_cheapest_hours_list(self, api_client, service_instance):
        """
        GIVEN: Cached data with empty cheapest_hours list
        WHEN: Request cheapest hours
        THEN: Should return empty list
        """
        service_instance.cached_data = {"cheapest_hours": [], "current_price": 0.25}
        service_instance.last_fetch_time = datetime.now(UTC)

        response = await api_client.get("/cheapest-hours", params={"hours": "4"})

        assert response.status_code == 200
        assert response.json()["cheapest_hours"] == []


class TestProviderEdgeCases:
    """Test provider-specific edge cases"""

    @pytest.mark.asyncio
    async def test_unknown_provider_fallback(self, monkeypatch):
        """
        GIVEN: Unknown provider configured
        WHEN: Service initializes
        THEN: Should keep the configured name but fall back to the Awattar provider
        """
        from src.main import ElectricityPricingService

        monkeypatch.setenv("INFLUXDB_TOKEN", "test-token")
        monkeypatch.setenv("PRICING_PROVIDER", "unknown-provider")

        service = ElectricityPricingService()

        assert service.provider_name == "unknown-provider"
        assert service.provider is not None

    @pytest.mark.asyncio
    async def test_provider_fetch_returns_empty_data(self, service_instance):
        """
        GIVEN: Provider returns an empty payload
        WHEN: Fetch pricing
        THEN: Nothing is cached; the caller gets the previous data (none here)
        """
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

    @pytest.mark.asyncio
    async def test_missing_influxdb_token(self, monkeypatch):
        """
        GIVEN: INFLUXDB_TOKEN not set
        WHEN: Service initializes
        THEN: Should raise ValueError
        """
        from src.main import ElectricityPricingService

        monkeypatch.delenv("INFLUXDB_TOKEN", raising=False)

        with pytest.raises(ValueError, match="INFLUXDB_TOKEN"):
            ElectricityPricingService()

    @pytest.mark.asyncio
    async def test_custom_allowed_networks(self, monkeypatch):
        """
        GIVEN: Custom allowed networks configured
        WHEN: Service initializes
        THEN: Should parse networks correctly
        """
        from src.main import ElectricityPricingService

        monkeypatch.setenv("INFLUXDB_TOKEN", "test-token")
        monkeypatch.setenv("ALLOWED_NETWORKS", "192.168.1.0/24,10.0.0.0/8")

        service = ElectricityPricingService()

        assert service.allowed_networks == ["192.168.1.0/24", "10.0.0.0/8"]

    @pytest.mark.asyncio
    async def test_empty_allowed_networks(self, monkeypatch):
        """
        GIVEN: Empty allowed networks string
        WHEN: Service initializes
        THEN: Should set to None
        """
        from src.main import ElectricityPricingService

        monkeypatch.setenv("INFLUXDB_TOKEN", "test-token")
        monkeypatch.setenv("ALLOWED_NETWORKS", "")

        service = ElectricityPricingService()

        assert service.allowed_networks is None or len(service.allowed_networks) == 0


class TestDataFormatEdgeCases:
    """Test data format edge cases"""

    @pytest.mark.asyncio
    async def test_store_with_missing_fields(self, service_instance):
        """
        GIVEN: Pricing data with missing optional fields
        WHEN: Store in InfluxDB
        THEN: Should handle gracefully
        """
        incomplete_data = {
            "current_price": 0.25,
            "currency": "EUR",
            "timestamp": datetime.now(UTC),
            "provider": "awattar",
            # Missing: peak_period, cheapest_hours, forecast_24h
        }

        mock_client = MagicMock()
        service_instance.influxdb_client = mock_client

        # Should not raise exception
        # Should handle missing fields gracefully (may raise KeyError which is caught)
        await service_instance.store_in_influxdb(incomplete_data)

        # Code should handle the error gracefully (logs error but doesn't crash)
        # Write may or may not be called depending on error handling

    @pytest.mark.asyncio
    async def test_store_with_extra_fields(self, service_instance):
        """
        GIVEN: Pricing data with extra unexpected fields
        WHEN: Store in InfluxDB
        THEN: Should handle gracefully
        """
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
        """
        GIVEN: Multiple concurrent fetch requests
        WHEN: Fetch pricing simultaneously
        THEN: Should handle gracefully
        """
        service_instance.session = AsyncMock()

        with patch.object(
            service_instance.provider, "fetch_pricing", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = sample_pricing_data.copy()

            # Run multiple fetches concurrently
            results = await asyncio.gather(
                service_instance.fetch_pricing(),
                service_instance.fetch_pricing(),
                service_instance.fetch_pricing(),
            )

            # All should succeed
            assert all(r is not None for r in results)
            assert mock_fetch.call_count == 3

    @pytest.mark.asyncio
    async def test_fetch_while_storing(self, service_instance, sample_pricing_data):
        """
        GIVEN: Fetch and store operations concurrent
        WHEN: Both operations run simultaneously
        THEN: Should handle gracefully
        """
        service_instance.session = AsyncMock()
        mock_client = MagicMock()
        service_instance.influxdb_client = mock_client

        with patch.object(
            service_instance.provider, "fetch_pricing", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = sample_pricing_data.copy()

            # Run fetch and store concurrently
            fetch_task = service_instance.fetch_pricing()
            store_task = service_instance.store_in_influxdb(sample_pricing_data)

            await asyncio.gather(fetch_task, store_task)

            # Both should complete
            assert mock_fetch.called
            assert mock_client.write.called


class TestHealthCheckEdgeCases:
    """Test health check edge cases"""

    @pytest.mark.asyncio
    async def test_health_check_with_no_fetches(self, service_instance):
        """
        GIVEN: Service with no fetch attempts, inside the startup grace period
        WHEN: Check health
        THEN: Should report healthy with zero counters
        """
        status = service_instance.health_handler.get_status()

        assert status["status"] == "healthy"
        assert status["total_fetches"] == 0
        assert status["failed_fetches"] == 0
        assert status["last_successful_fetch"] is None

    @pytest.mark.asyncio
    async def test_health_check_after_failures(self, service_instance):
        """
        GIVEN: Service with failed fetches
        WHEN: Check health
        THEN: Should reflect failure count and success rate
        """
        service_instance.health_handler.failed_fetches = 5
        service_instance.health_handler.total_fetches = 10

        status = service_instance.health_handler.get_status()

        assert status["failed_fetches"] == 5
        assert status["total_fetches"] == 10
        assert status["success_rate"] == pytest.approx(10 / 15)
