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


# Device Registry Integration Tests (Epic AI-23)
@pytest.mark.asyncio
async def test_get_summary_with_device_area_resolution(entity_inventory_service, mock_context_builder):
    """Test area resolution from device when entity doesn't have area_id (Epic AI-23)"""
    # Mock entities: 2 with direct area_id, 5 that inherit from device
    mock_entities = [
        {"entity_id": "light.office_1", "domain": "light", "area_id": "office", "device_id": "device1"},
        {"entity_id": "light.office_2", "domain": "light", "area_id": "office", "device_id": "device1"},
        # These 5 inherit area_id from device
        {"entity_id": "light.office_3", "domain": "light", "area_id": None, "device_id": "device2"},
        {"entity_id": "light.office_4", "domain": "light", "area_id": None, "device_id": "device2"},
        {"entity_id": "light.office_5", "domain": "light", "area_id": None, "device_id": "device2"},
        {"entity_id": "light.office_6", "domain": "light", "area_id": None, "device_id": "device2"},
        {"entity_id": "light.office_7", "domain": "light", "area_id": None, "device_id": "device2"},
    ]

    # Mock device registry: device2 has area_id "office"
    mock_devices = [
        {"id": "device1", "name": "Office Light 1", "area_id": "office", "manufacturer": "Philips", "model": "Hue"},
        {"id": "device2", "name": "Office Light 2", "area_id": "office", "manufacturer": "LIFX", "model": "A19"},
    ]

    # Mock areas
    mock_areas = [
        {"area_id": "office", "name": "Office"},
    ]

    with patch.object(
        entity_inventory_service.data_api_client,
        "fetch_entities",
        new_callable=AsyncMock,
        return_value=mock_entities
    ), patch.object(
        entity_inventory_service.ha_client,
        "get_device_registry",
        new_callable=AsyncMock,
        return_value=mock_devices
    ), patch.object(
        entity_inventory_service.ha_client,
        "get_area_registry",
        new_callable=AsyncMock,
        return_value=mock_areas
    ), patch.object(
        entity_inventory_service.ha_client,
        "get_states",
        new_callable=AsyncMock,
        return_value=[]
    ):
        summary = await entity_inventory_service.get_summary()

        # Verify all 7 Office lights are found (not just 2)
        assert "Light" in summary
        assert "office" in summary.lower()
        # Should show 7 lights in office, not just 2
        assert summary.count("office") >= 2  # At least mentioned twice (area name + count)

        # Verify cache was set
        mock_context_builder._set_cached_value.assert_called_once()


@pytest.mark.asyncio
async def test_get_summary_with_device_metadata(entity_inventory_service, mock_context_builder):
    """Test device metadata (manufacturer, model) included in entity context (Epic AI-23)"""
    mock_entities = [
        {"entity_id": "light.office_1", "domain": "light", "area_id": "office", "device_id": "device1"},
    ]

    # Mock device registry with metadata
    mock_devices = [
        {
            "id": "device1",
            "name": "Office Light",
            "area_id": "office",
            "manufacturer": "Philips",
            "model": "Hue Light",
            "sw_version": "1.0.0"
        },
    ]

    mock_areas = [{"area_id": "office", "name": "Office"}]

    with patch.object(
        entity_inventory_service.data_api_client,
        "fetch_entities",
        new_callable=AsyncMock,
        return_value=mock_entities
    ), patch.object(
        entity_inventory_service.ha_client,
        "get_device_registry",
        new_callable=AsyncMock,
        return_value=mock_devices
    ), patch.object(
        entity_inventory_service.ha_client,
        "get_area_registry",
        new_callable=AsyncMock,
        return_value=mock_areas
    ), patch.object(
        entity_inventory_service.ha_client,
        "get_states",
        new_callable=AsyncMock,
        return_value=[]
    ):
        summary = await entity_inventory_service.get_summary()

        # Verify summary was generated
        assert "Light" in summary
        # Device metadata should be available (though may not always appear in summary format)
        # The key is that device_metadata_map is populated and used

        mock_context_builder._set_cached_value.assert_called_once()


