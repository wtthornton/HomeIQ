"""
Unit tests for Context7 cross-references system.
"""

import pytest
from datetime import datetime
from pathlib import Path
import tempfile
import shutil
import yaml

from tapps_agents.context7.cross_references import (
    CrossReference,
    CrossReferenceManager,
    TopicIndex
)
from tapps_agents.context7.cache_structure import CacheStructure


@pytest.fixture
def temp_cache_dir():
    """Create temporary cache directory."""
    temp_dir = tempfile.mkdtemp()
    cache_root = Path(temp_dir) / "context7-cache"
    yield cache_root
    shutil.rmtree(temp_dir)


@pytest.fixture
def cache_structure(temp_cache_dir):
    """Create CacheStructure instance."""
    structure = CacheStructure(temp_cache_dir)
    structure.initialize()
    return structure


@pytest.fixture
def cross_ref_manager(cache_structure):
    """Create CrossReferenceManager instance."""
    return CrossReferenceManager(cache_structure)


class TestCrossReference:
    """Tests for CrossReference dataclass."""
    
    def test_create_cross_reference(self):
        """Test creating a cross-reference."""
        ref = CrossReference(
            source_library="react",
            source_topic="hooks",
            target_library="vue",
            target_topic="composition-api",
            relationship_type="similar",
            confidence=0.85
        )
        
        assert ref.source_library == "react"
        assert ref.source_topic == "hooks"
        assert ref.target_library == "vue"
        assert ref.target_topic == "composition-api"
        assert ref.relationship_type == "similar"
        assert ref.confidence == 0.85
        assert ref.created_at is not None
    
    def test_to_dict(self):
        """Test converting to dictionary."""
        ref = CrossReference(
            source_library="react",
            source_topic="hooks",
            target_library="vue",
            target_topic="composition-api"
        )
        
        data = ref.to_dict()
        assert isinstance(data, dict)
        assert data["source_library"] == "react"
        assert data["source_topic"] == "hooks"
        assert data["target_library"] == "vue"
        assert data["target_topic"] == "composition-api"
    
    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "source_library": "react",
            "source_topic": "hooks",
            "target_library": "vue",
            "target_topic": "composition-api",
            "relationship_type": "similar",
            "confidence": 0.85,
            "created_at": "2025-01-01T00:00:00Z"
        }
        
        ref = CrossReference.from_dict(data)
        assert ref.source_library == "react"
        assert ref.source_topic == "hooks"
        assert ref.target_library == "vue"
        assert ref.target_topic == "composition-api"
        assert ref.relationship_type == "similar"
        assert ref.confidence == 0.85


class TestTopicIndex:
    """Tests for TopicIndex dataclass."""
    
    def test_create_topic_index(self):
        """Test creating a topic index."""
        index = TopicIndex(topic="hooks")
        
        assert index.topic == "hooks"
        assert index.libraries == {}
        assert index.relationships == []
        assert index.last_updated is not None
    
    def test_to_dict(self):
        """Test converting to dictionary."""
        index = TopicIndex(
            topic="hooks",
            libraries={"react": ["hooks", "usestate"]}
        )
        
        data = index.to_dict()
        assert isinstance(data, dict)
        assert data["topic"] == "hooks"
        assert "react" in data["libraries"]
    
    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "topic": "hooks",
            "libraries": {"react": ["hooks"]},
            "relationships": [],
            "last_updated": "2025-01-01T00:00:00Z"
        }
        
        index = TopicIndex.from_dict(data)
        assert index.topic == "hooks"
        assert "react" in index.libraries


