"""
Unit tests for Training Data Generator

Epic AI-12, Story AI12.6: Training Data Generation from User Devices
Tests for TrainingDataGenerator class.
"""

import pytest
import json
import csv
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path
from tempfile import TemporaryDirectory

from src.services.entity.training_data_generator import (
    TrainingDataGenerator,
    QueryEntityPair
)
from src.services.entity.personalized_index import PersonalizedEntityIndex, EntityIndexEntry, EntityVariant
from src.services.learning.feedback_tracker import FeedbackTracker, EntityResolutionFeedback, FeedbackType


class TestTrainingDataGenerator:
    """Test TrainingDataGenerator class"""
    
    @pytest.fixture
    def personalized_index(self):
        """Create mock personalized index"""
        index = Mock(spec=PersonalizedEntityIndex)
        index._index = {}
        index.get_entity = Mock(return_value=None)
        return index
    
    @pytest.fixture
    def mock_entity_entry(self):
        """Create mock entity entry"""
        entry = Mock(spec=EntityIndexEntry)
        entry.entity_id = "light.office"
        entry.domain = "light"
        entry.area_id = "office"
        entry.area_name = "Office"
        entry.variants = []
        return entry
    
    @pytest.fixture
    def mock_variant(self):
        """Create mock variant"""
        variant = Mock(spec=EntityVariant)
        variant.variant_name = "Office Light"
        variant.variant_type = "name"
        return variant
    
    @pytest.fixture
    def generator(self, personalized_index):
        """Create TrainingDataGenerator instance"""
        return TrainingDataGenerator(personalized_index)
    
    def test_generate_synthetic_queries(self, generator, personalized_index, mock_entity_entry, mock_variant):
        """Test generating synthetic queries"""
        mock_entity_entry.variants = [mock_variant]
        personalized_index._index = {"light.office": mock_entity_entry}
        
        pairs = generator.generate_synthetic_queries(limit=10)
        
        assert len(pairs) > 0
        assert all(isinstance(pair, QueryEntityPair) for pair in pairs)
        assert pairs[0].query.startswith("turn on")
        assert pairs[0].entity_id == "light.office"
        assert pairs[0].source == "synthetic"
    
    def test_generate_synthetic_queries_with_entity_filter(self, generator, personalized_index, mock_entity_entry, mock_variant):
        """Test generating synthetic queries with entity filter"""
        mock_entity_entry.variants = [mock_variant]
        personalized_index._index = {"light.office": mock_entity_entry}
        
        pairs = generator.generate_synthetic_queries(entity_id="light.office", limit=10)
        
        assert len(pairs) > 0
        assert all(pair.entity_id == "light.office" for pair in pairs)
    
    def test_generate_query_variations(self, generator):
        """Test generating query variations"""
        variations = generator._generate_query_variations("Office Light", "light")
        
        assert len(variations) > 0
        assert any("turn on" in v.lower() for v in variations)
        assert any("turn off" in v.lower() for v in variations)
    
    def test_generate_query_variations_different_domain(self, generator):
        """Test generating query variations for different domain"""
        variations = generator._generate_query_variations("Living Room", "climate")
        
        assert len(variations) > 0
        assert any("temperature" in v.lower() for v in variations)
    
    @pytest.mark.asyncio
    async def test_extract_from_user_feedback(self, generator, personalized_index, mock_entity_entry):
        """Test extracting query-entity pairs from user feedback"""
        # Create feedback tracker
        feedback_tracker = Mock(spec=FeedbackTracker)
        
        feedback = EntityResolutionFeedback(
            feedback_id="123",
            query="turn on the office light",
            device_name="office light",
            suggested_entity_id="light.office",
            actual_entity_id="light.office",
            feedback_type=FeedbackType.APPROVE,
            confidence_score=0.9,
            area_id="office"
        )
        
        feedback_tracker.get_feedback_for_device = AsyncMock(return_value=[feedback])
        personalized_index.get_entity.return_value = mock_entity_entry
        
        generator.feedback_tracker = feedback_tracker
        
        pairs = await generator.extract_from_user_feedback("office light", limit=10)
        
        assert len(pairs) == 1
        assert pairs[0].query == "turn on the office light"
        assert pairs[0].entity_id == "light.office"
        assert pairs[0].source == "user_feedback"
        assert pairs[0].confidence == 0.9
    
    @pytest.mark.asyncio
    async def test_extract_from_user_feedback_no_tracker(self, generator):
        """Test extracting from user feedback when tracker not available"""
        generator.feedback_tracker = None
        
        pairs = await generator.extract_from_user_feedback("office light", limit=10)
        
        assert len(pairs) == 0
    
    @pytest.mark.asyncio
    async def test_generate_personalized_dataset(self, generator, personalized_index, mock_entity_entry, mock_variant):
        """Test generating personalized dataset"""
        mock_entity_entry.variants = [mock_variant]
        personalized_index._index = {"light.office": mock_entity_entry}
        
        pairs = await generator.generate_personalized_dataset(
            include_synthetic=True,
            include_feedback=False,
            limit=100
        )
        
        assert len(pairs) > 0
        assert all(pair.source == "synthetic" for pair in pairs)
    
    @pytest.mark.asyncio
    async def test_generate_personalized_dataset_with_feedback(self, generator, personalized_index, mock_entity_entry, mock_variant):
        """Test generating personalized dataset with feedback"""
        mock_entity_entry.variants = [mock_variant]
        personalized_index._index = {"light.office": mock_entity_entry}
        personalized_index.get_entity.return_value = mock_entity_entry
        
        # Create feedback tracker
        feedback_tracker = Mock(spec=FeedbackTracker)
        feedback = EntityResolutionFeedback(
            feedback_id="123",
            query="turn on the office light",
            device_name="office light",
            suggested_entity_id="light.office",
            actual_entity_id="light.office",
            feedback_type=FeedbackType.APPROVE,
            confidence_score=0.9
        )
        feedback_tracker.get_feedback_for_device = AsyncMock(return_value=[feedback])
        
        generator.feedback_tracker = feedback_tracker
        
        pairs = await generator.generate_personalized_dataset(
            include_synthetic=True,
            include_feedback=True,
            limit=100
        )
        
        assert len(pairs) > 0
        sources = set(pair.source for pair in pairs)
        assert "synthetic" in sources or "user_feedback" in sources
    
    def test_export_to_json(self, generator):
        """Test exporting to JSON format"""
        pairs = [
            QueryEntityPair(
                query="turn on office light",
                entity_id="light.office",
                device_name="office light",
                domain="light",
                source="synthetic"
            )
        ]
        
        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.json"
            
            result = generator.export_to_json(pairs, output_path)
            
            assert result is True
            assert output_path.exists()
            
            # Verify JSON content
            with open(output_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            assert "metadata" in data
            assert "pairs" in data
            assert len(data["pairs"]) == 1
            assert data["pairs"][0]["query"] == "turn on office light"
    
    def test_export_to_csv(self, generator):
        """Test exporting to CSV format"""
        pairs = [
            QueryEntityPair(
                query="turn on office light",
                entity_id="light.office",
                device_name="office light",
                domain="light",
                source="synthetic"
            )
        ]
        
        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.csv"
            
            result = generator.export_to_csv(pairs, output_path)
            
            assert result is True
            assert output_path.exists()
            
            # Verify CSV content
            with open(output_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            assert len(rows) == 1
            assert rows[0]["query"] == "turn on office light"
            assert rows[0]["entity_id"] == "light.office"
    
    def test_export_for_simulation_json(self, generator):
        """Test exporting for simulation framework (JSON)"""
        pairs = [
            QueryEntityPair(
                query="turn on office light",
                entity_id="light.office",
                device_name="office light",
                domain="light",
                source="synthetic"
            )
        ]
        
        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.json"
            
            result = generator.export_for_simulation(pairs, output_path, format="json")
            
            assert result is True
            assert output_path.exists()
    
    def test_export_for_simulation_csv(self, generator):
        """Test exporting for simulation framework (CSV)"""
        pairs = [
            QueryEntityPair(
                query="turn on office light",
                entity_id="light.office",
                device_name="office light",
                domain="light",
                source="synthetic"
            )
        ]
        
        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.csv"
            
            result = generator.export_for_simulation(pairs, output_path, format="csv")
            
            assert result is True
            assert output_path.exists()
    
    def test_export_for_simulation_unsupported_format(self, generator):
        """Test exporting with unsupported format"""
        pairs = []
        
        result = generator.export_for_simulation(pairs, "test.xml", format="xml")
        
        assert result is False
    
    def test_get_dataset_stats(self, generator):
        """Test getting dataset statistics"""
        pairs = [
            QueryEntityPair(
                query="turn on office light",
                entity_id="light.office",
                device_name="office light",
                domain="light",
                area_id="office",
                area_name="Office",
                confidence=0.9,
                source="synthetic"
            ),
            QueryEntityPair(
                query="turn off kitchen light",
                entity_id="light.kitchen",
                device_name="kitchen light",
                domain="light",
                area_id="kitchen",
                area_name="Kitchen",
                confidence=0.8,
                source="user_feedback"
            )
        ]
        
        stats = generator.get_dataset_stats(pairs)
        
        assert stats["total_pairs"] == 2
        assert stats["by_source"]["synthetic"] == 1
        assert stats["by_source"]["user_feedback"] == 1
        assert stats["by_domain"]["light"] == 2
        assert stats["by_area"]["Office"] == 1
        assert stats["by_area"]["Kitchen"] == 1
        assert stats["avg_confidence"] > 0.8
    
    def test_get_dataset_stats_empty(self, generator):
        """Test getting statistics for empty dataset"""
        stats = generator.get_dataset_stats([])
        
        assert stats["total_pairs"] == 0
        assert stats["avg_confidence"] == 0.0


class TestQueryEntityPair:
    """Test QueryEntityPair dataclass"""
    
    def test_query_entity_pair_creation(self):
        """Test creating QueryEntityPair"""
        pair = QueryEntityPair(
            query="turn on office light",
            entity_id="light.office",
            device_name="office light",
            domain="light",
            area_id="office",
            area_name="Office",
            confidence=0.9,
            source="synthetic"
        )
        
        assert pair.query == "turn on office light"
        assert pair.entity_id == "light.office"
        assert pair.device_name == "office light"
        assert pair.domain == "light"
        assert pair.area_id == "office"
        assert pair.area_name == "Office"
        assert pair.confidence == 0.9
        assert pair.source == "synthetic"
    
    def test_query_entity_pair_defaults(self):
        """Test QueryEntityPair with defaults"""
        pair = QueryEntityPair(
            query="turn on light",
            entity_id="light.office",
            device_name="light",
            domain="light"
        )
        
        assert pair.area_id is None
        assert pair.confidence == 1.0
        assert pair.source == "synthetic"
        assert pair.created_at is None

