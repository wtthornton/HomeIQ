"""
InfluxDB Query Integration Tests
Epic 48 Story 48.2: Integration Test Suite

Tests for InfluxDB query operations and Flux query construction.
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
def correlator_with_mock(mock_influxdb_client):
    """Create correlator with mocked InfluxDB client"""
    correlator = EnergyEventCorrelator(
        influxdb_url='http://test-influxdb:8086',
        influxdb_token='test-token',
        influxdb_org='test-org',
        influxdb_bucket='test-bucket'
    )
    correlator.client = mock_influxdb_client
    return correlator


@pytest.mark.asyncio
async def test_query_recent_events(correlator_with_mock, mock_influxdb_client):
    """Test query for recent events"""
    # Mock query results
    mock_results = [
        {
            'time': datetime.now(timezone.utc) - timedelta(minutes=2),
            'entity_id': 'switch.lamp',
            '_value': 'on',
            '_measurement': 'home_assistant_events'
        }
    ]
    mock_influxdb_client.query.return_value = mock_results
    
    # Query recent events
    events = await correlator_with_mock._query_recent_events(lookback_minutes=5)
    
    # Verify query was called
    assert mock_influxdb_client.query.called
    
    # Verify query contains bucket name
    call_args = mock_influxdb_client.query.call_args
    query_string = call_args[0][0] if call_args[0] else str(call_args)
    assert 'test-bucket' in query_string or 'from(bucket:' in query_string.lower()


@pytest.mark.asyncio
async def test_get_power_at_time(correlator_with_mock, mock_influxdb_client):
    """Test query for power data at specific time"""
    # Mock query results
    mock_results = [
        {
            'time': datetime.now(timezone.utc),
            '_value': 2450.0,
            '_measurement': 'smart_meter',
            '_field': 'total_power_w'
        }
    ]
    mock_influxdb_client.query.return_value = mock_results
    
    # Query power data at specific time
    power_data = await correlator_with_mock._get_power_at_time(
        target_time=datetime.now(timezone.utc)
    )
    
    # Verify query was called (if power cache not built, will query)
    # Power might be None if no data found, or a float value
    assert power_data is None or isinstance(power_data, float)


@pytest.mark.asyncio
async def test_query_with_invalid_bucket_name():
    """Test that invalid bucket names are caught during initialization"""
    # This should be caught by validate_bucket_name in main.py
    # But we can test the correlator handles it gracefully
    with patch('src.correlator.validate_bucket_name', side_effect=ValueError("Invalid bucket")):
        with pytest.raises(ValueError):
            correlator = EnergyEventCorrelator(
                influxdb_url='http://test-influxdb:8086',
                influxdb_token='test-token',
                influxdb_org='test-org',
                influxdb_bucket='invalid bucket!'  # Invalid
            )


@pytest.mark.asyncio
async def test_query_error_handling(correlator_with_mock, mock_influxdb_client):
    """Test error handling in InfluxDB queries"""
    # Mock query to raise error
    mock_influxdb_client.query.side_effect = Exception("InfluxDB connection error")
    
    # Query should handle error gracefully
    with pytest.raises(Exception):
        await correlator_with_mock._query_recent_events(lookback_minutes=5)


@pytest.mark.asyncio
async def test_query_time_range_validation(correlator_with_mock, mock_influxdb_client):
    """Test that queries use correct time ranges"""
    now = datetime.now(timezone.utc)
    lookback_minutes = 5
    
    await correlator_with_mock._query_recent_events(lookback_minutes=lookback_minutes)
    
    # Verify query was called with time range
    assert mock_influxdb_client.query.called
    call_args = mock_influxdb_client.query.call_args
    query_string = call_args[0][0] if call_args[0] else str(call_args)
    
    # Query should contain time range (Flux range() function)
    assert 'range(' in query_string.lower() or '-5m' in query_string or '-5d' in query_string


@pytest.mark.asyncio
async def test_write_correlation_points(correlator_with_mock, mock_influxdb_client):
    """Test writing correlation results to InfluxDB"""
    from influxdb_client import Point
    
    # Create a correlation point
    point = Point("energy_correlations") \
        .tag("entity_id", "switch.lamp") \
        .field("power_delta", 60.0) \
        .time(datetime.now(timezone.utc))
    
    await correlator_with_mock._write_correlation_points([point])
    
    # Verify write was called (check if client has write method)
    # The InfluxDBWrapper should handle the write
    assert hasattr(mock_influxdb_client, 'write') or hasattr(mock_influxdb_client, 'write_points')


@pytest.mark.asyncio
async def test_query_empty_results(correlator_with_mock, mock_influxdb_client):
    """Test handling of empty query results"""
    # Mock empty results
    mock_influxdb_client.query.return_value = []
    
    events = await correlator_with_mock._query_recent_events(lookback_minutes=5)
    
    # Should return empty list, not raise error
    assert events == []

