"""Tests for Areas Service"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.areas_service import AreasService
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
def areas_service(mock_settings, mock_context_builder):
    """Create AreasService instance"""
    return AreasService(
        settings=mock_settings,
        context_builder=mock_context_builder
    )


@pytest.mark.asyncio
async def test_get_areas_list_with_areas(areas_service, mock_context_builder):
    """Test getting areas list with areas"""
    mock_areas = [
        {"area_id": "office", "name": "Office"},
        {"area_id": "kitchen", "name": "Kitchen"},
        {"area_id": "bedroom", "name": "Bedroom"},
    ]

    with patch.object(
        areas_service.ha_client,
        "get_area_registry",
        new_callable=AsyncMock,
        return_value=mock_areas
    ):
        areas_list = await areas_service.get_areas_list()

        assert "office" in areas_list
        assert "kitchen" in areas_list
        assert "bedroom" in areas_list
        mock_context_builder._set_cached_value.assert_called_once()


@pytest.mark.asyncio
async def test_get_areas_list_empty(areas_service, mock_context_builder):
    """Test getting areas list with no areas"""
    with patch.object(
        areas_service.ha_client,
        "get_area_registry",
        new_callable=AsyncMock,
        return_value=[]
    ):
        areas_list = await areas_service.get_areas_list()

        assert "No areas found" in areas_list
        mock_context_builder._set_cached_value.assert_called_once()


@pytest.mark.asyncio
async def test_get_areas_list_cached(areas_service, mock_context_builder):
    """Test getting areas list from cache"""
    cached_list = "office, kitchen, bedroom"
    mock_context_builder._get_cached_value = AsyncMock(return_value=cached_list)

    areas_list = await areas_service.get_areas_list()

    assert areas_list == cached_list


@pytest.mark.asyncio
async def test_close(areas_service):
    """Test closing service resources"""
    areas_service.ha_client.close = AsyncMock()

    await areas_service.close()

    areas_service.ha_client.close.assert_called_once()

