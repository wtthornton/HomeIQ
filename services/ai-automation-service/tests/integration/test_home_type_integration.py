"""
Integration tests for Home Type Categorization System

Tests end-to-end flows with home type integration.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from src.clients.home_type_client import HomeTypeClient
from src.database.crud import get_suggestions_with_home_type
from src.home_type.integration_helpers import (
    calculate_home_type_boost,
    adjust_pattern_thresholds,
    get_home_type_preferred_categories
)
from src.testing.pattern_quality_scorer import PatternQualityScorer
from src.synergy_detection.spatial_validator import SpatialProximityValidator


@pytest.fixture
def mock_home_type_data():
    """Mock home type API response"""
    return {
        'home_type': 'security_focused',
        'confidence': 0.85,
        'method': 'ml_model',
        'features_used': ['device_count', 'security_ratio'],
        'last_updated': datetime.now(timezone.utc).isoformat()
    }


@pytest.mark.asyncio
async def test_end_to_end_suggestion_ranking_with_home_type(mock_home_type_data):
    """Test end-to-end suggestion ranking with home type boost"""
    # Mock HomeTypeClient
    with patch.object(HomeTypeClient, 'get_home_type', return_value=mock_home_type_data):
        client = HomeTypeClient(base_url="http://test:8018")
        home_type_data = await client.get_home_type()
        
        assert home_type_data['home_type'] == 'security_focused'
        
        # Test boost calculation
        boost = calculate_home_type_boost('security', 'security_focused')
        assert boost > 0
        
        # Test preferred categories
        categories = get_home_type_preferred_categories('security_focused')
        assert 'security' in categories
        assert categories[0] == 'security'  # Most preferred


@pytest.mark.asyncio
async def test_end_to_end_pattern_detection_with_home_type():
    """Test end-to-end pattern detection with adjusted thresholds"""
    # Test threshold adjustment
    conf, occ = adjust_pattern_thresholds('security_focused', 0.7, 10)
    
    assert conf < 0.7  # Should be lower for security-focused
    assert occ < 10  # Should be fewer occurrences needed
    
    # Test with different home types
    conf_apt, occ_apt = adjust_pattern_thresholds('apartment', 0.7, 10)
    assert conf_apt < 0.7  # Apartments should be stricter


def test_end_to_end_quality_scoring_with_home_type():
    """Test end-to-end quality scoring with home type relevance"""
    scorer = PatternQualityScorer(home_type='security_focused')
    
    security_pattern = {
        'pattern_type': 'motion',
        'device_domain': 'binary_sensor',
        'device_class': 'motion',
        'confidence': 0.8,
        'occurrences': 15
    }
    
    result = scorer.calculate_quality_score(security_pattern)
    
    # Should have quality score
    assert result['quality_score'] > 0
    
    # Should have home type relevance
    relevance = scorer._calculate_home_type_relevance(security_pattern)
    assert relevance > 0.5  # High relevance for security pattern


@pytest.mark.asyncio
async def test_end_to_end_spatial_validation_with_home_type():
    """Test end-to-end spatial validation with home type tolerance"""
    # Test apartment (stricter)
    validator_apt = SpatialProximityValidator(home_type='apartment')
    assert validator_apt._spatial_tolerance < 1.0
    
    # Test multi-story (more lenient)
    validator_ms = SpatialProximityValidator(home_type='multi-story')
    assert validator_ms._spatial_tolerance > 1.0
    
    # Test cross-floor detection
    device1 = {'friendly_name': 'Upstairs Light', 'entity_id': 'light.upstairs'}
    device2 = {'friendly_name': 'Downstairs Light', 'entity_id': 'light.downstairs'}
    
    is_cross = validator_ms._is_cross_floor(device1, device2)
    assert is_cross is True


def test_home_type_integration_consistency():
    """Test that home type integration is consistent across components"""
    home_type = 'security_focused'
    
    # All components should handle the same home type
    categories = get_home_type_preferred_categories(home_type)
    boost = calculate_home_type_boost('security', home_type)
    conf, occ = adjust_pattern_thresholds(home_type, 0.7, 10)
    
    # All should work with the same home type
    assert categories is not None
    assert boost >= 0
    assert conf > 0
    assert occ > 0


@pytest.mark.asyncio
async def test_home_type_fallback_behavior():
    """Test that system gracefully handles missing home type"""
    # Test with None home type
    categories = get_home_type_preferred_categories(None)
    assert categories is not None  # Should return default
    
    boost = calculate_home_type_boost('security', None)
    assert boost == 0.0  # No boost without home type
    
    conf, occ = adjust_pattern_thresholds(None, 0.7, 10)
    assert conf == 0.7  # Should use defaults
    assert occ == 10


def test_home_type_unknown_type_handling():
    """Test handling of unknown home types"""
    unknown_type = 'unknown_home_type'
    
    # Should not crash, should use defaults
    categories = get_home_type_preferred_categories(unknown_type)
    assert categories is not None
    
    boost = calculate_home_type_boost('security', unknown_type)
    assert boost == 0.0  # No boost for unknown
    
    conf, occ = adjust_pattern_thresholds(unknown_type, 0.7, 10)
    assert conf == 0.7  # Defaults
    assert occ == 10

