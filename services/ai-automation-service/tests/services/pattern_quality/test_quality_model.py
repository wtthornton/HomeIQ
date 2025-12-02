"""
Unit tests for Pattern Quality Model

Epic AI-13: ML-Based Pattern Quality & Active Learning
Story AI13.2: Pattern Quality Model Training
"""

import pytest
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile
import shutil

import sys
from pathlib import Path as PathLib

# Add src to path for imports
src_path = PathLib(__file__).parent.parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from services.pattern_quality.quality_model import PatternQualityModel
from services.pattern_quality.features import PatternFeatures


@pytest.fixture
def model():
    """Create PatternQualityModel instance."""
    return PatternQualityModel(n_estimators=10, max_depth=5, random_state=42)


@pytest.fixture
def sample_training_data():
    """Create sample training data."""
    n_samples = 100
    n_features = PatternFeatures.feature_count()
    
    # Create synthetic features
    X = np.random.rand(n_samples, n_features)
    
    # Create labels (slightly imbalanced)
    y = np.random.choice([0, 1], size=n_samples, p=[0.4, 0.6])
    
    return X, y


def test_model_initialization(model):
    """Test model initialization."""
    assert model is not None
    assert model.version == "1.0.0"
    assert model.trained_at is None
    assert model.metrics == {}
    assert model.feature_importance is None


def test_model_training(model, sample_training_data):
    """Test model training."""
    X, y = sample_training_data
    
    metrics = model.train(X, y)
    
    assert 'accuracy' in metrics
    assert 'precision' in metrics
    assert 'recall' in metrics
    assert 'f1' in metrics
    assert 'roc_auc' in metrics
    assert 'confusion_matrix' in metrics
    
    assert 0.0 <= metrics['accuracy'] <= 1.0
    assert 0.0 <= metrics['precision'] <= 1.0
    assert 0.0 <= metrics['recall'] <= 1.0
    assert 0.0 <= metrics['f1'] <= 1.0
    assert 0.0 <= metrics['roc_auc'] <= 1.0
    
    assert model.trained_at is not None
    assert model.feature_importance is not None


def test_model_training_single_class(model):
    """Test model training with single class (edge case)."""
    X = np.random.rand(50, PatternFeatures.feature_count())
    y = np.ones(50)  # All same class
    
    # Should not raise error, but may warn
    metrics = model.train(X, y)
    assert 'accuracy' in metrics


def test_predict_quality(model, sample_training_data):
    """Test quality prediction for a pattern."""
    X, y = sample_training_data
    model.train(X, y)
    
    # Create pattern dict
    pattern_dict = {
        'pattern_type': 'time_of_day',
        'confidence': 0.8,
        'occurrences': 20,
        'first_seen': '2025-01-01T00:00:00Z',
        'last_seen': '2025-01-15T00:00:00Z'
    }
    
    quality_score = model.predict_quality(pattern_dict)
    
    assert 0.0 <= quality_score <= 1.0


def test_predict_quality_batch(model, sample_training_data):
    """Test batch quality prediction."""
    X, y = sample_training_data
    model.train(X, y)
    
    patterns = [
        {'pattern_type': 'time_of_day', 'confidence': 0.8, 'occurrences': 20},
        {'pattern_type': 'co_occurrence', 'confidence': 0.6, 'occurrences': 10},
    ]
    
    quality_scores = model.predict_quality_batch(patterns)
    
    assert len(quality_scores) == 2
    assert all(0.0 <= score <= 1.0 for score in quality_scores)


def test_predict_quality_untrained(model):
    """Test quality prediction when model not trained."""
    pattern_dict = {'pattern_type': 'time_of_day', 'confidence': 0.8}
    
    # Should return default score (0.5) when not trained
    quality_score = model.predict_quality(pattern_dict)
    assert quality_score == 0.5


