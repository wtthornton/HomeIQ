"""
Unit tests for Feedback Aggregator

Epic AI-13: ML-Based Pattern Quality & Active Learning
Story AI13.4: Active Learning Infrastructure
"""

import pytest
from unittest.mock import AsyncMock, Mock

import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from services.learning.feedback_aggregator import PatternFeedbackAggregator
from services.learning.pattern_feedback_tracker import PatternFeedbackTracker


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    session = AsyncMock()
    return session


@pytest.fixture
def aggregator(mock_db_session):
    """Create PatternFeedbackAggregator instance."""
    return PatternFeedbackAggregator(mock_db_session)


@pytest.mark.asyncio
async def test_aggregate_feedback(aggregator, mock_db_session):
    """Test aggregating feedback for a pattern."""
    # Mock tracker.get_pattern_feedback
    with patch.object(aggregator.tracker, 'get_pattern_feedback', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {
            'pattern_id': 1,
            'approvals': 8,
            'rejections': 2,
            'approval_rate': 0.8,
            'total_feedback': 10,
            'last_feedback': None,
            'entity_selections': []
        }
        
        result = await aggregator.aggregate_feedback(pattern_id=1)
        
        assert result['pattern_id'] == 1
        assert result['approvals'] == 8
        assert result['rejections'] == 2
        assert result['approval_rate'] == 0.8


@pytest.mark.asyncio
async def test_identify_high_quality_patterns(aggregator, mock_db_session):
    """Test identifying high-quality patterns."""
    # Mock suggestion query
    mock_suggestion_result = Mock()
    mock_suggestion_result.all.return_value = [
        (10, 1),  # (suggestion_id, pattern_id)
        (11, 1),
        (12, 2),
        (13, 2)
    ]
    
    # Mock feedback query
    mock_feedback_result = Mock()
    mock_feedback_result.all.return_value = [
        Mock(suggestion_id=10, approvals=8, rejections=2),  # Pattern 1: 80% approval
        Mock(suggestion_id=11, approvals=9, rejections=1),  # Pattern 1: 90% approval
        Mock(suggestion_id=12, approvals=2, rejections=8),  # Pattern 2: 20% approval
        Mock(suggestion_id=13, approvals=1, rejections=9),  # Pattern 2: 10% approval
    ]
    
    mock_db_session.execute = AsyncMock(side_effect=[
        mock_suggestion_result,
        mock_feedback_result
    ])
    
    high_quality = await aggregator.identify_high_quality_patterns(
        min_approval_rate=0.8,
        min_feedback_count=5
    )
    
    # Pattern 1 should be high quality (85% approval, 20 feedback)
    assert 1 in high_quality
    # Pattern 2 should not be high quality (15% approval)
    assert 2 not in high_quality


@pytest.mark.asyncio
async def test_identify_high_quality_patterns_insufficient_feedback(aggregator, mock_db_session):
    """Test that patterns with insufficient feedback are excluded."""
    # Mock suggestion query
    mock_suggestion_result = Mock()
    mock_suggestion_result.all.return_value = [(10, 1)]
    
    # Mock feedback query (only 3 feedback samples, below min_feedback_count=5)
    mock_feedback_result = Mock()
    mock_feedback_result.all.return_value = [
        Mock(suggestion_id=10, approvals=3, rejections=0),  # 100% but only 3 samples
    ]
    
    mock_db_session.execute = AsyncMock(side_effect=[
        mock_suggestion_result,
        mock_feedback_result
    ])
    
    high_quality = await aggregator.identify_high_quality_patterns(
        min_approval_rate=0.8,
        min_feedback_count=5
    )
    
    # Should be empty (insufficient feedback)
    assert len(high_quality) == 0


@pytest.mark.asyncio
async def test_identify_low_quality_patterns(aggregator, mock_db_session):
    """Test identifying low-quality patterns."""
    # Mock suggestion query
    mock_suggestion_result = Mock()
    mock_suggestion_result.all.return_value = [
        (10, 1),  # (suggestion_id, pattern_id)
        (11, 1),
        (12, 2),
        (13, 2)
    ]
    
    # Mock feedback query
    mock_feedback_result = Mock()
    mock_feedback_result.all.return_value = [
        Mock(suggestion_id=10, approvals=2, rejections=8),  # Pattern 1: 20% approval
        Mock(suggestion_id=11, approvals=1, rejections=9),  # Pattern 1: 10% approval
        Mock(suggestion_id=12, approvals=8, rejections=2),  # Pattern 2: 80% approval
        Mock(suggestion_id=13, approvals=9, rejections=1),  # Pattern 2: 90% approval
    ]
    
    mock_db_session.execute = AsyncMock(side_effect=[
        mock_suggestion_result,
        mock_feedback_result
    ])
    
    low_quality = await aggregator.identify_low_quality_patterns(
        max_approval_rate=0.3,
        min_feedback_count=5
    )
    
    # Pattern 1 should be low quality (15% approval, 20 feedback)
    assert 1 in low_quality
    # Pattern 2 should not be low quality (85% approval)
    assert 2 not in low_quality


@pytest.mark.asyncio
async def test_identify_low_quality_patterns_insufficient_feedback(aggregator, mock_db_session):
    """Test that patterns with insufficient feedback are excluded."""
    # Mock suggestion query
    mock_suggestion_result = Mock()
    mock_suggestion_result.all.return_value = [(10, 1)]
    
    # Mock feedback query (only 3 feedback samples, below min_feedback_count=5)
    mock_feedback_result = Mock()
    mock_feedback_result.all.return_value = [
        Mock(suggestion_id=10, approvals=0, rejections=3),  # 0% but only 3 samples
    ]
    
    mock_db_session.execute = AsyncMock(side_effect=[
        mock_suggestion_result,
        mock_feedback_result
    ])
    
    low_quality = await aggregator.identify_low_quality_patterns(
        max_approval_rate=0.3,
        min_feedback_count=5
    )
    
    # Should be empty (insufficient feedback)
    assert len(low_quality) == 0


@pytest.mark.asyncio
async def test_identify_high_quality_patterns_no_suggestions(aggregator, mock_db_session):
    """Test identifying high-quality patterns when no suggestions exist."""
    # Mock empty suggestion query
    mock_suggestion_result = Mock()
    mock_suggestion_result.all.return_value = []
    mock_db_session.execute = AsyncMock(return_value=mock_suggestion_result)
    
    high_quality = await aggregator.identify_high_quality_patterns()
    
    assert len(high_quality) == 0


@pytest.mark.asyncio
async def test_identify_low_quality_patterns_no_suggestions(aggregator, mock_db_session):
    """Test identifying low-quality patterns when no suggestions exist."""
    # Mock empty suggestion query
    mock_suggestion_result = Mock()
    mock_suggestion_result.all.return_value = []
    mock_db_session.execute = AsyncMock(return_value=mock_suggestion_result)
    
    low_quality = await aggregator.identify_low_quality_patterns()
    
    assert len(low_quality) == 0

