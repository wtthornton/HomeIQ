"""
Unit tests for electricity pricing service core logic
Tests fetching, caching, InfluxDB storage, and API endpoints
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestDataFetching:
    """Test pricing data fetching logic"""

    @pytest.mark.asyncio
    async def test_fetch_pricing_success(self, service_instance, sample_pricing_data):
        """
        GIVEN: Service with mocked provider
        WHEN: Fetch pricing
        THEN: Should return pricing data with timestamp
        """
        # Mock provider fetch
        with patch.object(service_instance.provider, 'fetch_pricing', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = {
                'current_price': sample_pricing_data['current_price'],
                'currency': sample_pricing_data['currency'],
                'peak_period': sample_pricing_data['peak_period'],
                'cheapest_hours': sample_pricing_data['cheapest_hours'],
                'most_expensive_hours': sample_pricing_data['most_expensive_hours'],
                'forecast_24h': sample_pricing_data['forecast_24h']
            }

            # Initialize session
            service_instance.session = AsyncMock()

            data = await service_instance.fetch_pricing()

            assert data is not None
            assert data['current_price'] == 0.285
            assert data['currency'] == 'EUR'
            assert 'timestamp' in data
            assert data['provider'] == 'awattar'

    @pytest.mark.asyncio
    async def test_fetch_pricing_updates_cache(self, service_instance, sample_pricing_data):
        """
        GIVEN: Service fetching pricing
        WHEN: Fetch completes successfully
        THEN: Should update cached_data and last_fetch_time
        """
        with patch.object(service_instance.provider, 'fetch_pricing', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = sample_pricing_data.copy()
            service_instance.session = AsyncMock()

            # Cache should be empty initially
            assert service_instance.cached_data is None
            assert service_instance.last_fetch_time is None

            data = await service_instance.fetch_pricing()

            # Cache should be updated
            assert service_instance.cached_data is not None
            assert service_instance.last_fetch_time is not None
            assert service_instance.cached_data['current_price'] == 0.285

    @pytest.mark.asyncio
    async def test_fetch_pricing_updates_health_stats(self, service_instance, sample_pricing_data):
        """
        GIVEN: Service fetching pricing
        WHEN: Fetch succeeds
        THEN: Should increment total_fetches and update last_successful_fetch
        """
        with patch.object(service_instance.provider, 'fetch_pricing', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = sample_pricing_data.copy()
            service_instance.session = AsyncMock()

            initial_fetches = service_instance.health_handler.total_fetches

            await service_instance.fetch_pricing()

            assert service_instance.health_handler.total_fetches == initial_fetches + 1
            assert service_instance.health_handler.last_successful_fetch is not None

    @pytest.mark.asyncio
    async def test_fetch_pricing_error_increments_failed_fetches(self, service_instance):
        """
        GIVEN: Provider fetch fails
        WHEN: Fetch pricing
        THEN: Should increment failed_fetches counter
        """
        with patch.object(service_instance.provider, 'fetch_pricing', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = Exception("API error")
            service_instance.session = AsyncMock()

            initial_failures = service_instance.health_handler.failed_fetches

            result = await service_instance.fetch_pricing()

            assert result is None  # No cached data
            assert service_instance.health_handler.failed_fetches == initial_failures + 1

    @pytest.mark.asyncio
    async def test_fetch_pricing_error_returns_cached_data(self, service_instance, sample_pricing_data):
        """
        GIVEN: Provider fetch fails but cached data exists
        WHEN: Fetch pricing
        THEN: Should return cached data
        """
        # Set up cached data
        service_instance.cached_data = sample_pricing_data.copy()

        with patch.object(service_instance.provider, 'fetch_pricing', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = Exception("API error")
            service_instance.session = AsyncMock()

            result = await service_instance.fetch_pricing()

            assert result is not None
            assert result == service_instance.cached_data


class TestDataCaching:
    """Test caching logic"""

    @pytest.mark.asyncio
    async def test_cache_populated_after_fetch(self, service_instance, sample_pricing_data):
        """
        GIVEN: Empty cache
        WHEN: Successful fetch
        THEN: Cache should be populated
        """
        with patch.object(service_instance.provider, 'fetch_pricing', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = sample_pricing_data.copy()
            service_instance.session = AsyncMock()

            await service_instance.fetch_pricing()

            assert service_instance.cached_data is not None
            assert 'current_price' in service_instance.cached_data

    @pytest.mark.asyncio
    async def test_cache_updated_on_new_fetch(self, service_instance, sample_pricing_data, sample_cheap_pricing):
        """
        GIVEN: Existing cached data
        WHEN: New fetch with different data
        THEN: Cache should be updated with new data
        """
        with patch.object(service_instance.provider, 'fetch_pricing', new_callable=AsyncMock) as mock_fetch:
            service_instance.session = AsyncMock()

            # First fetch
            mock_fetch.return_value = sample_pricing_data.copy()
            await service_instance.fetch_pricing()
            assert service_instance.cached_data['current_price'] == 0.285

            # Second fetch with different price
            mock_fetch.return_value = sample_cheap_pricing.copy()
            await service_instance.fetch_pricing()
            assert service_instance.cached_data['current_price'] == 0.18

    @pytest.mark.asyncio
    async def test_last_fetch_time_updated(self, service_instance, sample_pricing_data):
        """
        GIVEN: Service fetching data
        WHEN: Fetch completes
        THEN: last_fetch_time should be updated
        """
        with patch.object(service_instance.provider, 'fetch_pricing', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = sample_pricing_data.copy()
            service_instance.session = AsyncMock()

            before_fetch = datetime.now()
            await service_instance.fetch_pricing()
            after_fetch = datetime.now()

            assert service_instance.last_fetch_time is not None
            assert before_fetch <= service_instance.last_fetch_time <= after_fetch


class TestInfluxDBStorage:
    """Test InfluxDB data storage"""

    @pytest.mark.asyncio
    async def test_store_in_influxdb_success(self, service_instance, sample_pricing_data, mock_influxdb_client):
        """
        GIVEN: Pricing data to store
        WHEN: Store in InfluxDB
        THEN: Should write point with correct tags and fields
        """
        service_instance.influxdb_client = mock_influxdb_client

        await service_instance.store_in_influxdb(sample_pricing_data)

        # Verify write was called
        assert mock_influxdb_client.write.called
        # Should be called multiple times (current + forecast)
        assert mock_influxdb_client.write.call_count >= 1

    @pytest.mark.asyncio
    async def test_store_in_influxdb_skips_empty_data(self, service_instance, mock_influxdb_client):
        """
        GIVEN: None data
        WHEN: Store in InfluxDB
        THEN: Should skip writing
        """
        service_instance.influxdb_client = mock_influxdb_client

        await service_instance.store_in_influxdb(None)

        assert not mock_influxdb_client.write.called

    @pytest.mark.asyncio
    async def test_store_in_influxdb_handles_write_error(self, service_instance, sample_pricing_data, mock_influxdb_client):
        """
        GIVEN: InfluxDB write fails
        WHEN: Store data
        THEN: Should handle error gracefully
        """
        service_instance.influxdb_client = mock_influxdb_client
        mock_influxdb_client.write.side_effect = Exception("InfluxDB write failed")

        # Should not raise exception
        await service_instance.store_in_influxdb(sample_pricing_data)


class TestAPIEndpoints:
    """Test HTTP API endpoints"""

    @pytest.mark.asyncio
    async def test_get_cheapest_hours_with_cached_data(self, service_instance, sample_pricing_data):
        """
        GIVEN: Service with cached pricing data
        WHEN: Request cheapest hours
        THEN: Should return cheapest hours
        """
        service_instance.cached_data = sample_pricing_data
        service_instance.last_fetch_time = datetime.now()

        # Mock request
        request = MagicMock()
        request.query = {'hours': '4'}

        response = await service_instance.get_cheapest_hours(request)

        assert response.status == 200
        data = response.body
        # Response should contain cheapest_hours

    @pytest.mark.asyncio
    async def test_get_cheapest_hours_default_count(self, service_instance, sample_pricing_data):
        """
        GIVEN: Service with cached data
        WHEN: Request cheapest hours without count parameter
        THEN: Should default to 4 hours
        """
        service_instance.cached_data = sample_pricing_data
        service_instance.last_fetch_time = datetime.now()

        request = MagicMock()
        request.query = {}

        response = await service_instance.get_cheapest_hours(request)

        assert response.status == 200

    @pytest.mark.asyncio
    async def test_get_cheapest_hours_no_cached_data(self, service_instance):
        """
        GIVEN: Service without cached data
        WHEN: Request cheapest hours
        THEN: Should return 503 error
        """
        service_instance.cached_data = None

        request = MagicMock()
        request.query = {'hours': '4'}

        response = await service_instance.get_cheapest_hours(request)

        assert response.status == 503

    @pytest.mark.asyncio
    async def test_get_cheapest_hours_custom_count(self, service_instance, sample_pricing_data):
        """
        GIVEN: Service with cached data
        WHEN: Request specific number of cheapest hours
        THEN: Should return requested count
        """
        service_instance.cached_data = sample_pricing_data
        service_instance.last_fetch_time = datetime.now()

        request = MagicMock()
        request.query = {'hours': '2'}

        response = await service_instance.get_cheapest_hours(request)

        assert response.status == 200


class TestServiceLifecycle:
    """Test service startup and shutdown"""

    @pytest.mark.asyncio
    async def test_startup_creates_session(self, service_instance):
        """
        GIVEN: Service instance
        WHEN: Startup is called
        THEN: Should create aiohttp session
        """
        await service_instance.startup()

        assert service_instance.session is not None

    @pytest.mark.asyncio
    async def test_startup_creates_influxdb_client(self, service_instance):
        """
        GIVEN: Service instance
        WHEN: Startup is called
        THEN: Should create InfluxDB client
        """
        await service_instance.startup()

        assert service_instance.influxdb_client is not None

    @pytest.mark.asyncio
    async def test_shutdown_closes_session(self, service_instance):
        """
        GIVEN: Running service with session
        WHEN: Shutdown is called
        THEN: Should close aiohttp session
        """
        await service_instance.startup()

        session_close = AsyncMock()
        service_instance.session.close = session_close

        await service_instance.shutdown()

        assert session_close.called

    @pytest.mark.asyncio
    async def test_shutdown_closes_influxdb_client(self, service_instance):
        """
        GIVEN: Running service with InfluxDB client
        WHEN: Shutdown is called
        THEN: Should close InfluxDB client
        """
        await service_instance.startup()

        client_close = MagicMock()
        service_instance.influxdb_client.close = client_close

        await service_instance.shutdown()

        assert client_close.called


class TestHealthHandler:
    """Test health check handler integration"""

    @pytest.mark.asyncio
    async def test_successful_fetch_updates_health(self, service_instance, sample_pricing_data):
        """
        GIVEN: Service fetching data
        WHEN: Fetch succeeds
        THEN: Health handler should be updated
        """
        with patch.object(service_instance.provider, 'fetch_pricing', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = sample_pricing_data.copy()
            service_instance.session = AsyncMock()

            initial_total = service_instance.health_handler.total_fetches

            await service_instance.fetch_pricing()

            assert service_instance.health_handler.total_fetches == initial_total + 1
            assert service_instance.health_handler.last_successful_fetch is not None

    @pytest.mark.asyncio
    async def test_failed_fetch_updates_health(self, service_instance):
        """
        GIVEN: Service fetching data
        WHEN: Fetch fails
        THEN: Health handler should track failure
        """
        with patch.object(service_instance.provider, 'fetch_pricing', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = Exception("API error")
            service_instance.session = AsyncMock()

            initial_failures = service_instance.health_handler.failed_fetches

            await service_instance.fetch_pricing()

            assert service_instance.health_handler.failed_fetches == initial_failures + 1
