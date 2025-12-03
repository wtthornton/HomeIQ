"""Tests for Home Assistant Client"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp

from src.clients.ha_client import HomeAssistantClient


@pytest.fixture
def ha_client():
    """Create HomeAssistantClient instance"""
    return HomeAssistantClient(
        ha_url="http://test-ha:8123",
        access_token="test-token"
    )


@pytest.mark.asyncio
async def test_get_area_registry_success(ha_client):
    """Test successfully fetching area registry"""
    mock_areas = [
        {"area_id": "office", "name": "Office"},
        {"area_id": "kitchen", "name": "Kitchen"},
    ]

    mock_session = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_areas)
    mock_response.raise_for_status = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response
    mock_session.get.return_value.__aexit__.return_value = None

    ha_client._get_session = AsyncMock(return_value=mock_session)

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

