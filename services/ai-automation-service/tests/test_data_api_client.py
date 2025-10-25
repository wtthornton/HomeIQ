"""
Unit tests for Data API Client
"""

import pytest
import httpx
import pandas as pd
import os
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from src.clients.data_api_client import DataAPIClient


@pytest.fixture
def mock_response():
    """Create a mock HTTP response"""
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json = MagicMock()
    return response


@pytest.fixture
def data_api_client(test_config):
    """Create a DataAPIClient instance using test configuration"""
    return DataAPIClient(base_url=test_config.get('data_api_url', 'http://localhost:8006'))


class TestDataAPIClient:
    """Test Data API Client"""
    
    @pytest.mark.asyncio
    async def test_init_with_monkeypatch(self, monkeypatch):
        """Test client initialization using Context7 monkeypatch pattern"""
        # Context7 pattern: Use monkeypatch for isolated environment testing
        monkeypatch.setenv("DATA_API_URL", "http://test-override:8006")
        
        client = DataAPIClient(base_url=os.getenv('DATA_API_URL', 'http://localhost:8006'))
        assert client.base_url == "http://test-override:8006"
        assert client.client is not None
        await client.close()
    
    @pytest.mark.asyncio
    async def test_fetch_events_success(self, data_api_client, mock_response):
        """Test successful event fetching"""
        # Mock data
        mock_events = [
            {
                "timestamp": "2025-10-15T12:00:00Z",
                "entity_id": "light.bedroom",
                "event_type": "state_changed",
                "old_state": {"state": "off"},
                "new_state": {"state": "on"},
                "attributes": {"brightness": 255},
                "tags": {}
            },
            {
                "timestamp": "2025-10-15T12:05:00Z",
                "entity_id": "light.living_room",
                "event_type": "state_changed",
                "old_state": {"state": "off"},
                "new_state": {"state": "on"},
                "attributes": {"brightness": 200},
                "tags": {}
            }
        ]
        
        mock_response.json.return_value = {"events": mock_events}
        
        with patch.object(data_api_client.client, 'get', return_value=mock_response):
            df = await data_api_client.fetch_events(
                start_time=datetime(2025, 10, 15, 0, 0, 0),
                end_time=datetime(2025, 10, 15, 23, 59, 59)
            )
            
            assert isinstance(df, pd.DataFrame)
            assert len(df) == 2
            assert 'timestamp' in df.columns
            assert 'entity_id' in df.columns
            assert df.iloc[0]['entity_id'] == 'light.bedroom'
            assert df.iloc[1]['entity_id'] == 'light.living_room'
    
    @pytest.mark.asyncio
    async def test_fetch_events_empty_result(self, data_api_client, mock_response):
        """Test fetching events with empty result"""
        mock_response.json.return_value = {"events": []}
        
        with patch.object(data_api_client.client, 'get', return_value=mock_response):
            df = await data_api_client.fetch_events()
            
            assert isinstance(df, pd.DataFrame)
            assert len(df) == 0
    
    @pytest.mark.asyncio
    async def test_fetch_events_with_filters(self, data_api_client, mock_response):
        """Test fetching events with filters"""
        mock_response.json.return_value = {"events": []}
        
        with patch.object(data_api_client.client, 'get', return_value=mock_response) as mock_get:
            await data_api_client.fetch_events(
                entity_id="light.bedroom",
                device_id="device123",
                event_type="state_changed"
            )
            
            # Verify filters were passed
            call_kwargs = mock_get.call_args[1]
            assert 'params' in call_kwargs
            params = call_kwargs['params']
            assert params['entity_id'] == "light.bedroom"
            assert params['device_id'] == "device123"
            assert params['event_type'] == "state_changed"
    
    @pytest.mark.asyncio
    async def test_fetch_events_http_error(self, data_api_client):
        """Test fetch events with HTTP error"""
        with patch.object(data_api_client.client, 'get', side_effect=httpx.HTTPStatusError(
            "Server error",
            request=MagicMock(),
            response=MagicMock(status_code=500)
        )):
            with pytest.raises(httpx.HTTPStatusError):
                await data_api_client.fetch_events()
    
    @pytest.mark.asyncio
    async def test_fetch_events_retry_logic(self, data_api_client, mock_response):
        """Test retry logic on transient failures"""
        mock_response.json.return_value = {"events": []}
        
        # Fail twice, then succeed
        with patch.object(data_api_client.client, 'get') as mock_get:
            mock_get.side_effect = [
                httpx.TimeoutException("Timeout 1"),
                httpx.TimeoutException("Timeout 2"),
                mock_response
            ]
            
            df = await data_api_client.fetch_events()
            
            # Should have retried 3 times
            assert mock_get.call_count == 3
            assert isinstance(df, pd.DataFrame)
    
    @pytest.mark.asyncio
    async def test_fetch_devices_success(self, data_api_client, mock_response):
        """Test successful device fetching"""
        mock_devices = [
            {
                "device_id": "device1",
                "name": "Bedroom Light",
                "manufacturer": "Philips",
                "model": "Hue",
                "area_id": "bedroom",
                "entity_count": 1
            },
            {
                "device_id": "device2",
                "name": "Living Room Sensor",
                "manufacturer": "Aqara",
                "model": "Temperature Sensor",
                "area_id": "living_room",
                "entity_count": 2
            }
        ]
        
        mock_response.json.return_value = {"devices": mock_devices}
        
        with patch.object(data_api_client.client, 'get', return_value=mock_response):
            devices = await data_api_client.fetch_devices()
            
            assert isinstance(devices, list)
            assert len(devices) == 2
            assert devices[0]['device_id'] == 'device1'
            assert devices[1]['name'] == 'Living Room Sensor'
    
    @pytest.mark.asyncio
    async def test_fetch_devices_with_filters(self, data_api_client, mock_response):
        """Test fetching devices with filters"""
        mock_response.json.return_value = {"devices": []}
        
        with patch.object(data_api_client.client, 'get', return_value=mock_response) as mock_get:
            await data_api_client.fetch_devices(
                manufacturer="Philips",
                model="Hue",
                area_id="bedroom"
            )
            
            # Verify filters were passed
            call_kwargs = mock_get.call_args[1]
            assert 'params' in call_kwargs
            params = call_kwargs['params']
            assert params['manufacturer'] == "Philips"
            assert params['model'] == "Hue"
            assert params['area_id'] == "bedroom"
    
    @pytest.mark.asyncio
    async def test_fetch_entities_success(self, data_api_client, mock_response):
        """Test successful entity fetching"""
        mock_entities = [
            {
                "entity_id": "light.bedroom",
                "device_id": "device1",
                "domain": "light",
                "platform": "hue",
                "area_id": "bedroom",
                "disabled": False
            },
            {
                "entity_id": "sensor.temperature",
                "device_id": "device2",
                "domain": "sensor",
                "platform": "aqara",
                "area_id": "living_room",
                "disabled": False
            }
        ]
        
        mock_response.json.return_value = {"entities": mock_entities}
        
        with patch.object(data_api_client.client, 'get', return_value=mock_response):
            entities = await data_api_client.fetch_entities()
            
            assert isinstance(entities, list)
            assert len(entities) == 2
            assert entities[0]['entity_id'] == 'light.bedroom'
            assert entities[1]['domain'] == 'sensor'
    
    @pytest.mark.asyncio
    async def test_fetch_entities_with_filters(self, data_api_client, mock_response):
        """Test fetching entities with filters"""
        mock_response.json.return_value = {"entities": []}
        
        with patch.object(data_api_client.client, 'get', return_value=mock_response) as mock_get:
            await data_api_client.fetch_entities(
                device_id="device1",
                domain="light",
                platform="hue",
                area_id="bedroom"
            )
            
            # Verify filters were passed
            call_kwargs = mock_get.call_args[1]
            assert 'params' in call_kwargs
            params = call_kwargs['params']
            assert params['device_id'] == "device1"
            assert params['domain'] == "light"
            assert params['platform'] == "hue"
            assert params['area_id'] == "bedroom"
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, data_api_client, mock_response):
        """Test health check"""
        mock_health = {
            "status": "healthy",
            "service": "data-api",
            "version": "1.0.0"
        }
        
        mock_response.json.return_value = mock_health
        
        with patch.object(data_api_client.client, 'get', return_value=mock_response):
            health = await data_api_client.health_check()
            
            assert health['status'] == 'healthy'
            assert health['service'] == 'data-api'
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, data_api_client):
        """Test health check with failure"""
        with patch.object(data_api_client.client, 'get', side_effect=httpx.HTTPError("Connection failed")):
            with pytest.raises(httpx.HTTPError):
                await data_api_client.health_check()
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager"""
        async with DataAPIClient(base_url="http://test:8006") as client:
            assert client is not None
        # Client should be closed after context
    
    @pytest.mark.asyncio
    async def test_close(self, data_api_client):
        """Test close method"""
        await data_api_client.close()
        # Should not raise any errors


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_data_api_connection():
    """
    Integration test with real Data API
    Requires: docker-compose up data-api
    """
    client = DataAPIClient(base_url="http://localhost:8006")
    
    try:
        # Test health check
        health = await client.health_check()
        assert 'status' in health
        
        # Test fetch devices
        devices = await client.fetch_devices(limit=10)
        assert isinstance(devices, list)
        
        # Test fetch entities
        entities = await client.fetch_entities(limit=10)
        assert isinstance(entities, list)
        
        # Test fetch events (last 1 day)
        start_time = datetime.utcnow() - timedelta(days=1)
        events_df = await client.fetch_events(start_time=start_time, limit=100)
        assert isinstance(events_df, pd.DataFrame)
        
    finally:
        await client.close()

