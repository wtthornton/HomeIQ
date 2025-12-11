"""
Unit tests for Feedback Processor

Epic AI-12, Story AI12.5: Index Update from User Feedback
Tests for FeedbackProcessor class.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from src.services.learning.feedback_processor import FeedbackProcessor
from src.services.entity.personalized_index import PersonalizedEntityIndex
from src.services.entity.index_updater import IndexUpdater
from src.services.learning.feedback_tracker import FeedbackTracker, FeedbackType, EntityResolutionFeedback


class TestFeedbackProcessor:
    """Test FeedbackProcessor class"""
    
    @pytest.fixture
    def db_session(self):
        """Create mock database session"""
        session = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.add = Mock()
        session.execute = AsyncMock()
        return session
    
    @pytest.fixture
    def personalized_index(self):
        """Create mock personalized index"""
        return Mock(spec=PersonalizedEntityIndex)
    
    @pytest.fixture
    def feedback_tracker(self, db_session):
        """Create mock feedback tracker"""
        tracker = Mock(spec=FeedbackTracker)
        tracker.get_feedback_stats = AsyncMock(return_value={
            "total_feedback": 10,
            "approve_count": 7,
            "reject_count": 1,
            "correct_count": 2,
            "custom_mapping_count": 0,
            "avg_confidence": 0.8,
            "device_names": {"office light": 10}
        })
        tracker.get_feedback_for_device = AsyncMock(return_value=[])
        return tracker
    
    @pytest.fixture
    def index_updater(self, personalized_index, feedback_tracker):
        """Create mock index updater"""
        updater = Mock(spec=IndexUpdater)
        updater.process_feedback_batch = AsyncMock(return_value={
            "processed": 5,
            "updated": 5,
            "errors": 0,
            "by_type": {"approve": 3, "correct": 2}
        })
        updater.get_update_stats = Mock(return_value={
            "total_variants_with_confidence": 10,
            "total_selections": 15,
            "entities_with_feedback": 5
        })
        return updater
    
    @pytest.fixture
    def processor(self, db_session, personalized_index, index_updater):
        """Create FeedbackProcessor instance"""
        return FeedbackProcessor(db_session, personalized_index, index_updater)
    
    @pytest.mark.asyncio
    async def test_analyze_feedback_patterns(self, processor, feedback_tracker):
        """Test analyzing feedback patterns"""
        # Mock feedback
        feedbacks = [
            EntityResolutionFeedback(
                feedback_id="1",
                query="turn on",
                device_name="office light",
                suggested_entity_id="light.office",
                actual_entity_id="light.office_main",
                feedback_type=FeedbackType.CORRECT,
                confidence_score=0.6
            ),
            EntityResolutionFeedback(
                feedback_id="2",
                query="turn on",
                device_name="office light",
                suggested_entity_id="light.office",
                actual_entity_id="light.office",
                feedback_type=FeedbackType.APPROVE,
                confidence_score=0.9
            )
        ]
        
        feedback_tracker.get_feedback_for_device.return_value = feedbacks
        
        analysis = await processor.analyze_feedback_patterns("office light")
        
        assert analysis["total_feedback"] == 10
        assert analysis["approval_rate"] == 0.7
        assert analysis["correction_rate"] == 0.2
        assert len(analysis["common_corrections"]) > 0
        assert len(analysis["recommendations"]) > 0
    
    @pytest.mark.asyncio
    async def test_analyze_feedback_patterns_empty(self, processor, feedback_tracker):
        """Test analyzing feedback patterns with no feedback"""
        feedback_tracker.get_feedback_stats.return_value = {
            "total_feedback": 0,
            "approve_count": 0,
            "reject_count": 0,
            "correct_count": 0,
            "custom_mapping_count": 0,
            "avg_confidence": 0.0,
            "device_names": {}
        }
        
        analysis = await processor.analyze_feedback_patterns()
        
        assert analysis["total_feedback"] == 0
        assert analysis["approval_rate"] == 0.0
        assert len(analysis["recommendations"]) == 0
    
    @pytest.mark.asyncio
    async def test_process_feedback_and_update(self, processor, index_updater):
        """Test processing feedback and updating index"""
        result = await processor.process_feedback_and_update("office light", limit=10)
        
        assert result["feedback_processed"] == 5
        assert result["index_updated"] == 5
        assert result["errors"] == 0
        assert "index_stats" in result
        index_updater.process_feedback_batch.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_learning_opportunities(self, processor, feedback_tracker):
        """Test getting learning opportunities"""
        # Mock feedback with corrections
        feedbacks = [
            EntityResolutionFeedback(
                feedback_id="1",
                query="turn on",
                device_name="office light",
                suggested_entity_id="light.office",
                actual_entity_id="light.office_main",
                feedback_type=FeedbackType.CORRECT,
                confidence_score=0.6
            ),
            EntityResolutionFeedback(
                feedback_id="2",
                query="turn on",
                device_name="office light",
                suggested_entity_id="light.office",
                actual_entity_id="light.office_main",
                feedback_type=FeedbackType.CORRECT,
                confidence_score=0.7
            ),
            EntityResolutionFeedback(
                feedback_id="3",
                query="turn on",
                device_name="office light",
                suggested_entity_id="light.office",
                actual_entity_id="light.office_main",
                feedback_type=FeedbackType.CORRECT,
                confidence_score=0.8
            )
        ]
        
        feedback_tracker.get_feedback_stats.return_value = {
            "total_feedback": 3,
            "approve_count": 0,
            "reject_count": 0,
            "correct_count": 3,
            "custom_mapping_count": 0,
            "avg_confidence": 0.7,
            "device_names": {"office light": 3}
        }
        
        feedback_tracker.get_feedback_for_device.return_value = feedbacks
        
        opportunities = await processor.get_learning_opportunities(min_corrections=3)
        
        assert len(opportunities) > 0
        opp = opportunities[0]
        assert opp["device_name"] == "office light"
        assert opp["preferred_mapping"] == "light.office_main"
        assert opp["correction_count"] == 3
    
    @pytest.mark.asyncio
    async def test_get_learning_opportunities_insufficient(self, processor, feedback_tracker):
        """Test getting learning opportunities with insufficient corrections"""
        feedback_tracker.get_feedback_stats.return_value = {
            "total_feedback": 2,
            "approve_count": 0,
            "reject_count": 0,
            "correct_count": 2,
            "custom_mapping_count": 0,
            "avg_confidence": 0.7,
            "device_names": {"office light": 2}
        }
        
        feedback_tracker.get_feedback_for_device.return_value = []
        
        opportunities = await processor.get_learning_opportunities(min_corrections=3)
        
        assert len(opportunities) == 0
    
    @pytest.mark.asyncio
    async def test_analyze_feedback_patterns_high_correction_rate(self, processor, feedback_tracker):
        """Test analyzing feedback patterns with high correction rate"""
        feedback_tracker.get_feedback_stats.return_value = {
            "total_feedback": 10,
            "approve_count": 2,
            "reject_count": 1,
            "correct_count": 7,  # High correction rate
            "custom_mapping_count": 0,
            "avg_confidence": 0.6,
            "device_names": {"office light": 10}
        }
        
        feedbacks = [
            EntityResolutionFeedback(
                feedback_id=str(i),
                query="turn on",
                device_name="office light",
                suggested_entity_id="light.office",
                actual_entity_id="light.office_main",
                feedback_type=FeedbackType.CORRECT,
                confidence_score=0.6
            )
            for i in range(7)
        ]
        
        feedback_tracker.get_feedback_for_device.return_value = feedbacks
        
        analysis = await processor.analyze_feedback_patterns("office light")
        
        assert analysis["correction_rate"] > 0.3
        # Should have recommendation about high correction rate
        assert any("correction rate" in rec.lower() for rec in analysis["recommendations"])
    
    @pytest.mark.asyncio
    async def test_analyze_feedback_patterns_low_confidence(self, processor, feedback_tracker):
        """Test analyzing feedback patterns with low confidence"""
        feedback_tracker.get_feedback_stats.return_value = {
            "total_feedback": 10,
            "approve_count": 5,
            "reject_count": 2,
            "correct_count": 3,
            "custom_mapping_count": 0,
            "avg_confidence": 0.5,  # Low confidence
            "device_names": {"office light": 10}
        }
        
        feedbacks = [
            EntityResolutionFeedback(
                feedback_id=str(i),
                query="turn on",
                device_name="office light",
                suggested_entity_id="light.office",
                actual_entity_id="light.office",
                feedback_type=FeedbackType.APPROVE,
                confidence_score=0.5
            )
            for i in range(5)
        ]
        
        feedback_tracker.get_feedback_for_device.return_value = feedbacks
        
        analysis = await processor.analyze_feedback_patterns("office light")
        
        # Should have recommendation about low confidence
        assert any("confidence" in rec.lower() for rec in analysis["recommendations"])

