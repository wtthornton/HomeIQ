"""
Unit tests for Client modules

Epic 39, Story 39.8: Pattern Service Testing & Validation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pandas as pd
from datetime import datetime, timezone, timedelta

from src.clients.data_api_client import DataAPIClient
from src.clients.mqtt_client import MQTTNotificationClient


class TestDataAPIClient:
    """Test suite for DataAPIClient."""
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_fetch_events_success(self):
        """Test successful event fetching."""
        # Mock response
        mock_response = AsyncMock()
        mock_response.json.return_value = [
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "entity_id": "light.office",
                "state": "on",
                "event_type": "state_changed"
            }
        ]
        mock_response.raise_for_status = AsyncMock()
        
        # Mock httpx.AsyncClient
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        
        client = DataAPIClient(base_url="http://test:8006")
        # Replace the client with our mock
        client.client = mock_client
        df = await client.fetch_events()
        
        assert isinstance(df, pd.DataFrame)
        mock_client.get.assert_called_once()
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_fetch_devices_success(self):
        """Test successful device fetching."""
        # Mock response
        mock_response = AsyncMock()
        mock_response.json.return_value = [
            {
                "device_id": "light.office",
                "name": "Office Light",
                "area_id": "office"
            }
        ]
        mock_response.raise_for_status = AsyncMock()
        
        # Mock httpx.AsyncClient
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        
        client = DataAPIClient(base_url="http://test:8006")
        # Replace the client with our mock
        client.client = mock_client
        devices = await client.fetch_devices()
        
        assert isinstance(devices, list)
        assert len(devices) == 1
        assert devices[0]["device_id"] == "light.office"
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_fetch_entities_success(self):
        """Test successful entity fetching."""
        # Mock response
        mock_response = AsyncMock()
        mock_response.json.return_value = [
            {
                "entity_id": "light.office",
                "device_id": "light.office",
                "domain": "light"
            }
        ]
        mock_response.raise_for_status = AsyncMock()
        
        # Mock httpx.AsyncClient
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        
        client = DataAPIClient(base_url="http://test:8006")
        # Replace the client with our mock
        client.client = mock_client
        entities = await client.fetch_entities()
        
        assert isinstance(entities, list)
        assert len(entities) == 1
        assert entities[0]["entity_id"] == "light.office"


class TestMQTTNotificationClient:
    """Test suite for MQTTNotificationClient."""
    
    @pytest.mark.unit
    def test_publish_notification(self):
        """Test publishing MQTT notification."""
        with patch("paho.mqtt.client.Client") as mock_mqtt_class:
            mock_client = MagicMock()
            mock_mqtt_class.return_value = mock_client
            mock_client.connect = MagicMock(return_value=0)
            mock_client.publish = MagicMock(return_value=MagicMock(rc=0, mid=1))  # MQTTMessageInfo
            mock_client.loop_start = MagicMock()
            
            mqtt_client = MQTTNotificationClient(
                broker="test-broker",
                port=1883,
                enabled=True
            )
            mqtt_client.is_connected = True  # Simulate connected state
            mqtt_client.client = mock_client
            
            payload = {"status": "test", "data": "test_data"}
            result = mqtt_client.publish("test/topic", payload)
            
            assert result is True
            mock_client.publish.assert_called_once()
    
    @pytest.mark.unit
    def test_publish_disabled(self):
        """Test that publishing is disabled when client is disabled."""
        mqtt_client = MQTTNotificationClient(enabled=False)
        
        payload = {"status": "test"}
        result = mqtt_client.publish("test/topic", payload)
        
        assert result is False  # Should return False when disabled