def test_model_save_and_load(model, sample_training_data):
    """Test model save and load."""
    X, y = sample_training_data
    model.train(X, y)
    
    # Create temporary directory
    temp_dir = Path(tempfile.mkdtemp())
    model_path = temp_dir / "test_model.joblib"
    
    try:
        # Save model
        model.save(model_path)
        assert model_path.exists()
        
        # Load model
        loaded_model = PatternQualityModel.load(model_path)
        
        assert loaded_model.version == model.version
        assert loaded_model.metrics == model.metrics
        assert loaded_model.feature_importance == model.feature_importance
        
        # Test that loaded model can predict
        pattern_dict = {'pattern_type': 'time_of_day', 'confidence': 0.8}
        original_score = model.predict_quality(pattern_dict)
        loaded_score = loaded_model.predict_quality(pattern_dict)
        
        assert abs(original_score - loaded_score) < 0.01  # Should be very close
    finally:
        # Cleanup
        shutil.rmtree(temp_dir)


def test_model_save_nonexistent_directory(model, sample_training_data):
    """Test model save creates directory if it doesn't exist."""
    X, y = sample_training_data
    model.train(X, y)
    
    temp_dir = Path(tempfile.mkdtemp())
    model_path = temp_dir / "nonexistent" / "test_model.joblib"
    
    try:
        # Should create directory
        model.save(model_path)
        assert model_path.exists()
    finally:
        shutil.rmtree(temp_dir)


def test_get_feature_importance(model, sample_training_data):
    """Test feature importance retrieval."""
    X, y = sample_training_data
    model.train(X, y)
    
    top_features = model.get_feature_importance(top_n=10)
    
    assert isinstance(top_features, dict)
    assert len(top_features) <= 10
    
    # Check that importance values are reasonable
    for feature, importance in top_features.items():
        assert isinstance(feature, str)
        assert 0.0 <= importance <= 1.0


def test_get_feature_importance_untrained(model):
    """Test feature importance when model not trained."""
    top_features = model.get_feature_importance()
    
    assert top_features == {}


def test_model_metrics_structure(model, sample_training_data):
    """Test that metrics have correct structure."""
    X, y = sample_training_data
    metrics = model.train(X, y)
    
    # Check required metrics
    required_metrics = ['accuracy', 'precision', 'recall', 'f1', 'roc_auc', 'confusion_matrix']
    for metric in required_metrics:
        assert metric in metrics
    
    # Check confusion matrix structure
    cm = metrics['confusion_matrix']
    assert isinstance(cm, list)
    
    # Check TP, TN, FP, FN
    assert 'true_positives' in metrics
    assert 'true_negatives' in metrics
    assert 'false_positives' in metrics
    assert 'false_negatives' in metrics


def test_model_with_imbalanced_data(model):
    """Test model training with highly imbalanced data."""
    n_samples = 100
    n_features = PatternFeatures.feature_count()
    
    X = np.random.rand(n_samples, n_features)
    # Highly imbalanced: 90% class 0, 10% class 1
    y = np.random.choice([0, 1], size=n_samples, p=[0.9, 0.1])
    
    # Should handle imbalance with class_weight='balanced'
    metrics = model.train(X, y)
    
    assert 'accuracy' in metrics
    assert 'precision' in metrics
    assert 'recall' in metrics


def test_model_versioning(model, sample_training_data):
    """Test model versioning."""
    X, y = sample_training_data
    model.train(X, y)
    
    # Check version is set
    assert model.version == "1.0.0"
    
    # Check trained_at is set
    assert model.trained_at is not None


def test_model_persistence_metadata(model, sample_training_data):
    """Test that model metadata is preserved during save/load."""
    X, y = sample_training_data
    model.train(X, y)
    
    temp_dir = Path(tempfile.mkdtemp())
    model_path = temp_dir / "test_model.joblib"
    
    try:
        model.save(model_path)
        loaded_model = PatternQualityModel.load(model_path)
        
        # Check metadata
        assert loaded_model.version == model.version
        assert loaded_model.trained_at == model.trained_at
        assert loaded_model.metrics == model.metrics
        assert loaded_model.feature_importance == model.feature_importance
    finally:
        shutil.rmtree(temp_dir)

