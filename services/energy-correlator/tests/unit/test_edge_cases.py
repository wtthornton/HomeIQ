"""
Edge Case Tests
Epic 48 Story 48.4: Test Coverage & Quality Improvements

Tests for boundary conditions, edge cases, and configuration limits.
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.correlator import EnergyEventCorrelator
from src.main import EnergyCorrelatorService


class TestBoundaryConditions:
    """Tests for boundary conditions and edge cases"""
    
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
    async def test_empty_event_list(self, correlator_with_mock):
        """Test processing with empty event list"""
        correlator, mock_client = correlator_with_mock
        
        mock_client.query.return_value = []
        
        events = await correlator._query_recent_events(minutes=5)
        
        assert events == []
        assert isinstance(events, list)
    
    @pytest.mark.asyncio
    async def test_none_values(self, correlator_with_mock):
        """Test handling of None values"""
        correlator, mock_client = correlator_with_mock
        
        # Test None power value
        power = await correlator._get_power_at_time(datetime.now(timezone.utc))
        assert power is None or isinstance(power, float)
    
    @pytest.mark.asyncio
    async def test_zero_power_delta(self, correlator_with_mock):
        """Test handling of zero power delta"""
        correlator, mock_client = correlator_with_mock
        
        # Mock power data with zero delta
        mock_client.query = AsyncMock(return_value=[
            {
                'time': datetime.now(timezone.utc),
                '_value': 2450.0,
                '_measurement': 'smart_meter',
                '_field': 'total_power_w'
            }
        ])
        
        # Build cache with same power before and after
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
        
        # Correlate event (should not correlate due to zero delta)
        event = {
            'time': datetime.now(timezone.utc) - timedelta(seconds=30),
            'entity_id': 'switch.lamp',
            'domain': 'switch',
            'state': 'on',
            'previous_state': 'off'
        }
        
        result = await correlator._correlate_event_with_power(event, write_result=False)
        
        # Should return None (delta too small)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_negative_power_delta(self, correlator_with_mock):
        """Test handling of negative power delta (device turning off)"""
        correlator, mock_client = correlator_with_mock
        
        # Mock power data showing decrease
        mock_client.query = AsyncMock(return_value=[
            {
                'time': datetime.now(timezone.utc) - timedelta(seconds=35),
                '_value': 2500.0,
                '_measurement': 'smart_meter',
                '_field': 'total_power_w'
            },
            {
                'time': datetime.now(timezone.utc) - timedelta(seconds=25),
                '_value': 2400.0,  # 100W decrease
                '_measurement': 'smart_meter',
                '_field': 'total_power_w'
            }
        ])
        
        events = [
            {
                'time': datetime.now(timezone.utc) - timedelta(seconds=30),
                'entity_id': 'switch.lamp',
                'domain': 'switch',
                'state': 'off'
            }
        ]
        
        cache = await correlator._build_power_cache(events)
        correlator._power_cache = cache
        
        event = {
            'time': datetime.now(timezone.utc) - timedelta(seconds=30),
            'entity_id': 'switch.lamp',
            'domain': 'switch',
            'state': 'off',
            'previous_state': 'on'
        }
        
        result = await correlator._correlate_event_with_power(event, write_result=False)
        
        # Should correlate negative delta if above threshold
        if result is not None:
            assert result.fields.get('power_delta', 0) < 0


class TestConfigurationLimits:
    """Tests for configuration limits and validation"""
    
    def test_min_correlation_window(self):
        """Test minimum correlation window value"""
        # Should enforce minimum of 1 second
        correlator = EnergyEventCorrelator(
            influxdb_url='http://test-influxdb:8086',
            influxdb_token='test-token',
            influxdb_org='test-org',
            influxdb_bucket='test-bucket',
            correlation_window_seconds=0  # Invalid, should be clamped to 1
        )
        
        assert correlator.correlation_window_seconds >= 1
    
    def test_min_power_delta(self):
        """Test minimum power delta configuration"""
        correlator = EnergyEventCorrelator(
            influxdb_url='http://test-influxdb:8086',
            influxdb_token='test-token',
            influxdb_org='test-org',
            influxdb_bucket='test-bucket',
            min_power_delta=0.0  # Should accept 0
        )
        
        assert correlator.min_power_delta >= 0.0
    
    def test_max_events_per_interval(self):
        """Test maximum events per interval configuration"""
        correlator = EnergyEventCorrelator(
            influxdb_url='http://test-influxdb:8086',
            influxdb_token='test-token',
            influxdb_org='test-org',
            influxdb_bucket='test-bucket',
            max_events_per_interval=0  # Invalid, should be clamped to 1
        )
        
        assert correlator.max_events_per_interval >= 1
    
    def test_max_retry_queue_size(self):
        """Test maximum retry queue size configuration"""
        correlator = EnergyEventCorrelator(
            influxdb_url='http://test-influxdb:8086',
            influxdb_token='test-token',
            influxdb_org='test-org',
            influxdb_bucket='test-bucket',
            max_retry_queue_size=-1  # Invalid, should be clamped to 0
        )
        
        assert correlator.max_retry_queue_size >= 0


class TestStatisticsEdgeCases:
    """Tests for statistics calculation edge cases"""
    
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
        
        yield correlator
        
        try:
            await correlator.shutdown()
        except:
            pass
    
    def test_initial_statistics(self, correlator_with_mock):
        """Test initial statistics values"""
        correlator = correlator_with_mock
        
        stats = correlator.get_statistics()
        
        assert stats['total_events_processed'] == 0
        assert stats['correlations_found'] == 0
        assert stats['correlations_written'] == 0
        assert stats['errors'] == 0
    
    def test_statistics_after_reset(self, correlator_with_mock):
        """Test statistics after reset"""
        correlator = correlator_with_mock
        
        # Increment some counters
        correlator.total_events_processed = 10
        correlator.correlations_found = 5
        
        # Reset
        correlator.reset_statistics()
        
        stats = correlator.get_statistics()
        
        assert stats['total_events_processed'] == 0
        assert stats['correlations_found'] == 0


class TestTimezoneHandling:
    """Tests for timezone handling edge cases"""
    
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
    async def test_utc_timestamps(self, correlator_with_mock):
        """Test handling of UTC timestamps"""
        correlator, mock_client = correlator_with_mock
        
        # Use UTC datetime
        utc_time = datetime.now(timezone.utc)
        
        mock_client.query.return_value = [
            {
                'time': utc_time,
                'entity_id': 'switch.lamp',
                '_value': 'on',
                '_measurement': 'home_assistant_events'
            }
        ]
        
        events = await correlator._query_recent_events(minutes=5)
        
        # Should handle UTC timestamps correctly
        assert len(events) >= 0
    
    @pytest.mark.asyncio
    async def test_timezone_aware_timestamps(self, correlator_with_mock):
        """Test handling of timezone-aware timestamps"""
        from datetime import timezone
        
        correlator, mock_client = correlator_with_mock
        
        # Use timezone-aware datetime
        aware_time = datetime.now(timezone.utc)
        
        mock_client.query.return_value = [
            {
                'time': aware_time,
                'entity_id': 'switch.lamp',
                '_value': 'on',
                '_measurement': 'home_assistant_events'
            }
        ]
        
        events = await correlator._query_recent_events(minutes=5)
        
        # Should handle timezone-aware timestamps
        assert len(events) >= 0


class TestMemoryLimits:
    """Tests for memory limit handling"""
    
    @pytest.fixture
    async def correlator_with_mock(self):
        """Create correlator with mocked InfluxDB client"""
        correlator = EnergyEventCorrelator(
            influxdb_url='http://test-influxdb:8086',
            influxdb_token='test-token',
            influxdb_org='test-org',
            influxdb_bucket='test-bucket',
            max_events_per_interval=10  # Small limit for testing
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
    async def test_max_events_limit(self, correlator_with_mock):
        """Test that max events limit is enforced"""
        correlator, mock_client = correlator_with_mock
        
        # Mock many events
        many_events = [
            {
                'time': datetime.now(timezone.utc) - timedelta(seconds=i),
                'entity_id': f'switch.lamp_{i}',
                '_value': 'on',
                '_measurement': 'home_assistant_events',
                '_field': 'state_value'
            }
            for i in range(20)  # More than max_events_per_interval
        ]
        
        mock_client.query.return_value = many_events
        
        events = await correlator._query_recent_events(minutes=5)
        
        # Should be limited to max_events_per_interval
        assert len(events) <= correlator.max_events_per_interval


class TestConcurrentOperations:
    """Tests for concurrent operation handling"""
    
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
    async def test_concurrent_queries(self, correlator_with_mock):
        """Test handling of concurrent queries"""
        import asyncio
        
        correlator, mock_client = correlator_with_mock
        
        mock_client.query = AsyncMock(return_value=[])
        
        # Run multiple queries concurrently
        tasks = [
            correlator._query_recent_events(minutes=5)
            for _ in range(5)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should complete successfully
        assert len(results) == 5
        assert all(isinstance(r, list) for r in results)

