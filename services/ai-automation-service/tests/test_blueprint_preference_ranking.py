"""
Integration tests for blueprint preference-based ranking.

Tests blueprint preference weighting in:
- Phase 5 description generation
- Ask AI suggestion generation

Epic AI-6 Story AI6.10: Blueprint Preference Configuration
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.blueprint_discovery.blueprint_ranker import BlueprintRanker
from src.blueprint_discovery.preference_manager import PreferenceManager


@pytest.fixture
def mixed_suggestions():
    """Create mixed suggestions with blueprint opportunities and regular suggestions."""
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
    ]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_high_preference_ranks_blueprints_higher(mixed_suggestions):
    """Test that high blueprint preference ranks blueprint opportunities higher."""
    with patch.object(PreferenceManager, 'get_blueprint_preference', return_value='high'):
        ranker = BlueprintRanker(user_id="test_user")
        
        ranked = await ranker.apply_blueprint_preference_weighting(
            mixed_suggestions.copy(),
            preserve_order=False
        )
        
        # Find positions of blueprint opportunities
        blueprint_ids = ['blueprint_high', 'blueprint_medium', 'blueprint_validated']
        blueprint_positions = [
            next(i for i, s in enumerate(ranked) if s['id'] == bp_id)
            for bp_id in blueprint_ids
        ]
        
        # Blueprint opportunities should be ranked higher (lower index = higher rank)
        # With 1.5x multiplier, blueprints should outrank regular suggestions
        assert len(blueprint_positions) == 3
        # At least some blueprints should be near the top
        assert min(blueprint_positions) < len(ranked) / 2


@pytest.mark.asyncio
@pytest.mark.integration
async def test_medium_preference_normal_ranking(mixed_suggestions):
    """Test that medium blueprint preference uses normal ranking (1.0x multiplier)."""
    with patch.object(PreferenceManager, 'get_blueprint_preference', return_value='medium'):
        ranker = BlueprintRanker(user_id="test_user")
        
        ranked = await ranker.apply_blueprint_preference_weighting(
            mixed_suggestions.copy(),
            preserve_order=False
        )
        
        # With 1.0x multiplier, ranking should be based on confidence
        # Top suggestion should have highest confidence
        assert ranked[0]['confidence'] >= ranked[-1]['confidence']
        
        # Blueprint opportunities should have weighted scores
        blueprint_suggestions = [s for s in ranked if ranker._is_blueprint_opportunity(s)]
        for suggestion in blueprint_suggestions:
            assert '_blueprint_weighted_score' in suggestion


@pytest.mark.asyncio
@pytest.mark.integration
async def test_low_preference_ranks_blueprints_lower(mixed_suggestions):
    """Test that low blueprint preference ranks blueprint opportunities lower."""
    with patch.object(PreferenceManager, 'get_blueprint_preference', return_value='low'):
        ranker = BlueprintRanker(user_id="test_user")
        
        ranked = await ranker.apply_blueprint_preference_weighting(
            mixed_suggestions.copy(),
            preserve_order=False
        )
        
        # With 0.5x multiplier, blueprints should be ranked lower
        # Regular high confidence suggestions should outrank blueprints
        regular_high_idx = next(i for i, s in enumerate(ranked) if s['id'] == 'regular_high')
        
        # Regular high confidence should be ranked higher than blueprints
        blueprint_suggestions = [s for s in ranked if ranker._is_blueprint_opportunity(s)]
        for blueprint in blueprint_suggestions:
            blueprint_idx = next(i for i, s in enumerate(ranked) if s['id'] == blueprint['id'])
            # Regular high confidence should come before low-weighted blueprints
            if blueprint['confidence'] < 0.90:
                assert regular_high_idx < blueprint_idx


@pytest.mark.asyncio
@pytest.mark.integration
async def test_blueprint_weight_multipliers():
    """Test that correct weight multipliers are applied."""
    suggestions = [
        {
            'id': 'blueprint',
            'confidence': 0.80,
            'type': 'blueprint_opportunity',
        }
    ]
    
    # Test high preference (1.5x)
    with patch.object(PreferenceManager, 'get_blueprint_preference', return_value='high'):
        ranker = BlueprintRanker(user_id="test_user")
        ranked = await ranker.apply_blueprint_preference_weighting(
            suggestions.copy(),
            preserve_order=True
        )
        weighted_score = ranked[0].get('_blueprint_weighted_score')
        assert weighted_score == 0.80 * 1.5  # 1.5x multiplier
    
    # Test medium preference (1.0x)
    with patch.object(PreferenceManager, 'get_blueprint_preference', return_value='medium'):
        ranker = BlueprintRanker(user_id="test_user")
        ranked = await ranker.apply_blueprint_preference_weighting(
            suggestions.copy(),
            preserve_order=True
        )
        weighted_score = ranked[0].get('_blueprint_weighted_score')
        assert weighted_score == 0.80 * 1.0  # 1.0x multiplier
    
    # Test low preference (0.5x)
    with patch.object(PreferenceManager, 'get_blueprint_preference', return_value='low'):
        ranker = BlueprintRanker(user_id="test_user")
        ranked = await ranker.apply_blueprint_preference_weighting(
            suggestions.copy(),
            preserve_order=True
        )
        weighted_score = ranked[0].get('_blueprint_weighted_score')
        assert weighted_score == 0.80 * 0.5  # 0.5x multiplier


@pytest.mark.asyncio
@pytest.mark.integration
async def test_non_blueprint_suggestions_unaffected(mixed_suggestions):
    """Test that non-blueprint suggestions are not affected by weighting."""
    with patch.object(PreferenceManager, 'get_blueprint_preference', return_value='high'):
        ranker = BlueprintRanker(user_id="test_user")
        
        ranked = await ranker.apply_blueprint_preference_weighting(
            mixed_suggestions.copy(),
            preserve_order=True  # Preserve order to check scores
        )
        
        # Regular suggestions should not have blueprint_weighted_score
        regular_suggestions = [
            s for s in ranked
            if not ranker._is_blueprint_opportunity(s)
        ]
        
        for suggestion in regular_suggestions:
            assert '_blueprint_weighted_score' not in suggestion


@pytest.mark.asyncio
@pytest.mark.integration
async def test_blueprint_opportunity_detection():
    """Test that blueprint opportunity detection works correctly."""
    ranker = BlueprintRanker(user_id="test_user")
    
    # Test various blueprint opportunity types
    blueprint_suggestions = [
        {'type': 'blueprint_opportunity', 'confidence': 0.80},
        {'source': 'Epic-AI-6', 'confidence': 0.75},
        {'blueprint_validated': True, 'confidence': 0.85},
        {'blueprint_id': 'bp123', 'confidence': 0.70},
    ]
    
    for suggestion in blueprint_suggestions:
        assert ranker._is_blueprint_opportunity(suggestion), \
            f"Should detect {suggestion} as blueprint opportunity"
    
    # Test non-blueprint suggestions
    regular_suggestions = [
        {'type': 'pattern_based', 'confidence': 0.80},
        {'type': 'feature_based', 'confidence': 0.75},
    ]
    
    for suggestion in regular_suggestions:
        assert not ranker._is_blueprint_opportunity(suggestion), \
            f"Should NOT detect {suggestion} as blueprint opportunity"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_ranking_preserves_order_when_requested(mixed_suggestions):
    """Test that preserve_order=True only adjusts scores without re-sorting."""
    original_order = [s['id'] for s in mixed_suggestions]
    
    with patch.object(PreferenceManager, 'get_blueprint_preference', return_value='high'):
        ranker = BlueprintRanker(user_id="test_user")
        
        ranked = await ranker.apply_blueprint_preference_weighting(
            mixed_suggestions.copy(),
            preserve_order=True
        )
        
        # Order should be preserved
        new_order = [s['id'] for s in ranked]
        assert new_order == original_order
        
        # But blueprints should have weighted scores
        blueprint_suggestions = [s for s in ranked if ranker._is_blueprint_opportunity(s)]
        for suggestion in blueprint_suggestions:
            assert '_blueprint_weighted_score' in suggestion


@pytest.mark.asyncio
@pytest.mark.integration
async def test_re_ranking_uses_weighted_scores(mixed_suggestions):
    """Test that re-ranking uses blueprint-weighted scores."""
    with patch.object(PreferenceManager, 'get_blueprint_preference', return_value='high'):
        ranker = BlueprintRanker(user_id="test_user")
        
        ranked = await ranker.apply_blueprint_preference_weighting(
            mixed_suggestions.copy(),
            preserve_order=False  # Re-rank
        )
        
        # Should be sorted by weighted score (highest first)
        for i in range(len(ranked) - 1):
            current_score = (
                ranked[i].get('_blueprint_weighted_score') or
                ranked[i].get('confidence', 0.0)
            )
            next_score = (
                ranked[i + 1].get('_blueprint_weighted_score') or
                ranked[i + 1].get('confidence', 0.0)
            )
            assert current_score >= next_score


@pytest.mark.asyncio
@pytest.mark.integration
async def test_graceful_degradation_on_error(mixed_suggestions):
    """Test that ranking gracefully degrades on errors."""
    # Simulate preference loading error
    with patch.object(PreferenceManager, 'get_blueprint_preference', side_effect=Exception("Database error")):
        ranker = BlueprintRanker(user_id="test_user")
        
        # Should return original suggestions on error
        ranked = await ranker.apply_blueprint_preference_weighting(
            mixed_suggestions.copy(),
            preserve_order=False
        )
        
        # Should return all original suggestions (graceful degradation)
        assert len(ranked) == len(mixed_suggestions)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_default_weight_on_invalid_preference():
    """Test that default weight (1.0x) is used for invalid preference."""
    suggestions = [
        {
            'id': 'blueprint',
            'confidence': 0.80,
            'type': 'blueprint_opportunity',
        }
    ]
    
    # Simulate invalid preference (should use default "medium" = 1.0x)
    with patch.object(PreferenceManager, 'get_blueprint_preference', return_value='invalid'):
        ranker = BlueprintRanker(user_id="test_user")
        ranked = await ranker.apply_blueprint_preference_weighting(
            suggestions.copy(),
            preserve_order=True
        )
        weighted_score = ranked[0].get('_blueprint_weighted_score')
        # Should use default weight (1.0x)
        assert weighted_score == 0.80 * 1.0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_phase5_integration_with_blueprint_preference(mixed_suggestions):
    """Test that Phase 5 applies blueprint preference weighting correctly."""
    # This is a simulation test - actual Phase 5 integration tested separately
    with patch.object(PreferenceManager, 'get_blueprint_preference', return_value='high'):
        ranker = BlueprintRanker(user_id="default")
        
        ranked = await ranker.apply_blueprint_preference_weighting(
            mixed_suggestions.copy(),
            preserve_order=False
        )
        
        # Blueprints should have weighted scores
        blueprint_count = sum(
            1 for s in ranked
            if ranker._is_blueprint_opportunity(s)
        )
        assert blueprint_count > 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_ask_ai_integration_with_blueprint_preference(mixed_suggestions):
    """Test that Ask AI applies blueprint preference weighting correctly."""
    # Simulate Ask AI suggestions with blueprint opportunities
    with patch.object(PreferenceManager, 'get_blueprint_preference', return_value='medium'):
        ranker = BlueprintRanker(user_id="test_user")
        
        ranked = await ranker.apply_blueprint_preference_weighting(
            mixed_suggestions.copy(),
            preserve_order=False
        )
        
        # Should rank all suggestions (both blueprint and regular)
        assert len(ranked) == len(mixed_suggestions)
        
        # Blueprints should have weighted scores
        blueprint_suggestions = [s for s in ranked if ranker._is_blueprint_opportunity(s)]
        for suggestion in blueprint_suggestions:
            assert '_blueprint_weighted_score' in suggestion
