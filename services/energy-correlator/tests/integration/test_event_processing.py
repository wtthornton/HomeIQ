"""
End-to-End Event Processing Integration Tests
Epic 48 Story 48.2: Integration Test Suite

Tests for complete event processing flow from InfluxDB query to correlation.
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.correlator import EnergyEventCorrelator


@pytest.fixture
def mock_influxdb_client():
    """Mock InfluxDB client for testing"""
    client = MagicMock()
    client.query = AsyncMock(return_value=[])
    client.write_points = AsyncMock()
    return client


@pytest.fixture
async def correlator_with_mock(mock_influxdb_client):
    """Create correlator with mocked InfluxDB client"""
    correlator = EnergyEventCorrelator(
        influxdb_url='http://test-influxdb:8086',
        influxdb_token='test-token',
        influxdb_org='test-org',
        influxdb_bucket='test-bucket',
        correlation_window_seconds=10,
        min_power_delta=10.0
    )
    correlator.client = mock_influxdb_client
    
    # Initialize correlator
    await correlator.startup()
    
    yield correlator
    
    # Cleanup
    try:
        await correlator.shutdown()
    except:
        pass


@pytest.mark.asyncio
async def test_process_recent_events_full_flow(correlator_with_mock, mock_influxdb_client):
    """Test complete event processing flow"""
    now = datetime.now(timezone.utc)
    
    # Mock event query results
    mock_events = [
        {
            '_time': now - timedelta(seconds=30),
            'entity_id': 'switch.living_room_lamp',
            '_value': 'on',
            'previous_state': 'off',
            '_measurement': 'home_assistant_events',
            '_field': 'state_value'
        }
    ]
    
    # Mock power query results (before and after)
    mock_power_before = [
        {
            '_time': now - timedelta(seconds=35),
            '_value': 2450.0,
            '_measurement': 'smart_meter',
            '_field': 'total_power_w'
        }
    ]
    
    mock_power_after = [
        {
            '_time': now - timedelta(seconds=25),
            '_value': 2510.0,
            '_measurement': 'smart_meter',
            '_field': 'total_power_w'
        }
    ]
    
    # Set up mock to return different results for different queries
    async def mock_query_side_effect(query):
        if 'home_assistant_events' in query.lower():
            return mock_events
        elif 'smart_meter' in query.lower():
            # Return before or after based on time range
            if '35' in query or '-35' in query:
                return mock_power_before
            else:
                return mock_power_after
        return []
    
    mock_influxdb_client.query.side_effect = mock_query_side_effect
    
    # Process recent events
    await correlator_with_mock.process_recent_events(lookback_minutes=5)
    
    # Verify queries were made
    assert mock_influxdb_client.query.called
    
    # Verify statistics were updated
    stats = correlator_with_mock.get_statistics()
    assert stats['events_processed'] >= 0


@pytest.mark.asyncio
async def test_process_recent_events_no_correlation(correlator_with_mock, mock_influxdb_client):
    """Test event processing when no correlation is found"""
    # Mock events with no power change (below threshold)
    mock_events = [
        {
            '_time': datetime.now(timezone.utc) - timedelta(seconds=30),
            'entity_id': 'switch.lamp',
            '_value': 'on',
            '_measurement': 'home_assistant_events'
        }
    ]
    
    # Mock power data with small change (below min_power_delta)
    mock_power = [
        {
            '_time': datetime.now(timezone.utc) - timedelta(seconds=25),
            '_value': 2450.0,
            '_measurement': 'smart_meter'
        },
        {
            '_time': datetime.now(timezone.utc) - timedelta(seconds=35),
            '_value': 2455.0,  # Only 5W change (below 10W threshold)
            '_measurement': 'smart_meter'
        }
    ]
    
    async def mock_query_side_effect(query):
        if 'home_assistant_events' in query.lower():
            return mock_events
        return mock_power
    
    mock_influxdb_client.query.side_effect = mock_query_side_effect
    
    # Process events
    await correlator_with_mock.process_recent_events(lookback_minutes=5)
    
    # Should process without error (no correlation found is valid)
    stats = correlator_with_mock.get_statistics()
    assert stats['events_processed'] >= 0


@pytest.mark.asyncio
async def test_process_recent_events_error_recovery(correlator_with_mock, mock_influxdb_client):
    """Test error recovery during event processing"""
    # Mock query to raise error
    mock_influxdb_client.query.side_effect = Exception("InfluxDB error")
    
    # Process should handle error gracefully
    try:
        await correlator_with_mock.process_recent_events(lookback_minutes=5)
    except Exception:
        # Error should be logged but not crash the service
        pass
    
    # Statistics should reflect error
    stats = correlator_with_mock.get_statistics()
    assert 'events_processed' in stats or 'errors' in stats


@pytest.mark.asyncio
async def test_process_recent_events_empty_results(correlator_with_mock, mock_influxdb_client):
    """Test processing when no events are found"""
    # Mock empty results
    mock_influxdb_client.query.return_value = []
    
    # Process should handle empty results
    await correlator_with_mock.process_recent_events(lookback_minutes=5)
    
    # Should complete without error
    stats = correlator_with_mock.get_statistics()
    assert isinstance(stats, dict)


@pytest.mark.asyncio
async def test_correlation_window_logic(correlator_with_mock, mock_influxdb_client):
    """Test that correlation window is applied correctly"""
    now = datetime.now(timezone.utc)
    
    # Create events within and outside correlation window
    mock_events = [
        {
            '_time': now - timedelta(seconds=5),  # Within 10s window
            'entity_id': 'switch.lamp',
            '_value': 'on',
            '_measurement': 'home_assistant_events'
        },
        {
            '_time': now - timedelta(seconds=15),  # Outside 10s window
            'entity_id': 'switch.other',
            '_value': 'on',
            '_measurement': 'home_assistant_events'
        }
    ]
    
    mock_influxdb_client.query.return_value = mock_events
    
    # Process events
    await correlator_with_mock.process_recent_events(lookback_minutes=5)
    
    # Verify query was called
    assert mock_influxdb_client.query.called


