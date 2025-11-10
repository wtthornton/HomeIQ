"""
Unit Tests for Deduplicator

Tests fuzzy matching and duplicate detection.
"""
import pytest
from datetime import datetime

from src.miner.deduplicator import Deduplicator
from src.miner.models import AutomationMetadata


class TestDeduplicator:
    """Test Deduplicator functionality"""
    
    @pytest.fixture
    def dedup(self):
        """Create deduplicator instance"""
        return Deduplicator(similarity_threshold=0.85)
    
    @pytest.fixture
    def sample_metadata(self):
        """Create sample automation metadata"""
        return AutomationMetadata(
            title="Motion-activated lighting",
            description="Turn on lights when motion detected",
            devices=["motion_sensor", "light"],
            integrations=["mqtt"],
            triggers=[{"type": "state"}],
            conditions=[],
            actions=[{"service": "light.turn_on"}],
            use_case="comfort",
            complexity="low",
            quality_score=0.85,
            vote_count=500,
            source="discourse",
            source_id="12345",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    def test_calculate_title_similarity_identical(self, dedup):
        """Test similarity calculation for identical titles"""
        title1 = "Motion-activated lighting"
        title2 = "Motion-activated lighting"
        
        similarity = dedup.calculate_title_similarity(title1, title2)
        
        assert similarity == 1.0
    
    def test_calculate_title_similarity_similar(self, dedup):
        """Test similarity for similar titles"""
        title1 = "Motion activated lighting system"
        title2 = "Motion-activated lighting"
        
        similarity = dedup.calculate_title_similarity(title1, title2)
        
        assert similarity > 0.8
    
    def test_calculate_title_similarity_different(self, dedup):
        """Test similarity for different titles"""
        title1 = "Motion-activated lighting"
        title2 = "Temperature control automation"
        
        similarity = dedup.calculate_title_similarity(title1, title2)
        
        assert similarity < 0.5
    
    def test_is_duplicate_same_source_id(self, dedup, sample_metadata):
        """Test duplicate detection - same source_id"""
        metadata1 = sample_metadata
        metadata2 = sample_metadata.model_copy(update={"title": "Different title"})
        
        is_dup = dedup.is_duplicate(metadata1, metadata2)
        
        assert is_dup is True
    
    def test_is_duplicate_similar_title_same_devices(self, dedup, sample_metadata):
        """Test duplicate detection - similar title and devices"""
        metadata1 = sample_metadata
        metadata2 = sample_metadata.model_copy(update={
            "source_id": "67890",
            "title": "Motion activated lighting"  # Very similar
        })
        
        is_dup = dedup.is_duplicate(metadata1, metadata2)
        
        assert is_dup is True
    
    def test_is_not_duplicate_different_title(self, dedup, sample_metadata):
        """Test not duplicate - different title"""
        metadata1 = sample_metadata
        metadata2 = sample_metadata.model_copy(update={
            "source_id": "67890",
            "title": "Temperature control system"
        })
        
        is_dup = dedup.is_duplicate(metadata1, metadata2)
        
        assert is_dup is False
    
    def test_select_best_by_quality(self, dedup):
        """Test selecting best automation by quality score"""
        auto1 = AutomationMetadata(
            title="Test", description="Test", devices=[], integrations=[],
            triggers=[], conditions=[], actions=[], use_case="comfort",
            complexity="low", quality_score=0.7, vote_count=100,
            source="discourse", source_id="1",
            created_at=datetime.utcnow(), updated_at=datetime.utcnow()
        )
        auto2 = AutomationMetadata(
            title="Test", description="Test", devices=[], integrations=[],
            triggers=[], conditions=[], actions=[], use_case="comfort",
            complexity="low", quality_score=0.9, vote_count=500,
            source="discourse", source_id="2",
            created_at=datetime.utcnow(), updated_at=datetime.utcnow()
        )
        
        best = dedup.select_best([auto1, auto2])
        
        assert best.source_id == "2"
        assert best.quality_score == 0.9


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

