"""
Unit tests for EntityAttributeService

Tests entity enrichment with attributes from Home Assistant.
"""

from unittest.mock import AsyncMock

import pytest
from src.services.entity_attribute_service import EnrichedEntity, EntityAttributeService


class TestEntityAttributeService:
    """Test suite for EntityAttributeService"""

    @pytest.fixture
    def mock_ha_client(self):
        """Mock HA client"""
        client = AsyncMock()
        return client

    @pytest.fixture
    def attribute_service(self, mock_ha_client):
        """EntityAttributeService instance"""
        return EntityAttributeService(mock_ha_client)

    @pytest.mark.asyncio
    async def test_enrich_entity_with_attributes_success(self, attribute_service, mock_ha_client):
        """Test successful entity enrichment"""
        # Mock HA response
        mock_ha_client.get_entity_state.return_value = {
            'state': 'on',
            'attributes': {
                'friendly_name': 'Office Light',
                'icon': 'mdi:lightbulb',
                'device_class': 'light',
                'unit_of_measurement': 'lm',
                'is_hue_group': True,
                'brightness': 255,
                'color_temp': 370,
                'supported_features': 43
            },
            'last_changed': '2025-01-24T10:00:00',
            'last_updated': '2025-01-24T10:00:00'
        }

        result = await attribute_service.enrich_entity_with_attributes('light.office')

        assert result is not None
        assert result['entity_id'] == 'light.office'
        assert result['friendly_name'] == 'Office Light'
        assert result['state'] == 'on'
        assert result['is_group'] is True
        assert result['integration'] == 'hue'
        assert result['attributes']['brightness'] == 255
        assert 'is_hue_group' in result['attributes']
        assert result['attributes']['is_hue_group'] is True

    @pytest.mark.asyncio
    async def test_enrich_entity_not_found(self, attribute_service, mock_ha_client):
        """Test entity not found in HA"""
        mock_ha_client.get_entity_state.return_value = None

        result = await attribute_service.enrich_entity_with_attributes('light.nonexistent')

        assert result is None

    @pytest.mark.asyncio
    async def test_enrich_multiple_entities(self, attribute_service, mock_ha_client):
        """Test batch enrichment of multiple entities"""
        # Mock HA responses
        mock_ha_client.get_entity_state.side_effect = [
            {
                'state': 'on',
                'attributes': {
                    'friendly_name': 'Office Light',
                    'is_hue_group': True
                }
            },
            {
                'state': 'off',
                'attributes': {
                    'friendly_name': 'Kitchen Light',
                    'is_hue_group': False
                }
            }
        ]

        result = await attribute_service.enrich_multiple_entities(['light.office', 'light.kitchen'])

        assert len(result) == 2
        assert 'light.office' in result
        assert 'light.kitchen' in result
        assert result['light.office']['is_group'] is True
        assert result['light.kitchen']['is_group'] is False

    @pytest.mark.asyncio
    async def test_determine_is_group_hue(self, attribute_service):
        """Test Hue group detection"""
        attributes = {'is_hue_group': True}
        result = attribute_service._determine_is_group('light.office', attributes)
        assert result is True

        attributes = {'is_hue_group': False}
        result = attribute_service._determine_is_group('light.office', attributes)
        assert result is False

        attributes = {}
        result = attribute_service._determine_is_group('light.office', attributes)
        assert result is False

    @pytest.mark.asyncio
    async def test_get_integration_from_attributes(self, attribute_service):
        """Test integration type detection"""
        # Test Hue
        attributes = {'is_hue_group': True}
        result = attribute_service._get_integration_from_attributes(attributes)
        assert result == 'hue'

        # Test Zigbee
        attributes = {'device_id': 'zigbee_abc123'}
        result = attribute_service._get_integration_from_attributes(attributes)
        assert result == 'zigbee'

        # Test MQTT
        attributes = {'device_id': 'mqtt_device_xyz'}
        result = attribute_service._get_integration_from_attributes(attributes)
        assert result == 'mqtt'

        # Test unknown
        attributes = {}
        result = attribute_service._get_integration_from_attributes(attributes)
        assert result == 'unknown'

    @pytest.mark.asyncio
    async def test_enrich_entity_handles_exception(self, attribute_service, mock_ha_client):
        """Test error handling during enrichment"""
        # Mock HA client to raise exception
        mock_ha_client.get_entity_state.side_effect = Exception("Network error")

        result = await attribute_service.enrich_entity_with_attributes('light.office')

        assert result is None


class TestEnrichedEntity:
    """Test suite for EnrichedEntity dataclass"""

    def test_enriched_entity_initialization(self):
        """Test EnrichedEntity dataclass initialization"""
        entity = EnrichedEntity(
            entity_id='light.office',
            domain='light',
            friendly_name='Office Light',
            icon='mdi:lightbulb',
            state='on',
            is_group=True,
            integration='hue'
        )

        assert entity.entity_id == 'light.office'
        assert entity.domain == 'light'
        assert entity.friendly_name == 'Office Light'
        assert entity.state == 'on'
        assert entity.is_group is True
        assert entity.integration == 'hue'
        assert entity.attributes is not None

    def test_enriched_entity_post_init(self):
        """Test EnrichedEntity post-initialization"""
        entity = EnrichedEntity(
            entity_id='light.office',
            domain='light'
        )

        assert entity.attributes == {}


@pytest.mark.asyncio
async def test_integration_with_ha_client():
    """Integration test with real HA client (if available)"""
    # This is a placeholder for integration test when HA is available
    # Skip if HA not available
    pass

