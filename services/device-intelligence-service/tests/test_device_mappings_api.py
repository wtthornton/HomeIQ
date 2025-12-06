"""
Unit tests for Device Mappings API endpoints (Epic AI-24).

Tests for type, relationships, and context endpoints with caching.
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from src.device_mappings.base import DeviceType
from src.device_mappings.cache import clear_cache, get_cache
from src.main import app


class TestDeviceMappingsAPI:
    """Tests for device mappings API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_hue_handler(self):
        """Create mock Hue handler."""
        handler = MagicMock()
        handler.can_handle.return_value = True
        handler.identify_type.return_value = DeviceType.GROUP
        handler.get_relationships.return_value = [
            {"type": "contains", "device_id": "light1", "description": "Contains light1"}
        ]
        handler.enrich_context.return_value = "Office Hue Room - controls all lights in the area"
        handler.__class__.__name__ = "HueHandler"
        return handler
    
    @pytest.fixture
    def sample_device_data(self):
        """Sample device data for testing."""
        return {
            "device_id": "hue_room_office",
            "manufacturer": "Signify",
            "model": "Room",
            "name": "Office",
            "area_id": "office"
        }
    
    def test_get_device_type_with_handler(self, client, mock_hue_handler, sample_device_data):
        """Test getting device type when handler is found."""
        with patch('src.api.device_mappings_router.get_registry') as mock_get_registry:
            registry = MagicMock()
            registry.find_handler.return_value = mock_hue_handler
            registry.get_handler_name.return_value = "hue"
            mock_get_registry.return_value = registry
            
            # Clear cache first
            clear_cache()
            
            response = client.post(
                "/api/device-mappings/hue_room_office/type",
                json=sample_device_data
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["device_id"] == "hue_room_office"
            assert data["type"] == "group"
            assert data["handler"] == "HueHandler"
            assert data["handler_name"] == "hue"
    
    def test_get_device_type_no_handler(self, client, sample_device_data):
        """Test getting device type when no handler is found."""
        with patch('src.api.device_mappings_router.get_registry') as mock_get_registry:
            registry = MagicMock()
            registry.find_handler.return_value = None
            mock_get_registry.return_value = registry
            
            # Clear cache first
            clear_cache()
            
            response = client.post(
                "/api/device-mappings/hue_room_office/type",
                json=sample_device_data
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["device_id"] == "hue_room_office"
            assert data["type"] == "individual"
            assert data["handler"] is None
            assert "message" in data
    
    def test_get_device_type_cache(self, client, mock_hue_handler, sample_device_data):
        """Test that device type is cached."""
        with patch('src.api.device_mappings_router.get_registry') as mock_get_registry:
            registry = MagicMock()
            registry.find_handler.return_value = mock_hue_handler
            registry.get_handler_name.return_value = "hue"
            mock_get_registry.return_value = registry
            
            # Clear cache first
            clear_cache()
            
            # First request
            response1 = client.post(
                "/api/device-mappings/hue_room_office/type",
                json=sample_device_data
            )
            assert response1.status_code == 200
            
            # Second request should use cache (registry.find_handler should not be called again)
            registry.find_handler.reset_mock()
            response2 = client.post(
                "/api/device-mappings/hue_room_office/type",
                json=sample_device_data
            )
            assert response2.status_code == 200
            assert response1.json() == response2.json()
            # Handler should not be called again (cached)
            registry.find_handler.assert_not_called()
    
    def test_get_device_type_id_mismatch(self, client, sample_device_data):
        """Test that device ID mismatch returns 400."""
        response = client.post(
            "/api/device-mappings/wrong_id/type",
            json=sample_device_data
        )
        
        assert response.status_code == 400
        assert "must match" in response.json()["detail"].lower()
    
    def test_get_device_relationships(self, client, mock_hue_handler, sample_device_data):
        """Test getting device relationships."""
        with patch('src.api.device_mappings_router.get_registry') as mock_get_registry:
            registry = MagicMock()
            registry.find_handler.return_value = mock_hue_handler
            registry.get_handler_name.return_value = "hue"
            mock_get_registry.return_value = registry
            
            # Clear cache first
            clear_cache()
            
            response = client.post(
                "/api/device-mappings/hue_room_office/relationships",
                json=sample_device_data
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["device_id"] == "hue_room_office"
            assert "relationships" in data
            assert len(data["relationships"]) > 0
            assert data["handler"] == "HueHandler"
    
    def test_get_device_context(self, client, mock_hue_handler, sample_device_data):
        """Test getting device context."""
        with patch('src.api.device_mappings_router.get_registry') as mock_get_registry:
            registry = MagicMock()
            registry.find_handler.return_value = mock_hue_handler
            registry.get_handler_name.return_value = "hue"
            mock_get_registry.return_value = registry
            
            # Clear cache first
            clear_cache()
            
            response = client.post(
                "/api/device-mappings/hue_room_office/context",
                json=sample_device_data
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["device_id"] == "hue_room_office"
            assert "context" in data
            assert "Hue Room" in data["context"]
            assert data["handler"] == "HueHandler"
    
    def test_reload_clears_cache(self, client):
        """Test that reload endpoint clears cache."""
        # Set some cache entries
        cache = get_cache()
        cache.set("test_key", "test_value")
        assert cache.size() > 0
        
        with patch('src.api.device_mappings_router.reload_registry') as mock_reload:
            registry = MagicMock()
            registry.get_all_handlers.return_value = {"hue": MagicMock()}
            mock_reload.return_value = registry
            
            response = client.post("/api/device-mappings/reload")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["cache_cleared"] is True
            # Cache should be cleared
            assert cache.size() == 0
    
    def test_get_status(self, client):
        """Test getting device mappings status."""
        with patch('src.api.device_mappings_router.get_registry') as mock_get_registry:
            registry = MagicMock()
            registry.get_all_handlers.return_value = {"hue": MagicMock(), "wled": MagicMock()}
            mock_get_registry.return_value = registry
            
            response = client.get("/api/device-mappings/status")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "operational"
            assert data["handler_count"] == 2
            assert "hue" in data["handlers"]
            assert "wled" in data["handlers"]
            assert "cache_size" in data

