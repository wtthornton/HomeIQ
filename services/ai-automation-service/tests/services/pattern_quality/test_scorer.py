"""
Unit tests for Pattern Quality Scorer

Epic AI-13: ML-Based Pattern Quality & Active Learning
Story AI13.3: Pattern Quality Scoring Service
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import shutil

import sys
from pathlib import Path as PathLib

# Add src to path for imports
src_path = PathLib(__file__).parent.parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from services.pattern_quality.scorer import PatternQualityScorer
from services.pattern_quality.quality_model import PatternQualityModel


@pytest.fixture
def mock_model():
    """Create mock PatternQualityModel."""
    model = Mock(spec=PatternQualityModel)
    model.predict_quality.return_value = 0.85
    model.predict_quality_batch.return_value = [0.85, 0.75]
    return model


def test_scorer_initialization():
    """Test scorer initialization."""
    scorer = PatternQualityScorer()
    assert scorer is not None
    assert scorer.model_path is not None


def test_scorer_initialization_with_path():
    """Test scorer initialization with custom model path."""
    custom_path = Path("/custom/path/model.joblib")
    scorer = PatternQualityScorer(model_path=custom_path)
    assert scorer.model_path == custom_path


@patch('services.pattern_quality.scorer.PatternQualityModel.load')
def test_scorer_loads_model_when_exists(mock_load, mock_model):
    """Test that scorer loads model when file exists."""
    mock_load.return_value = mock_model
    
    # Create temporary file
    temp_dir = Path(tempfile.mkdtemp())
    model_path = temp_dir / "test_model.joblib"
    model_path.touch()  # Create empty file
    
    try:
        scorer = PatternQualityScorer(model_path=str(model_path))
        assert scorer.model is not None
    finally:
        shutil.rmtree(temp_dir)


def test_scorer_handles_missing_model():
    """Test that scorer handles missing model file gracefully."""
    # Use non-existent path
    scorer = PatternQualityScorer(model_path="/nonexistent/path/model.joblib")
    assert scorer.model is None


def test_score_pattern_with_model(mock_model):
    """Test scoring a single pattern when model is loaded."""
    scorer = PatternQualityScorer()
    scorer.model = mock_model
    
    pattern = {'pattern_type': 'time_of_day', 'confidence': 0.8}
    score = scorer.score_pattern(pattern)
    
    assert score == 0.85
    mock_model.predict_quality.assert_called_once_with(pattern)


def test_score_pattern_without_model():
    """Test scoring when model is not loaded (returns default)."""
    scorer = PatternQualityScorer()
    scorer.model = None
    
    pattern = {'pattern_type': 'time_of_day', 'confidence': 0.8}
    score = scorer.score_pattern(pattern)
    
    assert score == 0.5  # Default score


def test_score_patterns_batch_with_model(mock_model):
    """Test batch scoring when model is loaded."""
    scorer = PatternQualityScorer()
    scorer.model = mock_model
    
    patterns = [
        {'pattern_type': 'time_of_day', 'confidence': 0.8},
        {'pattern_type': 'co_occurrence', 'confidence': 0.6}
    ]
    
    scores = scorer.score_patterns(patterns)
    
    assert scores == [0.85, 0.75]
    mock_model.predict_quality_batch.assert_called_once_with(patterns)


def test_score_patterns_batch_without_model():
    """Test batch scoring when model is not loaded."""
    scorer = PatternQualityScorer()
    scorer.model = None
    
    patterns = [
        {'pattern_type': 'time_of_day', 'confidence': 0.8},
        {'pattern_type': 'co_occurrence', 'confidence': 0.6}
    ]
    
    scores = scorer.score_patterns(patterns)
    
    assert scores == [0.5, 0.5]  # Default scores


def test_score_patterns_empty_list():
    """Test scoring empty pattern list."""
    scorer = PatternQualityScorer()
    scores = scorer.score_patterns([])
    
    assert scores == []


def test_filter_by_quality(mock_model):
    """Test quality threshold filtering."""
    scorer = PatternQualityScorer()
    scorer.model = mock_model
    
    # Mock different scores
    mock_model.predict_quality_batch.return_value = [0.9, 0.6, 0.8, 0.5]
    
    patterns = [
        {'pattern_type': 'time_of_day', 'confidence': 0.9},
        {'pattern_type': 'co_occurrence', 'confidence': 0.6},
        {'pattern_type': 'anomaly', 'confidence': 0.8},
        {'pattern_type': 'seasonal', 'confidence': 0.5}
    ]
    
    filtered = scorer.filter_by_quality(patterns, threshold=0.7)
    
    # Should only include patterns with score >= 0.7
    assert len(filtered) == 2
    assert all(score >= 0.7 for _, score in filtered)


def test_filter_by_quality_all_below_threshold(mock_model):
    """Test filtering when all patterns are below threshold."""
    scorer = PatternQualityScorer()
    scorer.model = mock_model
    
    mock_model.predict_quality_batch.return_value = [0.5, 0.4, 0.3]
    
    patterns = [
        {'pattern_type': 'time_of_day'},
        {'pattern_type': 'co_occurrence'},
        {'pattern_type': 'anomaly'}
    ]
    
    filtered = scorer.filter_by_quality(patterns, threshold=0.7)
    
    assert len(filtered) == 0


def test_filter_by_quality_empty_list():
    """Test filtering empty pattern list."""
    scorer = PatternQualityScorer()
    filtered = scorer.filter_by_quality([], threshold=0.7)
    
    assert filtered == []


def test_rank_by_quality(mock_model):
    """Test ranking patterns by quality score."""
    scorer = PatternQualityScorer()
    scorer.model = mock_model
    
    # Mock scores in random order
    mock_model.predict_quality_batch.return_value = [0.6, 0.9, 0.3, 0.8]
    
    patterns = [
        {'pattern_type': 'time_of_day'},
        {'pattern_type': 'co_occurrence'},
        {'pattern_type': 'anomaly'},
        {'pattern_type': 'seasonal'}
    ]
    
    ranked = scorer.rank_by_quality(patterns)
    
    # Should be sorted by score (descending)
    assert len(ranked) == 4
    scores = [score for _, score in ranked]
    assert scores == sorted(scores, reverse=True)
    assert scores[0] == 0.9  # Highest score first


def test_rank_by_quality_empty_list():
    """Test ranking empty pattern list."""
    scorer = PatternQualityScorer()
    ranked = scorer.rank_by_quality([])
    
    assert ranked == []


def test_is_model_loaded_with_model(mock_model):
    """Test is_model_loaded when model is loaded."""
    scorer = PatternQualityScorer()
    scorer.model = mock_model
    
    assert scorer.is_model_loaded() is True


def test_is_model_loaded_without_model():
    """Test is_model_loaded when model is not loaded."""
    scorer = PatternQualityScorer()
    scorer.model = None
    
    assert scorer.is_model_loaded() is False


def test_get_model_path_default():
    """Test default model path generation."""
    scorer = PatternQualityScorer()
    path = scorer.model_path
    
    assert path is not None
    assert isinstance(path, Path)
    assert "pattern_quality_model.joblib" in str(path)


def test_get_model_path_custom():
    """Test custom model path."""
    custom_path = "/custom/path/model.joblib"
    scorer = PatternQualityScorer(model_path=custom_path)
    
    assert scorer.model_path == Path(custom_path)

