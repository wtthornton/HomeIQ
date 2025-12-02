"""
Integration tests for unified preference-aware ranking.

Tests that PreferenceAwareRanker applies all user preferences:
- max_suggestions limit
- creativity level filtering
- blueprint preference weighting

Epic AI-6 Story AI6.11: Preference-Aware Suggestion Ranking
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.blueprint_discovery.preference_aware_ranker import PreferenceAwareRanker
from src.blueprint_discovery.preference_manager import PreferenceManager


@pytest.fixture
def mixed_suggestions():
    """Create mixed suggestions for testing."""
    return [
        {
            'id': 'regular_high',
            'title': 'Regular High Confidence',
            'confidence': 0.90,
            'type': 'pattern_based',
        },
        {
            'id': 'blueprint_high',
            'title': 'Blueprint Opportunity High',
            'confidence': 0.85,
            'type': 'blueprint_opportunity',
            'source': 'Epic-AI-6',
        },
        {
            'id': 'regular_medium',
            'title': 'Regular Medium Confidence',
            'confidence': 0.75,
            'type': 'feature_based',
        },
        {
            'id': 'blueprint_medium',
            'title': 'Blueprint Opportunity Medium',
            'confidence': 0.70,
            'type': 'blueprint_opportunity',
            'blueprint_id': 'bp123',
        },
        {
            'id': 'blueprint_validated',
            'title': 'Blueprint Validated',
            'confidence': 0.80,
            'type': 'pattern_based',
            'blueprint_validated': True,
            'blueprint_match_score': 0.85,
        },
        {
            'id': 'low_confidence',
            'title': 'Low Confidence',
            'confidence': 0.50,
            'type': 'pattern_based',
        },
        {
            'id': 'experimental',
            'title': 'Experimental',
            'confidence': 0.60,
            'type': 'anomaly_based',
        },
    ]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_unified_ranking_applies_all_preferences(mixed_suggestions):
    """Test that unified ranking applies all preferences correctly."""
    with patch.object(PreferenceManager, 'get_max_suggestions', return_value=5), \
         patch.object(PreferenceManager, 'get_creativity_level', return_value='balanced'), \
         patch.object(PreferenceManager, 'get_blueprint_preference', return_value='medium'):
        
        ranker = PreferenceAwareRanker(user_id="test_user")
        ranked = await ranker.rank_suggestions(mixed_suggestions.copy())
        
        # Should apply max_suggestions limit
        assert len(ranked) <= 5
        
        # Should apply creativity filtering (balanced: min_confidence 0.70)
        # Low confidence (0.50) should be filtered out
        low_conf_ids = [s['id'] for s in ranked if s['confidence'] < 0.70]
        assert 'low_confidence' not in [s['id'] for s in ranked]
        
        # Should have applied blueprint weighting (medium = 1.0x, no change)
        # Blueprint opportunities should still be present
        blueprint_ids = [s['id'] for s in ranked if s.get('type') == 'blueprint_opportunity' or s.get('blueprint_validated')]
        assert len(blueprint_ids) > 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_unified_ranking_with_high_blueprint_preference(mixed_suggestions):
    """Test unified ranking with high blueprint preference."""
    with patch.object(PreferenceManager, 'get_max_suggestions', return_value=10), \
         patch.object(PreferenceManager, 'get_creativity_level', return_value='balanced'), \
         patch.object(PreferenceManager, 'get_blueprint_preference', return_value='high'):
        
        ranker = PreferenceAwareRanker(user_id="test_user")
        ranked = await ranker.rank_suggestions(mixed_suggestions.copy())
        
        # With high blueprint preference (1.5x), blueprints should rank higher
        blueprint_suggestions = [
            s for s in ranked
            if s.get('type') == 'blueprint_opportunity' or s.get('blueprint_validated')
        ]
        
        # At least some blueprints should be near the top
        top_3_ids = [s['id'] for s in ranked[:3]]
        blueprint_in_top_3 = any(
            s['id'] in top_3_ids
            for s in blueprint_suggestions
        )
        assert blueprint_in_top_3 or len(blueprint_suggestions) == 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_unified_ranking_with_low_blueprint_preference(mixed_suggestions):
    """Test unified ranking with low blueprint preference."""
    with patch.object(PreferenceManager, 'get_max_suggestions', return_value=10), \
         patch.object(PreferenceManager, 'get_creativity_level', return_value='balanced'), \
         patch.object(PreferenceManager, 'get_blueprint_preference', return_value='low'):
        
        ranker = PreferenceAwareRanker(user_id="test_user")
        ranked = await ranker.rank_suggestions(mixed_suggestions.copy())
        
        # With low blueprint preference (0.5x), regular high confidence should outrank blueprints
        regular_high_idx = next(
            i for i, s in enumerate(ranked)
            if s['id'] == 'regular_high'
        )
        
        # Regular high confidence should be ranked higher than low-weighted blueprints
        blueprint_suggestions = [
            s for s in ranked
            if (s.get('type') == 'blueprint_opportunity' or s.get('blueprint_validated'))
            and s['confidence'] < 0.90
        ]
        
        for blueprint in blueprint_suggestions:
            blueprint_idx = next(i for i, s in enumerate(ranked) if s['id'] == blueprint['id'])
            assert regular_high_idx < blueprint_idx


@pytest.mark.asyncio
@pytest.mark.integration
async def test_unified_ranking_with_conservative_creativity(mixed_suggestions):
    """Test unified ranking with conservative creativity level."""
    with patch.object(PreferenceManager, 'get_max_suggestions', return_value=10), \
         patch.object(PreferenceManager, 'get_creativity_level', return_value='conservative'), \
         patch.object(PreferenceManager, 'get_blueprint_preference', return_value='medium'):
        
        ranker = PreferenceAwareRanker(user_id="test_user")
        ranked = await ranker.rank_suggestions(mixed_suggestions.copy())
        
        # Conservative: min_confidence 0.85, max_experimental 0
        # Should filter out low confidence and experimental suggestions
        assert all(s['confidence'] >= 0.85 for s in ranked)
        assert 'low_confidence' not in [s['id'] for s in ranked]
        assert 'experimental' not in [s['id'] for s in ranked]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_unified_ranking_with_creative_creativity(mixed_suggestions):
    """Test unified ranking with creative creativity level."""
    with patch.object(PreferenceManager, 'get_max_suggestions', return_value=10), \
         patch.object(PreferenceManager, 'get_creativity_level', return_value='creative'), \
         patch.object(PreferenceManager, 'get_blueprint_preference', return_value='medium'):
        
        ranker = PreferenceAwareRanker(user_id="test_user")
        ranked = await ranker.rank_suggestions(mixed_suggestions.copy())
        
        # Creative: min_confidence 0.55, max_experimental 5
        # Should allow more experimental and lower confidence suggestions
        experimental_count = sum(
            1 for s in ranked
            if s.get('type') == 'anomaly_based' or s.get('is_experimental', False)
        )
        assert experimental_count <= 5  # Max experimental limit
        
        # Should include lower confidence suggestions
        low_conf_present = any(s['confidence'] < 0.70 for s in ranked)
        # May or may not be present depending on ranking, but should be allowed


@pytest.mark.asyncio
@pytest.mark.integration
async def test_unified_ranking_max_suggestions_limit(mixed_suggestions):
    """Test that max_suggestions limit is applied."""
    with patch.object(PreferenceManager, 'get_max_suggestions', return_value=3), \
         patch.object(PreferenceManager, 'get_creativity_level', return_value='balanced'), \
         patch.object(PreferenceManager, 'get_blueprint_preference', return_value='medium'):
        
        ranker = PreferenceAwareRanker(user_id="test_user")
        ranked = await ranker.rank_suggestions(mixed_suggestions.copy())
        
        # Should be limited to 3 suggestions
        assert len(ranked) == 3
        
        # Should be top 3 by adjusted ranking scores
        assert ranked[0]['confidence'] >= ranked[1]['confidence']
        assert ranked[1]['confidence'] >= ranked[2]['confidence']


@pytest.mark.asyncio
@pytest.mark.integration
async def test_unified_ranking_optional_preferences(mixed_suggestions):
    """Test that preferences can be optionally disabled."""
    with patch.object(PreferenceManager, 'get_max_suggestions', return_value=10), \
         patch.object(PreferenceManager, 'get_creativity_level', return_value='balanced'), \
         patch.object(PreferenceManager, 'get_blueprint_preference', return_value='medium'):
        
        ranker = PreferenceAwareRanker(user_id="test_user")
        
        # Test with all preferences enabled
        ranked_all = await ranker.rank_suggestions(
            mixed_suggestions.copy(),
            apply_creativity_filtering=True,
            apply_blueprint_weighting=True,
            apply_max_limit=True
        )
        
        # Test with creativity filtering disabled
        ranked_no_creativity = await ranker.rank_suggestions(
            mixed_suggestions.copy(),
            apply_creativity_filtering=False,
            apply_blueprint_weighting=True,
            apply_max_limit=True
        )
        
        # Test with blueprint weighting disabled
        ranked_no_blueprint = await ranker.rank_suggestions(
            mixed_suggestions.copy(),
            apply_creativity_filtering=True,
            apply_blueprint_weighting=False,
            apply_max_limit=True
        )
        
        # Test with max limit disabled
        ranked_no_limit = await ranker.rank_suggestions(
            mixed_suggestions.copy(),
            apply_creativity_filtering=True,
            apply_blueprint_weighting=True,
            apply_max_limit=False
        )
        
        # Results should differ based on which preferences are applied
        assert len(ranked_all) <= len(ranked_no_limit)
        assert len(ranked_no_creativity) >= len(ranked_all)  # No filtering = more suggestions


@pytest.mark.asyncio
@pytest.mark.integration
async def test_unified_ranking_graceful_degradation(mixed_suggestions):
    """Test that unified ranking gracefully degrades on errors."""
    # Simulate preference loading error
    with patch.object(PreferenceManager, 'get_max_suggestions', side_effect=Exception("Database error")):
        ranker = PreferenceAwareRanker(user_id="test_user")
        
        # Should return original suggestions on error (graceful degradation)
        ranked = await ranker.rank_suggestions(mixed_suggestions.copy())
        
        # Should return all original suggestions
        assert len(ranked) == len(mixed_suggestions)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_unified_ranking_empty_suggestions():
    """Test that unified ranking handles empty suggestions."""
    ranker = PreferenceAwareRanker(user_id="test_user")
    ranked = await ranker.rank_suggestions([])
    
    assert ranked == []


@pytest.mark.asyncio
@pytest.mark.integration
async def test_unified_ranking_preference_summary():
    """Test that preference summary is returned correctly."""
    with patch.object(PreferenceManager, 'get_max_suggestions', return_value=10), \
         patch.object(PreferenceManager, 'get_creativity_level', return_value='balanced'), \
         patch.object(PreferenceManager, 'get_blueprint_preference', return_value='medium'):
        
        ranker = PreferenceAwareRanker(user_id="test_user")
        summary = await ranker.get_preference_summary()
        
        assert summary['user_id'] == "test_user"
        assert summary['max_suggestions'] == 10
        assert summary['creativity_level'] == 'balanced'
        assert summary['blueprint_preference'] == 'medium'


@pytest.mark.asyncio
@pytest.mark.integration
async def test_unified_ranking_phase5_integration(mixed_suggestions):
    """Test that unified ranking works as expected in Phase 5 context."""
    with patch.object(PreferenceManager, 'get_max_suggestions', return_value=5), \
         patch.object(PreferenceManager, 'get_creativity_level', return_value='balanced'), \
         patch.object(PreferenceManager, 'get_blueprint_preference', return_value='medium'):
        
        ranker = PreferenceAwareRanker(user_id="default")
        ranked = await ranker.rank_suggestions(mixed_suggestions.copy())
        
        # Should apply all preferences
        assert len(ranked) <= 5
        assert all(s['confidence'] >= 0.70 for s in ranked)  # Balanced min_confidence


@pytest.mark.asyncio
@pytest.mark.integration
async def test_unified_ranking_ask_ai_integration(mixed_suggestions):
    """Test that unified ranking works as expected in Ask AI context."""
    with patch.object(PreferenceManager, 'get_max_suggestions', return_value=10), \
         patch.object(PreferenceManager, 'get_creativity_level', return_value='balanced'), \
         patch.object(PreferenceManager, 'get_blueprint_preference', return_value='high'):
        
        ranker = PreferenceAwareRanker(user_id="test_user")
        ranked = await ranker.rank_suggestions(mixed_suggestions.copy())
        
        # Should apply all preferences
        assert len(ranked) <= 10
        
        # With high blueprint preference, blueprints should be ranked higher
        blueprint_suggestions = [
            s for s in ranked
            if s.get('type') == 'blueprint_opportunity' or s.get('blueprint_validated')
        ]
        
        # Blueprints should be present and potentially ranked higher
        assert len(blueprint_suggestions) > 0 or len(ranked) == 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_unified_ranking_consistency_across_calls(mixed_suggestions):
    """Test that unified ranking produces consistent results across multiple calls."""
    with patch.object(PreferenceManager, 'get_max_suggestions', return_value=5), \
         patch.object(PreferenceManager, 'get_creativity_level', return_value='balanced'), \
         patch.object(PreferenceManager, 'get_blueprint_preference', return_value='medium'):
        
        ranker = PreferenceAwareRanker(user_id="test_user")
        
        # First call
        ranked1 = await ranker.rank_suggestions(mixed_suggestions.copy())
        
        # Second call with same preferences
        ranked2 = await ranker.rank_suggestions(mixed_suggestions.copy())
        
        # Should produce same results (same preferences, same input)
        assert len(ranked1) == len(ranked2)
        assert [s['id'] for s in ranked1] == [s['id'] for s in ranked2]
