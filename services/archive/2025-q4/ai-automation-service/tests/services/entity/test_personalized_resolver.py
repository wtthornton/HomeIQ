"""
Unit tests for PersonalizedEntityResolver

Epic AI-12, Story AI12.2: Natural Language Entity Resolver Enhancement
Tests for personalized entity resolver with semantic search and confidence scoring.
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock

from src.services.entity.personalized_resolver import (
    PersonalizedEntityResolver,
    ResolutionResult
)
from src.services.entity.personalized_index import PersonalizedEntityIndex


class TestPersonalizedEntityResolver:
    """Test PersonalizedEntityResolver class"""
    
    @pytest.fixture
    def index(self):
        """Create PersonalizedEntityIndex instance"""
        index = PersonalizedEntityIndex()
        # Add test entities
        index.add_entity(
            entity_id="light.office",
            domain="light",
            name_variants={
                "name": "Office Lamp",
                "name_by_user": "Desk Light"
            },
            area_id="office",
            area_name="Office"
        )
        index.add_entity(
            entity_id="light.kitchen",
            domain="light",
            name_variants={
                "name": "Kitchen Light"
            },
            area_id="kitchen",
            area_name="Kitchen"
        )
        return index
    
    @pytest.fixture
    def mock_ha_client(self):
        """Mock Home Assistant client"""
        return Mock()
    
    @pytest.fixture
    def mock_data_api_client(self):
        """Mock Data API client"""
        client = Mock()
        client.fetch_areas = AsyncMock(return_value=[])
        return client
    
    @pytest.fixture
    def resolver(self, index, mock_ha_client, mock_data_api_client):
        """Create PersonalizedEntityResolver instance"""
        return PersonalizedEntityResolver(
            personalized_index=index,
            ha_client=mock_ha_client,
            data_api_client=mock_data_api_client
        )
    
    @pytest.mark.asyncio
    async def test_resolve_device_names_single(self, resolver):
        """Test resolving single device name"""
        results = await resolver.resolve_device_names(["office lamp"])
        
        assert len(results) == 1
        assert "office lamp" in results
        assert results["office lamp"] == "light.office"
    
    @pytest.mark.asyncio
    async def test_resolve_device_names_multiple(self, resolver):
        """Test resolving multiple device names"""
        results = await resolver.resolve_device_names([
            "office lamp",
            "kitchen light"
        ])
        
        assert len(results) == 2
        assert results["office lamp"] == "light.office"
        assert results["kitchen light"] == "light.kitchen"
    
    @pytest.mark.asyncio
    async def test_resolve_device_names_with_user_name(self, resolver):
        """Test resolving using user-defined name"""
        results = await resolver.resolve_device_names(["desk light"])
        
        assert len(results) == 1
        assert results["desk light"] == "light.office"
    
    @pytest.mark.asyncio
    async def test_resolve_device_names_with_area_filter(self, resolver):
        """Test resolving with area filter"""
        results = await resolver.resolve_device_names(
            ["light"],
            area_id="office"
        )
        
        assert len(results) > 0
        assert results["light"] == "light.office"
    
    @pytest.mark.asyncio
    async def test_resolve_device_names_with_domain_filter(self, resolver):
        """Test resolving with domain filter"""
        results = await resolver.resolve_device_names(
            ["office lamp"],
            domain="light"
        )
        
        assert len(results) == 1
        assert results["office lamp"] == "light.office"
    
    @pytest.mark.asyncio
    async def test_resolve_device_names_with_query_context(self, resolver):
        """Test resolving with query context"""
        results = await resolver.resolve_device_names(
            ["lamp"],
            query="turn on the office lamp"
        )
        
        # Query context should help match "office lamp"
        assert len(results) > 0
    
    @pytest.mark.asyncio
    async def test_resolve_device_names_unresolved(self, resolver):
        """Test resolving non-existent device name"""
        results = await resolver.resolve_device_names(
            ["nonexistent device"],
            use_fallback=False
        )
        
        # Should return empty if no fallback
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_resolve_device_names_with_fallback(self, resolver):
        """Test resolving with fallback resolver"""
        # Create mock fallback resolver
        mock_fallback = Mock()
        mock_fallback.resolve_device_names = AsyncMock(
            return_value={"nonexistent": "light.fallback"}
        )
        resolver.fallback_resolver = mock_fallback
        
        results = await resolver.resolve_device_names(
            ["nonexistent device"],
            use_fallback=True
        )
        
        # Should use fallback for unresolved
        assert len(results) > 0
        mock_fallback.resolve_device_names.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_resolve_single_device(self, resolver):
        """Test resolving single device with confidence"""
        result = await resolver.resolve_single_device("office lamp")
        
        assert result is not None
        assert result.entity_id == "light.office"
        assert result.confidence > 0.5
        assert result.matched_variant is not None
        assert result.area_id == "office"
    
    @pytest.mark.asyncio
    async def test_resolve_single_device_not_found(self, resolver):
        """Test resolving non-existent device"""
        result = await resolver.resolve_single_device("nonexistent device")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_resolve_single_device_exact_match(self, resolver):
        """Test exact match boosts confidence"""
        result = await resolver.resolve_single_device("Desk Light")
        
        assert result is not None
        assert result.entity_id == "light.office"
        # Exact match should have higher confidence
        assert result.confidence > 0.7
    
    @pytest.mark.asyncio
    async def test_resolve_single_device_user_name_boost(self, resolver):
        """Test user-defined name boosts confidence"""
        result = await resolver.resolve_single_device("desk light")
        
        assert result is not None
        # User-defined names should have higher confidence
        if result.matched_type == "name_by_user":
            assert result.confidence > 0.8
    
    @pytest.mark.asyncio
    async def test_resolve_with_context(self, resolver, mock_data_api_client):
        """Test resolving with full context"""
        mock_data_api_client.fetch_areas.return_value = [
            {"area_id": "office", "name": "Office"}
        ]
        
        results = await resolver.resolve_with_context(
            device_names=["lamp"],
            query="turn on the office lamp",
            area_hint="office"
        )
        
        assert len(results) > 0
        assert "lamp" in results
        assert results["lamp"].entity_id == "light.office"
    
    @pytest.mark.asyncio
    async def test_get_resolution_confidence_exact_match(self, resolver):
        """Test confidence score for exact match"""
        confidence = await resolver.get_resolution_confidence(
            "Office Lamp",
            "light.office"
        )
        
        assert confidence > 0.9
    
    @pytest.mark.asyncio
    async def test_get_resolution_confidence_user_name(self, resolver):
        """Test confidence score for user-defined name"""
        confidence = await resolver.get_resolution_confidence(
            "Desk Light",
            "light.office"
        )
        
        # User-defined names should have highest confidence
        assert confidence >= 0.95
    
    @pytest.mark.asyncio
    async def test_get_resolution_confidence_partial_match(self, resolver):
        """Test confidence score for partial match"""
        confidence = await resolver.get_resolution_confidence(
            "office",
            "light.office"
        )
        
        # Partial match should have lower confidence
        assert 0.5 < confidence < 0.9
    
    @pytest.mark.asyncio
    async def test_get_resolution_confidence_no_match(self, resolver):
        """Test confidence score for no match"""
        confidence = await resolver.get_resolution_confidence(
            "nonexistent",
            "light.office"
        )
        
        assert confidence == 0.0
    
    @pytest.mark.asyncio
    async def test_get_resolution_confidence_wrong_entity(self, resolver):
        """Test confidence score for wrong entity"""
        confidence = await resolver.get_resolution_confidence(
            "office lamp",
            "light.kitchen"  # Wrong entity
        )
        
        assert confidence == 0.0
    
    def test_get_index_stats(self, resolver):
        """Test getting index statistics"""
        stats = resolver.get_index_stats()
        
        assert "total_entities" in stats
        assert stats["total_entities"] == 2


class TestResolutionResult:
    """Test ResolutionResult dataclass"""
    
    def test_resolution_result_creation(self):
        """Test creating ResolutionResult"""
        result = ResolutionResult(
            entity_id="light.office",
            confidence=0.95,
            matched_variant="Office Lamp",
            matched_type="name",
            area_id="office",
            area_name="Office"
        )
        
        assert result.entity_id == "light.office"
        assert result.confidence == 0.95
        assert result.matched_variant == "Office Lamp"
        assert result.matched_type == "name"
        assert result.area_id == "office"
        assert result.area_name == "Office"

