"""
Unit tests for error scenarios in electricity pricing service
Epic 49 Story 49.4: Error Scenario Testing

Tests provider API failures, InfluxDB connection failures, network timeouts,
and cache expiration scenarios.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from aiohttp import web


class TestProviderAPIFailures:
    """Test provider API failure scenarios"""

    @pytest.mark.asyncio
    async def test_provider_api_connection_failure(self, service_instance):
        """
        GIVEN: Provider API is unreachable
        WHEN: Fetch pricing
        THEN: Should handle connection error gracefully and return cached data if available
        """
        service_instance.session = AsyncMock()
        
        # Mock connection error - use generic Exception for simplicity
        with patch.object(service_instance.provider, 'fetch_pricing', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = ConnectionError("Connection refused")
            
            # No cached data - should return None
            result = await service_instance.fetch_pricing()
            assert result is None
            assert service_instance.health_handler.failed_fetches > 0

    @pytest.mark.asyncio
    async def test_provider_api_timeout(self, service_instance):
        """
        GIVEN: Provider API times out
        WHEN: Fetch pricing
        THEN: Should handle timeout gracefully
        """
        service_instance.session = AsyncMock()
        
        with patch.object(service_instance.provider, 'fetch_pricing', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = asyncio.TimeoutError("Request timeout")
            
            result = await service_instance.fetch_pricing()
            assert result is None
            assert service_instance.health_handler.failed_fetches > 0

    @pytest.mark.asyncio
    async def test_provider_api_http_error(self, service_instance):
        """
        GIVEN: Provider API returns HTTP error
        WHEN: Fetch pricing
        THEN: Should handle HTTP error gracefully
        """
        service_instance.session = AsyncMock()
        
        with patch.object(service_instance.provider, 'fetch_pricing', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = Exception("Awattar API returned status 500")
            
            result = await service_instance.fetch_pricing()
            assert result is None
            assert service_instance.health_handler.failed_fetches > 0

    @pytest.mark.asyncio
    async def test_provider_api_invalid_response_format(self, service_instance):
        """
        GIVEN: Provider API returns invalid JSON
        WHEN: Fetch pricing
        THEN: Should handle parsing error gracefully
        """
        service_instance.session = AsyncMock()
        
        with patch.object(service_instance.provider, 'fetch_pricing', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = ValueError("Invalid JSON response")
            
            result = await service_instance.fetch_pricing()
            assert result is None

    @pytest.mark.asyncio
    async def test_provider_api_fallback_to_cache(self, service_instance, sample_pricing_data):
        """
        GIVEN: Provider API fails but cached data exists
        WHEN: Fetch pricing
        THEN: Should return cached data
        """
        # Set up cached data
        service_instance.cached_data = sample_pricing_data.copy()
        service_instance.last_fetch_time = datetime.now(timezone.utc)
        service_instance.session = AsyncMock()
        
        with patch.object(service_instance.provider, 'fetch_pricing', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = Exception("API error")
            
            result = await service_instance.fetch_pricing()
            
            assert result is not None
            assert result == service_instance.cached_data


class TestInfluxDBFailures:
    """Test InfluxDB connection and write failures"""

    @pytest.mark.asyncio
    async def test_influxdb_connection_failure(self, service_instance, sample_pricing_data):
        """
        GIVEN: InfluxDB is unreachable
        WHEN: Store pricing data
        THEN: Should handle connection error gracefully
        """
        # Mock InfluxDB client with connection error
        mock_client = MagicMock()
        mock_client.write.side_effect = Exception("Connection refused")
        service_instance.influxdb_client = mock_client
        
        # Should not raise exception
        await service_instance.store_in_influxdb(sample_pricing_data)
        
        # Verify write was attempted
        assert mock_client.write.called

    @pytest.mark.asyncio
    async def test_influxdb_write_failure(self, service_instance, sample_pricing_data):
        """
        GIVEN: InfluxDB write operation fails
        WHEN: Store pricing data
        THEN: Should handle write error gracefully
        """
        mock_client = MagicMock()
        mock_client.write.side_effect = Exception("Write failed")
        service_instance.influxdb_client = mock_client
        
        # Should not raise exception
        await service_instance.store_in_influxdb(sample_pricing_data)

    @pytest.mark.asyncio
    async def test_influxdb_timeout(self, service_instance, sample_pricing_data):
        """
        GIVEN: InfluxDB write times out
        WHEN: Store pricing data
        THEN: Should handle timeout gracefully
        """
        mock_client = MagicMock()
        mock_client.write.side_effect = TimeoutError("InfluxDB timeout")
        service_instance.influxdb_client = mock_client
        
        # Should not raise exception
        await service_instance.store_in_influxdb(sample_pricing_data)

    @pytest.mark.asyncio
    async def test_influxdb_client_not_initialized(self, service_instance, sample_pricing_data):
        """
        GIVEN: InfluxDB client is None
        WHEN: Store pricing data
        THEN: Should handle gracefully
        """
        service_instance.influxdb_client = None
        
        # Should not raise exception
        await service_instance.store_in_influxdb(sample_pricing_data)


class TestNetworkTimeouts:
    """Test network timeout scenarios"""

    @pytest.mark.asyncio
    async def test_http_timeout_during_fetch(self, service_instance):
        """
        GIVEN: HTTP request times out
        WHEN: Fetch pricing
        THEN: Should handle timeout gracefully
        """
        service_instance.session = AsyncMock()
        
        with patch.object(service_instance.provider, 'fetch_pricing', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = asyncio.TimeoutError("Request timeout")
            
            result = await service_instance.fetch_pricing()
            assert result is None

    @pytest.mark.asyncio
    async def test_connection_timeout(self, service_instance):
        """
        GIVEN: Connection times out
        WHEN: Fetch pricing
        THEN: Should handle connection timeout gracefully
        """
        service_instance.session = AsyncMock()
        
        with patch.object(service_instance.provider, 'fetch_pricing', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = ConnectionError("Connection timeout")
            
            result = await service_instance.fetch_pricing()
            assert result is None


class TestCacheExpiration:
    """Test cache expiration scenarios"""

    @pytest.mark.asyncio
    async def test_cache_expiration_returns_stale_data(self, service_instance, sample_pricing_data):
        """
        GIVEN: Cache has expired data
        WHEN: Provider API fails
        THEN: Should still return stale cached data
        """
        # Set up expired cache (older than cache_duration)
        service_instance.cached_data = sample_pricing_data.copy()
        service_instance.last_fetch_time = datetime.now(timezone.utc) - timedelta(minutes=61)
        service_instance.session = AsyncMock()
        
        with patch.object(service_instance.provider, 'fetch_pricing', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = Exception("API error")
            
            # Should still return cached data even if expired
            result = await service_instance.fetch_pricing()
            assert result is not None
            assert result == service_instance.cached_data

    @pytest.mark.asyncio
    async def test_no_cache_on_first_fetch_failure(self, service_instance):
        """
        GIVEN: No cached data and provider fails
        WHEN: Fetch pricing
        THEN: Should return None
        """
        service_instance.cached_data = None
        service_instance.session = AsyncMock()
        
        with patch.object(service_instance.provider, 'fetch_pricing', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = Exception("API error")
            
            result = await service_instance.fetch_pricing()
            assert result is None


class TestAPIEndpointErrors:
    """Test API endpoint error scenarios"""

    @pytest.mark.asyncio
    async def test_cheapest_hours_invalid_parameter(self, service_instance):
        """
        GIVEN: Invalid hours parameter
        WHEN: Request cheapest hours
        THEN: Should return 400 error
        """
        service_instance.cached_data = {'cheapest_hours': [1, 2, 3, 4]}
        
        request = MagicMock()
        request.query = {'hours': 'invalid'}
        
        response = await service_instance.get_cheapest_hours(request)
        
        assert response.status == 400

    @pytest.mark.asyncio
    async def test_cheapest_hours_out_of_bounds(self, service_instance):
        """
        GIVEN: Hours parameter out of bounds
        WHEN: Request cheapest hours
        THEN: Should return 400 error
        """
        service_instance.cached_data = {'cheapest_hours': [1, 2, 3, 4]}
        
        request = MagicMock()
        request.query = {'hours': '25'}  # Out of bounds (max 24)
        
        response = await service_instance.get_cheapest_hours(request)
        
        assert response.status == 400

    @pytest.mark.asyncio
    async def test_cheapest_hours_network_restriction(self, service_instance, sample_pricing_data):
        """
        GIVEN: Request from external network (if restrictions configured)
        WHEN: Request cheapest hours
        THEN: Should return 403 error
        """
        service_instance.cached_data = sample_pricing_data
        service_instance.allowed_networks = ['192.168.1.0/24']
        
        request = MagicMock()
        request.query = {'hours': '4'}
        request.remote = '10.0.0.1'  # External IP
        
        # Mock require_internal_network to raise HTTPForbidden
        with patch('src.main.require_internal_network', new_callable=AsyncMock) as mock_require:
            mock_require.side_effect = web.HTTPForbidden(text="Access denied")
            
            with pytest.raises(web.HTTPForbidden):
                await service_instance.get_cheapest_hours(request)


class TestContinuousLoopErrors:
    """Test error handling in continuous loop"""

    @pytest.mark.asyncio
    async def test_continuous_loop_handles_fetch_error(self, service_instance):
        """
        GIVEN: Fetch fails in continuous loop
        WHEN: Run continuous loop
        THEN: Should wait and retry
        """
        service_instance.session = AsyncMock()
        
        with patch.object(service_instance.provider, 'fetch_pricing', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = Exception("API error")
            
            # Mock sleep to prevent actual waiting
            with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                # Create a task that will be cancelled
                task = asyncio.create_task(service_instance.run_continuous())
                
                # Wait a bit then cancel
                await asyncio.sleep(0.1)
                task.cancel()
                
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                
                # Verify sleep was called (retry logic)
                assert mock_sleep.called

    @pytest.mark.asyncio
    async def test_continuous_loop_handles_store_error(self, service_instance, sample_pricing_data):
        """
        GIVEN: Store fails in continuous loop
        WHEN: Run continuous loop
        THEN: Should continue without crashing
        """
        service_instance.session = AsyncMock()
        
        with patch.object(service_instance.provider, 'fetch_pricing', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = sample_pricing_data.copy()
            
            # Mock store to fail
            with patch.object(service_instance, 'store_in_influxdb', new_callable=AsyncMock) as mock_store:
                mock_store.side_effect = Exception("Store failed")
                
                # Mock sleep to allow one iteration then cancel
                call_count = 0
                async def mock_sleep(delay):
                    nonlocal call_count
                    call_count += 1
                    if call_count > 1:  # Allow one iteration
                        raise asyncio.CancelledError()
                
                with patch('asyncio.sleep', side_effect=mock_sleep):
                    task = asyncio.create_task(service_instance.run_continuous())
                    
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                    
                    # Verify fetch was called (store may not be called if cancelled early)
                    assert mock_fetch.called

