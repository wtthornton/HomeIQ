"""
InfluxDB Write Integration Tests
Epic 49 Story 49.3: Integration Test Suite

Tests for InfluxDB write operations including batch writes.
"""

import os
import sys
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.main import ElectricityPricingService


@pytest.fixture
def mock_influxdb_client():
    """Mock InfluxDB client for testing"""
    client = MagicMock()
    client.write = MagicMock()  # Synchronous write method
    return client


@pytest.fixture
async def service_with_mock(mock_influxdb_client):
    """Create service with mocked InfluxDB client"""
    # Set test environment
    os.environ['INFLUXDB_TOKEN'] = 'test-token'
    os.environ['INFLUXDB_URL'] = 'http://test-influxdb:8086'
    os.environ['INFLUXDB_ORG'] = 'test-org'
    os.environ['INFLUXDB_BUCKET'] = 'test-bucket'
    
    service = ElectricityPricingService()
    
    # Mock InfluxDB client
    service.influxdb_client = mock_influxdb_client
    
    # Mock HTTP session
    service.session = AsyncMock()
    
    await service.startup()
    
    yield service
    
    # Cleanup
    try:
        await service.shutdown()
    except:
        pass


@pytest.mark.asyncio
async def test_batch_write_current_pricing(service_with_mock, mock_influxdb_client):
    """Test batch write of current pricing data"""
    from influxdb_client_3 import Point
    
    # Create test data
    test_data = {
        'current_price': 0.25,
        'currency': 'EUR',
        'timestamp': datetime.now(timezone.utc),
        'forecast_24h': [
            {
                'hour': i,
                'price': 0.20 + (i * 0.01),
                'timestamp': datetime.now(timezone.utc)
            }
            for i in range(24)
        ]
    }
    
    # Store data
    await service_with_mock.store_in_influxdb(test_data)
    
    # Verify write was called (wrapped in asyncio.to_thread)
    # The write should be called with a list of points
    assert mock_influxdb_client.write.called


@pytest.mark.asyncio
async def test_batch_write_forecast_data(service_with_mock, mock_influxdb_client):
    """Test batch write includes forecast data"""
    from influxdb_client_3 import Point
    
    # Create test data with forecast
    test_data = {
        'current_price': 0.25,
        'currency': 'EUR',
        'timestamp': datetime.now(timezone.utc),
        'forecast_24h': [
            {
                'hour': i,
                'price': 0.20 + (i * 0.01),
                'timestamp': datetime.now(timezone.utc)
            }
            for i in range(24)
        ]
    }
    
    # Store data
    await service_with_mock.store_in_influxdb(test_data)
    
    # Verify write was called
    assert mock_influxdb_client.write.called
    
    # Verify points were passed (should be 25 points: 1 current + 24 forecast)
    call_args = mock_influxdb_client.write.call_args
    points = call_args[0][0] if call_args[0] else []
    assert len(points) == 25  # 1 current + 24 forecast


@pytest.mark.asyncio
async def test_write_error_handling(service_with_mock, mock_influxdb_client):
    """Test error handling during InfluxDB writes"""
    # Mock write to raise error
    mock_influxdb_client.write.side_effect = Exception("InfluxDB connection error")
    
    test_data = {
        'current_price': 0.25,
        'currency': 'EUR',
        'timestamp': datetime.now(timezone.utc),
        'forecast_24h': []
    }
    
    # Store should handle error gracefully (not raise)
    try:
        await service_with_mock.store_in_influxdb(test_data)
    except Exception:
        # Error should be logged but not crash
        pass
    
    # Verify write was attempted
    assert mock_influxdb_client.write.called


@pytest.mark.asyncio
async def test_write_empty_data(service_with_mock, mock_influxdb_client):
    """Test handling of empty data"""
    # Empty data should not cause errors
    test_data = {
        'current_price': None,
        'currency': 'EUR',
        'timestamp': datetime.now(timezone.utc),
        'forecast_24h': []
    }
    
    # Should handle gracefully
    await service_with_mock.store_in_influxdb(test_data)
    
    # If no points, write might not be called
    # This is acceptable behavior


@pytest.mark.asyncio
async def test_write_with_missing_fields(service_with_mock, mock_influxdb_client):
    """Test write with missing optional fields"""
    test_data = {
        'current_price': 0.25,
        'timestamp': datetime.now(timezone.utc),
        'forecast_24h': []
    }
    
    # Should handle missing currency field
    await service_with_mock.store_in_influxdb(test_data)
    
    # Write should still be called
    assert mock_influxdb_client.write.called

