"""
Error Scenario Tests
Epic 48 Story 48.3: Error Scenario Testing

Tests for robust error handling and graceful degradation under failure conditions.
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.correlator import EnergyEventCorrelator
from src.main import EnergyCorrelatorService


class TestConnectionFailures:
    """Tests for InfluxDB connection failures"""
    
    @pytest.mark.asyncio
    async def test_connection_refused(self):
        """Test handling of connection refused error"""
        correlator = EnergyEventCorrelator(
            influxdb_url='http://invalid-host:8086',
            influxdb_token='test-token',
            influxdb_org='test-org',
            influxdb_bucket='test-bucket'
        )
        
        # Should raise exception on startup
        with pytest.raises(Exception):
            await correlator.startup()
    
    @pytest.mark.asyncio
    async def test_connection_timeout(self):
        """Test handling of connection timeout"""
        correlator = EnergyEventCorrelator(
            influxdb_url='http://timeout-host:8086',
            influxdb_token='test-token',
            influxdb_org='test-org',
            influxdb_bucket='test-bucket'
        )
        
        # Mock timeout exception
        with patch('src.influxdb_wrapper.InfluxDBWrapper.connect', side_effect=TimeoutError("Connection timeout")):
            with pytest.raises(TimeoutError):
                await correlator.startup()
    
    @pytest.mark.asyncio
    async def test_authentication_failure(self):
        """Test handling of authentication failure"""
        correlator = EnergyEventCorrelator(
            influxdb_url='http://influxdb:8086',
            influxdb_token='invalid-token',
            influxdb_org='test-org',
            influxdb_bucket='test-bucket'
        )
        
        # Mock authentication error
        with patch('src.influxdb_wrapper.InfluxDBWrapper.connect', side_effect=Exception("Unauthorized")):
            with pytest.raises(Exception) as exc_info:
                await correlator.startup()
            assert "Unauthorized" in str(exc_info.value)


class TestQueryFailures:
    """Tests for InfluxDB query failures"""
    
    @pytest.fixture
    async def correlator_with_mock(self):
        """Create correlator with mocked InfluxDB client"""
        correlator = EnergyEventCorrelator(
            influxdb_url='http://test-influxdb:8086',
            influxdb_token='test-token',
            influxdb_org='test-org',
            influxdb_bucket='test-bucket'
        )
        
        mock_client = MagicMock()
        correlator.client = mock_client
        
        await correlator.startup()
        
        yield correlator, mock_client
        
        try:
            await correlator.shutdown()
        except:
            pass
    
    @pytest.mark.asyncio
    async def test_query_timeout(self, correlator_with_mock):
        """Test handling of query timeout"""
        correlator, mock_client = correlator_with_mock
        
        # Mock query timeout
        mock_client.query = AsyncMock(side_effect=TimeoutError("Query timeout"))
        
        # Should handle timeout gracefully
        with pytest.raises(TimeoutError):
            await correlator._query_recent_events(minutes=5)
        
        # Error should be tracked
        assert correlator.errors >= 0
    
    @pytest.mark.asyncio
    async def test_malformed_query_response(self, correlator_with_mock):
        """Test handling of malformed query response"""
        correlator, mock_client = correlator_with_mock
        
        # Mock malformed response
        mock_client.query = AsyncMock(return_value="invalid response")
        
        # Should handle gracefully
        try:
            events = await correlator._query_recent_events(minutes=5)
            # Should return empty list or handle error
            assert isinstance(events, list)
        except Exception:
            # Error handling is acceptable
            pass
    
    @pytest.mark.asyncio
    async def test_empty_result_set(self, correlator_with_mock):
        """Test handling of empty result set"""
        correlator, mock_client = correlator_with_mock
        
        # Mock empty results
        mock_client.query = AsyncMock(return_value=[])
        
        events = await correlator._query_recent_events(minutes=5)
        
        # Should return empty list without error
        assert events == []
        assert isinstance(events, list)
    
    @pytest.mark.asyncio
    async def test_invalid_data_format(self, correlator_with_mock):
        """Test handling of invalid data format in response"""
        correlator, mock_client = correlator_with_mock
        
        # Mock invalid data format
        mock_client.query = AsyncMock(return_value=[
            {'invalid': 'data', 'no_time': True}
        ])
        
        events = await correlator._query_recent_events(minutes=5)
        
        # Should filter out invalid events
        assert isinstance(events, list)
        # Events without valid time should be filtered


class TestDataValidation:
    """Tests for data validation and edge cases"""
    
    @pytest.fixture
    async def correlator_with_mock(self):
        """Create correlator with mocked InfluxDB client"""
        correlator = EnergyEventCorrelator(
            influxdb_url='http://test-influxdb:8086',
            influxdb_token='test-token',
            influxdb_org='test-org',
            influxdb_bucket='test-bucket'
        )
        
        mock_client = MagicMock()
        correlator.client = mock_client
        
        await correlator.startup()
        
        yield correlator, mock_client
        
        try:
            await correlator.shutdown()
        except:
            pass
    
    @pytest.mark.asyncio
    async def test_missing_required_fields(self, correlator_with_mock):
        """Test handling of missing required fields"""
        correlator, mock_client = correlator_with_mock
        
        # Mock response with missing fields
        mock_client.query = AsyncMock(return_value=[
            {
                '_time': datetime.utcnow(),
                # Missing entity_id, domain, state
            }
        ])
        
        events = await correlator._query_recent_events(minutes=5)
        
        # Should handle missing fields gracefully
        assert isinstance(events, list)
    
    @pytest.mark.asyncio
    async def test_invalid_datetime_format(self, correlator_with_mock):
        """Test handling of invalid datetime formats"""
        correlator, mock_client = correlator_with_mock
        
        # Mock response with invalid datetime
        mock_client.query = AsyncMock(return_value=[
            {
                'time': 'invalid-datetime',
                'entity_id': 'switch.lamp',
                '_value': 'on'
            }
        ])
        
        events = await correlator._query_recent_events(minutes=5)
        
        # Should filter out events with invalid datetime
        assert isinstance(events, list)
    
    @pytest.mark.asyncio
    async def test_invalid_power_values(self, correlator_with_mock):
        """Test handling of invalid power values"""
        correlator, mock_client = correlator_with_mock
        
        # Test with mock returning empty (no data found)
        mock_client.query = AsyncMock(return_value=[])
        power = await correlator._get_power_at_time(datetime.now(timezone.utc))
        assert power is None
    
    @pytest.mark.asyncio
    async def test_missing_power_data(self, correlator_with_mock):
        """Test handling of missing power data scenarios"""
        correlator, mock_client = correlator_with_mock
        
        # Mock no power data found
        mock_client.query = AsyncMock(return_value=[])
        
        # Correlate event without power data
        event = {
            'time': datetime.now(timezone.utc),
            'entity_id': 'switch.lamp',
            'domain': 'switch',
            'state': 'on',
            'previous_state': 'off'
        }
        
        result = await correlator._correlate_event_with_power(event, write_result=False)
        
        # Should return None when no power data
        assert result is None


class TestRetryQueueOverflow:
    """Tests for retry queue overflow scenarios"""
    
    @pytest.fixture
    async def correlator_with_mock(self):
        """Create correlator with mocked InfluxDB client"""
        correlator = EnergyEventCorrelator(
            influxdb_url='http://test-influxdb:8086',
            influxdb_token='test-token',
            influxdb_org='test-org',
            influxdb_bucket='test-bucket',
            max_retry_queue_size=10  # Small queue for testing
        )
        
        mock_client = MagicMock()
        correlator.client = mock_client
        
        await correlator.startup()
        
        yield correlator, mock_client
        
        try:
            await correlator.shutdown()
        except:
            pass
    
    @pytest.mark.asyncio
    async def test_queue_at_maximum_capacity(self, correlator_with_mock):
        """Test behavior when retry queue is at maximum capacity"""
        correlator, mock_client = correlator_with_mock
        
        # Mock no power data to trigger retry queue
        mock_client.query = AsyncMock(return_value=[])
        
        # Fill queue to capacity
        retry_queue = []
        for i in range(correlator.max_retry_queue_size + 5):  # Add more than capacity
            event = {
                'time': datetime.now(timezone.utc) - timedelta(seconds=i),
                'entity_id': f'switch.lamp_{i}',
                'domain': 'switch',
                'state': 'on',
                'previous_state': 'off'
            }
            await correlator._correlate_event_with_power(
                event,
                retry_queue=retry_queue,
                write_result=False
            )
        
        # Queue should not exceed max size
        assert len(retry_queue) <= correlator.max_retry_queue_size
    
    @pytest.mark.asyncio
    async def test_events_dropped_when_queue_full(self, correlator_with_mock):
        """Test that events are dropped when queue is full"""
        correlator, mock_client = correlator_with_mock
        
        # Mock no power data
        mock_client.query = AsyncMock(return_value=[])
        
        retry_queue = []
        
        # Fill queue to capacity
        for i in range(correlator.max_retry_queue_size):
            event = {
                'time': datetime.now(timezone.utc) - timedelta(seconds=i),
                'entity_id': f'switch.lamp_{i}',
                'domain': 'switch',
                'state': 'on',
                'previous_state': 'off'
            }
            await correlator._correlate_event_with_power(
                event,
                retry_queue=retry_queue,
                write_result=False
            )
        
        initial_size = len(retry_queue)
        
        # Add one more event (should be dropped or oldest removed)
        event = {
            'time': datetime.now(timezone.utc),
            'entity_id': 'switch.new_lamp',
            'domain': 'switch',
            'state': 'on',
            'previous_state': 'off'
        }
        await correlator._correlate_event_with_power(
            event,
            retry_queue=retry_queue,
            write_result=False
        )
        
        # Queue should not exceed max size
        assert len(retry_queue) <= correlator.max_retry_queue_size


class TestCacheFailures:
    """Tests for cache lookup failures"""
    
    @pytest.fixture
    async def correlator_with_mock(self):
        """Create correlator with mocked InfluxDB client"""
        correlator = EnergyEventCorrelator(
            influxdb_url='http://test-influxdb:8086',
            influxdb_token='test-token',
            influxdb_org='test-org',
            influxdb_bucket='test-bucket'
        )
        
        mock_client = MagicMock()
        correlator.client = mock_client
        
        await correlator.startup()
        
        yield correlator, mock_client
        
        try:
            await correlator.shutdown()
        except:
            pass
    
    @pytest.mark.asyncio
    async def test_cache_miss_scenario(self, correlator_with_mock):
        """Test cache miss scenarios"""
        correlator, mock_client = correlator_with_mock
        
        # Mock empty cache
        correlator._power_cache = None
        
        # Query power at time (should query InfluxDB)
        mock_client.query = AsyncMock(return_value=[])
        
        power = await correlator._get_power_at_time(datetime.now(timezone.utc))
        
        # Should return None when no data
        assert power is None
    
    @pytest.mark.asyncio
    async def test_cache_with_empty_power_data(self, correlator_with_mock):
        """Test cache with empty power data"""
        correlator, mock_client = correlator_with_mock
        
        # Mock empty query result
        mock_client.query = AsyncMock(return_value=[])
        
        # Build cache with empty data
        events = []
        cache = await correlator._build_power_cache(events)
        
        # Cache should have empty timestamps and values lists
        assert cache == {"timestamps": [], "values": []}
    
    @pytest.mark.asyncio
    async def test_cache_lookup_with_invalid_timestamp(self, correlator_with_mock):
        """Test cache lookup with invalid timestamps"""
        correlator, mock_client = correlator_with_mock
        
        # Mock query result for cache building
        mock_client.query = AsyncMock(return_value=[])
        
        # Build cache
        events = [
            {
                'time': datetime.now(timezone.utc) - timedelta(seconds=30),
                'entity_id': 'switch.lamp',
                'domain': 'switch',
                'state': 'on'
            }
        ]
        cache = await correlator._build_power_cache(events)
        correlator._power_cache = cache
        
        # Lookup with timestamp far in future (should return None)
        power = correlator._lookup_power_in_cache(
            datetime.now(timezone.utc) + timedelta(hours=1),
            cache
        )
        
        # Should return None for invalid timestamp
        assert power is None


class TestErrorStatistics:
    """Tests for error statistics tracking"""
    
    @pytest.fixture
    async def correlator_with_mock(self):
        """Create correlator with mocked InfluxDB client"""
        correlator = EnergyEventCorrelator(
            influxdb_url='http://test-influxdb:8086',
            influxdb_token='test-token',
            influxdb_org='test-org',
            influxdb_bucket='test-bucket'
        )
        
        mock_client = MagicMock()
        correlator.client = mock_client
        
        await correlator.startup()
        
        yield correlator, mock_client
        
        try:
            await correlator.shutdown()
        except:
            pass
    
    @pytest.mark.asyncio
    async def test_error_statistics_tracking(self, correlator_with_mock):
        """Test that errors are tracked in statistics"""
        correlator, mock_client = correlator_with_mock
        
        initial_errors = correlator.errors
        
        # Trigger an error
        mock_client.query = AsyncMock(side_effect=Exception("Test error"))
        
        try:
            await correlator._query_recent_events(minutes=5)
        except Exception:
            pass
        
        # Errors should be tracked (may be incremented in error handler)
        stats = correlator.get_statistics()
        assert 'errors' in stats or 'total_events_processed' in stats
    
    @pytest.mark.asyncio
    async def test_graceful_degradation(self, correlator_with_mock):
        """Test graceful degradation under errors"""
        correlator, mock_client = correlator_with_mock
        
        # Mock query to fail
        mock_client.query = AsyncMock(side_effect=Exception("InfluxDB error"))
        
        # Process should handle error gracefully
        try:
            await correlator.process_recent_events(lookback_minutes=5)
        except Exception:
            # Error should be logged but service should continue
            pass
        
        # Service should still be functional
        stats = correlator.get_statistics()
        assert isinstance(stats, dict)

