"""
Unit tests for AreaResolver

Epic AI-12, Story AI12.3: Area Name Resolution
Tests for area name resolution with semantic search, hierarchies, and area-aware filtering.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.services.entity.area_resolver import AreaResolver, AreaInfo


class TestAreaResolver:
    """Test AreaResolver class"""
    
    @pytest.fixture
    def resolver(self):
        """Create AreaResolver instance"""
        return AreaResolver()
    
    def test_init(self, resolver):
        """Test resolver initialization"""
        assert resolver._area_index == {}
        assert resolver._name_index == {}
        assert resolver._hierarchy_index == {}
        assert resolver.embedding_model_name == "all-MiniLM-L6-v2"
    
    def test_add_area_basic(self, resolver):
        """Test adding area to index"""
        resolver.add_area(
            area_id="office",
            name="Office"
        )
        
        assert "office" in resolver._area_index
        area_info = resolver._area_index["office"]
        assert area_info.area_id == "office"
        assert area_info.name == "Office"
        assert len(area_info.aliases) == 0
    
    def test_add_area_with_aliases(self, resolver):
        """Test adding area with aliases"""
        resolver.add_area(
            area_id="office",
            name="Office",
            aliases=["Work Space", "Desk Area"]
        )
        
        area_info = resolver._area_index["office"]
        assert len(area_info.aliases) == 2
        assert "Work Space" in area_info.aliases
        assert "Desk Area" in area_info.aliases
        
        # Check name index
        assert "office" in resolver._name_index
        assert "work space" in resolver._name_index
        assert "desk area" in resolver._name_index
    
    def test_add_area_with_hierarchy(self, resolver):
        """Test adding area with parent"""
        resolver.add_area(
            area_id="floor1",
            name="First Floor",
            parent_area_id=None
        )
        
        resolver.add_area(
            area_id="office",
            name="Office",
            parent_area_id="floor1",
            parent_area_name="First Floor"
        )
        
        # Check hierarchy
        children = resolver.get_child_areas("floor1")
        assert "office" in children
        
        # Check area info
        area_info = resolver._area_index["office"]
        assert area_info.parent_area_id == "floor1"
        assert area_info.parent_area_name == "First Floor"
    
    def test_resolve_area_name_exact_match(self, resolver):
        """Test resolving area name with exact match"""
        resolver.add_area(
            area_id="office",
            name="Office"
        )
        
        area_id = resolver.resolve_area_name("Office")
        assert area_id == "office"
    
    def test_resolve_area_name_case_insensitive(self, resolver):
        """Test resolving area name is case insensitive"""
        resolver.add_area(
            area_id="office",
            name="Office"
        )
        
        area_id = resolver.resolve_area_name("office")
        assert area_id == "office"
        
        area_id = resolver.resolve_area_name("OFFICE")
        assert area_id == "office"
    
    def test_resolve_area_name_by_alias(self, resolver):
        """Test resolving area name by alias"""
        resolver.add_area(
            area_id="office",
            name="Office",
            aliases=["Work Space"]
        )
        
        area_id = resolver.resolve_area_name("Work Space")
        assert area_id == "office"
    
    def test_resolve_area_name_partial_match(self, resolver):
        """Test resolving area name with partial match"""
        resolver.add_area(
            area_id="office",
            name="Office Room"
        )
        
        area_id = resolver.resolve_area_name("office")
        assert area_id == "office"
    
    @patch('src.services.entity.area_resolver.SentenceTransformer')
    def test_resolve_area_name_semantic(self, mock_transformer, resolver):
        """Test resolving area name with semantic search"""
        # Mock embedding model
        mock_model = MagicMock()
        mock_model.encode.return_value = [0.1, 0.2, 0.3]
        mock_transformer.return_value = mock_model
        
        resolver.add_area(
            area_id="office",
            name="Office"
        )
        
        # Mock embeddings
        mock_model.encode.side_effect = [
            [0.1, 0.2, 0.3],  # Query embedding
            [0.1, 0.2, 0.3],  # Office embedding (high similarity)
        ]
        
        area_id = resolver.resolve_area_name("work space", use_semantic=True)
        
        # Should find office via semantic similarity
        assert area_id is not None
    
    def test_resolve_area_name_not_found(self, resolver):
        """Test resolving non-existent area name"""
        area_id = resolver.resolve_area_name("nonexistent")
        assert area_id is None
    
    def test_get_area_info(self, resolver):
        """Test getting area information"""
        resolver.add_area(
            area_id="office",
            name="Office",
            aliases=["Work Space"]
        )
        
        area_info = resolver.get_area_info("office")
        assert area_info is not None
        assert area_info.area_id == "office"
        assert area_info.name == "Office"
        assert len(area_info.aliases) == 1
    
    def test_get_area_name(self, resolver):
        """Test getting area name by area_id"""
        resolver.add_area(
            area_id="office",
            name="Office"
        )
        
        name = resolver.get_area_name("office")
        assert name == "Office"
        
        name = resolver.get_area_name("nonexistent")
        assert name is None
    
    def test_get_child_areas(self, resolver):
        """Test getting child areas"""
        resolver.add_area(
            area_id="floor1",
            name="First Floor"
        )
        
        resolver.add_area(
            area_id="office",
            name="Office",
            parent_area_id="floor1"
        )
        
        resolver.add_area(
            area_id="kitchen",
            name="Kitchen",
            parent_area_id="floor1"
        )
        
        children = resolver.get_child_areas("floor1")
        assert len(children) == 2
        assert "office" in children
        assert "kitchen" in children
    
    def test_get_all_areas_in_hierarchy(self, resolver):
        """Test getting all areas in hierarchy recursively"""
        resolver.add_area(
            area_id="floor1",
            name="First Floor"
        )
        
        resolver.add_area(
            area_id="office",
            name="Office",
            parent_area_id="floor1"
        )
        
        resolver.add_area(
            area_id="desk",
            name="Desk Area",
            parent_area_id="office"
        )
        
        all_areas = resolver.get_all_areas_in_hierarchy("floor1")
        assert "floor1" in all_areas
        assert "office" in all_areas
        assert "desk" in all_areas
    
    def test_filter_entities_by_area(self, resolver):
        """Test filtering entities by area"""
        area_map = {
            "light.office1": "office",
            "light.office2": "office",
            "light.kitchen": "kitchen"
        }
        
        entity_ids = ["light.office1", "light.office2", "light.kitchen"]
        
        filtered = resolver.filter_entities_by_area(
            entity_ids=entity_ids,
            area_id="office",
            area_map=area_map
        )
        
        assert len(filtered) == 2
        assert "light.office1" in filtered
        assert "light.office2" in filtered
        assert "light.kitchen" not in filtered
    
    def test_filter_entities_by_area_with_children(self, resolver):
        """Test filtering entities by area including children"""
        resolver.add_area(
            area_id="floor1",
            name="First Floor"
        )
        
        resolver.add_area(
            area_id="office",
            name="Office",
            parent_area_id="floor1"
        )
        
        area_map = {
            "light.office1": "office",
            "light.kitchen": "kitchen"
        }
        
        entity_ids = ["light.office1", "light.kitchen"]
        
        filtered = resolver.filter_entities_by_area(
            entity_ids=entity_ids,
            area_id="floor1",
            include_children=True,
            area_map=area_map
        )
        
        # Should include office (child of floor1)
        assert "light.office1" in filtered
    
    def test_extract_area_from_query(self, resolver):
        """Test extracting area name from query"""
        resolver.add_area(
            area_id="office",
            name="Office"
        )
        
        resolver.add_area(
            area_id="kitchen",
            name="Kitchen",
            aliases=["Cooking Area"]
        )
        
        # Test main name
        area_name = resolver.extract_area_from_query("turn on the office light")
        assert area_name == "Office"
        
        # Test alias
        area_name = resolver.extract_area_from_query("turn on the cooking area light")
        assert area_name == "Kitchen"
        
        # Test not found
        area_name = resolver.extract_area_from_query("turn on the bedroom light")
        assert area_name is None
    
    def test_clear(self, resolver):
        """Test clearing area index"""
        resolver.add_area(
            area_id="office",
            name="Office"
        )
        
        assert len(resolver._area_index) > 0
        
        resolver.clear()
        
        assert len(resolver._area_index) == 0
        assert len(resolver._name_index) == 0
        assert len(resolver._hierarchy_index) == 0
    
    def test_get_stats(self, resolver):
        """Test getting area index statistics"""
        resolver.add_area(
            area_id="office",
            name="Office",
            aliases=["Work Space"]
        )
        
        resolver.add_area(
            area_id="kitchen",
            name="Kitchen"
        )
        
        stats = resolver.get_stats()
        
        assert stats["total_areas"] == 2
        assert stats["total_aliases"] == 1
        assert stats["total_hierarchies"] == 0


class TestAreaInfo:
    """Test AreaInfo dataclass"""
    
    def test_area_info_creation(self):
        """Test creating AreaInfo"""
        area_info = AreaInfo(
            area_id="office",
            name="Office",
            aliases=["Work Space"],
            parent_area_id="floor1",
            parent_area_name="First Floor"
        )
        
        assert area_info.area_id == "office"
        assert area_info.name == "Office"
        assert len(area_info.aliases) == 1
        assert area_info.parent_area_id == "floor1"
        assert area_info.parent_area_name == "First Floor"

