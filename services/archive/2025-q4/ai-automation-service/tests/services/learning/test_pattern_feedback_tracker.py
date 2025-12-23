"""
Unit tests for Pattern Feedback Tracker

Epic AI-13: ML-Based Pattern Quality & Active Learning
Story AI13.4: Active Learning Infrastructure
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timezone

import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from services.learning.pattern_feedback_tracker import PatternFeedbackTracker
from database.models import Pattern, Suggestion, UserFeedback


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    session = AsyncMock()
    return session


@pytest.fixture
def tracker(mock_db_session):
    """Create PatternFeedbackTracker instance."""
    return PatternFeedbackTracker(mock_db_session)


@pytest.fixture
def sample_pattern():
    """Create sample Pattern model."""
    pattern = Mock(spec=Pattern)
    pattern.id = 1
    pattern.pattern_type = 'time_of_day'
    pattern.pattern_metadata = {}
    return pattern


@pytest.fixture
def sample_suggestion():
    """Create sample Suggestion model."""
    suggestion = Mock(spec=Suggestion)
    suggestion.id = 10
    suggestion.pattern_id = 1
    return suggestion


@pytest.fixture
def sample_feedback():
    """Create sample UserFeedback."""
    feedback = Mock(spec=UserFeedback)
    feedback.id = 1
    feedback.suggestion_id = 10
    feedback.action = 'approved'
    feedback.feedback_text = 'Great pattern!'
    feedback.created_at = datetime.now(timezone.utc)
    return feedback


@pytest.mark.asyncio
async def test_track_approval(tracker, mock_db_session, sample_pattern, sample_suggestion):
    """Test tracking pattern approval."""
    # Mock database operations
    mock_db_session.get = AsyncMock(side_effect=lambda model, id: {
        (Suggestion, 10): sample_suggestion,
        (Pattern, 1): sample_pattern
    }.get((model, id)))
    
    with patch('services.learning.pattern_feedback_tracker.store_feedback', new_callable=AsyncMock) as mock_store:
        mock_store.return_value = Mock(
            id=1,
            suggestion_id=10,
            action='approved',
            created_at=datetime.now(timezone.utc)
        )
        
        feedback = await tracker.track_approval(
            pattern_id=1,
            suggestion_id=10,
            feedback_text='Great pattern!'
        )
        
        assert feedback.action == 'approved'
        assert mock_store.called


@pytest.mark.asyncio
async def test_track_rejection(tracker, mock_db_session, sample_pattern, sample_suggestion):
    """Test tracking pattern rejection."""
    mock_db_session.get = AsyncMock(side_effect=lambda model, id: {
        (Suggestion, 10): sample_suggestion,
        (Pattern, 1): sample_pattern
    }.get((model, id)))
    
    with patch('services.learning.pattern_feedback_tracker.store_feedback', new_callable=AsyncMock) as mock_store:
        mock_store.return_value = Mock(
            id=1,
            suggestion_id=10,
            action='rejected',
            created_at=datetime.now(timezone.utc)
        )
        
        feedback = await tracker.track_rejection(
            pattern_id=1,
            suggestion_id=10,
            feedback_text='Not useful'
        )
        
        assert feedback.action == 'rejected'
        assert mock_store.called


@pytest.mark.asyncio
async def test_track_entity_selection(tracker, mock_db_session, sample_pattern):
    """Test tracking entity selections."""
    mock_db_session.get = AsyncMock(return_value=sample_pattern)
    mock_db_session.commit = AsyncMock()
    
    selection = await tracker.track_entity_selection(
        pattern_id=1,
        selected_entities=['light.kitchen', 'sensor.motion'],
        suggestion_id=10
    )
    
    assert 'entities' in selection
    assert 'suggestion_id' in selection
    assert 'timestamp' in selection
    assert len(selection['entities']) == 2
    assert mock_db_session.commit.called


@pytest.mark.asyncio
async def test_track_entity_selection_pattern_not_found(tracker, mock_db_session):
    """Test tracking entity selection when pattern not found."""
    mock_db_session.get = AsyncMock(return_value=None)
    
    with pytest.raises(ValueError, match="Pattern 1 not found"):
        await tracker.track_entity_selection(
            pattern_id=1,
            selected_entities=['light.kitchen']
        )


@pytest.mark.asyncio
async def test_get_pattern_feedback(tracker, mock_db_session):
    """Test getting aggregated feedback for a pattern."""
    # Mock suggestion query
    mock_suggestion_result = Mock()
    mock_suggestion_result.all.return_value = [(10,), (11,)]
    
    mock_suggestion_query = Mock()
    mock_suggestion_query.where.return_value = mock_suggestion_query
    mock_db_session.execute = AsyncMock(return_value=mock_suggestion_result)
    
    # Mock feedback query
    mock_feedback_result = Mock()
    mock_feedback_row = Mock()
    mock_feedback_row.approvals = 5
    mock_feedback_row.rejections = 2
    mock_feedback_row.last_feedback = datetime.now(timezone.utc)
    mock_feedback_result.first.return_value = mock_feedback_row
    
    # Mock pattern query
    mock_pattern = Mock(spec=Pattern)
    mock_pattern.pattern_metadata = {'entity_selections': []}
    mock_db_session.get = AsyncMock(return_value=mock_pattern)
    
    feedback = await tracker.get_pattern_feedback(pattern_id=1)
    
    assert feedback['pattern_id'] == 1
    assert feedback['approvals'] == 5
    assert feedback['rejections'] == 2
    assert feedback['approval_rate'] == 5 / 7
    assert feedback['total_feedback'] == 7


@pytest.mark.asyncio
async def test_get_pattern_feedback_no_suggestions(tracker, mock_db_session):
    """Test getting feedback when pattern has no suggestions."""
    # Mock empty suggestion query
    mock_suggestion_result = Mock()
    mock_suggestion_result.all.return_value = []
    mock_db_session.execute = AsyncMock(return_value=mock_suggestion_result)
    
    feedback = await tracker.get_pattern_feedback(pattern_id=1)
    
    assert feedback['pattern_id'] == 1
    assert feedback['approvals'] == 0
    assert feedback['rejections'] == 0
    assert feedback['approval_rate'] == 0.0
    assert feedback['total_feedback'] == 0


@pytest.mark.asyncio
async def test_get_feedback_statistics(tracker, mock_db_session):
    """Test getting feedback statistics."""
    # Mock suggestion query
    mock_suggestion_result = Mock()
    mock_suggestion_result.all.return_value = [(10, 1), (11, 1), (12, 2)]
    mock_db_session.execute = AsyncMock(side_effect=[
        mock_suggestion_result,  # First call for suggestions
        Mock(first=lambda: None, all=lambda: [])  # Second call for feedback
    ])
    
    # Mock pattern count query
    mock_pattern_count_result = Mock()
    mock_pattern_count_result.scalar.return_value = 10
    mock_db_session.execute = AsyncMock(side_effect=[
        mock_suggestion_result,
        Mock(first=lambda: None, all=lambda: []),
        mock_pattern_count_result
    ])
    
    stats = await tracker.get_feedback_statistics()
    
    assert 'total_patterns' in stats
    assert 'patterns_with_feedback' in stats
    assert 'total_approvals' in stats
    assert 'total_rejections' in stats
    assert 'overall_approval_rate' in stats


@pytest.mark.asyncio
async def test_get_feedback_statistics_with_pattern_ids(tracker, mock_db_session):
    """Test getting feedback statistics with pattern filter."""
    # Mock suggestion query
    mock_suggestion_result = Mock()
    mock_suggestion_result.all.return_value = [(10, 1), (11, 1)]
    mock_db_session.execute = AsyncMock(side_effect=[
        mock_suggestion_result,
        Mock(first=lambda: None, all=lambda: [])
    ])
    
    stats = await tracker.get_feedback_statistics(pattern_ids=[1, 2])
    
    assert stats['total_patterns'] == 2


@pytest.mark.asyncio
async def test_track_approval_pattern_metadata_update(tracker, mock_db_session, sample_pattern, sample_suggestion):
    """Test that pattern metadata is updated on approval."""
    mock_db_session.get = AsyncMock(side_effect=lambda model, id: {
        (Suggestion, 10): sample_suggestion,
        (Pattern, 1): sample_pattern
    }.get((model, id)))
    mock_db_session.commit = AsyncMock()
    
    with patch('services.learning.pattern_feedback_tracker.store_feedback', new_callable=AsyncMock) as mock_store:
        mock_feedback = Mock()
        mock_feedback.created_at = datetime.now(timezone.utc)
        mock_store.return_value = mock_feedback
        
        await tracker.track_approval(pattern_id=1, suggestion_id=10)
        
        # Check that pattern metadata was updated
        assert 'last_feedback' in sample_pattern.pattern_metadata
        assert sample_pattern.pattern_metadata['last_feedback_action'] == 'approved'
        assert mock_db_session.commit.called


@pytest.mark.asyncio
async def test_track_rejection_pattern_metadata_update(tracker, mock_db_session, sample_pattern, sample_suggestion):
    """Test that pattern metadata is updated on rejection."""
    mock_db_session.get = AsyncMock(side_effect=lambda model, id: {
        (Suggestion, 10): sample_suggestion,
        (Pattern, 1): sample_pattern
    }.get((model, id)))
    mock_db_session.commit = AsyncMock()
    
    with patch('services.learning.pattern_feedback_tracker.store_feedback', new_callable=AsyncMock) as mock_store:
        mock_feedback = Mock()
        mock_feedback.created_at = datetime.now(timezone.utc)
        mock_store.return_value = mock_feedback
        
        await tracker.track_rejection(pattern_id=1, suggestion_id=10)
        
        # Check that pattern metadata was updated
        assert 'last_feedback' in sample_pattern.pattern_metadata
        assert sample_pattern.pattern_metadata['last_feedback_action'] == 'rejected'
        assert mock_db_session.commit.called