class TestCrossReferenceManager:
    """Tests for CrossReferenceManager."""
    
    def test_initialize(self, cross_ref_manager):
        """Test initialization."""
        assert cross_ref_manager.cache_structure is not None
        assert cross_ref_manager.cross_refs_file.exists() or cross_ref_manager.cache_structure.cache_root.exists()
    
    def test_add_cross_reference(self, cross_ref_manager):
        """Test adding a cross-reference."""
        cross_ref_manager.add_cross_reference(
            source_library="react",
            source_topic="hooks",
            target_library="vue",
            target_topic="composition-api",
            relationship_type="similar",
            confidence=0.85
        )
        
        refs = cross_ref_manager.get_cross_references("react", "hooks")
        assert len(refs) == 1
        assert refs[0].target_library == "vue"
        assert refs[0].target_topic == "composition-api"
    
    def test_add_duplicate_cross_reference(self, cross_ref_manager):
        """Test adding duplicate cross-reference updates existing."""
        cross_ref_manager.add_cross_reference(
            source_library="react",
            source_topic="hooks",
            target_library="vue",
            target_topic="composition-api",
            confidence=0.85
        )
        
        # Add same reference with different confidence
        cross_ref_manager.add_cross_reference(
            source_library="react",
            source_topic="hooks",
            target_library="vue",
            target_topic="composition-api",
            confidence=0.95
        )
        
        refs = cross_ref_manager.get_cross_references("react", "hooks")
        assert len(refs) == 1
        assert refs[0].confidence == 0.95
    
    def test_get_cross_references(self, cross_ref_manager):
        """Test getting cross-references."""
        cross_ref_manager.add_cross_reference(
            source_library="react",
            source_topic="hooks",
            target_library="vue",
            target_topic="composition-api",
            relationship_type="similar"
        )
        
        cross_ref_manager.add_cross_reference(
            source_library="react",
            source_topic="hooks",
            target_library="angular",
            target_topic="services",
            relationship_type="related"
        )
        
        refs = cross_ref_manager.get_cross_references("react", "hooks")
        assert len(refs) == 2
        
        # Test filtering by relationship type
        similar_refs = cross_ref_manager.get_cross_references("react", "hooks", relationship_type="similar")
        assert len(similar_refs) == 1
        assert similar_refs[0].target_library == "vue"
    
    def test_get_cross_references_sorted_by_confidence(self, cross_ref_manager):
        """Test that cross-references are sorted by confidence."""
        cross_ref_manager.add_cross_reference(
            source_library="react",
            source_topic="hooks",
            target_library="vue",
            target_topic="composition-api",
            confidence=0.7
        )
        
        cross_ref_manager.add_cross_reference(
            source_library="react",
            source_topic="hooks",
            target_library="angular",
            target_topic="services",
            confidence=0.9
        )
        
        refs = cross_ref_manager.get_cross_references("react", "hooks")
        assert len(refs) == 2
        assert refs[0].confidence == 0.9  # Highest first
        assert refs[1].confidence == 0.7
    
    def test_get_related_topics(self, cross_ref_manager):
        """Test getting related topics."""
        cross_ref_manager.add_cross_reference(
            source_library="react",
            source_topic="hooks",
            target_library="vue",
            target_topic="composition-api"
        )
        
        related = cross_ref_manager.get_related_topics("hooks")
        # Should have relationships from topic index
        assert isinstance(related, list)
    
    def test_find_similar_topics(self, cross_ref_manager):
        """Test finding similar topics."""
        cross_ref_manager.add_cross_reference(
            source_library="react",
            source_topic="hooks",
            target_library="vue",
            target_topic="composition-api",
            relationship_type="similar",
            confidence=0.85
        )
        
        cross_ref_manager.add_cross_reference(
            source_library="react",
            source_topic="hooks",
            target_library="angular",
            target_topic="services",
            relationship_type="related",
            confidence=0.6
        )
        
        similar = cross_ref_manager.find_similar_topics("react", "hooks", min_confidence=0.7)
        assert len(similar) == 1
        assert similar[0].target_library == "vue"
        assert similar[0].confidence >= 0.7
    
    def test_get_topic_index(self, cross_ref_manager):
        """Test getting topic index."""
        cross_ref_manager.add_cross_reference(
            source_library="react",
            source_topic="hooks",
            target_library="vue",
            target_topic="composition-api"
        )
        
        index = cross_ref_manager.get_topic_index("hooks")
        assert index is not None
        assert index.topic == "hooks"
    
    def test_remove_cross_reference(self, cross_ref_manager):
        """Test removing a cross-reference."""
        cross_ref_manager.add_cross_reference(
            source_library="react",
            source_topic="hooks",
            target_library="vue",
            target_topic="composition-api"
        )
        
        removed = cross_ref_manager.remove_cross_reference(
            source_library="react",
            source_topic="hooks",
            target_library="vue",
            target_topic="composition-api"
        )
        
        assert removed is True
        
        refs = cross_ref_manager.get_cross_references("react", "hooks")
        assert len(refs) == 0
    
    def test_remove_nonexistent_cross_reference(self, cross_ref_manager):
        """Test removing non-existent cross-reference."""
        removed = cross_ref_manager.remove_cross_reference(
            source_library="react",
            source_topic="hooks",
            target_library="vue",
            target_topic="composition-api"
        )
        
        assert removed is False
    
    def test_get_all_cross_references(self, cross_ref_manager):
        """Test getting all cross-references."""
        cross_ref_manager.add_cross_reference(
            source_library="react",
            source_topic="hooks",
            target_library="vue",
            target_topic="composition-api"
        )
        
        cross_ref_manager.add_cross_reference(
            source_library="angular",
            source_topic="services",
            target_library="react",
            target_topic="context"
        )
        
        all_refs = cross_ref_manager.get_all_cross_references()
        assert len(all_refs) == 2
        assert "react/hooks" in all_refs
        assert "angular/services" in all_refs
    
    def test_clear_cross_references(self, cross_ref_manager):
        """Test clearing all cross-references."""
        cross_ref_manager.add_cross_reference(
            source_library="react",
            source_topic="hooks",
            target_library="vue",
            target_topic="composition-api"
        )
        
        cross_ref_manager.clear_cross_references()
        
        all_refs = cross_ref_manager.get_all_cross_references()
        assert len(all_refs) == 0
    
    def test_persistence(self, cross_ref_manager, cache_structure):
        """Test that cross-references persist across instances."""
        cross_ref_manager.add_cross_reference(
            source_library="react",
            source_topic="hooks",
            target_library="vue",
            target_topic="composition-api"
        )
        
        # Create new manager instance
        new_manager = CrossReferenceManager(cache_structure)
        
        refs = new_manager.get_cross_references("react", "hooks")
        assert len(refs) == 1
        assert refs[0].target_library == "vue"


class TestAutoDiscovery:
    """Tests for auto-discovery functionality."""
    
    def test_auto_discover_cross_references_placeholder(self, cross_ref_manager):
        """Test auto-discovery placeholder (basic implementation)."""
        # This is a placeholder method, so we just test it doesn't crash
        cross_ref_manager.auto_discover_cross_references(
            library="react",
            topic="hooks",
            content="Similar to Vue Composition API"
        )
        
        # Method should complete without error
        assert True

