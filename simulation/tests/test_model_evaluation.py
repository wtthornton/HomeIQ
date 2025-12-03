"""
Unit tests for ModelEvaluator.
"""

import tempfile
from pathlib import Path

import pytest

from src.retraining.model_evaluator import ModelEvaluator


@pytest.fixture
def evaluator():
    """Create model evaluator."""
    return ModelEvaluator()


def test_compare_models(evaluator):
    """Test model comparison."""
    current_metrics = {
        "accuracy": 0.85,
        "precision": 0.82,
        "recall": 0.88,
        "f1_score": 0.85
    }
    
    previous_metrics = {
        "accuracy": 0.80,
        "precision": 0.78,
        "recall": 0.85,
        "f1_score": 0.81
    }
    
    comparison = evaluator.compare_models(current_metrics, previous_metrics)
    
    assert comparison["overall_improvement"] is True
    assert len(comparison["improvements"]) > 0


def test_detect_regression(evaluator):
    """Test regression detection."""
    current_metrics = {
        "accuracy": 0.75,
        "precision": 0.72,
        "recall": 0.78,
        "f1_score": 0.75
    }
    
    previous_metrics = {
        "accuracy": 0.85,
        "precision": 0.82,
        "recall": 0.88,
        "f1_score": 0.85
    }
    
    has_regression, details = evaluator.detect_regression(
        current_metrics,
        previous_metrics
    )
    
    assert has_regression is True
    assert details["has_regression"] is True

