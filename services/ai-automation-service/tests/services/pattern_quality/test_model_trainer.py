"""
Unit tests for Pattern Quality Model Trainer

Epic AI-13: ML-Based Pattern Quality & Active Learning
Story AI13.2: Pattern Quality Model Training
"""

import pytest
import numpy as np
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone, timedelta

import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from services.pattern_quality.model_trainer import PatternQualityTrainer
from services.pattern_quality.quality_model import PatternQualityModel
from database.models import Pattern, Suggestion, UserFeedback


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    session = AsyncMock()
    return session


@pytest.fixture
def trainer(mock_db_session):
    """Create PatternQualityTrainer instance."""
    return PatternQualityTrainer(mock_db_session)


@pytest.fixture
def sample_pattern():
    """Create sample Pattern model."""
    pattern = Mock(spec=Pattern)
    pattern.id = 1
    pattern.pattern_type = 'time_of_day'
    pattern.device_id = 'light.kitchen_light'
    pattern.pattern_metadata = {}
    pattern.confidence = 0.85
    pattern.occurrences = 42
    pattern.first_seen = datetime.now(timezone.utc) - timedelta(days=30)
    pattern.last_seen = datetime.now(timezone.utc) - timedelta(days=1)
    pattern.trend_direction = 'increasing'
    pattern.trend_strength = 0.7
    pattern.calibrated = True
    pattern.deprecated = False
    pattern.needs_review = False
    pattern.raw_confidence = 0.80
    return pattern


@pytest.fixture
def sample_feedback():
    """Create sample UserFeedback."""
    feedback = Mock(spec=UserFeedback)
    feedback.id = 1
    feedback.suggestion_id = 1
    feedback.action = 'approved'
    feedback.feedback_text = 'Great suggestion!'
    return feedback


@pytest.mark.asyncio
async def test_load_training_data_with_feedback(trainer, mock_db_session, sample_pattern, sample_feedback):
    """Test loading training data from user feedback."""
    # Mock database query result
    mock_result = Mock()
    mock_result.all.return_value = [(sample_pattern, sample_feedback)]
    
    mock_execute = AsyncMock(return_value=mock_result)
    mock_db_session.execute = mock_execute
    
    X, y = await trainer.load_training_data()
    
    # Should have called execute
    assert mock_execute.called
    
    # Should return arrays (may be empty if no valid data)
    assert isinstance(X, np.ndarray)
    assert isinstance(y, np.ndarray)


@pytest.mark.asyncio
async def test_load_training_data_no_feedback(trainer, mock_db_session):
    """Test loading training data when no feedback exists."""
    # Mock empty result
    mock_result = Mock()
    mock_result.all.return_value = []
    
    mock_execute = AsyncMock(return_value=mock_result)
    mock_db_session.execute = mock_execute
    
    X, y = await trainer.load_training_data()
    
    assert len(X) == 0
    assert len(y) == 0


@pytest.mark.asyncio
async def test_load_training_data_approved_rejected(trainer, mock_db_session, sample_pattern):
    """Test loading training data with both approved and rejected feedback."""
    # Create approved feedback
    approved_feedback = Mock(spec=UserFeedback)
    approved_feedback.action = 'approved'
    
    # Create rejected feedback
    rejected_feedback = Mock(spec=UserFeedback)
    rejected_feedback.action = 'rejected'
    
    # Mock database query result
    mock_result = Mock()
    mock_result.all.return_value = [
        (sample_pattern, approved_feedback),
        (sample_pattern, rejected_feedback)
    ]
    
    mock_execute = AsyncMock(return_value=mock_result)
    mock_db_session.execute = mock_execute
    
    X, y = await trainer.load_training_data()
    
    # Should have both classes
    assert len(X) == 2
    assert len(y) == 2
    assert 1 in y  # Approved
    assert 0 in y  # Rejected


@pytest.mark.asyncio
async def test_load_training_data_skips_modified(trainer, mock_db_session, sample_pattern):
    """Test that modified feedback is skipped."""
    # Create modified feedback
    modified_feedback = Mock(spec=UserFeedback)
    modified_feedback.action = 'modified'
    
    # Mock database query result
    mock_result = Mock()
    mock_result.all.return_value = [(sample_pattern, modified_feedback)]
    
    mock_execute = AsyncMock(return_value=mock_result)
    mock_db_session.execute = mock_execute
    
    X, y = await trainer.load_training_data()
    
    # Should skip modified feedback
    assert len(X) == 0
    assert len(y) == 0


