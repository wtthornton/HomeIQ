"""Tests for Home Assistant Client"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp
import json

from src.clients.ha_client import HomeAssistantClient


@pytest.fixture
def ha_client():
    """Create HomeAssistantClient instance"""
    return HomeAssistantClient(
        ha_url="http://test-ha:8123",
        access_token="test-token"
    )


@pytest.mark.asyncio
async def test_get_area_registry_websocket_success(ha_client):
    """Test successfully fetching area registry via WebSocket API (2025 best practice)"""
    mock_areas = [
        {"area_id": "office", "name": "Office", "aliases": ["workspace"]},
        {"area_id": "kitchen", "name": "Kitchen", "aliases": []},
    ]

    # Mock WebSocket connection and responses
    mock_websocket = AsyncMock()
    
    # Auth required response
    auth_required = json.dumps({"type": "auth_required", "ha_version": "2025.1.0"})
    # Auth OK response
    auth_ok = json.dumps({"type": "auth_ok"})
    # Area registry response
    area_response = json.dumps({
        "id": 1,
        "type": "result",
        "success": True,
        "result": mock_areas
    })
    
    # Setup WebSocket receive sequence
    mock_websocket.recv.side_effect = [auth_required, auth_ok, area_response]
    mock_websocket.send = AsyncMock()
    mock_websocket.__aenter__ = AsyncMock(return_value=mock_websocket)
    mock_websocket.__aexit__ = AsyncMock(return_value=None)

    with patch('websockets.connect', return_value=mock_websocket):
        areas = await ha_client.get_area_registry()

    assert len(areas) == 2
    assert areas[0]["area_id"] == "office"
    assert areas[0]["name"] == "Office"
    # Verify WebSocket was used
    assert mock_websocket.send.called


@pytest.mark.asyncio
async def test_get_area_registry_websocket_fallback_to_rest(ha_client):
    """Test WebSocket failure falls back to REST API"""
    mock_areas = [
        {"area_id": "office", "name": "Office"},
    ]

    # Mock WebSocket failure
    mock_websocket = AsyncMock()
    mock_websocket.__aenter__.side_effect = Exception("WebSocket connection failed")
    
    # Mock REST API success
    mock_session = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_areas)
    mock_response.raise_for_status = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response
    mock_session.get.return_value.__aexit__.return_value = None

    ha_client._get_session = AsyncMock(return_value=mock_session)

    with patch('websockets.connect', return_value=mock_websocket):
        areas = await ha_client.get_area_registry()

    assert len(areas) == 1
    assert areas[0]["area_id"] == "office"


@pytest.mark.asyncio
async def test_get_area_registry_success(ha_client):
    """Test successfully fetching area registry via REST API (fallback)"""
    mock_areas = [
        {"area_id": "office", "name": "Office"},
        {"area_id": "kitchen", "name": "Kitchen"},
    ]

    # Mock WebSocket failure
    mock_websocket = AsyncMock()
    mock_websocket.__aenter__.side_effect = Exception("WebSocket unavailable")
    
    mock_session = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_areas)
    mock_response.raise_for_status = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response
    mock_session.get.return_value.__aexit__.return_value = None

    ha_client._get_session = AsyncMock(return_value=mock_session)

    with patch('websockets.connect', return_value=mock_websocket):
        areas = await ha_client.get_area_registry()

    assert len(areas) == 2
    assert areas[0]["area_id"] == "office"


@pytest.mark.asyncio
async def test_get_area_registry_404(ha_client):
    """Test handling 404 for area registry (endpoint not available)"""
    mock_session = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status = 404
    mock_session.get.return_value.__aenter__.return_value = mock_response
    mock_session.get.return_value.__aexit__.return_value = None

    ha_client._get_session = AsyncMock(return_value=mock_session)

    areas = await ha_client.get_area_registry()

    # Should return empty list for 404
    assert areas == []


@pytest.mark.asyncio
async def test_get_area_registry_dict_response(ha_client):
    """Test handling dict response with 'areas' key"""
    mock_response_data = {
        "areas": [
            {"area_id": "office", "name": "Office"}
        ]
    }

    mock_session = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_response_data)
    mock_response.raise_for_status = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response
    mock_session.get.return_value.__aexit__.return_value = None

    ha_client._get_session = AsyncMock(return_value=mock_session)

    areas = await ha_client.get_area_registry()

    assert len(areas) == 1
    assert areas[0]["area_id"] == "office"


@pytest.mark.asyncio
async def test_get_services_success(ha_client):
    """Test successfully fetching services"""
    mock_services = {
        "light": {
            "turn_on": {},
            "turn_off": {}
        }
    }

    mock_session = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_services)
    mock_response.raise_for_status = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response
    mock_session.get.return_value.__aexit__.return_value = None

    ha_client._get_session = AsyncMock(return_value=mock_session)

    services = await ha_client.get_services()

    assert "light" in services
    assert "turn_on" in services["light"]


@pytest.mark.asyncio
async def test_get_states_success(ha_client):
    """Test successfully fetching states"""
    mock_states = [
        {"entity_id": "light.office_1", "state": "on"},
        {"entity_id": "sensor.temp_1", "state": "25"},
    ]

    mock_session = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_states)
    mock_response.raise_for_status = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response
    mock_session.get.return_value.__aexit__.return_value = None

    ha_client._get_session = AsyncMock(return_value=mock_session)

    states = await ha_client.get_states()

    assert len(states) == 2
    assert states[0]["entity_id"] == "light.office_1"


@pytest.mark.asyncio
async def test_get_helpers_success(ha_client):
    """Test successfully fetching helpers"""
    mock_states = [
        {"entity_id": "input_boolean.test", "state": "on", "attributes": {"friendly_name": "Test"}},
        {"entity_id": "input_number.volume", "state": "50", "attributes": {"friendly_name": "Volume"}},
        {"entity_id": "light.office_1", "state": "on"},  # Not a helper
    ]

    ha_client.get_states = AsyncMock(return_value=mock_states)

    helpers = await ha_client.get_helpers()

    assert len(helpers) == 2
    assert any(h["type"] == "input_boolean" for h in helpers)
    assert any(h["type"] == "input_number" for h in helpers)


@pytest.mark.asyncio
async def test_get_scenes_success(ha_client):
    """Test successfully fetching scenes"""
    mock_states = [
        {"entity_id": "scene.morning", "state": "scening", "attributes": {"friendly_name": "Morning"}},
        {"entity_id": "scene.evening", "state": "scening", "attributes": {"friendly_name": "Evening"}},
        {"entity_id": "light.office_1", "state": "on"},  # Not a scene
    ]

    ha_client.get_states = AsyncMock(return_value=mock_states)

    scenes = await ha_client.get_scenes()

    assert len(scenes) == 2
    assert any(s["entity_id"] == "scene.morning" for s in scenes)
    assert any(s["entity_id"] == "scene.evening" for s in scenes)


@pytest.mark.asyncio
async def test_get_helpers_error(ha_client):
    """Test handling errors when fetching helpers"""
    ha_client.get_states = AsyncMock(side_effect=Exception("API Error"))

    with pytest.raises(Exception, match="Failed to fetch helpers"):
        await ha_client.get_helpers()


@pytest.mark.asyncio
async def test_get_scenes_error(ha_client):
    """Test handling errors when fetching scenes"""
    ha_client.get_states = AsyncMock(side_effect=Exception("API Error"))

    with pytest.raises(Exception, match="Failed to fetch scenes"):
        await ha_client.get_scenes()


@pytest.mark.asyncio
async def test_close(ha_client):
    """Test closing client"""
    mock_session = AsyncMock()
    mock_session.closed = False
    ha_client._session = mock_session

    await ha_client.close()

    mock_session.close.assert_called_once()


@pytest.mark.asyncio
async def test_close_no_session(ha_client):
    """Test closing when no session exists"""
    ha_client._session = None

    # Should not raise error
    await ha_client.close()


# Device Registry Tests (Epic AI-23)
@pytest.mark.asyncio
async def test_get_device_registry_websocket_success(ha_client):
    """Test successfully fetching device registry via WebSocket API (2025 best practice)"""
    mock_devices = [
        {
            "id": "device1",
            "name": "Office Light Device",
            "area_id": "office",
            "manufacturer": "Philips",
            "model": "Hue Light",
            "sw_version": "1.0.0"
        },
        {
            "id": "device2",
            "name": "Kitchen Light Device",
            "area_id": "kitchen",
            "manufacturer": "LIFX",
            "model": "A19",
            "sw_version": "2.0.0"
        },
    ]

    # Mock WebSocket connection and responses
    mock_websocket = AsyncMock()
    
    # Auth required response
    auth_required = json.dumps({"type": "auth_required", "ha_version": "2025.1.0"})
    # Auth OK response
    auth_ok = json.dumps({"type": "auth_ok"})
    # Device registry response
    device_response = json.dumps({
        "id": 2,
        "type": "result",
        "success": True,
        "result": mock_devices
    })
    
    # Setup WebSocket receive sequence
    mock_websocket.recv.side_effect = [auth_required, auth_ok, device_response]
    mock_websocket.send = AsyncMock()
    mock_websocket.__aenter__ = AsyncMock(return_value=mock_websocket)
    mock_websocket.__aexit__ = AsyncMock(return_value=None)

    with patch('websockets.connect', return_value=mock_websocket):
        devices = await ha_client.get_device_registry()

    assert len(devices) == 2
    assert devices[0]["id"] == "device1"
    assert devices[0]["area_id"] == "office"
    assert devices[0]["manufacturer"] == "Philips"
    # Verify WebSocket was used
    assert mock_websocket.send.called


@pytest.mark.asyncio
async def test_get_device_registry_websocket_fallback_to_rest(ha_client):
    """Test WebSocket failure falls back to REST API"""
    mock_devices = [
        {
            "id": "device1",
            "name": "Office Light Device",
            "area_id": "office",
            "manufacturer": "Philips",
            "model": "Hue Light"
        },
    ]

    # Mock WebSocket failure
    mock_websocket = AsyncMock()
    mock_websocket.__aenter__.side_effect = Exception("WebSocket connection failed")
    
    # Mock REST API success
    mock_session = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_devices)
    mock_response.raise_for_status = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response
    mock_session.get.return_value.__aexit__.return_value = None

    ha_client._get_session = AsyncMock(return_value=mock_session)

    with patch('websockets.connect', return_value=mock_websocket):
        devices = await ha_client.get_device_registry()

    assert len(devices) == 1
    assert devices[0]["id"] == "device1"
    assert devices[0]["area_id"] == "office"


@pytest.mark.asyncio
async def test_get_device_registry_404(ha_client):
    """Test handling 404 for device registry (endpoint not available)"""
    mock_session = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status = 404
    mock_session.get.return_value.__aenter__.return_value = mock_response
    mock_session.get.return_value.__aexit__.return_value = None

    ha_client._get_session = AsyncMock(return_value=mock_session)

    devices = await ha_client.get_device_registry()

    # Should return empty list for 404
    assert devices == []


@pytest.mark.asyncio
async def test_get_device_registry_dict_response(ha_client):
    """Test handling dict response with 'devices' key"""
    mock_response_data = {
        "devices": [
            {
                "id": "device1",
                "name": "Office Light Device",
                "area_id": "office"
            }
        ]
    }

    mock_session = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_response_data)
    mock_response.raise_for_status = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response
    mock_session.get.return_value.__aexit__.return_value = None

    ha_client._get_session = AsyncMock(return_value=mock_session)

    devices = await ha_client.get_device_registry()

    assert len(devices) == 1
    assert devices[0]["id"] == "device1"


# Entity Registry Tests (Epic AI-23)
@pytest.mark.asyncio
async def test_get_entity_registry_websocket_success(ha_client):
    """Test successfully fetching entity registry via WebSocket API (2025 best practice)"""
    mock_entities = [
        {
            "entity_id": "light.office_1",
            "name": "Office Light",
            "aliases": ["workspace light", "desk light"],
            "category": "light",
            "disabled_by": None
        },
        {
            "entity_id": "sensor.temp_1",
            "name": "Temperature Sensor",
            "aliases": [],
            "category": "diagnostic",
            "disabled_by": None
        },
    ]

    # Mock WebSocket connection and responses
    mock_websocket = AsyncMock()
    
    # Auth required response
    auth_required = json.dumps({"type": "auth_required", "ha_version": "2025.1.0"})
    # Auth OK response
    auth_ok = json.dumps({"type": "auth_ok"})
    # Entity registry response
    entity_response = json.dumps({
        "id": 3,
        "type": "result",
        "success": True,
        "result": mock_entities
    })
    
    # Setup WebSocket receive sequence
    mock_websocket.recv.side_effect = [auth_required, auth_ok, entity_response]
    mock_websocket.send = AsyncMock()
    mock_websocket.__aenter__ = AsyncMock(return_value=mock_websocket)
    mock_websocket.__aexit__ = AsyncMock(return_value=None)

    with patch('websockets.connect', return_value=mock_websocket):
        entities = await ha_client.get_entity_registry()

    assert len(entities) == 2
    assert entities[0]["entity_id"] == "light.office_1"
    assert entities[0]["aliases"] == ["workspace light", "desk light"]
    assert entities[0]["category"] == "light"
    # Verify WebSocket was used
    assert mock_websocket.send.called


@pytest.mark.asyncio
async def test_get_entity_registry_websocket_fallback_to_rest(ha_client):
    """Test WebSocket failure falls back to REST API"""
    mock_entities = [
        {
            "entity_id": "light.office_1",
            "name": "Office Light",
            "aliases": ["workspace light"]
        },
    ]

    # Mock WebSocket failure
    mock_websocket = AsyncMock()
    mock_websocket.__aenter__.side_effect = Exception("WebSocket connection failed")
    
    # Mock REST API success
    mock_session = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_entities)
    mock_response.raise_for_status = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response
    mock_session.get.return_value.__aexit__.return_value = None

    ha_client._get_session = AsyncMock(return_value=mock_session)

    with patch('websockets.connect', return_value=mock_websocket):
        entities = await ha_client.get_entity_registry()

    assert len(entities) == 1
    assert entities[0]["entity_id"] == "light.office_1"


@pytest.mark.asyncio
async def test_get_entity_registry_404(ha_client):
    """Test handling 404 for entity registry (endpoint not available)"""
    mock_session = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status = 404
    mock_session.get.return_value.__aenter__.return_value = mock_response
    mock_session.get.return_value.__aexit__.return_value = None

    ha_client._get_session = AsyncMock(return_value=mock_session)

    entities = await ha_client.get_entity_registry()

    # Should return empty list for 404
    assert entities == []


@pytest.mark.asyncio
async def test_get_entity_registry_dict_response(ha_client):
    """Test handling dict response with 'entities' key"""
    mock_response_data = {
        "entities": [
            {
                "entity_id": "light.office_1",
                "name": "Office Light",
                "aliases": ["workspace light"]
            }
        ]
    }

    mock_session = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_response_data)
    mock_response.raise_for_status = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response
    mock_session.get.return_value.__aexit__.return_value = None

    ha_client._get_session = AsyncMock(return_value=mock_session)

    entities = await ha_client.get_entity_registry()

    assert len(entities) == 1
    assert entities[0]["entity_id"] == "light.office_1"