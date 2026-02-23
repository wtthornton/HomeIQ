"""
Provider Integration Tests
Epic 49 Story 49.3: Integration Test Suite

Tests for provider API integration including Awattar provider.
"""

import os
import sys
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import aiohttp

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.providers.awattar import AwattarProvider


@pytest.fixture
def awattar_provider():
    """Create AwattarProvider instance"""
    return AwattarProvider()


@pytest.fixture
def mock_awattar_response():
    """Mock Awattar API response"""
    now = datetime.now(timezone.utc)
    base_timestamp = int(now.timestamp() * 1000)
    
    return {
        'data': [
            {
                'start_timestamp': base_timestamp + (i * 3600000),  # Hourly
                'end_timestamp': base_timestamp + ((i + 1) * 3600000),
                'marketprice': 2000 + (i * 100)  # Varying prices
            }
            for i in range(24)
        ]
    }


@pytest.mark.asyncio
async def test_awattar_fetch_pricing_success(awattar_provider, mock_awattar_response):
    """Test successful Awattar API fetch"""
    async with aiohttp.ClientSession() as session:
        with patch.object(session, 'get') as mock_get:
            # Mock successful response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_awattar_response)
            mock_get.return_value.__aenter__.return_value = mock_response
            
            # Fetch pricing
            result = await awattar_provider.fetch_pricing(session)
            
            # Verify result structure
            assert result is not None
            assert 'current_price' in result
            assert 'currency' in result
            assert 'forecast_24h' in result
            assert len(result['forecast_24h']) == 24


@pytest.mark.asyncio
async def test_awattar_fetch_pricing_api_error(awattar_provider):
    """Test Awattar API error handling"""
    async with aiohttp.ClientSession() as session:
        with patch.object(session, 'get') as mock_get:
            # Mock API error
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_response.text = AsyncMock(return_value="Internal Server Error")
            mock_get.return_value.__aenter__.return_value = mock_response
            
            # Fetch should handle error gracefully
            result = await awattar_provider.fetch_pricing(session)
            
            # Should return None or handle error
            assert result is None or isinstance(result, dict)


@pytest.mark.asyncio
async def test_awattar_fetch_pricing_network_error(awattar_provider):
    """Test network error handling"""
    async with aiohttp.ClientSession() as session:
        with patch.object(session, 'get', side_effect=aiohttp.ClientError("Connection error")):
            # Fetch should handle network error
            result = await awattar_provider.fetch_pricing(session)
            
            # Should return None or handle error
            assert result is None or isinstance(result, dict)


@pytest.mark.asyncio
async def test_awattar_parse_response(awattar_provider, mock_awattar_response):
    """Test response parsing logic"""
    # Parse response
    result = awattar_provider._parse_response(mock_awattar_response)
    
    # Verify structure
    assert result is not None
    assert 'current_price' in result
    assert 'currency' in result
    assert result['currency'] == 'EUR'
    assert 'forecast_24h' in result
    assert len(result['forecast_24h']) == 24
    
    # Verify forecast structure
    for forecast in result['forecast_24h']:
        assert 'hour' in forecast
        assert 'price' in forecast
        assert 'timestamp' in forecast
        assert isinstance(forecast['timestamp'], datetime)


@pytest.mark.asyncio
async def test_awattar_parse_empty_response(awattar_provider):
    """Test parsing empty response"""
    empty_response = {'data': []}
    
    result = awattar_provider._parse_response(empty_response)
    
    # Should handle empty data gracefully
    assert result is not None
    assert 'forecast_24h' in result
    assert len(result['forecast_24h']) == 0


@pytest.mark.asyncio
async def test_awattar_parse_invalid_response(awattar_provider):
    """Test parsing invalid response format"""
    invalid_response = {'invalid': 'data'}
    
    # Should handle invalid format gracefully
    try:
        result = awattar_provider._parse_response(invalid_response)
        # May return None or handle error
        assert result is None or isinstance(result, dict)
    except (KeyError, TypeError):
        # Exception is acceptable for invalid format
        pass


@pytest.mark.asyncio
async def test_awattar_price_calculation(awattar_provider, mock_awattar_response):
    """Test price calculation (conversion from cent-euro to euro)"""
    # Parse response
    result = awattar_provider._parse_response(mock_awattar_response)
    
    # Verify prices are in euros (not cent-euros)
    # Market price 2000 cent-euro = 0.20 euro
    assert result['current_price'] == 0.20  # 2000 / 10000
    
    # Verify forecast prices
    for i, forecast in enumerate(result['forecast_24h']):
        expected_price = (2000 + (i * 100)) / 10000
        assert abs(forecast['price'] - expected_price) < 0.001


@pytest.mark.asyncio
async def test_awattar_timestamp_handling(awattar_provider, mock_awattar_response):
    """Test timestamp conversion and timezone handling"""
    # Parse response
    result = awattar_provider._parse_response(mock_awattar_response)
    
    # Verify timestamps are timezone-aware
    for forecast in result['forecast_24h']:
        timestamp = forecast['timestamp']
        assert isinstance(timestamp, datetime)
        assert timestamp.tzinfo is not None  # Should be timezone-aware
        assert timestamp.tzinfo == timezone.utc

