"""
Unit tests for Active Learning Infrastructure

Epic AI-12, Story AI12.4: Active Learning Infrastructure
Tests for FeedbackTracker and ActiveLearner.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from src.services.learning.feedback_tracker import (
    FeedbackTracker,
    FeedbackType,
    EntityResolutionFeedback
)
from src.services.learning.active_learner import ActiveLearner
from src.services.entity.personalized_index import PersonalizedEntityIndex, EntityIndexEntry, EntityVariant


class TestFeedbackTracker:
    """Test FeedbackTracker class"""
    
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
    def tracker(self, db_session):
        """Create FeedbackTracker instance"""
        return FeedbackTracker(db_session)
    
    @pytest.mark.asyncio
    async def test_track_feedback_approve(self, tracker, db_session):
        """Test tracking approve feedback"""
        feedback_id = await tracker.track_feedback(
            query="turn on the office light",
            device_name="office light",
            suggested_entity_id="light.office",
            actual_entity_id="light.office",
            feedback_type=FeedbackType.APPROVE,
            confidence_score=0.9
        )
        
        assert feedback_id is not None
        assert len(feedback_id) > 0
        db_session.add.assert_called_once()
        db_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_track_feedback_reject(self, tracker, db_session):
        """Test tracking reject feedback"""
        feedback_id = await tracker.track_feedback(
            query="turn on the office light",
            device_name="office light",
            suggested_entity_id="light.office",
            actual_entity_id=None,
            feedback_type=FeedbackType.REJECT,
            confidence_score=0.5
        )
        
        assert feedback_id is not None
        db_session.add.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_track_feedback_correct(self, tracker, db_session):
        """Test tracking correction feedback"""
        feedback_id = await tracker.track_feedback(
            query="turn on the office light",
            device_name="office light",
            suggested_entity_id="light.office",
            actual_entity_id="light.office_main",
            feedback_type=FeedbackType.CORRECT,
            confidence_score=0.7,
            area_id="office"
        )
        
        assert feedback_id is not None
        db_session.add.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_track_feedback_custom_mapping(self, tracker, db_session):
        """Test tracking custom mapping feedback"""
        feedback_id = await tracker.track_feedback(
            query="turn on my desk lamp",
            device_name="desk lamp",
            suggested_entity_id=None,
            actual_entity_id="light.desk",
            feedback_type=FeedbackType.CUSTOM_MAPPING,
            area_id="office"
        )
        
        assert feedback_id is not None
        db_session.add.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_feedback_for_device(self, tracker, db_session):
        """Test getting feedback for a device"""
        # Mock database result
        mock_record = Mock()
        mock_record.feedback_text = '{"feedback_id": "123", "device_name": "office light", "query": "turn on", "suggested_entity_id": "light.office", "actual_entity_id": "light.office", "feedback_type": "approve", "confidence_score": 0.9, "area_id": null, "context": {}, "created_at": "2025-01-01T00:00:00"}'
        
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_record]
        db_session.execute.return_value = mock_result
        
        feedbacks = await tracker.get_feedback_for_device("office light")
        
        assert len(feedbacks) == 1
        assert feedbacks[0].device_name == "office light"
        assert feedbacks[0].feedback_type == FeedbackType.APPROVE
    
    @pytest.mark.asyncio
    async def test_get_feedback_stats(self, tracker, db_session):
        """Test getting feedback statistics"""
        # Mock database result
        mock_record1 = Mock()
        mock_record1.feedback_text = '{"feedback_id": "123", "device_name": "office light", "query": "turn on", "suggested_entity_id": "light.office", "actual_entity_id": "light.office", "feedback_type": "approve", "confidence_score": 0.9, "area_id": null, "context": {}, "created_at": "2025-01-01T00:00:00"}'
        
        mock_record2 = Mock()
        mock_record2.feedback_text = '{"feedback_id": "456", "device_name": "office light", "query": "turn on", "suggested_entity_id": "light.office", "actual_entity_id": "light.office_main", "feedback_type": "correct", "confidence_score": 0.7, "area_id": "office", "context": {}, "created_at": "2025-01-01T00:00:00"}'
        
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_record1, mock_record2]
        db_session.execute.return_value = mock_result
        
        stats = await tracker.get_feedback_stats()
        
        assert stats["total_feedback"] == 2
        assert stats["approve_count"] == 1
        assert stats["correct_count"] == 1
        assert stats["avg_confidence"] > 0
    
    @pytest.mark.asyncio
    async def test_get_feedback_stats_empty(self, tracker, db_session):
        """Test getting feedback statistics with no feedback"""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        db_session.execute.return_value = mock_result
        
        stats = await tracker.get_feedback_stats()
        
        assert stats["total_feedback"] == 0
        assert stats["approve_count"] == 0
        assert stats["avg_confidence"] == 0.0


class TestActiveLearner:
    """Test ActiveLearner class"""
    
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
        index = Mock(spec=PersonalizedEntityIndex)
        index.get_entity = Mock(return_value=None)
        return index
    
    @pytest.fixture
    def learner(self, db_session, personalized_index):
        """Create ActiveLearner instance"""
        return ActiveLearner(
            db=db_session,
            personalized_index=personalized_index
        )
    
    @pytest.mark.asyncio
    async def test_process_feedback_approve(self, learner, db_session):
        """Test processing approve feedback"""
        feedback_id = await learner.process_feedback(
            query="turn on the office light",
            device_name="office light",
            suggested_entity_id="light.office",
            actual_entity_id="light.office",
            feedback_type=FeedbackType.APPROVE,
            confidence_score=0.9
        )
        
        assert feedback_id is not None
        db_session.add.assert_called()
    
    @pytest.mark.asyncio
    async def test_process_feedback_reject(self, learner, db_session):
        """Test processing reject feedback"""
        feedback_id = await learner.process_feedback(
            query="turn on the office light",
            device_name="office light",
            suggested_entity_id="light.office",
            actual_entity_id=None,
            feedback_type=FeedbackType.REJECT,
            confidence_score=0.5
        )
        
        assert feedback_id is not None
    
    @pytest.mark.asyncio
    async def test_process_feedback_correct(self, learner, db_session):
        """Test processing correction feedback"""
        feedback_id = await learner.process_feedback(
            query="turn on the office light",
            device_name="office light",
            suggested_entity_id="light.office",
            actual_entity_id="light.office_main",
            feedback_type=FeedbackType.CORRECT,
            confidence_score=0.7,
            area_id="office"
        )
        
        assert feedback_id is not None
    
    @pytest.mark.asyncio
    async def test_process_feedback_custom_mapping(self, learner, db_session):
        """Test processing custom mapping feedback"""
        feedback_id = await learner.process_feedback(
            query="turn on my desk lamp",
            device_name="desk lamp",
            suggested_entity_id=None,
            actual_entity_id="light.desk",
            feedback_type=FeedbackType.CUSTOM_MAPPING,
            area_id="office"
        )
        
        assert feedback_id is not None
    
    @pytest.mark.asyncio
    async def test_analyze_feedback_patterns(self, learner, db_session):
        """Test analyzing feedback patterns"""
        # Mock feedback tracker
        mock_stats = {
            "total_feedback": 10,
            "approve_count": 7,
            "reject_count": 1,
            "correct_count": 2,
            "custom_mapping_count": 0,
            "avg_confidence": 0.8,
            "device_names": {"office light": 10}
        }
        
        mock_feedbacks = [
            EntityResolutionFeedback(
                feedback_id="123",
                query="turn on",
                device_name="office light",
                suggested_entity_id="light.office",
                actual_entity_id="light.office_main",
                feedback_type=FeedbackType.CORRECT,
                confidence_score=0.7
            )
        ]
        
        learner.feedback_tracker.get_feedback_stats = AsyncMock(return_value=mock_stats)
        learner.feedback_tracker.get_feedback_for_device = AsyncMock(return_value=mock_feedbacks)
        
        analysis = await learner.analyze_feedback_patterns("office light")
        
        assert analysis["total_feedback"] == 10
        assert analysis["approval_rate"] == 0.7
        assert analysis["correction_rate"] == 0.2
        assert len(analysis["recommendations"]) >= 0
    
    @pytest.mark.asyncio
    async def test_get_learning_summary(self, learner, db_session):
        """Test getting learning summary"""
        # Mock feedback tracker
        mock_stats = {
            "total_feedback": 10,
            "approve_count": 7,
            "reject_count": 1,
            "correct_count": 2,
            "custom_mapping_count": 0,
            "avg_confidence": 0.8,
            "device_names": {"office light": 10}
        }
        
        learner.feedback_tracker.get_feedback_stats = AsyncMock(return_value=mock_stats)
        learner.feedback_tracker.get_feedback_for_device = AsyncMock(return_value=[])
        
        summary = await learner.get_learning_summary()
        
        assert summary["total_feedback"] == 10
        assert summary["feedback_by_type"]["approve"] == 7
        assert summary["feedback_by_type"]["correct"] == 2
        assert summary["avg_confidence"] == 0.8
        assert summary["device_count"] == 1
    
    @pytest.mark.asyncio
    async def test_boost_entity_confidence(self, learner, personalized_index):
        """Test boosting entity confidence"""
        # Mock entity entry
        entry = Mock(spec=EntityIndexEntry)
        entry.entity_id = "light.office"
        personalized_index.get_entity.return_value = entry
        
        await learner._boost_entity_confidence("office light", "light.office")
        
        personalized_index.get_entity.assert_called_once_with("light.office")
    
    @pytest.mark.asyncio
    async def test_reduce_entity_confidence(self, learner, personalized_index):
        """Test reducing entity confidence"""
        # Mock entity entry
        entry = Mock(spec=EntityIndexEntry)
        entry.entity_id = "light.office"
        personalized_index.get_entity.return_value = entry
        
        await learner._reduce_entity_confidence("office light", "light.office")
        
        personalized_index.get_entity.assert_called_once_with("light.office")
    
    @pytest.mark.asyncio
    async def test_add_custom_mapping(self, learner, personalized_index):
        """Test adding custom mapping"""
        # Mock entity entry
        entry = Mock(spec=EntityIndexEntry)
        entry.entity_id = "light.desk"
        personalized_index.get_entity.return_value = entry
        
        await learner._add_custom_mapping("desk lamp", "light.desk", "office")
        
        personalized_index.get_entity.assert_called_once_with("light.desk")


class TestFeedbackType:
    """Test FeedbackType enum"""
    
    def test_feedback_type_values(self):
        """Test FeedbackType enum values"""
        assert FeedbackType.APPROVE.value == "approve"
        assert FeedbackType.REJECT.value == "reject"
        assert FeedbackType.CORRECT.value == "correct"
        assert FeedbackType.CUSTOM_MAPPING.value == "custom_mapping"
    
    def test_feedback_type_from_string(self):
        """Test creating FeedbackType from string"""
        assert FeedbackType("approve") == FeedbackType.APPROVE
        assert FeedbackType("reject") == FeedbackType.REJECT
        assert FeedbackType("correct") == FeedbackType.CORRECT
        assert FeedbackType("custom_mapping") == FeedbackType.CUSTOM_MAPPING


class TestEntityResolutionFeedback:
    """Test EntityResolutionFeedback dataclass"""
    
    def test_feedback_creation(self):
        """Test creating EntityResolutionFeedback"""
        feedback = EntityResolutionFeedback(
            feedback_id="123",
            query="turn on the office light",
            device_name="office light",
            suggested_entity_id="light.office",
            actual_entity_id="light.office",
            feedback_type=FeedbackType.APPROVE,
            confidence_score=0.9,
            area_id="office",
            context={"test": "value"},
            created_at=datetime.utcnow()
        )
        
        assert feedback.feedback_id == "123"
        assert feedback.query == "turn on the office light"
        assert feedback.device_name == "office light"
        assert feedback.suggested_entity_id == "light.office"
        assert feedback.actual_entity_id == "light.office"
        assert feedback.feedback_type == FeedbackType.APPROVE
        assert feedback.confidence_score == 0.9
        assert feedback.area_id == "office"
        assert feedback.context == {"test": "value"}

