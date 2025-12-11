"""
Discovery Service Integration Tests
Epic 50 Story 50.3: Integration Test Suite

Tests for discovery service integration with data-api.
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import aiohttp

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.discovery_service import DiscoveryService


@pytest.fixture
def mock_data_api_response():
    """Mock data-api response"""
    return {
        'devices': [
            {
                'device_id': 'device_123',
                'name': 'Living Room Lamp',
                'manufacturer': 'Philips',
                'model': 'Hue'
            }
        ],
        'entities': [
            {
                'entity_id': 'switch.living_room_lamp',
                'device_id': 'device_123',
                'area_id': 'area_living_room'
            }
        ],
        'areas': [
            {
                'area_id': 'area_living_room',
                'name': 'Living Room'
            }
        ]
    }


@pytest.fixture
async def discovery_service():
    """Create discovery service with mocked dependencies"""
    os.environ['DATA_API_URL'] = 'http://test-data-api:8006'
    
    service = DiscoveryService()
    
    # Mock HTTP session
    service.session = AsyncMock()
    
    yield service
    
    # Cleanup
    try:
        await service.shutdown()
    except:
        pass


@pytest.mark.asyncio
async def test_device_discovery(discovery_service, mock_data_api_response):
    """Test device discovery from data-api"""
    # Mock data-api response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_data_api_response)
    
    with patch.object(discovery_service.session, 'get') as mock_get:
        mock_get.return_value.__aenter__.return_value = mock_response
        
        # Discover devices
        devices = await discovery_service.discover_devices()
        
        # Verify discovery occurred
        assert devices is not None
        assert isinstance(devices, dict)


@pytest.mark.asyncio
async def test_entity_discovery(discovery_service, mock_data_api_response):
    """Test entity discovery from data-api"""
    # Mock data-api response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_data_api_response)
    
    with patch.object(discovery_service.session, 'get') as mock_get:
        mock_get.return_value.__aenter__.return_value = mock_response
        
        # Discover entities
        entities = await discovery_service.discover_entities()
        
        # Verify discovery occurred
        assert entities is not None
        assert isinstance(entities, dict)


@pytest.mark.asyncio
async def test_get_device_info(discovery_service, mock_data_api_response):
    """Test getting device info for entity"""
    # Mock cached data
    discovery_service._device_cache = {
        'switch.living_room_lamp': {
            'device_id': 'device_123',
            'name': 'Living Room Lamp'
        }
    }
    
    # Get device info
    device_info = await discovery_service.get_device_info('switch.living_room_lamp')
    
    # Verify device info returned
    assert device_info is not None
    assert 'device_id' in device_info


@pytest.mark.asyncio
async def test_get_area_info(discovery_service, mock_data_api_response):
    """Test getting area info for entity"""
    # Mock cached data
    discovery_service._entity_cache = {
        'switch.living_room_lamp': {
            'area_id': 'area_living_room'
        }
    }
    discovery_service._area_cache = {
        'area_living_room': {
            'name': 'Living Room'
        }
    }
    
    # Get area info
    area_info = await discovery_service.get_area_info('switch.living_room_lamp')
    
    # Verify area info returned
    assert area_info is not None


@pytest.mark.asyncio
async def test_cache_refresh(discovery_service, mock_data_api_response):
    """Test cache refresh mechanism"""
    # Mock data-api response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_data_api_response)
    
    with patch.object(discovery_service.session, 'get') as mock_get:
        mock_get.return_value.__aenter__.return_value = mock_response
        
        # Refresh cache
        await discovery_service.refresh_cache()
        
        # Verify cache was refreshed
        assert discovery_service._device_cache is not None
        assert discovery_service._entity_cache is not None


@pytest.mark.asyncio
async def test_discovery_error_handling(discovery_service):
    """Test error handling in discovery service"""
    # Mock API error
    mock_response = AsyncMock()
    mock_response.status = 500
    mock_response.text = AsyncMock(return_value="Internal Server Error")
    
    with patch.object(discovery_service.session, 'get') as mock_get:
        mock_get.return_value.__aenter__.return_value = mock_response
        
        # Discover should handle error gracefully
        devices = await discovery_service.discover_devices()
        
        # Should return empty dict or None on error
        assert devices is None or isinstance(devices, dict)


@pytest.mark.asyncio
async def test_data_api_integration(discovery_service, mock_data_api_response):
    """Test integration with data-api service"""
    # Mock successful data-api response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_data_api_response)
    
    with patch.object(discovery_service.session, 'get') as mock_get:
        mock_get.return_value.__aenter__.return_value = mock_response
        
        # Test full integration
        await discovery_service.refresh_cache()
        
        # Verify data-api was called
        assert mock_get.called
        
        # Verify cache was populated
        assert discovery_service._device_cache is not None

