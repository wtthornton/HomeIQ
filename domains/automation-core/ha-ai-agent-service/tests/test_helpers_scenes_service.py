"""Tests for Helpers & Scenes Service"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.helpers_scenes_service import HelpersScenesService
from src.config import Settings
from src.services.context_builder import ContextBuilder


@pytest.fixture
def mock_settings():
    """Create mock settings"""
    return Settings(
        ha_url="http://test-ha:8123",
        ha_token="test-token"
    )


@pytest.fixture
def mock_context_builder():
    """Create mock context builder"""
    builder = MagicMock(spec=ContextBuilder)
    builder._get_cached_value = AsyncMock(return_value=None)
    builder._set_cached_value = AsyncMock()
    return builder


@pytest.fixture
def helpers_scenes_service(mock_settings, mock_context_builder):
    """Create HelpersScenesService instance"""
    return HelpersScenesService(
        settings=mock_settings,
        context_builder=mock_context_builder
    )


@pytest.mark.asyncio
async def test_get_summary_with_helpers_and_scenes(helpers_scenes_service, mock_context_builder):
    """Test getting summary with helpers and scenes"""
    mock_helpers = [
        {"id": "morning_routine", "type": "input_boolean", "entity_id": "input_boolean.morning_routine", "name": "Morning Routine"},
        {"id": "night_mode", "type": "input_boolean", "entity_id": "input_boolean.night_mode", "name": "Night Mode"},
        {"id": "brightness_level", "type": "input_number", "entity_id": "input_number.brightness_level", "name": "Brightness Level"},
    ]
    mock_scenes = [
        {"id": "morning_scene", "entity_id": "scene.morning_scene", "name": "Morning Scene"},
        {"id": "evening_scene", "entity_id": "scene.evening_scene", "name": "Evening Scene"},
    ]

    with patch.object(
        helpers_scenes_service.ha_client,
        "get_helpers",
        new_callable=AsyncMock,
        return_value=mock_helpers
    ), patch.object(
        helpers_scenes_service.ha_client,
        "get_scenes",
        new_callable=AsyncMock,
        return_value=mock_scenes
    ):
        summary = await helpers_scenes_service.get_summary()

        assert "input_boolean" in summary
        assert "input_number" in summary
        assert "morning_routine" in summary
        assert "Scenes:" in summary
        assert "Morning Scene" in summary
        mock_context_builder._set_cached_value.assert_called_once()


@pytest.mark.asyncio
async def test_get_summary_empty(helpers_scenes_service, mock_context_builder):
    """Test getting summary with no helpers/scenes"""
    with patch.object(
        helpers_scenes_service.ha_client,
        "get_helpers",
        new_callable=AsyncMock,
        return_value=[]
    ), patch.object(
        helpers_scenes_service.ha_client,
        "get_scenes",
        new_callable=AsyncMock,
        return_value=[]
    ):
        summary = await helpers_scenes_service.get_summary()

        assert "No helpers found" in summary
        assert "No scenes found" in summary
        mock_context_builder._set_cached_value.assert_called_once()


@pytest.mark.asyncio
async def test_get_summary_cached(helpers_scenes_service, mock_context_builder):
    """Test getting summary from cache"""
    cached_summary = "input_boolean: morning_routine (1 helpers)\nScenes: Morning Scene (1 scenes)"
    mock_context_builder._get_cached_value = AsyncMock(return_value=cached_summary)

    summary = await helpers_scenes_service.get_summary()

    assert summary == cached_summary


@pytest.mark.asyncio
async def test_close(helpers_scenes_service):
    """Test closing service resources"""
    helpers_scenes_service.ha_client.close = AsyncMock()

    await helpers_scenes_service.close()

    helpers_scenes_service.ha_client.close.assert_called_once()

