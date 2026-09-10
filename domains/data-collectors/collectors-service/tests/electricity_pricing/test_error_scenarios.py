"""Unit tests for error scenarios in the electricity-pricing adapter.

Tests provider API failures, InfluxDB connection failures, network timeouts,
and cache expiration scenarios.
"""

import asyncio
import contextlib
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestProviderAPIFailures:
    """Test provider API failure scenarios"""

    @pytest.mark.asyncio
    async def test_provider_api_connection_failure(self, service_instance):
        """GIVEN: Provider API unreachable | WHEN: Fetch | THEN: None, failure counted"""
        service_instance.session = AsyncMock()

        with patch.object(
            service_instance.provider, "fetch_pricing", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.side_effect = ConnectionError("Connection refused")

            result = await service_instance.fetch_pricing()
            assert result is None
            assert service_instance.health_handler.failed_fetches > 0

    @pytest.mark.asyncio
    async def test_provider_api_timeout(self, service_instance):
        """GIVEN: Provider API times out | WHEN: Fetch | THEN: Handled gracefully"""
        service_instance.session = AsyncMock()

        with patch.object(
            service_instance.provider, "fetch_pricing", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.side_effect = TimeoutError("Request timeout")

            result = await service_instance.fetch_pricing()
            assert result is None
            assert service_instance.health_handler.failed_fetches > 0

    @pytest.mark.asyncio
    async def test_provider_api_http_error(self, service_instance):
        """GIVEN: Provider API returns HTTP error | WHEN: Fetch | THEN: Handled gracefully"""
        service_instance.session = AsyncMock()

        with patch.object(
            service_instance.provider, "fetch_pricing", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.side_effect = Exception("Awattar API returned status 500")

            result = await service_instance.fetch_pricing()
            assert result is None
            assert service_instance.health_handler.failed_fetches > 0

    @pytest.mark.asyncio
    async def test_provider_api_invalid_response_format(self, service_instance):
        """GIVEN: Provider API returns invalid JSON | WHEN: Fetch | THEN: Handled gracefully"""
        service_instance.session = AsyncMock()

        with patch.object(
            service_instance.provider, "fetch_pricing", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.side_effect = ValueError("Invalid JSON response")

            result = await service_instance.fetch_pricing()
            assert result is None

    @pytest.mark.asyncio
    async def test_provider_api_fallback_to_cache(self, service_instance, sample_pricing_data):
        """GIVEN: Provider fails, cache exists | WHEN: Fetch | THEN: Return cached data"""
        service_instance.cached_data = sample_pricing_data.copy()
        service_instance.last_fetch_time = datetime.now(UTC)
        service_instance.session = AsyncMock()

        with patch.object(
            service_instance.provider, "fetch_pricing", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.side_effect = Exception("API error")

            result = await service_instance.fetch_pricing()

            assert result is not None
            assert result == service_instance.cached_data


class TestInfluxDBFailures:
    """Test InfluxDB connection and write failures"""

    @pytest.mark.asyncio
    async def test_influxdb_connection_failure(self, service_instance, sample_pricing_data):
        """GIVEN: InfluxDB unreachable | WHEN: Store | THEN: Handled gracefully"""
        mock_client = MagicMock()
        mock_client.write.side_effect = Exception("Connection refused")
        service_instance.influxdb_client = mock_client

        await service_instance.store_in_influxdb(sample_pricing_data)

        assert mock_client.write.called

    @pytest.mark.asyncio
    async def test_influxdb_write_failure(self, service_instance, sample_pricing_data):
        """GIVEN: InfluxDB write fails | WHEN: Store | THEN: Handled gracefully"""
        mock_client = MagicMock()
        mock_client.write.side_effect = Exception("Write failed")
        service_instance.influxdb_client = mock_client

        await service_instance.store_in_influxdb(sample_pricing_data)

    @pytest.mark.asyncio
    async def test_influxdb_timeout(self, service_instance, sample_pricing_data):
        """GIVEN: InfluxDB write times out | WHEN: Store | THEN: Handled gracefully"""
        mock_client = MagicMock()
        mock_client.write.side_effect = TimeoutError("InfluxDB timeout")
        service_instance.influxdb_client = mock_client

        await service_instance.store_in_influxdb(sample_pricing_data)

    @pytest.mark.asyncio
    async def test_influxdb_client_not_initialized(self, service_instance, sample_pricing_data):
        """GIVEN: InfluxDB client is None | WHEN: Store | THEN: Handled gracefully"""
        service_instance.influxdb_client = None

        await service_instance.store_in_influxdb(sample_pricing_data)


class TestNetworkTimeouts:
    """Test network timeout scenarios"""

    @pytest.mark.asyncio
    async def test_http_timeout_during_fetch(self, service_instance):
        """GIVEN: HTTP request times out | WHEN: Fetch | THEN: Handled gracefully"""
        service_instance.session = AsyncMock()

        with patch.object(
            service_instance.provider, "fetch_pricing", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.side_effect = TimeoutError("Request timeout")

            result = await service_instance.fetch_pricing()
            assert result is None

    @pytest.mark.asyncio
    async def test_connection_timeout(self, service_instance):
        """GIVEN: Connection times out | WHEN: Fetch | THEN: Handled gracefully"""
        service_instance.session = AsyncMock()

        with patch.object(
            service_instance.provider, "fetch_pricing", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.side_effect = ConnectionError("Connection timeout")

            result = await service_instance.fetch_pricing()
            assert result is None


class TestCacheExpiration:
    """Test cache expiration scenarios"""

    @pytest.mark.asyncio
    async def test_cache_expiration_returns_nothing(self, service_instance, sample_pricing_data):
        """GIVEN: Cache older than cache_duration | WHEN: Provider fails | THEN: None, failure counted"""
        service_instance.cached_data = sample_pricing_data.copy()
        service_instance.last_fetch_time = datetime.now(UTC) - timedelta(
            minutes=service_instance.cache_duration + 1
        )
        service_instance.session = AsyncMock()

        with patch.object(
            service_instance.provider, "fetch_pricing", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.side_effect = Exception("API error")

            result = await service_instance.fetch_pricing()

        assert result is None
        assert service_instance.health_handler.failed_fetches == 1

    @pytest.mark.asyncio
    async def test_no_cache_on_first_fetch_failure(self, service_instance):
        """GIVEN: No cache, provider fails | WHEN: Fetch | THEN: None"""
        service_instance.cached_data = None
        service_instance.session = AsyncMock()

        with patch.object(
            service_instance.provider, "fetch_pricing", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.side_effect = Exception("API error")

            result = await service_instance.fetch_pricing()
            assert result is None


class TestAPIEndpointErrors:
    """Test API endpoint error scenarios (network-restriction 403 is covered directly
    against `require_internal_network` in test_security.py rather than round-tripped
    through a second TestClient — a second lifespan cycle over the shared app would
    reassign every other adapter's module-level service singleton mid-suite)."""

    def test_cheapest_hours_invalid_parameter(self, api_client, service_instance):
        """GIVEN: Invalid hours parameter | WHEN: Request | THEN: 400"""
        service_instance.cached_data = {"cheapest_hours": [1, 2, 3, 4]}

        response = api_client.get("/cheapest-hours", params={"hours": "invalid"})

        assert response.status_code == 400

    def test_cheapest_hours_out_of_bounds(self, api_client, service_instance):
        """GIVEN: Hours parameter out of bounds | WHEN: Request | THEN: 400"""
        service_instance.cached_data = {"cheapest_hours": [1, 2, 3, 4]}

        response = api_client.get("/cheapest-hours", params={"hours": "25"})

        assert response.status_code == 400


class TestContinuousLoopErrors:
    """Test error handling in continuous loop"""

    @pytest.mark.asyncio
    async def test_continuous_loop_handles_fetch_error(self, service_instance):
        """GIVEN: Fetch fails in continuous loop | WHEN: Run | THEN: Wait and retry"""
        service_instance.session = AsyncMock()

        with patch.object(
            service_instance.provider, "fetch_pricing", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.side_effect = Exception("API error")

            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                task = asyncio.create_task(service_instance.run_continuous())

                await asyncio.sleep(0.1)
                task.cancel()

                with contextlib.suppress(asyncio.CancelledError):
                    await task

                assert mock_sleep.called

    @pytest.mark.asyncio
    async def test_continuous_loop_handles_store_error(self, service_instance, sample_pricing_data):
        """GIVEN: Store fails in continuous loop | WHEN: Run | THEN: Continue without crashing"""
        service_instance.session = AsyncMock()

        with patch.object(
            service_instance.provider, "fetch_pricing", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = sample_pricing_data.copy()

            with patch.object(
                service_instance, "store_in_influxdb", new_callable=AsyncMock
            ) as mock_store:
                mock_store.side_effect = Exception("Store failed")

                call_count = 0

                async def mock_sleep(_delay):
                    nonlocal call_count
                    call_count += 1
                    if call_count > 1:
                        raise asyncio.CancelledError()

                with patch("asyncio.sleep", side_effect=mock_sleep):
                    task = asyncio.create_task(service_instance.run_continuous())

                    with contextlib.suppress(asyncio.CancelledError):
                        await task

                    assert mock_fetch.called