@pytest.mark.asyncio
async def test_train_with_data(trainer, mock_db_session, sample_pattern, sample_feedback):
    """Test training with available data."""
    # Mock database query result
    mock_result = Mock()
    mock_result.all.return_value = [(sample_pattern, sample_feedback)]
    
    mock_execute = AsyncMock(return_value=mock_result)
    mock_db_session.execute = mock_execute
    
    # Mock feature extraction to return valid data
    with patch.object(trainer.feature_extractor, 'extract_features') as mock_extract:
        mock_features = Mock()
        mock_features.to_list.return_value = [0.5] * PatternFeatures.feature_count()
        mock_extract.return_value = mock_features
        
        with patch.object(trainer.feature_extractor, 'to_numpy_array') as mock_to_array:
            # Create synthetic training data
            X = np.random.rand(1, PatternFeatures.feature_count())
            y = np.array([1])
            mock_to_array.return_value = X
            
            metrics = await trainer.train()
            
            assert 'accuracy' in metrics


@pytest.mark.asyncio
async def test_train_no_data(trainer, mock_db_session):
    """Test training when no data is available."""
    # Mock empty result
    mock_result = Mock()
    mock_result.all.return_value = []
    
    mock_execute = AsyncMock(return_value=mock_result)
    mock_db_session.execute = mock_execute
    
    # Should raise ValueError
    with pytest.raises(ValueError, match="No training data available"):
        await trainer.train()


@pytest.mark.asyncio
async def test_load_blueprint_data(trainer):
    """Test loading blueprint data (stub implementation)."""
    X, y = await trainer.load_blueprint_data()
    
    # Should return empty arrays (stub implementation)
    assert len(X) == 0
    assert len(y) == 0


@pytest.mark.asyncio
async def test_train_with_blueprint_pretraining(trainer, mock_db_session, sample_pattern, sample_feedback):
    """Test training with blueprint pre-training."""
    # Mock database query result
    mock_result = Mock()
    mock_result.all.return_value = [(sample_pattern, sample_feedback)]
    
    mock_execute = AsyncMock(return_value=mock_result)
    mock_db_session.execute = mock_execute
    
    # Mock feature extraction
    with patch.object(trainer.feature_extractor, 'extract_features') as mock_extract:
        mock_features = Mock()
        mock_features.to_list.return_value = [0.5] * PatternFeatures.feature_count()
        mock_extract.return_value = mock_features
        
        with patch.object(trainer.feature_extractor, 'to_numpy_array') as mock_to_array:
            X = np.random.rand(1, PatternFeatures.feature_count())
            y = np.array([1])
            mock_to_array.return_value = X
            
            metrics = await trainer.train_with_blueprint_pretraining()
            
            # Should return metrics (even if blueprint data is empty)
            assert isinstance(metrics, dict)


def test_save_model(trainer, sample_pattern, sample_feedback):
    """Test saving trained model."""
    import tempfile
    import shutil
    from pathlib import Path
    
    # Mock training
    with patch.object(trainer, 'load_training_data', new_callable=AsyncMock) as mock_load:
        X = np.random.rand(10, PatternFeatures.feature_count())
        y = np.random.randint(0, 2, 10)
        mock_load.return_value = (X, y)
        
        # Train model
        import asyncio
        asyncio.run(trainer.train())
        
        # Save model
        temp_dir = Path(tempfile.mkdtemp())
        model_path = str(temp_dir / "test_model.joblib")
        
        try:
            trainer.save_model(model_path)
            
            # Check file exists
            assert Path(model_path).exists()
        finally:
            shutil.rmtree(temp_dir)


def test_get_model(trainer):
    """Test getting the trained model."""
    model = trainer.get_model()
    
    assert isinstance(model, PatternQualityModel)


@pytest.mark.asyncio
async def test_load_training_data_error_handling(trainer, mock_db_session, sample_pattern, sample_feedback):
    """Test error handling during data loading."""
    # Mock database query result with error during feature extraction
    mock_result = Mock()
    mock_result.all.return_value = [(sample_pattern, sample_feedback)]
    
    mock_execute = AsyncMock(return_value=mock_result)
    mock_db_session.execute = mock_execute
    
    # Mock feature extraction to raise error
    with patch.object(trainer.feature_extractor, 'extract_features', side_effect=Exception("Test error")):
        X, y = await trainer.load_training_data()
        
        # Should handle error gracefully and skip problematic patterns
        assert isinstance(X, np.ndarray)
        assert isinstance(y, np.ndarray)

