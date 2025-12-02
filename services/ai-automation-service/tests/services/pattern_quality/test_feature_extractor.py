"""
Unit tests for Pattern Feature Extractor

Epic AI-13: ML-Based Pattern Quality & Active Learning
Story AI13.1: Pattern Quality Feature Engineering
"""

import pytest
import numpy as np
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from services.pattern_quality.feature_extractor import PatternFeatureExtractor
from services.pattern_quality.features import PatternFeatures


@pytest.fixture
def extractor():
    """Create feature extractor instance."""
    return PatternFeatureExtractor()


@pytest.fixture
def sample_pattern():
    """Create sample Pattern model (mock)."""
    now = datetime.now(timezone.utc)
    pattern = Mock()
    pattern.id = 1
    pattern.pattern_type = 'time_of_day'
    pattern.device_id = 'light.kitchen_light'
    pattern.pattern_metadata = {'conditions': [{'condition': 'state'}], 'actions': [{'service': 'light.turn_on'}]}
    pattern.confidence = 0.85
    pattern.occurrences = 42
    pattern.first_seen = now - timedelta(days=30)
    pattern.last_seen = now - timedelta(days=1)
    pattern.trend_direction = 'increasing'
    pattern.trend_strength = 0.7
    pattern.calibrated = True
    pattern.deprecated = False
    pattern.needs_review = False
    pattern.raw_confidence = 0.80
    return pattern


@pytest.fixture
def sample_pattern_dict():
    """Create sample pattern dict."""
    now = datetime.now(timezone.utc)
    return {
        'pattern_type': 'co_occurrence',
        'device_id': 'light.kitchen',
        'pattern_metadata': {'devices': ['light.kitchen', 'sensor.motion']},
        'confidence': 0.75,
        'occurrences': 15,
        'first_seen': now - timedelta(days=10),
        'last_seen': now - timedelta(days=1),
        'trend_direction': 'stable',
        'trend_strength': 0.5,
        'calibrated': False,
        'deprecated': False,
        'needs_review': False
    }


def test_extract_features_from_pattern_model(extractor, sample_pattern):
    """Test feature extraction from Pattern model."""
    features = extractor.extract_features(sample_pattern)
    
    assert isinstance(features, PatternFeatures)
    assert features.pattern_type_time_of_day == 1.0
    assert features.pattern_type_co_occurrence == 0.0
    assert features.confidence_raw == 0.80
    assert features.confidence_calibrated == 0.85
    assert features.occurrence_count_total == 42
    assert features.calibrated == 1.0
    assert features.is_deprecated == 0.0
    assert features.needs_review == 0.0
    assert features.metadata_has_conditions == 1.0
    assert features.metadata_has_actions == 1.0
    assert features.occurrence_trend_direction == 1.0  # increasing
    assert features.occurrence_trend_strength == 0.7


def test_extract_features_from_dict(extractor, sample_pattern_dict):
    """Test feature extraction from pattern dict."""
    features = extractor.extract_features(sample_pattern_dict)
    
    assert isinstance(features, PatternFeatures)
    assert features.pattern_type_co_occurrence == 1.0
    assert features.pattern_type_time_of_day == 0.0
    assert features.device_count_total >= 1  # At least device_id
    assert features.confidence_raw == 0.75
    assert features.occurrence_count_total == 15
    assert features.calibrated == 0.0
    assert features.occurrence_trend_direction == 0.0  # stable


def test_extract_features_batch(extractor, sample_pattern, sample_pattern_dict):
    """Test batch feature extraction."""
    patterns = [sample_pattern, sample_pattern_dict]
    features_list = extractor.extract_features_batch(patterns)
    
    assert len(features_list) == 2
    assert all(isinstance(f, PatternFeatures) for f in features_list)
    assert features_list[0].pattern_type_time_of_day == 1.0
    assert features_list[1].pattern_type_co_occurrence == 1.0


