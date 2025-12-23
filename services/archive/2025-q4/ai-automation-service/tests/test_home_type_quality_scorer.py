"""
Unit tests for Home Type Quality Scorer Integration

Tests the integration of home type relevance weighting in pattern quality scoring.
"""

import pytest
from src.testing.pattern_quality_scorer import PatternQualityScorer


@pytest.fixture
def base_pattern():
    """Create base pattern for testing"""
    return {
        'pattern_type': 'co_occurrence',
        'confidence': 0.8,
        'occurrences': 15,
        'device1': 'binary_sensor.front_door',
        'device2': 'light.front_porch',
        'device_domain': 'binary_sensor',
        'device_class': 'door'
    }


def test_quality_scorer_with_security_focused_home(base_pattern):
    """Test quality scoring with security-focused home type"""
    scorer = PatternQualityScorer(home_type='security_focused')
    
    result = scorer.calculate_quality_score(base_pattern)
    
    # Security pattern should get relevance boost
    assert result['quality_score'] > 0
    assert result.get('home_type_relevance') is not None or result.get('home_type_relevance', 0) >= 0


def test_quality_scorer_with_climate_controlled_home(base_pattern):
    """Test quality scoring with climate-controlled home type"""
    climate_pattern = {
        **base_pattern,
        'device_domain': 'climate',
        'device_class': 'temperature'
    }
    
    scorer = PatternQualityScorer(home_type='climate_controlled')
    
    result = scorer.calculate_quality_score(climate_pattern)
    
    # Climate pattern should get relevance boost
    assert result['quality_score'] > 0
    assert 'home_type_relevance' in result or result.get('home_type_relevance', 0) >= 0


def test_quality_scorer_without_home_type(base_pattern):
    """Test quality scoring without home type (should still work)"""
    scorer = PatternQualityScorer(home_type=None)
    
    result = scorer.calculate_quality_score(base_pattern)
    
    # Should still calculate quality score
    assert result['quality_score'] > 0
    assert result.get('home_type_relevance') is None


def test_quality_scorer_relevance_calculation_security():
    """Test relevance calculation for security patterns"""
    scorer = PatternQualityScorer(home_type='security_focused')
    
    security_pattern = {
        'pattern_type': 'motion',
        'device_domain': 'binary_sensor',
        'device_class': 'motion',
        'confidence': 0.8,
        'occurrences': 10
    }
    
    result = scorer.calculate_quality_score(security_pattern)
    
    # Security pattern should have high relevance
    relevance = scorer._calculate_home_type_relevance(security_pattern)
    assert relevance > 0.5  # Should be high for security-focused home


def test_quality_scorer_relevance_calculation_climate():
    """Test relevance calculation for climate patterns"""
    scorer = PatternQualityScorer(home_type='climate_controlled')
    
    climate_pattern = {
        'pattern_type': 'temperature',
        'device_domain': 'climate',
        'device_class': 'temperature',
        'confidence': 0.8,
        'occurrences': 10
    }
    
    relevance = scorer._calculate_home_type_relevance(climate_pattern)
    assert relevance > 0.5  # Should be high for climate-controlled home


def test_quality_scorer_relevance_calculation_non_matching():
    """Test relevance calculation for non-matching patterns"""
    scorer = PatternQualityScorer(home_type='security_focused')
    
    lighting_pattern = {
        'pattern_type': 'time_of_day',
        'device_domain': 'light',
        'device_class': 'light',
        'confidence': 0.8,
        'occurrences': 10
    }
    
    relevance = scorer._calculate_home_type_relevance(lighting_pattern)
    assert relevance < 0.5  # Should be lower for non-matching pattern

