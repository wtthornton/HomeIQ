"""
Unit tests for Index Updater

Epic AI-12, Story AI12.5: Index Update from User Feedback
Tests for IndexUpdater class.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from src.services.entity.index_updater import IndexUpdater
from src.services.entity.personalized_index import PersonalizedEntityIndex, EntityIndexEntry, EntityVariant
from src.services.learning.feedback_tracker import FeedbackTracker, FeedbackType, EntityResolutionFeedback


class TestIndexUpdater:
    """Test IndexUpdater class"""
    
    @pytest.fixture
    def personalized_index(self):
        """Create mock personalized index"""
        index = Mock(spec=PersonalizedEntityIndex)
        index._variant_index = {}
        index._generate_embedding = Mock(return_value=[0.1, 0.2, 0.3])
        return index
    
    @pytest.fixture
    def feedback_tracker(self):
        """Create mock feedback tracker"""
        tracker = Mock(spec=FeedbackTracker)
        tracker.get_feedback_for_device = AsyncMock(return_value=[])
        return tracker
    
    @pytest.fixture
    def index_updater(self, personalized_index, feedback_tracker):
        """Create IndexUpdater instance"""
        return IndexUpdater(personalized_index, feedback_tracker)
    
    @pytest.fixture
    def mock_entity_entry(self):
        """Create mock entity entry"""
        entry = Mock(spec=EntityIndexEntry)
        entry.entity_id = "light.office"
        entry.domain = "light"
        entry.area_id = "office"
        entry.area_name = "Office"
        entry.variants = []
        entry.last_updated = None
        return entry
    
    @pytest.mark.asyncio
    async def test_update_from_feedback_approve(self, index_updater, personalized_index, mock_entity_entry):
        """Test updating index from approve feedback"""
        personalized_index.get_entity.return_value = mock_entity_entry
        
        result = await index_updater.update_from_feedback(
            device_name="office light",
            entity_id="light.office",
            feedback_type=FeedbackType.APPROVE
        )
        
        assert result is True
        personalized_index.get_entity.assert_called_once_with("light.office")
    
    @pytest.mark.asyncio
    async def test_update_from_feedback_reject(self, index_updater, personalized_index, mock_entity_entry):
        """Test updating index from reject feedback"""
        personalized_index.get_entity.return_value = mock_entity_entry
        
        result = await index_updater.update_from_feedback(
            device_name="office light",
            entity_id="light.office",
            feedback_type=FeedbackType.REJECT
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_update_from_feedback_correct(self, index_updater, personalized_index, mock_entity_entry):
        """Test updating index from correct feedback"""
        personalized_index.get_entity.return_value = mock_entity_entry
        
        result = await index_updater.update_from_feedback(
            device_name="desk lamp",
            entity_id="light.office",
            feedback_type=FeedbackType.CORRECT,
            area_id="office"
        )
        
        assert result is True
        # Check that variant was added
        assert len(mock_entity_entry.variants) > 0
    
    @pytest.mark.asyncio
    async def test_update_from_feedback_custom_mapping(self, index_updater, personalized_index, mock_entity_entry):
        """Test updating index from custom mapping feedback"""
        personalized_index.get_entity.return_value = mock_entity_entry
        
        result = await index_updater.update_from_feedback(
            device_name="my desk light",
            entity_id="light.office",
            feedback_type=FeedbackType.CUSTOM_MAPPING,
            area_id="office"
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_update_from_feedback_entity_not_found(self, index_updater, personalized_index):
        """Test updating index when entity not found"""
        personalized_index.get_entity.return_value = None
        
        result = await index_updater.update_from_feedback(
            device_name="office light",
            entity_id="light.nonexistent",
            feedback_type=FeedbackType.APPROVE
        )
        
        # Should still return True (graceful failure)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_boost_variant_confidence(self, index_updater, personalized_index, mock_entity_entry):
        """Test boosting variant confidence"""
        personalized_index.get_entity.return_value = mock_entity_entry
        
        await index_updater._boost_variant_confidence("office light", "light.office")
        
        # Check confidence was boosted
        confidence = index_updater.get_variant_confidence("light.office", "office light")
        assert confidence > 0.5  # Should be boosted from default 0.5
    
    @pytest.mark.asyncio
    async def test_reduce_variant_confidence(self, index_updater, personalized_index, mock_entity_entry):
        """Test reducing variant confidence"""
        personalized_index.get_entity.return_value = mock_entity_entry
        
        # First boost it
        await index_updater._boost_variant_confidence("office light", "light.office")
        initial_confidence = index_updater.get_variant_confidence("light.office", "office light")
        
        # Then reduce it
        await index_updater._reduce_variant_confidence("office light", "light.office")
        reduced_confidence = index_updater.get_variant_confidence("light.office", "office light")
        
        assert reduced_confidence < initial_confidence
    
    @pytest.mark.asyncio
    async def test_add_custom_variant(self, index_updater, personalized_index, mock_entity_entry):
        """Test adding custom variant"""
        personalized_index.get_entity.return_value = mock_entity_entry
        
        await index_updater._add_custom_variant("desk lamp", "light.office", "office")
        
        # Check variant was added
        assert len(mock_entity_entry.variants) > 0
        variant = mock_entity_entry.variants[0]
        assert variant.variant_name == "desk lamp"
        assert variant.variant_type == "user_feedback"
        
        # Check confidence was set
        confidence = index_updater.get_variant_confidence("light.office", "desk lamp")
        assert confidence == 0.9  # High confidence for user-provided mappings
    
    @pytest.mark.asyncio
    async def test_add_custom_variant_existing(self, index_updater, personalized_index, mock_entity_entry):
        """Test adding custom variant when variant already exists"""
        # Add existing variant
        existing_variant = Mock(spec=EntityVariant)
        existing_variant.variant_name = "desk lamp"
        existing_variant.variant_type = "name"
        mock_entity_entry.variants.append(existing_variant)
        personalized_index.get_entity.return_value = mock_entity_entry
        
        await index_updater._add_custom_variant("desk lamp", "light.office", "office")
        
        # Check variant type was updated
        assert existing_variant.variant_type == "user_feedback"
    
    @pytest.mark.asyncio
    async def test_process_feedback_batch(self, index_updater, feedback_tracker, personalized_index, mock_entity_entry):
        """Test processing feedback batch"""
        # Mock feedback
        feedback = EntityResolutionFeedback(
            feedback_id="123",
            query="turn on",
            device_name="office light",
            suggested_entity_id="light.office",
            actual_entity_id="light.office",
            feedback_type=FeedbackType.APPROVE,
            confidence_score=0.9
        )
        
        feedback_tracker.get_feedback_for_device.return_value = [feedback]
        personalized_index.get_entity.return_value = mock_entity_entry
        
        stats = await index_updater.process_feedback_batch("office light", limit=10)
        
        assert stats["processed"] == 1
        assert stats["updated"] == 1
        assert stats["errors"] == 0
        assert stats["by_type"]["approve"] == 1
    
    @pytest.mark.asyncio
    async def test_process_feedback_batch_empty(self, index_updater, feedback_tracker):
        """Test processing empty feedback batch"""
        feedback_tracker.get_feedback_for_device.return_value = []
        
        stats = await index_updater.process_feedback_batch("office light", limit=10)
        
        assert stats["processed"] == 0
        assert stats["updated"] == 0
    
    def test_get_variant_confidence(self, index_updater):
        """Test getting variant confidence"""
        # Set confidence
        index_updater._variant_confidence["light.office"]["office light"] = 0.8
        
        confidence = index_updater.get_variant_confidence("light.office", "office light")
        assert confidence == 0.8
        
        # Test default
        confidence = index_updater.get_variant_confidence("light.office", "nonexistent")
        assert confidence == 0.5  # Default
    
    def test_get_variant_selection_count(self, index_updater):
        """Test getting variant selection count"""
        # Set selection count
        index_updater._variant_selections["light.office"]["office light"] = 5
        
        count = index_updater.get_variant_selection_count("light.office", "office light")
        assert count == 5
        
        # Test default
        count = index_updater.get_variant_selection_count("light.office", "nonexistent")
        assert count == 0  # Default
    
    def test_get_update_stats(self, index_updater):
        """Test getting update statistics"""
        # Add some data
        index_updater._variant_confidence["light.office"]["office light"] = 0.8
        index_updater._variant_selections["light.office"]["office light"] = 3
        
        stats = index_updater.get_update_stats()
        
        assert stats["total_variants_with_confidence"] == 1
        assert stats["total_selections"] == 3
        assert stats["entities_with_feedback"] == 1
    
    def test_find_variant(self, index_updater, mock_entity_entry):
        """Test finding variant"""
        variant1 = Mock(spec=EntityVariant)
        variant1.variant_name = "Office Light"
        variant2 = Mock(spec=EntityVariant)
        variant2.variant_name = "Desk Lamp"
        
        mock_entity_entry.variants = [variant1, variant2]
        
        found = index_updater._find_variant(mock_entity_entry, "desk lamp")
        assert found == variant2
        
        found = index_updater._find_variant(mock_entity_entry, "nonexistent")
        assert found is None

