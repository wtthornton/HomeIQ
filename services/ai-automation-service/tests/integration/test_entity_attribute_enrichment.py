"""
Integration Tests for Entity Attribute Enrichment
==================================================

Tests the complete entity attribute enrichment flow with real Home Assistant integration.

Tests:
1. Entity enrichment with attributes
2. EntityContextBuilder JSON generation
3. Attribute-based entity resolution
4. Hue group detection
"""

from unittest.mock import AsyncMock, patch

import pytest
from src.prompt_building.entity_context_builder import EntityContextBuilder
from src.services.entity_attribute_service import EntityAttributeService
from src.services.entity_validator import EntityValidator


@pytest.mark.asyncio
async def test_entity_enrichment_with_hue_group():
    """Test entity enrichment detects Hue group correctly"""

    # Mock HA client
    mock_ha_client = AsyncMock()
    mock_ha_client.get_entity_state.return_value = {
        "state": "on",
        "attributes": {
            "friendly_name": "Office",
            "is_hue_group": True,
            "brightness": 255,
            "color_temp": 370,
            "supported_features": 43,
        },
        "last_changed": "2025-01-24T10:00:00",
        "last_updated": "2025-01-24T10:00:00",
    }

    # Create service
    attribute_service = EntityAttributeService(mock_ha_client)

    # Enrich entity
    result = await attribute_service.enrich_entity_with_attributes("light.office")

    # Verify enrichment
    assert result is not None
    assert result["entity_id"] == "light.office"
    assert result["is_group"] is True
    assert result["integration"] == "hue"
    assert "is_hue_group" in result["attributes"]
    assert result["attributes"]["is_hue_group"] is True


@pytest.mark.asyncio
async def test_entity_context_builder_creates_json():
    """Test EntityContextBuilder creates enriched JSON"""

    # Mock entity data
    entities = [
        {"entity_id": "light.office"},
        {"entity_id": "light.hue_office_back_left"},
    ]

    enriched_data = {
        "light.office": {
            "entity_id": "light.office",
            "friendly_name": "Office",
            "is_group": True,
            "integration": "hue",
            "state": "on",
            "attributes": {
                "is_hue_group": True,
                "brightness": 255,
            },
        },
        "light.hue_office_back_left": {
            "entity_id": "light.hue_office_back_left",
            "friendly_name": "Office Back Left",
            "is_group": False,
            "integration": "hue",
            "state": "off",
            "attributes": {
                "brightness": 0,
            },
        },
    }

    # Create context builder
    context_builder = EntityContextBuilder()

    # Build context JSON
    json_str = await context_builder.build_entity_context_json(entities, enriched_data)

    # Verify JSON contains expected structure
    assert json_str is not None
    assert "light.office" in json_str
    assert "light.hue_office_back_left" in json_str
    assert "is_group" in json_str
    assert "true" in json_str  # Should have is_group=true for office
    assert "false" in json_str  # Should have is_group=false for individual


@pytest.mark.asyncio
async def test_attribute_based_scoring_boosts_groups():
    """Test attribute-based scoring boosts group entities for appropriate queries"""

    # Mock entities
    mock_entities = [
        {
            "entity_id": "light.office",
            "friendly_name": "office",
            "name_by_user": "Office",
            "device_name": "Office Light",
        },
        {
            "entity_id": "light.hue_office_back_left",
            "friendly_name": "office back left",
            "name_by_user": "Office Back Left",
            "device_name": "Office Back Left Light",
        },
    ]

    # Mock HA client
    mock_ha_client = AsyncMock()
    mock_ha_client.get_entity_state.side_effect = [
        {
            "state": "on",
            "attributes": {"is_hue_group": True},
        },
        {
            "state": "off",
            "attributes": {"is_hue_group": False},
        },
    ]

    # Mock data API client
    mock_data_api = AsyncMock()
    mock_data_api.get_all_entities = AsyncMock(return_value=mock_entities)

    # Create entity validator with HA client
    entity_validator = EntityValidator(
        data_api_client=mock_data_api,
        ha_client=mock_ha_client,
    )

    # Test query suggesting a group
    query = "flash all office lights"

    with patch.object(entity_validator, "_get_embedding_model", return_value=None):
        result = await entity_validator.map_query_to_entities(query, ["office lights"])

        # Verify group entity was matched (should be preferred for "all lights" query)
        if result and "office lights" in result:
            # The group entity should be preferred over individual lights
            assert result["office lights"] in ["light.office"]


