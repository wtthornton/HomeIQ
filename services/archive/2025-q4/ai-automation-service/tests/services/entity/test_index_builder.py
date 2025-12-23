"""
Unit tests for PersonalizedIndexBuilder

Epic AI-12, Story AI12.1: Personalized Entity Index Builder
Tests for building personalized index from Home Assistant Entity Registry.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.services.entity.index_builder import PersonalizedIndexBuilder
from src.services.entity.personalized_index import PersonalizedEntityIndex


class TestPersonalizedIndexBuilder:
    """Test PersonalizedIndexBuilder class"""
    
    @pytest.fixture
    def mock_ha_client(self):
        """Mock Home Assistant client"""
        client = Mock()
        client.get_entity_registry = AsyncMock(return_value=[])
        client.get_entity = AsyncMock(return_value=None)
        return client
    
    @pytest.fixture
    def mock_data_api_client(self):
        """Mock Data API client"""
        client = Mock()
        client.fetch_entities = AsyncMock(return_value=[])
        client.fetch_areas = AsyncMock(return_value=[])
        return client
    
    @pytest.fixture
    def builder(self, mock_ha_client, mock_data_api_client):
        """Create PersonalizedIndexBuilder instance"""
        return PersonalizedIndexBuilder(
            ha_client=mock_ha_client,
            data_api_client=mock_data_api_client
        )
    
    @pytest.fixture
    def index(self):
        """Create PersonalizedEntityIndex instance"""
        return PersonalizedEntityIndex()
    
    @pytest.mark.asyncio
    async def test_build_index_empty(self, builder, index, mock_ha_client):
        """Test building index with no entities"""
        mock_ha_client.get_entity_registry.return_value = []
        
        stats = await builder.build_index(index)
        
        assert stats["processed"] == 0
        assert stats["skipped"] == 0
        assert index.get_stats()["total_entities"] == 0
    
    @pytest.mark.asyncio
    async def test_build_index_single_entity(self, builder, index, mock_ha_client, mock_data_api_client):
        """Test building index with single entity"""
        mock_ha_client.get_entity_registry.return_value = [
            {
                "entity_id": "light.office",
                "name": "Office Lamp",
                "name_by_user": "Desk Light",
                "domain": "light",
                "device_id": "device123",
                "area_id": "office"
            }
        ]
        
        mock_data_api_client.fetch_areas.return_value = [
            {"area_id": "office", "name": "Office"}
        ]
        
        stats = await builder.build_index(index)
        
        assert stats["processed"] == 1
        assert stats["skipped"] == 0
        assert index.get_stats()["total_entities"] == 1
        
        # Check entity was added
        entry = index.get_entity("light.office")
        assert entry is not None
        assert entry.domain == "light"
        assert entry.area_id == "office"
        assert entry.area_name == "Office"
    
    @pytest.mark.asyncio
    async def test_build_index_multiple_entities(self, builder, index, mock_ha_client, mock_data_api_client):
        """Test building index with multiple entities"""
        mock_ha_client.get_entity_registry.return_value = [
            {
                "entity_id": "light.office",
                "name": "Office Lamp",
                "domain": "light",
                "area_id": "office"
            },
            {
                "entity_id": "light.kitchen",
                "name": "Kitchen Light",
                "domain": "light",
                "area_id": "kitchen"
            }
        ]
        
        mock_data_api_client.fetch_areas.return_value = [
            {"area_id": "office", "name": "Office"},
            {"area_id": "kitchen", "name": "Kitchen"}
        ]
        
        stats = await builder.build_index(index)
        
        assert stats["processed"] == 2
        assert index.get_stats()["total_entities"] == 2
    
    @pytest.mark.asyncio
    async def test_build_index_with_aliases(self, builder, index, mock_ha_client, mock_data_api_client):
        """Test building index with entity aliases"""
        mock_ha_client.get_entity_registry.return_value = [
            {
                "entity_id": "light.office",
                "name": "Office Lamp",
                "aliases": ["Desk Light", "Lamp"],
                "domain": "light"
            }
        ]
        
        mock_data_api_client.fetch_areas.return_value = []
        
        stats = await builder.build_index(index)
        
        assert stats["processed"] == 1
        entry = index.get_entity("light.office")
        assert entry is not None
        # Should have name + aliases
        assert len(entry.variants) >= 1
    
    @pytest.mark.asyncio
    async def test_build_index_with_list_aliases(self, builder, index, mock_ha_client, mock_data_api_client):
        """Test building index with list aliases"""
        mock_ha_client.get_entity_registry.return_value = [
            {
                "entity_id": "light.office",
                "name": "Office Lamp",
                "aliases": ["Desk Light", "Lamp"],
                "domain": "light"
            }
        ]
        
        mock_data_api_client.fetch_areas.return_value = []
        
        stats = await builder.build_index(index)
        
        assert stats["processed"] == 1
        entry = index.get_entity("light.office")
        assert entry is not None
    
    @pytest.mark.asyncio
    async def test_build_index_with_string_aliases(self, builder, index, mock_ha_client, mock_data_api_client):
        """Test building index with string alias"""
        mock_ha_client.get_entity_registry.return_value = [
            {
                "entity_id": "light.office",
                "name": "Office Lamp",
                "aliases": "Desk Light",  # String instead of list
                "domain": "light"
            }
        ]
        
        mock_data_api_client.fetch_areas.return_value = []
        
        stats = await builder.build_index(index)
        
        assert stats["processed"] == 1
        entry = index.get_entity("light.office")
        assert entry is not None
    
    @pytest.mark.asyncio
    async def test_build_index_handles_errors(self, builder, index, mock_ha_client, mock_data_api_client):
        """Test building index handles entity processing errors gracefully"""
        mock_ha_client.get_entity_registry.return_value = [
            {
                "entity_id": "light.office",
                "name": "Office Lamp",
                "domain": "light"
            },
            {
                # Missing entity_id - should be skipped
                "name": "Invalid Entity"
            }
        ]
        
        mock_data_api_client.fetch_areas.return_value = []
        
        stats = await builder.build_index(index)
        
        # Should process valid entity, skip invalid
        assert stats["processed"] == 1
        assert stats["skipped"] == 1
    
    @pytest.mark.asyncio
    async def test_build_index_incremental(self, builder, index, mock_ha_client, mock_data_api_client):
        """Test incremental index build"""
        # Initial build
        mock_ha_client.get_entity_registry.return_value = [
            {
                "entity_id": "light.office",
                "name": "Office Lamp",
                "domain": "light"
            }
        ]
        
        mock_data_api_client.fetch_areas.return_value = []
        
        await builder.build_index(index, incremental=False)
        assert index.get_stats()["total_entities"] == 1
        
        # Incremental update
        mock_ha_client.get_entity_registry.return_value = [
            {
                "entity_id": "light.office",
                "name": "Office Lamp Updated",
                "domain": "light"
            },
            {
                "entity_id": "light.kitchen",
                "name": "Kitchen Light",
                "domain": "light"
            }
        ]
        
        await builder.build_index(index, incremental=True)
        # Should have both entities
        assert index.get_stats()["total_entities"] == 2
    
    @pytest.mark.asyncio
    async def test_update_entity(self, builder, index, mock_ha_client, mock_data_api_client):
        """Test updating single entity"""
        # Add initial entity
        index.add_entity(
            entity_id="light.office",
            domain="light",
            name_variants={"name": "Office Lamp"}
        )
        
        # Mock updated entity
        mock_ha_client.get_entity.return_value = {
            "entity_id": "light.office",
            "name": "Office Lamp Updated",
            "domain": "light"
        }
        
        mock_data_api_client.fetch_areas.return_value = []
        
        result = await builder.update_entity(index, "light.office")
        
        assert result is True
        entry = index.get_entity("light.office")
        assert entry is not None
    
    @pytest.mark.asyncio
    async def test_update_entity_not_found(self, builder, index, mock_ha_client):
        """Test updating non-existent entity"""
        mock_ha_client.get_entity.return_value = None
        
        result = await builder.update_entity(index, "light.nonexistent")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_build_index_fallback_to_data_api(self, builder, index, mock_ha_client, mock_data_api_client):
        """Test fallback to Data API when HA client fails"""
        mock_ha_client.get_entity_registry.side_effect = Exception("HA API failed")
        
        mock_data_api_client.fetch_entities.return_value = [
            {
                "entity_id": "light.office",
                "name": "Office Lamp",
                "domain": "light"
            }
        ]
        
        mock_data_api_client.fetch_areas.return_value = []
        
        stats = await builder.build_index(index)
        
        # Should use Data API fallback
        assert stats["processed"] == 1