def test_to_numpy_array_single(extractor, sample_pattern):
    """Test conversion of single features to numpy array."""
    features = extractor.extract_features(sample_pattern)
    array = extractor.to_numpy_array(features)
    
    assert array.shape == (1, PatternFeatures.feature_count())
    assert array.dtype == np.float64 or array.dtype == np.float32


def test_to_numpy_array_batch(extractor, sample_pattern, sample_pattern_dict):
    """Test conversion of multiple features to numpy array."""
    features_list = extractor.extract_features_batch([sample_pattern, sample_pattern_dict])
    array = extractor.to_numpy_array(features_list)
    
    assert array.shape == (2, PatternFeatures.feature_count())


def test_feature_normalization(extractor, sample_pattern):
    """Test feature normalization."""
    features = extractor.extract_features(sample_pattern)
    
    # Confidence should be normalized
    assert 0.0 <= features.confidence_normalized <= 1.0
    assert features.confidence_normalized == 0.80  # Should match raw_confidence


def test_pattern_type_one_hot_encoding(extractor):
    """Test pattern type one-hot encoding."""
    pattern_types = ['time_of_day', 'co_occurrence', 'anomaly', 'seasonal', 'synergy']
    
    for pattern_type in pattern_types:
        pattern_dict = {'pattern_type': pattern_type, 'confidence': 0.5, 'occurrences': 10}
        features = extractor.extract_features(pattern_dict)
        
        # Check that only the correct pattern type is 1.0
        feature_name = extractor.PATTERN_TYPES[pattern_type]
        assert getattr(features, feature_name) == 1.0
        
        # Check that other pattern types are 0.0
        for other_type, other_feature in extractor.PATTERN_TYPES.items():
            if other_type != pattern_type:
                assert getattr(features, other_feature) == 0.0


def test_trend_direction_mapping(extractor):
    """Test trend direction numerical mapping."""
    trend_directions = {
        'decreasing': -1.0,
        'stable': 0.0,
        'increasing': 1.0,
    }
    
    for trend_dir, expected_value in trend_directions.items():
        pattern_dict = {
            'pattern_type': 'time_of_day',
            'trend_direction': trend_dir,
            'trend_strength': 0.5,
            'confidence': 0.5,
            'occurrences': 10
        }
        features = extractor.extract_features(pattern_dict)
        assert features.occurrence_trend_direction == expected_value


def test_time_span_calculation(extractor):
    """Test time span feature calculation."""
    now = datetime.now(timezone.utc)
    pattern_dict = {
        'pattern_type': 'time_of_day',
        'first_seen': now - timedelta(days=30),
        'last_seen': now - timedelta(days=1),
        'confidence': 0.5,
        'occurrences': 10
    }
    
    features = extractor.extract_features(pattern_dict)
    
    assert features.time_span_days == pytest.approx(29.0, abs=0.1)  # 30 - 1 days
    assert features.recency_days == pytest.approx(1.0, abs=0.1)  # 1 day ago
    assert features.age_days == pytest.approx(30.0, abs=0.1)  # 30 days old


def test_frequency_calculation(extractor):
    """Test occurrence frequency calculation."""
    now = datetime.now(timezone.utc)
    pattern_dict = {
        'pattern_type': 'time_of_day',
        'first_seen': now - timedelta(days=10),
        'last_seen': now - timedelta(days=1),
        'confidence': 0.5,
        'occurrences': 20
    }
    
    features = extractor.extract_features(pattern_dict)
    
    # Should be approximately 2 occurrences per day (20 occurrences / 10 days)
    assert features.occurrence_frequency == pytest.approx(2.0, abs=0.1)