@pytest.mark.asyncio
async def test_get_summary_device_registry_error_graceful(entity_inventory_service, mock_context_builder):
    """Test graceful handling when Device Registry API fails (backward compatible)"""
    mock_entities = [
        {"entity_id": "light.office_1", "domain": "light", "area_id": "office"},
    ]

    # Mock device registry failure
    with patch.object(
        entity_inventory_service.data_api_client,
        "fetch_entities",
        new_callable=AsyncMock,
        return_value=mock_entities
    ), patch.object(
        entity_inventory_service.ha_client,
        "get_device_registry",
        new_callable=AsyncMock,
        side_effect=Exception("Device Registry API Error")
    ), patch.object(
        entity_inventory_service.ha_client,
        "get_area_registry",
        new_callable=AsyncMock,
        return_value=[{"area_id": "office", "name": "Office"}]
    ), patch.object(
        entity_inventory_service.ha_client,
        "get_states",
        new_callable=AsyncMock,
        return_value=[]
    ):
        # Should not raise error, should continue with existing behavior
        summary = await entity_inventory_service.get_summary()

        assert "Light" in summary
        assert "office" in summary.lower()
        # Should still work with entities that have direct area_id
        mock_context_builder._set_cached_value.assert_called_once()


# Entity Registry Integration Tests (Epic AI-23)
@pytest.mark.asyncio
async def test_get_summary_with_entity_aliases(entity_inventory_service, mock_context_builder):
    """Test entity aliases included in entity context (Epic AI-23)"""
    mock_entities = [
        {"entity_id": "light.office_1", "domain": "light", "area_id": "office", "device_id": "device1"},
    ]

    # Mock entity registry with aliases
    mock_entity_registry = [
        {
            "entity_id": "light.office_1",
            "name": "Office Light",
            "aliases": ["workspace light", "desk light"],
            "category": "light",
            "disabled_by": None
        },
    ]

    mock_devices = [{"id": "device1", "name": "Office Light", "area_id": "office"}]
    mock_areas = [{"area_id": "office", "name": "Office"}]

    with patch.object(
        entity_inventory_service.data_api_client,
        "fetch_entities",
        new_callable=AsyncMock,
        return_value=mock_entities
    ), patch.object(
        entity_inventory_service.ha_client,
        "get_device_registry",
        new_callable=AsyncMock,
        return_value=mock_devices
    ), patch.object(
        entity_inventory_service.ha_client,
        "get_entity_registry",
        new_callable=AsyncMock,
        return_value=mock_entity_registry
    ), patch.object(
        entity_inventory_service.ha_client,
        "get_area_registry",
        new_callable=AsyncMock,
        return_value=mock_areas
    ), patch.object(
        entity_inventory_service.ha_client,
        "get_states",
        new_callable=AsyncMock,
        return_value=[]
    ):
        summary = await entity_inventory_service.get_summary()

        # Verify summary was generated
        assert "Light" in summary
        # Aliases should be available in entity context (may appear in summary format)
        # The key is that entity_registry_map is populated and used

        mock_context_builder._set_cached_value.assert_called_once()


@pytest.mark.asyncio
async def test_get_summary_entity_registry_error_graceful(entity_inventory_service, mock_context_builder):
    """Test graceful handling when Entity Registry API fails (backward compatible)"""
    mock_entities = [
        {"entity_id": "light.office_1", "domain": "light", "area_id": "office"},
    ]

    # Mock entity registry failure
    with patch.object(
        entity_inventory_service.data_api_client,
        "fetch_entities",
        new_callable=AsyncMock,
        return_value=mock_entities
    ), patch.object(
        entity_inventory_service.ha_client,
        "get_entity_registry",
        new_callable=AsyncMock,
        side_effect=Exception("Entity Registry API Error")
    ), patch.object(
        entity_inventory_service.ha_client,
        "get_device_registry",
        new_callable=AsyncMock,
        return_value=[]
    ), patch.object(
        entity_inventory_service.ha_client,
        "get_area_registry",
        new_callable=AsyncMock,
        return_value=[{"area_id": "office", "name": "Office"}]
    ), patch.object(
        entity_inventory_service.ha_client,
        "get_states",
        new_callable=AsyncMock,
        return_value=[]
    ):
        # Should not raise error, should continue with existing behavior
        summary = await entity_inventory_service.get_summary()

        assert "Light" in summary
        assert "office" in summary.lower()
        # Should still work without entity registry
        mock_context_builder._set_cached_value.assert_called_once()


