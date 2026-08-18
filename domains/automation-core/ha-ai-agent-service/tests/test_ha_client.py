"""Tests for Home Assistant Client"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.clients.ha_client import HomeAssistantClient


@pytest.fixture
def ha_client():
    """Create HomeAssistantClient instance"""
    return HomeAssistantClient(ha_url="http://test-ha:8123", access_token="test-token")


@pytest.mark.asyncio
async def test_get_area_registry_success(ha_client):
    """Area registry is read over the shared WebSocket connection."""
    mock_records = [
        {"area_id": "office", "name": "Office", "aliases": ["workspace"]},
        {"area_id": "kitchen", "name": "Kitchen", "aliases": []},
    ]
    connection = AsyncMock()
    connection.list_areas.return_value = mock_records

    with patch.object(HomeAssistantClient, "_connection", AsyncMock(return_value=connection)):
        result = await ha_client.get_area_registry()

    assert result == mock_records
    connection.list_areas.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_area_registry_empty(ha_client):
    """An empty area registry is returned as an empty list, not an error."""
    connection = AsyncMock()
    connection.list_areas.return_value = []

    with patch.object(HomeAssistantClient, "_connection", AsyncMock(return_value=connection)):
        assert await ha_client.get_area_registry() == []


@pytest.mark.asyncio
async def test_get_area_registry_error_drops_connection(ha_client):
    """A failed read propagates and clears the cached connection so the next call reconnects."""
    connection = AsyncMock()
    connection.list_areas.side_effect = RuntimeError("websocket closed")
    ha_client._ws = connection

    with (
        patch.object(HomeAssistantClient, "_connection", AsyncMock(return_value=connection)),
        pytest.raises(RuntimeError, match="websocket closed"),
    ):
        await ha_client.get_area_registry()

    assert ha_client._ws is None
    connection.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_services_success(ha_client):
    """Test successfully fetching services"""
    mock_services = {"light": {"turn_on": {}, "turn_off": {}}}

    mock_session = MagicMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_services)
    mock_response.raise_for_status = MagicMock()
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

    mock_session = MagicMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_states)
    mock_response.raise_for_status = MagicMock()
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
async def test_get_device_registry_success(ha_client):
    """Device registry is read over the shared WebSocket connection."""
    mock_records = [
        {"id": "dev_1", "name": "Office Light", "manufacturer": "Acme", "model": "L1", "area_id": "office"},
    ]
    connection = AsyncMock()
    connection.list_devices.return_value = mock_records

    with patch.object(HomeAssistantClient, "_connection", AsyncMock(return_value=connection)):
        result = await ha_client.get_device_registry()

    assert result == mock_records
    connection.list_devices.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_device_registry_empty(ha_client):
    """An empty device registry is returned as an empty list, not an error."""
    connection = AsyncMock()
    connection.list_devices.return_value = []

    with patch.object(HomeAssistantClient, "_connection", AsyncMock(return_value=connection)):
        assert await ha_client.get_device_registry() == []


@pytest.mark.asyncio
async def test_get_device_registry_error_drops_connection(ha_client):
    """A failed read propagates and clears the cached connection so the next call reconnects."""
    connection = AsyncMock()
    connection.list_devices.side_effect = RuntimeError("websocket closed")
    ha_client._ws = connection

    with (
        patch.object(HomeAssistantClient, "_connection", AsyncMock(return_value=connection)),
        pytest.raises(RuntimeError, match="websocket closed"),
    ):
        await ha_client.get_device_registry()

    assert ha_client._ws is None
    connection.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_entity_registry_success(ha_client):
    """Entity registry is read over the shared WebSocket connection."""
    mock_records = [
        {"entity_id": "light.office_1", "device_id": "dev_1", "area_id": "office", "disabled_by": None},
    ]
    connection = AsyncMock()
    connection.list_entities.return_value = mock_records

    with patch.object(HomeAssistantClient, "_connection", AsyncMock(return_value=connection)):
        result = await ha_client.get_entity_registry()

    assert result == mock_records
    connection.list_entities.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_entity_registry_empty(ha_client):
    """An empty entity registry is returned as an empty list, not an error."""
    connection = AsyncMock()
    connection.list_entities.return_value = []

    with patch.object(HomeAssistantClient, "_connection", AsyncMock(return_value=connection)):
        assert await ha_client.get_entity_registry() == []


@pytest.mark.asyncio
async def test_get_entity_registry_error_drops_connection(ha_client):
    """A failed read propagates and clears the cached connection so the next call reconnects."""
    connection = AsyncMock()
    connection.list_entities.side_effect = RuntimeError("websocket closed")
    ha_client._ws = connection

    with (
        patch.object(HomeAssistantClient, "_connection", AsyncMock(return_value=connection)),
        pytest.raises(RuntimeError, match="websocket closed"),
    ):
        await ha_client.get_entity_registry()

    assert ha_client._ws is None
    connection.close.assert_awaited_once()
