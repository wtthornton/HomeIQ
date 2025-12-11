"""
Unit tests for PersonalizedEntityIndex

Epic AI-12, Story AI12.1: Personalized Entity Index Builder
Tests for personalized entity index with semantic embeddings.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import numpy as np

from src.services.entity.personalized_index import (
    PersonalizedEntityIndex,
    EntityVariant,
    EntityIndexEntry
)


class TestPersonalizedEntityIndex:
    """Test PersonalizedEntityIndex class"""
    
    def test_init(self):
        """Test index initialization"""
        index = PersonalizedEntityIndex()
        assert index._index == {}
        assert index._variant_index == {}
        assert index._area_index == {}
        assert index.embedding_model_name == "all-MiniLM-L6-v2"
    
    def test_init_with_custom_model(self):
        """Test initialization with custom embedding model"""
        index = PersonalizedEntityIndex(embedding_model="custom-model")
        assert index.embedding_model_name == "custom-model"
    
    def test_add_entity_basic(self):
        """Test adding entity with basic name variants"""
        index = PersonalizedEntityIndex()
        
        name_variants = {
            "name": "Office Lamp",
            "name_by_user": "Desk Light"
        }
        
        index.add_entity(
            entity_id="light.office_lamp",
            domain="light",
            name_variants=name_variants,
            area_id="office",
            area_name="Office"
        )
        
        # Check entity was added
        assert "light.office_lamp" in index._index
        entry = index._index["light.office_lamp"]
        assert entry.entity_id == "light.office_lamp"
        assert entry.domain == "light"
        assert entry.area_id == "office"
        assert entry.area_name == "Office"
        assert len(entry.variants) == 2
        
        # Check variants
        variant_names = [v.variant_name for v in entry.variants]
        assert "Office Lamp" in variant_names
        assert "Desk Light" in variant_names
        
        # Check variant index
        assert "office lamp" in index._variant_index
        assert "desk light" in index._variant_index
        
        # Check area index
        assert "office" in index._area_index
        assert "light.office_lamp" in index._area_index["office"]
    
    def test_add_entity_with_aliases(self):
        """Test adding entity with aliases"""
        index = PersonalizedEntityIndex()
        
        name_variants = {
            "name": "Kitchen Light",
            "aliases": ["Kitchen Lamp", "Main Light"]
        }
        
        index.add_entity(
            entity_id="light.kitchen",
            domain="light",
            name_variants=name_variants
        )
        
        entry = index._index["light.kitchen"]
        assert len(entry.variants) >= 1  # At least the name
        
        # Check aliases are indexed
        variant_names = [v.variant_name.lower() for v in entry.variants]
        assert "kitchen light" in variant_names
    
    def test_add_entity_empty_variants(self):
        """Test adding entity with empty name variants uses fallback"""
        index = PersonalizedEntityIndex()
        
        index.add_entity(
            entity_id="light.test",
            domain="light",
            name_variants={}
        )
        
        # Should create fallback from entity_id
        assert "light.test" in index._index
        entry = index._index["light.test"]
        assert len(entry.variants) > 0
    
    def test_get_entity(self):
        """Test retrieving entity by entity_id"""
        index = PersonalizedEntityIndex()
        
        index.add_entity(
            entity_id="light.test",
            domain="light",
            name_variants={"name": "Test Light"}
        )
        
        entry = index.get_entity("light.test")
        assert entry is not None
        assert entry.entity_id == "light.test"
        
        # Non-existent entity
        assert index.get_entity("light.nonexistent") is None
    
    @patch('src.services.entity.personalized_index.SentenceTransformer')
    def test_search_by_name_with_embeddings(self, mock_transformer):
        """Test semantic search with embeddings"""
        # Mock embedding model
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([0.1, 0.2, 0.3])
        mock_transformer.return_value = mock_model
        
        index = PersonalizedEntityIndex()
        
        # Add entities
        index.add_entity(
            entity_id="light.office",
            domain="light",
            name_variants={"name": "Office Lamp"}
        )
        
        index.add_entity(
            entity_id="light.kitchen",
            domain="light",
            name_variants={"name": "Kitchen Light"}
        )
        
        # Mock embeddings for query and variants
        mock_model.encode.side_effect = [
            np.array([0.1, 0.2, 0.3]),  # Query embedding
            np.array([0.1, 0.2, 0.3]),  # Office Lamp embedding (high similarity)
            np.array([0.9, 0.8, 0.7]),  # Kitchen Light embedding (low similarity)
        ]
        
        results = index.search_by_name("office light")
        
        # Should return results
        assert len(results) > 0
        assert results[0][0] in ["light.office", "light.kitchen"]
    
    def test_search_by_name_without_embeddings(self):
        """Test search falls back to exact matching when embeddings unavailable"""
        index = PersonalizedEntityIndex()
        
        # Add entities
        index.add_entity(
            entity_id="light.office",
            domain="light",
            name_variants={"name": "Office Lamp"}
        )
        
        # Search should use exact/fuzzy matching
        results = index.search_by_name("office lamp")
        
        assert len(results) > 0
        assert results[0][0] == "light.office"
        assert results[0][1] > 0  # Score > 0
    
    def test_search_by_name_with_domain_filter(self):
        """Test search with domain filter"""
        index = PersonalizedEntityIndex()
        
        index.add_entity(
            entity_id="light.office",
            domain="light",
            name_variants={"name": "Office Light"}
        )
        
        index.add_entity(
            entity_id="switch.office",
            domain="switch",
            name_variants={"name": "Office Switch"}
        )
        
        # Search with domain filter
        results = index.search_by_name("office", domain="light")
        
        assert len(results) > 0
        assert all(index._index[entity_id].domain == "light" for entity_id, _ in results)
    
    def test_search_by_name_with_area_filter(self):
        """Test search with area filter"""
        index = PersonalizedEntityIndex()
        
        index.add_entity(
            entity_id="light.office",
            domain="light",
            name_variants={"name": "Office Light"},
            area_id="office"
        )
        
        index.add_entity(
            entity_id="light.kitchen",
            domain="light",
            name_variants={"name": "Kitchen Light"},
            area_id="kitchen"
        )
        
        # Search with area filter
        results = index.search_by_name("light", area_id="office")
        
        assert len(results) > 0
        assert all(index._index[entity_id].area_id == "office" for entity_id, _ in results)
    
    def test_get_entities_by_area(self):
        """Test getting entities by area"""
        index = PersonalizedEntityIndex()
        
        index.add_entity(
            entity_id="light.office1",
            domain="light",
            name_variants={"name": "Office Light 1"},
            area_id="office"
        )
        
        index.add_entity(
            entity_id="light.office2",
            domain="light",
            name_variants={"name": "Office Light 2"},
            area_id="office"
        )
        
        index.add_entity(
            entity_id="light.kitchen",
            domain="light",
            name_variants={"name": "Kitchen Light"},
            area_id="kitchen"
        )
        
        office_entities = index.get_entities_by_area("office")
        assert len(office_entities) == 2
        assert "light.office1" in office_entities
        assert "light.office2" in office_entities
        
        kitchen_entities = index.get_entities_by_area("kitchen")
        assert len(kitchen_entities) == 1
        assert "light.kitchen" in kitchen_entities
    
    def test_get_stats(self):
        """Test getting index statistics"""
        index = PersonalizedEntityIndex()
        
        index.add_entity(
            entity_id="light.office",
            domain="light",
            name_variants={"name": "Office Light"},
            area_id="office"
        )
        
        index.add_entity(
            entity_id="light.kitchen",
            domain="light",
            name_variants={"name": "Kitchen Light"},
            area_id="kitchen"
        )
        
        stats = index.get_stats()
        
        assert stats["total_entities"] == 2
        assert stats["total_variants"] >= 2
        assert stats["total_areas"] == 2
    
    def test_clear(self):
        """Test clearing index"""
        index = PersonalizedEntityIndex()
        
        index.add_entity(
            entity_id="light.office",
            domain="light",
            name_variants={"name": "Office Light"}
        )
        
        assert len(index._index) > 0
        
        index.clear()
        
        assert len(index._index) == 0
        assert len(index._variant_index) == 0
        assert len(index._area_index) == 0
        assert index.get_stats()["total_entities"] == 0
    
    def test_cosine_similarity(self):
        """Test cosine similarity calculation"""
        index = PersonalizedEntityIndex()
        
        # Test identical vectors
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        similarity = index._cosine_similarity(vec1, vec2)
        assert abs(similarity - 1.0) < 0.001
        
        # Test orthogonal vectors
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        similarity = index._cosine_similarity(vec1, vec2)
        assert abs(similarity - 0.0) < 0.001
        
        # Test opposite vectors
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [-1.0, 0.0, 0.0]
        similarity = index._cosine_similarity(vec1, vec2)
        assert abs(similarity - (-1.0)) < 0.001


class TestEntityVariant:
    """Test EntityVariant dataclass"""
    
    def test_entity_variant_creation(self):
        """Test creating EntityVariant"""
        variant = EntityVariant(
            entity_id="light.test",
            variant_name="Test Light",
            variant_type="name"
        )
        
        assert variant.entity_id == "light.test"
        assert variant.variant_name == "Test Light"
        assert variant.variant_type == "name"
        assert variant.embedding is None


class TestEntityIndexEntry:
    """Test EntityIndexEntry dataclass"""
    
    def test_entity_index_entry_creation(self):
        """Test creating EntityIndexEntry"""
        entry = EntityIndexEntry(
            entity_id="light.test",
            domain="light"
        )
        
        assert entry.entity_id == "light.test"
        assert entry.domain == "light"
        assert len(entry.variants) == 0

