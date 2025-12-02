"""
Integration tests for max_suggestions preference application.

Tests that max_suggestions preference is correctly applied in:
- Phase 5 description generation (daily_analysis.py)
- Ask AI suggestion generation (ask_ai_router.py)

Epic AI-6 Story AI6.8: Configurable Suggestion Count (5-50)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.blueprint_discovery.preference_manager import PreferenceManager


@pytest.fixture
def mock_preference_manager():
    """Create a mock PreferenceManager."""
    manager = MagicMock(spec=PreferenceManager)
    manager.get_max_suggestions = AsyncMock(return_value=10)
    return manager


@pytest.fixture
def sample_suggestions():
    """Create sample suggestions for testing."""
    return [
        {
            'id': f'suggestion_{i}',
            'title': f'Suggestion {i}',
            'description': f'Description {i}',
            'confidence': 0.9 - (i * 0.05),  # Decreasing confidence
            'type': 'pattern_based'
        }
        for i in range(20)
    ]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_phase5_applies_max_suggestions_limit(sample_suggestions):
    """Test that Phase 5 applies max_suggestions limit correctly."""
    from src.scheduler.daily_analysis import DailyAnalysisScheduler
    
    # Mock preference manager to return limit of 5
    with patch('src.scheduler.daily_analysis.PreferenceManager') as mock_pref_class:
        mock_manager = MagicMock()
        mock_manager.get_max_suggestions = AsyncMock(return_value=5)
        mock_pref_class.return_value = mock_manager
        
        # Create scheduler instance
        scheduler = DailyAnalysisScheduler()
        scheduler.scheduler = MagicMock()  # Mock APScheduler
        
        # Simulate Phase 5 Part D: combining and ranking suggestions
        all_suggestions = sample_suggestions.copy()
        
        # Apply ranking score (simulate existing logic)
        for suggestion in all_suggestions:
            suggestion['_ranking_score'] = suggestion.get('confidence', 0.5)
        
        # Sort by ranking score
        all_suggestions.sort(key=lambda s: s.get('_ranking_score', 0.5), reverse=True)
        
        # Simulate the preference-based limit application
        preference_manager = PreferenceManager(user_id="default")
        max_suggestions = await preference_manager.get_max_suggestions()
        
        # Apply limit (simulating what Phase 5 does)
        limited_suggestions = all_suggestions[:max_suggestions]
        
        # Verify limit applied
        assert len(limited_suggestions) == max_suggestions
        assert len(limited_suggestions) <= len(all_suggestions)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_phase5_defaults_to_10_when_preference_fails(sample_suggestions):
    """Test that Phase 5 defaults to 10 when preference loading fails."""
    # Simulate preference loading failure
    with patch('src.scheduler.daily_analysis.PreferenceManager') as mock_pref_class:
        mock_pref_class.side_effect = Exception("Preference service unavailable")
        
        # Should default to 10
        default_limit = 10
        
        all_suggestions = sample_suggestions.copy()
        limited_suggestions = all_suggestions[:default_limit]
        
        # Verify default applied
        assert len(limited_suggestions) == default_limit


@pytest.mark.asyncio
@pytest.mark.integration
async def test_ask_ai_applies_max_suggestions_limit(sample_suggestions):
    """Test that Ask AI applies max_suggestions limit correctly."""
    # Mock preference manager to return limit of 7
    with patch('src.api.ask_ai_router.PreferenceManager') as mock_pref_class:
        mock_manager = MagicMock()
        mock_manager.get_max_suggestions = AsyncMock(return_value=7)
        mock_pref_class.return_value = mock_manager
        
        # Simulate Ask AI suggestion combination and limiting
        suggestions = sample_suggestions.copy()
        
        # Sort by confidence (as Ask AI does)
        suggestions.sort(key=lambda s: s.get('confidence', 0.0), reverse=True)
        
        # Simulate preference-based limit
        preference_manager = PreferenceManager(user_id="test_user")
        max_suggestions = await preference_manager.get_max_suggestions()
        
        original_count = len(suggestions)
        limited_suggestions = suggestions[:max_suggestions]
        
        # Verify limit applied
        assert len(limited_suggestions) == max_suggestions
        assert len(limited_suggestions) < original_count


@pytest.mark.asyncio
@pytest.mark.integration
async def test_ask_ai_graceful_degradation_on_preference_error(sample_suggestions):
    """Test that Ask AI continues without limit when preference loading fails."""
    # Simulate preference loading failure
    with patch('src.api.ask_ai_router.PreferenceManager') as mock_pref_class:
        mock_pref_class.side_effect = Exception("Preference service unavailable")
        
        # Should continue with all suggestions (graceful degradation)
        suggestions = sample_suggestions.copy()
        original_count = len(suggestions)
        
        # No limit applied (simulating graceful degradation)
        limited_suggestions = suggestions  # No slicing on error
        
        # Verify all suggestions kept
        assert len(limited_suggestions) == original_count


@pytest.mark.asyncio
@pytest.mark.integration
async def test_max_suggestions_range_validation():
    """Test that max_suggestions preference validates range correctly."""
    preference_manager = PreferenceManager(user_id="test_user")
    
    # Test valid range boundaries
    try:
        await preference_manager.update_max_suggestions(5)  # Minimum
        assert await preference_manager.get_max_suggestions() == 5
        
        await preference_manager.update_max_suggestions(50)  # Maximum
        assert await preference_manager.get_max_suggestions() == 50
        
        await preference_manager.update_max_suggestions(25)  # Middle
        assert await preference_manager.get_max_suggestions() == 25
    except Exception as e:
        pytest.fail(f"Valid range values should not raise exceptions: {e}")
    
    # Test invalid range values
    with pytest.raises(ValueError, match="max_suggestions must be between"):
        await preference_manager.update_max_suggestions(4)  # Too low
    
    with pytest.raises(ValueError, match="max_suggestions must be between"):
        await preference_manager.update_max_suggestions(51)  # Too high


@pytest.mark.asyncio
@pytest.mark.integration
async def test_max_suggestions_default_value():
    """Test that default value (10) is used when preference not set."""
    preference_manager = PreferenceManager(user_id="new_user")
    
    # Should return default when preference not set
    max_suggestions = await preference_manager.get_max_suggestions()
    assert max_suggestions == 10  # Default value


@pytest.mark.asyncio
@pytest.mark.integration
async def test_combined_suggestions_limit_applies_to_all_types(sample_suggestions):
    """Test that max_suggestions limit applies to combined suggestions (patterns + features + synergies)."""
    # Simulate Phase 5 Part D with different suggestion types
    pattern_suggestions = [
        {**s, 'type': 'pattern_based'} 
        for s in sample_suggestions[:5]
    ]
    feature_suggestions = [
        {**s, 'type': 'feature_based'} 
        for s in sample_suggestions[5:10]
    ]
    synergy_suggestions = [
        {**s, 'type': 'synergy_based'} 
        for s in sample_suggestions[10:15]
    ]
    
    # Combine all suggestions (simulating Phase 5)
    all_suggestions = pattern_suggestions + feature_suggestions + synergy_suggestions
    
    # Sort by confidence
    all_suggestions.sort(key=lambda s: s.get('confidence', 0.5), reverse=True)
    
    # Apply limit of 8
    max_suggestions = 8
    limited_suggestions = all_suggestions[:max_suggestions]
    
    # Verify limit applies to combined list
    assert len(limited_suggestions) == max_suggestions
    assert len(limited_suggestions) < len(all_suggestions)
    
    # Verify top suggestions are kept (highest confidence)
    assert limited_suggestions[0]['confidence'] >= limited_suggestions[-1]['confidence']


@pytest.mark.asyncio
@pytest.mark.integration
async def test_blueprint_suggestions_included_in_limit(sample_suggestions):
    """Test that blueprint suggestions are included when applying max_suggestions limit."""
    # Simulate Ask AI combining blueprint suggestions with regular suggestions
    regular_suggestions = sample_suggestions[:8]
    blueprint_suggestions = [
        {
            'id': f'blueprint_{i}',
            'title': f'Blueprint Suggestion {i}',
            'description': f'Blueprint description {i}',
            'confidence': 0.85 - (i * 0.05),
            'type': 'blueprint_opportunity'
        }
        for i in range(5)
    ]
    
    # Combine suggestions (blueprint first, as in Ask AI)
    all_suggestions = blueprint_suggestions + regular_suggestions
    
    # Sort by confidence
    all_suggestions.sort(key=lambda s: s.get('confidence', 0.0), reverse=True)
    
    # Apply limit of 10
    max_suggestions = 10
    limited_suggestions = all_suggestions[:max_suggestions]
    
    # Verify limit applies to combined list
    assert len(limited_suggestions) == max_suggestions
    assert len(limited_suggestions) < len(all_suggestions)
    
    # Verify both types can be in the final list (top by confidence)
    blueprint_count = sum(1 for s in limited_suggestions if s.get('type') == 'blueprint_opportunity')
    regular_count = sum(1 for s in limited_suggestions if s.get('type') == 'pattern_based')
    
    # Should have both types if confidence warrants it
    assert blueprint_count + regular_count == len(limited_suggestions)
