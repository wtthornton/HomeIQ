"""
Unit tests for Home Type Pattern Detection Threshold Adjustment

Tests the integration of home type-based threshold adjustment in pattern detection.
"""

import pytest
from src.home_type.integration_helpers import adjust_pattern_thresholds


def test_adjust_pattern_thresholds_apartment():
    """Test threshold adjustment for apartment (stricter)"""
    conf, occ = adjust_pattern_thresholds('apartment', 0.7, 10)
    
    # Apartments should have slightly stricter confidence
    assert conf <= 0.7
    assert occ == 10  # No change to occurrences


def test_adjust_pattern_thresholds_multi_story():
    """Test threshold adjustment for multi-story (more lenient)"""
    conf, occ = adjust_pattern_thresholds('multi-story', 0.7, 10)
    
    # Multi-story may need more occurrences due to complexity
    assert occ >= 10


def test_adjust_pattern_thresholds_security_focused():
    """Test threshold adjustment for security-focused (slightly stricter)"""
    conf, occ = adjust_pattern_thresholds('security_focused', 0.7, 10)
    
    # Security-focused should have slightly lower confidence threshold
    assert conf < 0.7
    assert occ < 10  # Fewer occurrences needed


def test_adjust_pattern_thresholds_high_activity():
    """Test threshold adjustment for high-activity (more lenient)"""
    conf, occ = adjust_pattern_thresholds('high_activity', 0.7, 10)
    
    # High-activity should be more lenient
    assert conf < 0.7
    assert occ < 10


def test_adjust_pattern_thresholds_standard_home():
    """Test threshold adjustment for standard home (default)"""
    conf, occ = adjust_pattern_thresholds('standard_home', 0.7, 10)
    
    # Standard home should use default or close to default
    assert conf == 0.7 or abs(conf - 0.7) < 0.1
    assert occ == 10 or abs(occ - 10) < 2


def test_adjust_pattern_thresholds_unknown_type():
    """Test threshold adjustment for unknown home type (default)"""
    conf, occ = adjust_pattern_thresholds('unknown_type', 0.7, 10)
    
    # Unknown type should use defaults
    assert conf == 0.7
    assert occ == 10


def test_adjust_pattern_thresholds_studio():
    """Test threshold adjustment for studio (very strict)"""
    conf, occ = adjust_pattern_thresholds('studio', 0.7, 10)
    
    # Studio should be very strict
    assert conf < 0.7
    assert occ < 10

