"""
Unit tests for Home Type Suggestion Ranking

Tests the integration of home type boost into suggestion ranking.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.crud import get_suggestions_with_home_type
from src.database.models import Suggestion
from src.home_type.integration_helpers import calculate_home_type_boost


@pytest.fixture
def mock_db():
    """Create mock database session"""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_suggestions():
    """Create mock suggestions for testing"""
    suggestions = []
    for i in range(5):
        suggestion = MagicMock(spec=Suggestion)
        suggestion.id = i + 1
        suggestion.category = ['security', 'climate', 'lighting', 'appliance', 'general'][i]
        suggestion.confidence = 0.7 + (i * 0.05)
        suggestion.weighted_score = None
        suggestions.append(suggestion)
    return suggestions


@pytest.mark.asyncio
async def test_get_suggestions_with_home_type_applies_boost(mock_db, mock_suggestions):
    """Test that home type boost is applied to suggestions"""
    with patch('src.database.crud.get_suggestions', return_value=mock_suggestions):
        result = await get_suggestions_with_home_type(
            mock_db,
            status=None,
            limit=5,
            home_type='security_focused'
        )
        
        # Security suggestion should have boost applied
        security_suggestion = next(s for s in result if s.category == 'security')
        assert security_suggestion.weighted_score is not None
        assert security_suggestion.weighted_score > security_suggestion.confidence


@pytest.mark.asyncio
async def test_get_suggestions_with_home_type_re_sorts(mock_db, mock_suggestions):
    """Test that suggestions are re-sorted by weighted score after boost"""
    with patch('src.database.crud.get_suggestions', return_value=mock_suggestions):
        result = await get_suggestions_with_home_type(
            mock_db,
            status=None,
            limit=5,
            home_type='security_focused'
        )
        
        # Verify suggestions are sorted by weighted_score descending
        scores = [s.weighted_score or s.confidence for s in result]
        assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_get_suggestions_without_home_type_no_boost(mock_db, mock_suggestions):
    """Test that suggestions without home type don't get boost"""
    with patch('src.database.crud.get_suggestions', return_value=mock_suggestions):
        result = await get_suggestions_with_home_type(
            mock_db,
            status=None,
            limit=5,
            home_type=None
        )
        
        # No boost should be applied
        for suggestion in result:
            assert suggestion.weighted_score is None or suggestion.weighted_score == suggestion.confidence


def test_calculate_home_type_boost_security_focused():
    """Test boost calculation for security-focused home"""
    boost = calculate_home_type_boost('security', 'security_focused', base_boost=0.10)
    assert boost > 0
    assert boost <= 0.10


def test_calculate_home_type_boost_non_matching_category():
    """Test boost calculation for non-matching category"""
    boost = calculate_home_type_boost('lighting', 'security_focused', base_boost=0.10)
    assert boost == 0.0


def test_calculate_home_type_boost_preference_order():
    """Test that boost decreases with preference order"""
    from src.home_type.integration_helpers import get_home_type_preferred_categories
    
    preferred = get_home_type_preferred_categories('security_focused')
    
    # First preference should get higher boost
    boost1 = calculate_home_type_boost(preferred[0], 'security_focused', base_boost=0.10)
    if len(preferred) > 1:
        boost2 = calculate_home_type_boost(preferred[1], 'security_focused', base_boost=0.10)
        assert boost1 >= boost2


@pytest.mark.asyncio
async def test_get_suggestions_with_home_type_limit(mock_db, mock_suggestions):
    """Test that limit is respected"""
    with patch('src.database.crud.get_suggestions', return_value=mock_suggestions):
        result = await get_suggestions_with_home_type(
            mock_db,
            status=None,
            limit=3,
            home_type='security_focused'
        )
        
        assert len(result) == 3