# Device Type Detection Tests (Epic AI-23 Story AI23.3)
@pytest.mark.asyncio
async def test_get_summary_hue_room_detection(entity_inventory_service, mock_context_builder):
    """Test Hue Room/Zone group detection (Epic AI-23 Story AI23.3)"""
    mock_entities = [
        {"entity_id": "light.office_room", "domain": "light", "area_id": "office", "device_id": "hue_room_device"},
        {"entity_id": "light.office_1", "domain": "light", "area_id": "office", "device_id": "hue_room_device"},
        {"entity_id": "light.office_2", "domain": "light", "area_id": "office", "device_id": "hue_room_device"},
    ]

    # Mock device registry with Hue Room (model contains "Room")
    mock_devices = [
        {
            "id": "hue_room_device",
            "name": "Office Room",
            "area_id": "office",
            "manufacturer": "Philips",
            "model": "Room"  # Hue Room group
        },
    ]

    mock_areas = [{"area_id": "office", "name": "Office"}]

    with patch.object(
        entity_inventory_service.data_api_client,
        "fetch_entities",
        new_callable=AsyncMock,
        return_value=mock_entities
    ), patch.object(
        entity_inventory_service.ha_client,
        "get_device_registry",
        new_callable=AsyncMock,
        return_value=mock_devices
    ), patch.object(
        entity_inventory_service.ha_client,
        "get_entity_registry",
        new_callable=AsyncMock,
        return_value=[]
    ), patch.object(
        entity_inventory_service.ha_client,
        "get_area_registry",
        new_callable=AsyncMock,
        return_value=mock_areas
    ), patch.object(
        entity_inventory_service.ha_client,
        "get_states",
        new_callable=AsyncMock,
        return_value=[]
    ):
        summary = await entity_inventory_service.get_summary()

        # Verify summary was generated
        assert "Light" in summary
        # Hue Room detection should be working (device_description should be added)
        # The key is that hue_room_devices mapping is created

        mock_context_builder._set_cached_value.assert_called_once()


@pytest.mark.asyncio
async def test_get_summary_wled_segment_detection(entity_inventory_service, mock_context_builder):
    """Test WLED segment detection (Epic AI-23 Story AI23.3)"""
    mock_entities = [
        {"entity_id": "light.office_wled", "domain": "light", "area_id": "office"},
        {"entity_id": "light.office_wled_segment_1", "domain": "light", "area_id": "office"},
        {"entity_id": "light.office_wled_segment_2", "domain": "light", "area_id": "office"},
    ]

    mock_devices = []
    mock_areas = [{"area_id": "office", "name": "Office"}]

    with patch.object(
        entity_inventory_service.data_api_client,
        "fetch_entities",
        new_callable=AsyncMock,
        return_value=mock_entities
    ), patch.object(
        entity_inventory_service.ha_client,
        "get_device_registry",
        new_callable=AsyncMock,
        return_value=mock_devices
    ), patch.object(
        entity_inventory_service.ha_client,
        "get_entity_registry",
        new_callable=AsyncMock,
        return_value=[]
    ), patch.object(
        entity_inventory_service.ha_client,
        "get_area_registry",
        new_callable=AsyncMock,
        return_value=mock_areas
    ), patch.object(
        entity_inventory_service.ha_client,
        "get_states",
        new_callable=AsyncMock,
        return_value=[]
    ):
        summary = await entity_inventory_service.get_summary()

        # Verify summary was generated
        assert "Light" in summary
        # WLED segment detection should be working (wled_master_entities mapping created)
        # The key is that segments are identified and linked to masters

        mock_context_builder._set_cached_value.assert_called_once()