"""Tests for HTTP clients"""

import pytest
from unittest.mock import AsyncMock, patch

from src.clients.weather_api_client import WeatherAPIClient
from src.clients.sports_data_client import SportsDataClient
from src.clients.carbon_intensity_client import CarbonIntensityClient
from src.clients.data_api_client import DataAPIClient


@pytest.mark.asyncio
async def test_weather_api_client_success():
    """Test WeatherAPIClient successful fetch"""
    client = WeatherAPIClient(base_url="http://test-weather:8009")
    
    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "temperature": 72.5,
        "condition": "sunny",
        "humidity": 45
    }
    mock_response.raise_for_status = AsyncMock()
    
    with patch.object(client.client, 'get', return_value=mock_response):
        result = await client.get_current_weather()
        assert result is not None
        assert result["temperature"] == 72.5
    
    await client.close()


@pytest.mark.asyncio
async def test_weather_api_client_connection_error():
    """Test WeatherAPIClient graceful degradation on connection error"""
    client = WeatherAPIClient(base_url="http://test-weather:8009")
    
    with patch.object(client.client, 'get', side_effect=Exception("Connection failed")):
        result = await client.get_current_weather()
        assert result is None  # Graceful degradation
    
    await client.close()


@pytest.mark.asyncio
async def test_sports_data_client_success():
    """Test SportsDataClient successful fetch"""
    client = SportsDataClient(base_url="http://test-data:8006")
    
    mock_response = AsyncMock()
    mock_response.json.return_value = [
        {"id": "1", "team": "Lakers", "status": "live"}
    ]
    mock_response.raise_for_status = AsyncMock()
    
    with patch.object(client.client, 'get', return_value=mock_response):
        result = await client.get_live_games()
        assert isinstance(result, list)
        assert len(result) == 1
    
    await client.close()


@pytest.mark.asyncio
async def test_data_api_client_success():
    """Test DataAPIClient successful fetch"""
    client = DataAPIClient(base_url="http://test-data:8006")
    
    mock_response = AsyncMock()
    mock_response.json.return_value = [
        {"entity_id": "light.living_room", "state": "on"}
    ]
    mock_response.raise_for_status = AsyncMock()
    
    with patch.object(client.client, 'get', return_value=mock_response):
        result = await client.get_events(limit=10)
        assert isinstance(result, list)
        assert len(result) == 1
    
    await client.close()

