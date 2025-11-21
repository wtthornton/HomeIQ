"""
Test Device Intelligence Service integration
"""

from unittest.mock import AsyncMock, patch

import pytest
from src.clients.device_intelligence_client import DeviceIntelligenceClient


@pytest.mark.asyncio
async def test_get_devices_by_area():
    """Test getting devices by area"""
    client = DeviceIntelligenceClient()

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": "device1", "area_name": "office", "name": "Office Light"},
            {"id": "device2", "area_name": "kitchen", "name": "Kitchen Light"},
        ]
        mock_get.return_value = mock_response

        devices = await client.get_devices_by_area("office")
        assert len(devices) == 1
        assert devices[0]["name"] == "Office Light"

@pytest.mark.asyncio
async def test_get_device_details():
    """Test getting device details"""
    client = DeviceIntelligenceClient()

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "device1",
            "name": "Office Light",
            "manufacturer": "Inovelli",
            "model": "VZM31-SN",
            "area_name": "office",
            "health_score": 85,
            "capabilities": [
                {"feature": "led_notifications", "supported": True, "configured": False},
                {"feature": "smart_bulb_mode", "supported": True, "configured": True},
            ],
            "entities": [
                {
                    "entity_id": "light.office_main",
                    "domain": "light",
                    "state": "off",
                    "attributes": {"brightness": 0},
                },
            ],
        }
        mock_get.return_value = mock_response

        device = await client.get_device_details("device1")
        assert device["name"] == "Office Light"
        assert device["manufacturer"] == "Inovelli"
        assert len(device["capabilities"]) == 2
        assert device["capabilities"][0]["feature"] == "led_notifications"

@pytest.mark.asyncio
async def test_get_all_areas():
    """Test getting all areas"""
    client = DeviceIntelligenceClient()

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"area_id": "office", "name": "Office"},
            {"area_id": "kitchen", "name": "Kitchen"},
            {"area_id": "bedroom", "name": "Bedroom"},
        ]
        mock_get.return_value = mock_response

        areas = await client.get_all_areas()
        assert len(areas) == 3
        assert areas[0]["name"] == "Office"

@pytest.mark.asyncio
async def test_health_check():
    """Test health check"""
    client = DeviceIntelligenceClient()

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        is_healthy = await client.health_check()
        assert is_healthy is True

@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling"""
    client = DeviceIntelligenceClient()

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        devices = await client.get_devices_by_area("office")
        assert devices == []

        device = await client.get_device_details("device1")
        assert device is None

@pytest.mark.asyncio
async def test_device_not_found():
    """Test device not found scenario"""
    client = DeviceIntelligenceClient()

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        device = await client.get_device_details("nonexistent")
        assert device is None