def test_metadata_complexity(extractor):
    """Test metadata complexity calculation."""
    # Simple metadata
    pattern_dict1 = {
        'pattern_type': 'time_of_day',
        'pattern_metadata': {'key1': 'value1'},
        'confidence': 0.5,
        'occurrences': 10
    }
    features1 = extractor.extract_features(pattern_dict1)
    assert features1.metadata_complexity == 1.0
    
    # Complex metadata
    pattern_dict2 = {
        'pattern_type': 'time_of_day',
        'pattern_metadata': {'key1': 'value1', 'key2': 'value2', 'key3': 'value3'},
        'confidence': 0.5,
        'occurrences': 10
    }
    features2 = extractor.extract_features(pattern_dict2)
    assert features2.metadata_complexity == 3.0


def test_quality_indicators(extractor):
    """Test quality indicator features."""
    # Deprecated pattern
    pattern_dict1 = {
        'pattern_type': 'time_of_day',
        'deprecated': True,
        'needs_review': False,
        'calibrated': False,
        'confidence': 0.5,
        'occurrences': 10
    }
    features1 = extractor.extract_features(pattern_dict1)
    assert features1.is_deprecated == 1.0
    assert features1.needs_review == 0.0
    assert features1.calibrated == 0.0
    
    # Needs review pattern
    pattern_dict2 = {
        'pattern_type': 'time_of_day',
        'deprecated': False,
        'needs_review': True,
        'calibrated': True,
        'confidence': 0.5,
        'occurrences': 10
    }
    features2 = extractor.extract_features(pattern_dict2)
    assert features2.is_deprecated == 0.0
    assert features2.needs_review == 1.0
    assert features2.calibrated == 1.0


def test_fit_and_transform_scalers(extractor, sample_pattern, sample_pattern_dict):
    """Test scaler fitting and transformation."""
    patterns = [sample_pattern, sample_pattern_dict]
    features_list = extractor.extract_features_batch(patterns)
    
    # Fit scalers
    extractor.fit_scalers(features_list)
    assert extractor._fitted is True
    
    # Transform features
    scaled_array = extractor.transform_features(features_list, use_standard_scaler=True)
    assert scaled_array.shape == (2, PatternFeatures.feature_count())
    
    # MinMax scaler
    minmax_array = extractor.transform_features(features_list, use_standard_scaler=False)
    assert minmax_array.shape == (2, PatternFeatures.feature_count())


def test_features_to_dict(sample_pattern):
    """Test PatternFeatures.to_dict() method."""
    extractor = PatternFeatureExtractor()
    features = extractor.extract_features(sample_pattern)
    
    feature_dict = features.to_dict()
    assert isinstance(feature_dict, dict)
    assert len(feature_dict) == PatternFeatures.feature_count()
    assert 'pattern_type_time_of_day' in feature_dict
    assert 'confidence_raw' in feature_dict


def test_features_to_list(sample_pattern):
    """Test PatternFeatures.to_list() method."""
    extractor = PatternFeatureExtractor()
    features = extractor.extract_features(sample_pattern)
    
    feature_list = features.to_list()
    assert isinstance(feature_list, list)
    assert len(feature_list) == PatternFeatures.feature_count()
    assert all(isinstance(x, (int, float)) for x in feature_list)


def test_feature_names():
    """Test PatternFeatures.feature_names() class method."""
    feature_names = PatternFeatures.feature_names()
    assert isinstance(feature_names, list)
    assert len(feature_names) > 0
    assert 'pattern_type_time_of_day' in feature_names
    assert 'confidence_raw' in feature_names


def test_feature_count():
    """Test PatternFeatures.feature_count() class method."""
    count = PatternFeatures.feature_count()
    assert isinstance(count, int)
    assert count > 0
    assert count == len(PatternFeatures.feature_names())


def test_missing_values_handling(extractor):
    """Test handling of missing values in pattern."""
    # Minimal pattern with missing fields
    pattern_dict = {
        'pattern_type': 'time_of_day',
        'confidence': 0.5
    }
    
    features = extractor.extract_features(pattern_dict)
    
    # Should not raise errors and should have default values
    assert features.occurrence_count_total == 0
    assert features.time_span_days == 0.0
    assert features.recency_days == 0.0
    assert features.age_days == 0.0

