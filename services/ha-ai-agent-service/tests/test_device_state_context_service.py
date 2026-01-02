"""Tests for Device State Context Service"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.device_state_context_service import DeviceStateContextService
from src.config import Settings
from src.services.context_builder import ContextBuilder


@pytest.fixture
def mock_settings():
    """Create mock settings"""
    return Settings(
        ha_url="http://test-ha:8123",
        ha_token="test-token",
        data_api_url="http://test-data-api:8006"
    )


@pytest.fixture
def mock_context_builder():
    """Create mock context builder"""
    builder = MagicMock(spec=ContextBuilder)
    builder._get_cached_value = AsyncMock(return_value=None)
    builder._set_cached_value = AsyncMock()
    return builder


@pytest.fixture
def device_state_context_service(mock_settings, mock_context_builder):
    """Create DeviceStateContextService instance"""
    return DeviceStateContextService(
        settings=mock_settings,
        context_builder=mock_context_builder
    )


@pytest.mark.asyncio
async def test_get_state_context_with_entities(device_state_context_service, mock_context_builder):
    """Test getting state context for entities"""
    # Mock states response
    mock_states = [
        {
            "entity_id": "light.office_go",
            "state": "on",
            "attributes": {
                "brightness": 255,
                "color_mode": "rgb",
                "rgb_color": [255, 0, 0]
            }
        },
        {
            "entity_id": "light.office_back_right",
            "state": "off",
            "attributes": {}
        },
        {
            "entity_id": "sensor.temp_office",
            "state": "22.5",
            "attributes": {
                "unit_of_measurement": "°C"
            }
        }
    ]

    with patch.object(
        device_state_context_service.ha_client,
        "get_states",
        new_callable=AsyncMock,
        return_value=mock_states
    ):
        entity_ids = ["light.office_go", "light.office_back_right", "sensor.temp_office"]
        context = await device_state_context_service.get_state_context(entity_ids=entity_ids)

        # Verify context contains expected content
        assert "DEVICE STATES:" in context
        assert "light.office_go" in context
        assert "light.office_back_right" in context
        assert "sensor.temp_office" in context
        assert "on" in context
        assert "off" in context
        assert "brightness: 255" in context
        assert "color_mode: rgb" in context

        # Verify cache was set
        mock_context_builder._set_cached_value.assert_called_once()


@pytest.mark.asyncio
async def test_get_state_context_empty_entity_ids(device_state_context_service):
    """Test getting state context with no entity IDs"""
    context = await device_state_context_service.get_state_context(entity_ids=[])

    assert context == ""


@pytest.mark.asyncio
async def test_get_state_context_none_entity_ids(device_state_context_service):
    """Test getting state context with None entity IDs"""
    context = await device_state_context_service.get_state_context(entity_ids=None)

    assert context == ""


@pytest.mark.asyncio
async def test_get_state_context_cached(device_state_context_service, mock_context_builder):
    """Test getting state context from cache"""
    cached_context = "DEVICE STATES:\n- light.office_go: on (brightness: 255)"
    mock_context_builder._get_cached_value = AsyncMock(return_value=cached_context)

    context = await device_state_context_service.get_state_context(
        entity_ids=["light.office_go"]
    )

    assert context == cached_context
    # Should not call get_states when cached
    assert not device_state_context_service.ha_client.get_states.called


@pytest.mark.asyncio
async def test_get_state_context_api_error(device_state_context_service, mock_context_builder):
    """Test handling API errors gracefully"""
    with patch.object(
        device_state_context_service.ha_client,
        "get_states",
        new_callable=AsyncMock,
        side_effect=Exception("API error")
    ):
        entity_ids = ["light.office_go"]
        context = await device_state_context_service.get_state_context(entity_ids=entity_ids)

        # Should return empty string on error (graceful degradation)
        assert context == ""


@pytest.mark.asyncio
async def test_get_state_context_missing_entities(device_state_context_service, mock_context_builder):
    """Test handling missing entities gracefully"""
    # Mock states with different entities than requested
    mock_states = [
        {
            "entity_id": "light.office_go",
            "state": "on",
            "attributes": {}
        }
    ]

    with patch.object(
        device_state_context_service.ha_client,
        "get_states",
        new_callable=AsyncMock,
        return_value=mock_states
    ):
        # Request entity that doesn't exist in states
        entity_ids = ["light.nonexistent"]
        context = await device_state_context_service.get_state_context(entity_ids=entity_ids)

        # Should return empty string when no states found
        assert context == ""


@pytest.mark.asyncio
async def test_format_state_entry_light(device_state_context_service):
    """Test formatting light entity state"""
    state = {
        "entity_id": "light.office_go",
        "state": "on",
        "attributes": {
            "brightness": 255,
            "color_mode": "rgb",
            "rgb_color": [255, 0, 0],
            "color_temp": 370
        }
    }

    formatted = device_state_context_service._format_state_entry(state)

    assert "light.office_go" in formatted
    assert "on" in formatted
    assert "brightness: 255" in formatted
    assert "color_mode: rgb" in formatted
    assert "rgb: [255,0,0]" in formatted


@pytest.mark.asyncio
async def test_format_state_entry_climate(device_state_context_service):
    """Test formatting climate entity state"""
    state = {
        "entity_id": "climate.office",
        "state": "heat",
        "attributes": {
            "temperature": 22.0,
            "current_temperature": 20.5,
            "hvac_action": "heating"
        }
    }

    formatted = device_state_context_service._format_state_entry(state)

    assert "climate.office" in formatted
    assert "heat" in formatted
    assert "temperature: 22.0" in formatted
    assert "current: 20.5" in formatted
    assert "hvac_action: heating" in formatted


@pytest.mark.asyncio
async def test_get_cache_key(device_state_context_service):
    """Test cache key generation"""
    entity_ids = ["light.office_go", "light.office_back_right"]
    cache_key = device_state_context_service._get_cache_key(entity_ids)

    assert cache_key.startswith("device_state_context_")
    assert len(cache_key) > len("device_state_context_")

    # Same entity IDs should generate same key (order shouldn't matter)
    entity_ids_reversed = ["light.office_back_right", "light.office_go"]
    cache_key2 = device_state_context_service._get_cache_key(entity_ids_reversed)

    assert cache_key == cache_key2  # Should be same due to sorting


@pytest.mark.asyncio
async def test_close(device_state_context_service):
    """Test service cleanup"""
    # Should not raise any errors
    await device_state_context_service.close()