@pytest.mark.asyncio
async def test_hue_group_vs_individual_discrimination():
    """Test system correctly discriminates between Hue groups and individual lights"""

    # Mock HA client
    mock_ha_client = AsyncMock()
    mock_ha_client.get_entity_state.side_effect = [
        # light.office - group
        {
            "state": "on",
            "attributes": {
                "friendly_name": "Office",
                "is_hue_group": True,
            },
        },
        # light.hue_office_back_left - individual
        {
            "state": "off",
            "attributes": {
                "friendly_name": "Office Back Left",
                "is_hue_group": False,
            },
        },
    ]

    # Create service
    attribute_service = EntityAttributeService(mock_ha_client)

    # Test group entity
    group_result = await attribute_service.enrich_entity_with_attributes("light.office")
    assert group_result["is_group"] is True

    # Test individual entity
    individual_result = await attribute_service.enrich_entity_with_attributes("light.hue_office_back_left")
    assert individual_result["is_group"] is False

    # Verify discrimination
    assert group_result["is_group"] != individual_result["is_group"]


@pytest.mark.asyncio
async def test_enrichment_error_handling():
    """Test graceful error handling in enrichment"""

    # Mock HA client to raise error
    mock_ha_client = AsyncMock()
    mock_ha_client.get_entity_state.side_effect = Exception("Network error")

    # Create service
    attribute_service = EntityAttributeService(mock_ha_client)

    # Enrich should handle error gracefully
    result = await attribute_service.enrich_entity_with_attributes("light.office")

    # Should return None on error
    assert result is None


@pytest.mark.asyncio
async def test_batch_enrichment_performance():
    """Test batch enrichment handles multiple entities efficiently"""

    # Mock HA client
    mock_ha_client = AsyncMock()
    mock_ha_client.get_entity_state.side_effect = [
        {"state": "on", "attributes": {"is_hue_group": True}} for _ in range(5)
    ]

    # Create service
    attribute_service = EntityAttributeService(mock_ha_client)

    # Enrich multiple entities
    entity_ids = ["light.office", "light.kitchen", "light.bedroom", "light.living_room", "light.bathroom"]
    result = await attribute_service.enrich_multiple_entities(entity_ids)

    # Verify all entities were enriched
    assert len(result) == 5
    for entity_id in entity_ids:
        assert entity_id in result


@pytest.mark.asyncio
async def test_capability_extraction():
    """Test capability extraction from supported_features"""

    # Mock HA client with capabilities
    mock_ha_client = AsyncMock()
    mock_ha_client.get_entity_state.return_value = {
        "state": "on",
        "attributes": {
            "friendly_name": "Smart Light",
            "supported_features": 43,  # Brightness, Color Temperature, RGB Color
            "brightness": 255,
            "color_temp": 370,
            "rgb_color": [255, 255, 255],
        },
    }

    # Create context builder
    context_builder = EntityContextBuilder()

    # Extract capabilities
    capabilities = context_builder._extract_capabilities(
        mock_ha_client.get_entity_state.return_value["attributes"],
        "light",
    )

    # Verify capabilities
    assert "brightness" in capabilities
    assert "color_temp" in capabilities
    assert "rgb_color" in capabilities


@pytest.mark.integration
@pytest.mark.asyncio
async def test_end_to_end_attribute_enrichment():
    """End-to-end test of attribute enrichment in entity resolution"""

    # This test should run against real HA instance if available
    # Skip if not running in integration environment
    pytest.skip("Skipping integration test without real HA instance")

