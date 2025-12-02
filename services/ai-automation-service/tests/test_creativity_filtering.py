"""
Integration tests for creativity-based suggestion filtering.

Tests creativity level filtering in:
- Phase 5 description generation
- Ask AI suggestion generation

Epic AI-6 Story AI6.9: Configurable Creativity Levels
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.blueprint_discovery.creativity_filter import CreativityConfig, CreativityFilter
from src.blueprint_discovery.preference_manager import PreferenceManager


@pytest.fixture
def sample_suggestions_mixed():
    """Create mixed sample suggestions with various confidence levels and types."""
    suggestions = []
    
    # High confidence, blueprint-validated (should pass conservative)
    suggestions.append({
        'id': 'high_conf_blueprint',
        'title': 'High Confidence Blueprint',
        'confidence': 0.90,
        'type': 'pattern_based',
        'blueprint_validated': True,
        'blueprint_match_score': 0.85,
    })
    
    # Medium confidence (should pass balanced/creative)
    suggestions.append({
        'id': 'medium_conf',
        'title': 'Medium Confidence',
        'confidence': 0.75,
        'type': 'feature_based',
    })
    
    # Low confidence (should only pass creative)
    suggestions.append({
        'id': 'low_conf',
        'title': 'Low Confidence',
        'confidence': 0.60,
        'type': 'pattern_based',
    })
    
    # Experimental suggestion
    suggestions.append({
        'id': 'experimental',
        'title': 'Experimental Suggestion',
        'confidence': 0.80,
        'type': 'anomaly_based',
    })
    
    # Blueprint opportunity
    suggestions.append({
        'id': 'blueprint_opp',
        'title': 'Blueprint Opportunity',
        'confidence': 0.85,
        'type': 'blueprint_opportunity',
        'source': 'Epic-AI-6',
    })
    
    return suggestions


@pytest.mark.asyncio
@pytest.mark.integration
async def test_conservative_filtering(sample_suggestions_mixed):
    """Test conservative creativity level filtering."""
    # Mock preference manager to return conservative
    with patch.object(PreferenceManager, 'get_creativity_level', return_value='conservative'):
        filter_service = CreativityFilter(user_id="test_user")
        
        filtered = await filter_service.filter_suggestions(sample_suggestions_mixed, apply_ranking=True)
        
        # Conservative should only keep high confidence (>= 0.85)
        assert len(filtered) <= len(sample_suggestions_mixed)
        
        # All filtered suggestions should meet min_confidence threshold
        config = CreativityConfig.CREATIVITY_CONFIG['conservative']
        for suggestion in filtered:
            assert suggestion['confidence'] >= config['min_confidence']
        
        # No experimental suggestions in conservative mode
        experimental_count = sum(
            1 for s in filtered
            if filter_service._is_experimental(s)
        )
        assert experimental_count == 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_balanced_filtering(sample_suggestions_mixed):
    """Test balanced creativity level filtering."""
    # Mock preference manager to return balanced
    with patch.object(PreferenceManager, 'get_creativity_level', return_value='balanced'):
        filter_service = CreativityFilter(user_id="test_user")
        
        filtered = await filter_service.filter_suggestions(sample_suggestions_mixed, apply_ranking=True)
        
        # Balanced should keep medium confidence and above (>= 0.70)
        config = CreativityConfig.CREATIVITY_CONFIG['balanced']
        for suggestion in filtered:
            assert suggestion['confidence'] >= config['min_confidence']
        
        # Should allow up to 2 experimental
        experimental_count = sum(
            1 for s in filtered
            if filter_service._is_experimental(s)
        )
        assert experimental_count <= config['max_experimental']


@pytest.mark.asyncio
@pytest.mark.integration
async def test_creative_filtering(sample_suggestions_mixed):
    """Test creative creativity level filtering."""
    # Mock preference manager to return creative
    with patch.object(PreferenceManager, 'get_creativity_level', return_value='creative'):
        filter_service = CreativityFilter(user_id="test_user")
        
        filtered = await filter_service.filter_suggestions(sample_suggestions_mixed, apply_ranking=True)
        
        # Creative should keep lower confidence (>= 0.55)
        config = CreativityConfig.CREATIVITY_CONFIG['creative']
        for suggestion in filtered:
            assert suggestion['confidence'] >= config['min_confidence']
        
        # Should allow up to 5 experimental
        experimental_count = sum(
            1 for s in filtered
            if filter_service._is_experimental(s)
        )
        assert experimental_count <= config['max_experimental']


@pytest.mark.asyncio
@pytest.mark.integration
async def test_blueprint_weight_boosting():
    """Test that blueprint-validated suggestions get boosted."""
    suggestions = [
        {
            'id': 'blueprint',
            'confidence': 0.75,
            'blueprint_validated': True,
            'type': 'pattern_based',
        },
        {
            'id': 'regular',
            'confidence': 0.75,
            'type': 'pattern_based',
        },
    ]
    
    with patch.object(PreferenceManager, 'get_creativity_level', return_value='balanced'):
        filter_service = CreativityFilter(user_id="test_user")
        
        filtered = await filter_service.filter_suggestions(suggestions, apply_ranking=True)
        
        # Blueprint suggestion should be ranked higher
        blueprint_idx = next(
            i for i, s in enumerate(filtered)
            if s['id'] == 'blueprint'
        )
        regular_idx = next(
            i for i, s in enumerate(filtered)
            if s['id'] == 'regular'
        )
        
        # Blueprint should come first (higher ranking score)
        assert blueprint_idx < regular_idx


@pytest.mark.asyncio
@pytest.mark.integration
async def test_experimental_limit_enforced():
    """Test that experimental suggestion limits are enforced."""
    # Create many experimental suggestions
    experimental_suggestions = [
        {
            'id': f'exp_{i}',
            'confidence': 0.80 - (i * 0.05),
            'type': 'anomaly_based',
        }
        for i in range(10)
    ]
    
    # Test balanced (max 2 experimental)
    with patch.object(PreferenceManager, 'get_creativity_level', return_value='balanced'):
        filter_service = CreativityFilter(user_id="test_user")
        
        filtered = await filter_service.filter_suggestions(experimental_suggestions, apply_ranking=True)
        
        config = CreativityConfig.CREATIVITY_CONFIG['balanced']
        experimental_count = sum(
            1 for s in filtered
            if filter_service._is_experimental(s)
        )
        assert experimental_count <= config['max_experimental']


@pytest.mark.asyncio
@pytest.mark.integration
async def test_confidence_threshold_filtering():
    """Test that confidence threshold filtering works correctly."""
    suggestions = [
        {'id': f'suggestion_{i}', 'confidence': 0.5 + (i * 0.05), 'type': 'pattern_based'}
        for i in range(10)
    ]
    
    # Test conservative (min 0.85)
    with patch.object(PreferenceManager, 'get_creativity_level', return_value='conservative'):
        filter_service = CreativityFilter(user_id="test_user")
        
        filtered = await filter_service.filter_suggestions(suggestions, apply_ranking=True)
        
        # Should only keep suggestions with confidence >= 0.85
        for suggestion in filtered:
            assert suggestion['confidence'] >= 0.85
        
        # Count how many should pass
        expected_count = sum(1 for s in suggestions if s['confidence'] >= 0.85)
        assert len(filtered) == expected_count


@pytest.mark.asyncio
@pytest.mark.integration
async def test_graceful_degradation_on_error(sample_suggestions_mixed):
    """Test that filtering gracefully degrades on errors."""
    # Simulate preference loading error
    with patch.object(PreferenceManager, 'get_creativity_level', side_effect=Exception("Database error")):
        filter_service = CreativityFilter(user_id="test_user")
        
        # Should return original suggestions on error
        filtered = await filter_service.filter_suggestions(sample_suggestions_mixed, apply_ranking=True)
        
        # Should return all original suggestions (graceful degradation)
        assert len(filtered) == len(sample_suggestions_mixed)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_ranking_preserves_order():
    """Test that suggestions are properly ranked after filtering."""
    suggestions = [
        {'id': 'low', 'confidence': 0.75, 'type': 'pattern_based'},
        {'id': 'high', 'confidence': 0.90, 'type': 'pattern_based'},
        {'id': 'medium', 'confidence': 0.80, 'type': 'pattern_based'},
    ]
    
    with patch.object(PreferenceManager, 'get_creativity_level', return_value='balanced'):
        filter_service = CreativityFilter(user_id="test_user")
        
        filtered = await filter_service.filter_suggestions(suggestions, apply_ranking=True)
        
        # Should be sorted by confidence (highest first)
        for i in range(len(filtered) - 1):
            assert filtered[i]['confidence'] >= filtered[i + 1]['confidence']


@pytest.mark.asyncio
@pytest.mark.integration
async def test_experimental_detection():
    """Test that experimental suggestion detection works correctly."""
    filter_service = CreativityFilter(user_id="test_user")
    
    # Test various experimental types
    experimental_suggestions = [
        {'type': 'anomaly_based', 'confidence': 0.80},
        {'type': 'experimental', 'confidence': 0.75},
        {'type': 'synergy_advanced', 'confidence': 0.85},
        {'source': 'ml_enhanced', 'confidence': 0.70},
        {'pattern_type': 'anomaly', 'confidence': 0.75},
    ]
    
    for suggestion in experimental_suggestions:
        assert filter_service._is_experimental(suggestion), f"Should detect {suggestion} as experimental"
    
    # Test non-experimental
    non_experimental = [
        {'type': 'pattern_based', 'confidence': 0.80},
        {'type': 'feature_based', 'confidence': 0.75},
        {'type': 'blueprint_opportunity', 'confidence': 0.85},
    ]
    
    for suggestion in non_experimental:
        assert not filter_service._is_experimental(suggestion), f"Should NOT detect {suggestion} as experimental"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_phase5_integration_with_creativity():
    """Test that Phase 5 applies creativity filtering correctly."""
    # This is a simulation test - actual Phase 5 integration tested separately
    suggestions = [
        {
            'id': f'suggestion_{i}',
            'confidence': 0.5 + (i * 0.03),
            'type': 'pattern_based' if i % 2 == 0 else 'feature_based',
        }
        for i in range(20)
    ]
    
    with patch.object(PreferenceManager, 'get_creativity_level', return_value='balanced'):
        filter_service = CreativityFilter(user_id="default")
        
        filtered = await filter_service.filter_suggestions(suggestions, apply_ranking=True)
        
        # Should filter by confidence threshold
        config = CreativityConfig.CREATIVITY_CONFIG['balanced']
        for suggestion in filtered:
            assert suggestion['confidence'] >= config['min_confidence']


@pytest.mark.asyncio
@pytest.mark.integration
async def test_ask_ai_integration_with_creativity():
    """Test that Ask AI applies creativity filtering correctly."""
    # Simulate Ask AI suggestions with blueprint opportunities
    suggestions = [
        {
            'id': 'query_suggestion_1',
            'confidence': 0.75,
            'type': 'pattern_based',
        },
        {
            'id': 'blueprint_1',
            'confidence': 0.80,
            'type': 'blueprint_opportunity',
            'source': 'Epic-AI-6',
        },
        {
            'id': 'experimental_1',
            'confidence': 0.70,
            'type': 'anomaly_based',
        },
    ]
    
    with patch.object(PreferenceManager, 'get_creativity_level', return_value='balanced'):
        filter_service = CreativityFilter(user_id="test_user")
        
        filtered = await filter_service.filter_suggestions(suggestions, apply_ranking=True)
        
        # All should pass balanced threshold (>= 0.70)
        config = CreativityConfig.CREATIVITY_CONFIG['balanced']
        for suggestion in filtered:
            assert suggestion['confidence'] >= config['min_confidence']
        
        # Experimental should be limited
        experimental_count = sum(
            1 for s in filtered
            if filter_service._is_experimental(s)
        )
        assert experimental_count <= config['max_experimental']
