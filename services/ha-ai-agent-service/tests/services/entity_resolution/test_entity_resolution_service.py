"""
Tests for entity_resolution_service.py
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.services.entity_resolution.entity_resolution_service import EntityResolutionService
from src.clients.data_api_client import DataAPIClient


@pytest.fixture
def mock_data_api_client():
    """Mock Data API client"""
    client = MagicMock(spec=DataAPIClient)
    client.fetch_entities = AsyncMock(return_value=[
        {
            "entity_id": "light.office_top",
            "friendly_name": "Office Top Light",
            "area_id": "office",
            "domain": "light"
        },
        {
            "entity_id": "light.office_desk",
            "friendly_name": "Office Desk Light",
            "area_id": "office",
            "domain": "light"
        },
        {
            "entity_id": "light.kitchen",
            "friendly_name": "Kitchen Light",
            "area_id": "kitchen",
            "domain": "light"
        }
    ])
    return client


class TestEntityResolutionService:
    """Test EntityResolutionService class."""

    def test___init__(self, mock_data_api_client):
        """Test __init__ method."""
        service = EntityResolutionService(mock_data_api_client)
        assert service.data_api_client == mock_data_api_client

    def test__extract_area_from_prompt(self, mock_data_api_client):
        """Test _extract_area_from_prompt method."""
        service = EntityResolutionService(mock_data_api_client)
        
        # Test area extraction
        assert service._extract_area_from_prompt("turn on office lights") == "office"
        assert service._extract_area_from_prompt("kitchen light") == "kitchen"
        assert service._extract_area_from_prompt("bedroom fan") == "bedroom"
        assert service._extract_area_from_prompt("turn on lights") is None

    def test__filter_by_area(self, mock_data_api_client):
        """Test _filter_by_area method."""
        service = EntityResolutionService(mock_data_api_client)
        
        entities = [
            {"entity_id": "light.office", "area_id": "office"},
            {"entity_id": "light.kitchen", "area_id": "kitchen"},
            {"entity_id": "switch.office", "area_id": "office"}
        ]
        
        filtered = service._filter_by_area(entities, "office")
        assert len(filtered) == 2
        assert all(e["area_id"] == "office" for e in filtered)

    def test__filter_by_domain(self, mock_data_api_client):
        """Test _filter_by_domain method."""
        service = EntityResolutionService(mock_data_api_client)
        
        entities = [
            {"entity_id": "light.office", "domain": "light"},
            {"entity_id": "switch.office", "domain": "switch"},
            {"entity_id": "light.kitchen", "domain": "light"}
        ]
        
        filtered = service._filter_by_domain(entities, "light")
        assert len(filtered) == 2
        assert all(e["domain"] == "light" for e in filtered)

    def test__extract_positional_keywords(self, mock_data_api_client):
        """Test _extract_positional_keywords method."""
        service = EntityResolutionService(mock_data_api_client)
        
        keywords = service._extract_positional_keywords("top left light")
        assert "top" in keywords
        assert "left" in keywords
        
        keywords = service._extract_positional_keywords("desk ceiling floor")
        assert "desk" in keywords
        assert "ceiling" in keywords
        assert "floor" in keywords

    @pytest.mark.asyncio
    async def test_resolve_entities_with_area(self, mock_data_api_client):
        """Test resolve_entities with area filter."""
        service = EntityResolutionService(mock_data_api_client)
        
        result = await service.resolve_entities(
            "turn on office lights",
            target_domain="light"
        )
        
        assert result.success is True
        assert len(result.matched_entities) > 0
        assert "office" in result.matched_areas

    @pytest.mark.asyncio
    async def test_resolve_entities_with_context(self, mock_data_api_client):
        """Test resolve_entities with context entities."""
        service = EntityResolutionService(mock_data_api_client)
        
        context_entities = [
            {"entity_id": "light.office", "friendly_name": "Office Light", "area_id": "office"}
        ]
        
        result = await service.resolve_entities(
            "turn on office light",
            context_entities=context_entities
        )
        
        assert result.success is True
        assert len(result.matched_entities) > 0

    @pytest.mark.asyncio
    async def test_resolve_entities_no_data(self):
        """Test resolve_entities with no data available."""
        service = EntityResolutionService(None)
        
        result = await service.resolve_entities("turn on lights")
        
        assert result.success is False
        assert result.error is not None
        assert "entity data" in result.error.lower() or "data_api_client" in result.error.lower()