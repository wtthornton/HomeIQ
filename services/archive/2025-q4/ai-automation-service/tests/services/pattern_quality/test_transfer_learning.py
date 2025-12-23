"""
Unit tests for Transfer Learning from Blueprint Corpus

Epic AI-13: ML-Based Pattern Quality & Active Learning
Story AI13.6: Transfer Learning from Blueprint Corpus
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
import numpy as np

import sys
from pathlib import Path as PathLib

# Add src to path for imports
src_path = PathLib(__file__).parent.parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from services.pattern_quality.transfer_learner import (
    BlueprintTransferLearner,
    blueprint_to_pattern_features
)
from services.pattern_quality.quality_model import PatternQualityModel
from services.pattern_quality.features import PatternFeatures
from utils.miner_integration import MinerIntegration


@pytest.fixture
def sample_blueprint():
    """Create sample blueprint metadata."""
    return {
        'id': 'blueprint_1',
        'title': 'Motion-Activated Light',
        'quality_score': 0.85,
        'views': 500,
        'metadata': {
            '_blueprint_metadata': {
                'name': 'Motion-Activated Light',
                'description': 'Turn on lights when motion detected',
                'domain': 'automation'
            },
            '_blueprint_variables': {
                'motion_sensor': {
                    'domain': 'binary_sensor',
                    'device_class': 'motion'
                },
                'target_light': {
                    'domain': 'light'
                }
            },
            '_blueprint_devices': ['binary_sensor', 'light']
        }
    }


@pytest.fixture
def mock_miner_integration():
    """Create mock miner integration."""
    mock = Mock(spec=MinerIntegration)
    mock.is_available = AsyncMock(return_value=True)
    mock.search_blueprints = AsyncMock(return_value=[])
    return mock


def test_blueprint_to_pattern_features(sample_blueprint):
    """Test converting blueprint to PatternFeatures."""
    features = blueprint_to_pattern_features(sample_blueprint)
    
    assert isinstance(features, PatternFeatures)
    assert features.device_count_total == 2
    assert features.device_count_unique == 2
    assert features.confidence_raw == 0.85
    assert features.pattern_type_co_occurrence == 1.0
    assert features.calibrated == 1.0


def test_blueprint_to_pattern_features_minimal():
    """Test converting minimal blueprint."""
    minimal_blueprint = {
        'quality_score': 0.5,
        'metadata': {}
    }
    
    features = blueprint_to_pattern_features(minimal_blueprint)
    
    assert isinstance(features, PatternFeatures)
    assert features.confidence_raw == 0.5
    assert features.device_count_total == 0


@pytest.mark.asyncio
async def test_load_blueprint_corpus_available(mock_miner_integration):
    """Test loading blueprint corpus when miner is available."""
    # Mock blueprints
    mock_blueprints = [
        {
            'id': 'bp1',
            'quality_score': 0.8,
            'views': 100,
            'metadata': {
                '_blueprint_devices': ['light', 'sensor']
            }
        },
        {
            'id': 'bp2',
            'quality_score': 0.6,
            'views': 50,
            'metadata': {
                '_blueprint_devices': ['switch']
            }
        }
    ]
    
    mock_miner_integration.search_blueprints = AsyncMock(return_value=mock_blueprints)
    
    learner = BlueprintTransferLearner(miner_integration=mock_miner_integration)
    X, y = await learner.load_blueprint_corpus(limit=10)
    
    assert len(X) == 2
    assert len(y) == 2
    assert X.shape[1] == PatternFeatures.feature_count()
    assert y[0] == 1  # High quality (>0.7)
    assert y[1] == 0  # Low quality (<=0.7)


@pytest.mark.asyncio
async def test_load_blueprint_corpus_unavailable(mock_miner_integration):
    """Test loading blueprint corpus when miner is unavailable."""
    mock_miner_integration.is_available = AsyncMock(return_value=False)
    
    learner = BlueprintTransferLearner(miner_integration=mock_miner_integration)
    X, y = await learner.load_blueprint_corpus(limit=10)
    
    assert len(X) == 0
    assert len(y) == 0


@pytest.mark.asyncio
async def test_load_blueprint_corpus_empty(mock_miner_integration):
    """Test loading blueprint corpus when no blueprints found."""
    mock_miner_integration.search_blueprints = AsyncMock(return_value=[])
    
    learner = BlueprintTransferLearner(miner_integration=mock_miner_integration)
    X, y = await learner.load_blueprint_corpus(limit=10)
    
    assert len(X) == 0
    assert len(y) == 0


@pytest.mark.asyncio
async def test_pre_train_success(mock_miner_integration):
    """Test successful pre-training."""
    # Mock blueprints
    mock_blueprints = [
        {
            'id': 'bp1',
            'quality_score': 0.8,
            'views': 100,
            'metadata': {
                '_blueprint_devices': ['light']
            }
        }
    ] * 50  # 50 blueprints
    
    mock_miner_integration.search_blueprints = AsyncMock(return_value=mock_blueprints)
    
    learner = BlueprintTransferLearner(miner_integration=mock_miner_integration)
    model = PatternQualityModel(n_estimators=10, max_depth=5, random_state=42)
    
    metrics = await learner.pre_train(model, limit=100)
    
    assert metrics['status'] == 'success'
    assert metrics['samples'] == 50
    assert 'accuracy' in metrics


@pytest.mark.asyncio
async def test_pre_train_no_data(mock_miner_integration):
    """Test pre-training with no blueprint data."""
    mock_miner_integration.search_blueprints = AsyncMock(return_value=[])
    
    learner = BlueprintTransferLearner(miner_integration=mock_miner_integration)
    model = PatternQualityModel()
    
    metrics = await learner.pre_train(model, limit=100)
    
    assert metrics['status'] == 'skipped'
    assert metrics['samples'] == 0


@pytest.mark.asyncio
async def test_fine_tune_success(mock_miner_integration):
    """Test successful fine-tuning."""
    # Mock blueprints for combined training
    mock_blueprints = [
        {
            'id': 'bp1',
            'quality_score': 0.8,
            'views': 100,
            'metadata': {
                '_blueprint_devices': ['light']
            }
        }
    ] * 20
    
    mock_miner_integration.search_blueprints = AsyncMock(return_value=mock_blueprints)
    
    learner = BlueprintTransferLearner(miner_integration=mock_miner_integration)
    model = PatternQualityModel(n_estimators=10, max_depth=5, random_state=42)
    
    # Pre-train first
    await learner.pre_train(model, limit=50)
    
    # Fine-tune on user data
    X_user = np.random.rand(30, PatternFeatures.feature_count())
    y_user = np.random.randint(0, 2, 30)
    
    metrics = await learner.fine_tune(model, X_user, y_user)
    
    assert metrics['status'] == 'success'
    assert metrics['user_samples'] == 30
    assert 'accuracy' in metrics


@pytest.mark.asyncio
async def test_fine_tune_no_user_data(mock_miner_integration):
    """Test fine-tuning with no user data."""
    learner = BlueprintTransferLearner(miner_integration=mock_miner_integration)
    model = PatternQualityModel()
    
    X_user = np.array([]).reshape(0, PatternFeatures.feature_count())
    y_user = np.array([])
    
    metrics = await learner.fine_tune(model, X_user, y_user)
    
    assert metrics['status'] == 'skipped'
    assert metrics['samples'] == 0


@pytest.mark.asyncio
async def test_compare_models(mock_miner_integration):
    """Test comparing pre-trained vs non-pre-trained models."""
    # Mock blueprints
    mock_blueprints = [
        {
            'id': 'bp1',
            'quality_score': 0.8,
            'views': 100,
            'metadata': {
                '_blueprint_devices': ['light']
            }
        }
    ] * 50
    
    mock_miner_integration.search_blueprints = AsyncMock(return_value=mock_blueprints)
    
    learner = BlueprintTransferLearner(miner_integration=mock_miner_integration)
    
    # Pre-train model
    pre_trained_model = PatternQualityModel(n_estimators=10, max_depth=5, random_state=42)
    await learner.pre_train(pre_trained_model, limit=100)
    
    # Create test data
    X_test = np.random.rand(20, PatternFeatures.feature_count())
    y_test = np.random.randint(0, 2, 20)
    
    # Compare models
    comparison = await learner.compare_models(
        X_test, y_test, pre_trained_model
    )
    
    assert 'pre_trained' in comparison
    assert 'non_pre_trained' in comparison
    assert 'improvement' in comparison
    assert 'accuracy' in comparison['improvement']


@pytest.mark.asyncio
async def test_compare_models_with_custom_model(mock_miner_integration):
    """Test comparing with custom non-pre-trained model."""
    learner = BlueprintTransferLearner(miner_integration=mock_miner_integration)
    
    pre_trained_model = PatternQualityModel(n_estimators=10, max_depth=5, random_state=42)
    non_pre_trained_model = PatternQualityModel(n_estimators=10, max_depth=5, random_state=42)
    
    X_test = np.random.rand(20, PatternFeatures.feature_count())
    y_test = np.random.randint(0, 2, 20)
    
    # Train both models
    pre_trained_model.train(X_test, y_test)
    non_pre_trained_model.train(X_test, y_test)
    
    comparison = await learner.compare_models(
        X_test, y_test, pre_trained_model, non_pre_trained_model
    )
    
    assert 'pre_trained' in comparison
    assert 'non_pre_trained' in comparison
    assert 'improvement' in comparison

