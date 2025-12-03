"""Tests for Entity Inventory Service"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.entity_inventory_service import EntityInventoryService
from src.config import Settings
from src.services.context_builder import ContextBuilder


@pytest.fixture
def mock_settings():
    """Create mock settings"""
    return Settings(
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
def entity_inventory_service(mock_settings, mock_context_builder):
    """Create EntityInventoryService instance"""
    return EntityInventoryService(
        settings=mock_settings,
        context_builder=mock_context_builder
    )


@pytest.mark.asyncio
async def test_get_summary_with_entities(entity_inventory_service, mock_context_builder):
    """Test getting summary with entities"""
    # Mock entities response
    mock_entities = [
        {"entity_id": "light.office_1", "domain": "light", "area_id": "office"},
        {"entity_id": "light.office_2", "domain": "light", "area_id": "office"},
        {"entity_id": "light.kitchen_1", "domain": "light", "area_id": "kitchen"},
        {"entity_id": "sensor.temp_1", "domain": "sensor", "area_id": "office"},
        {"entity_id": "sensor.temp_2", "domain": "sensor", "area_id": None},  # unassigned
    ]

    with patch.object(
        entity_inventory_service.data_api_client,
        "fetch_entities",
        new_callable=AsyncMock,
        return_value=mock_entities
    ):
        summary = await entity_inventory_service.get_summary()

        # Verify summary contains expected content
        assert "Light" in summary
        assert "Sensor" in summary
        assert "office" in summary.lower()
        assert "kitchen" in summary.lower()
        assert "unassigned" in summary.lower()

        # Verify cache was set
        mock_context_builder._set_cached_value.assert_called_once()


@pytest.mark.asyncio
async def test_get_summary_empty_entities(entity_inventory_service, mock_context_builder):
    """Test getting summary with no entities"""
    with patch.object(
        entity_inventory_service.data_api_client,
        "fetch_entities",
        new_callable=AsyncMock,
        return_value=[]
    ):
        summary = await entity_inventory_service.get_summary()

        assert "No entities found" in summary
        mock_context_builder._set_cached_value.assert_called_once()


@pytest.mark.asyncio
async def test_get_summary_cached(entity_inventory_service, mock_context_builder):
    """Test getting summary from cache"""
    cached_summary = "Cached summary: Light: 5 entities (office: 3, kitchen: 2)"
    mock_context_builder._get_cached_value = AsyncMock(return_value=cached_summary)

    summary = await entity_inventory_service.get_summary()

    assert summary == cached_summary
    # Should not call fetch_entities when cached
    assert not hasattr(entity_inventory_service.data_api_client, "fetch_entities") or \
           not entity_inventory_service.data_api_client.fetch_entities.called


@pytest.mark.asyncio
async def test_get_summary_api_error(entity_inventory_service, mock_context_builder):
    """Test handling API errors gracefully"""
    with patch.object(
        entity_inventory_service.data_api_client,
        "fetch_entities",
        new_callable=AsyncMock,
        side_effect=Exception("API Error")
    ):
        summary = await entity_inventory_service.get_summary()

        assert "unavailable" in summary.lower()
        # Should not cache errors
        mock_context_builder._set_cached_value.assert_not_called()


@pytest.mark.asyncio
async def test_close(entity_inventory_service):
    """Test closing service resources"""
    entity_inventory_service.data_api_client.close = AsyncMock()

    await entity_inventory_service.close()

    entity_inventory_service.data_api_client.close.assert_called_once()

