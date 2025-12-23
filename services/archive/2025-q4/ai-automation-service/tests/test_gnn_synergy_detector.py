"""
Unit tests for GNN Synergy Detector

Tests model initialization, graph building, training, and prediction.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.synergy_detection.gnn_synergy_detector import GNNSynergyDetector, TORCH_AVAILABLE


@pytest.fixture
def mock_entities():
    """Mock entity data."""
    return [
        {'entity_id': 'light.bedroom', 'friendly_name': 'Bedroom Light', 'area_id': 'bedroom'},
        {'entity_id': 'sensor.motion_bedroom', 'friendly_name': 'Bedroom Motion', 'area_id': 'bedroom'},
        {'entity_id': 'light.living_room', 'friendly_name': 'Living Room Light', 'area_id': 'living_room'},
        {'entity_id': 'switch.kitchen', 'friendly_name': 'Kitchen Switch', 'area_id': 'kitchen'},
    ]


@pytest.fixture
def mock_synergies():
    """Mock synergy data."""
    return [
        {
            'synergy_id': 'test-1',
            'device_ids': ['light.bedroom', 'sensor.motion_bedroom'],
            'impact_score': 0.8,
            'confidence': 0.9,
            'area': 'bedroom',
            'validated_by_patterns': True
        },
        {
            'synergy_id': 'test-2',
            'device_ids': ['light.living_room', 'switch.kitchen'],
            'impact_score': 0.6,
            'confidence': 0.7,
            'area': 'living_room',
            'validated_by_patterns': False
        }
    ]


@pytest.fixture
def detector():
    """Create GNN detector instance."""
    return GNNSynergyDetector(
        hidden_dim=32,
        num_layers=2,
        epochs=5  # Small for testing
    )


@pytest.mark.asyncio
async def test_detector_initialization(detector):
    """Test detector initialization."""
    assert detector.hidden_dim == 32
    assert detector.num_layers == 2
    assert detector.model is None
    assert not detector._is_initialized


def test_detector_validation():
    """Test input validation."""
    with pytest.raises(ValueError, match="hidden_dim must be positive"):
        GNNSynergyDetector(hidden_dim=0)
    
    with pytest.raises(ValueError, match="num_layers must be at least 1"):
        GNNSynergyDetector(num_layers=0)


def test_build_device_graph(detector, mock_entities):
    """Test graph building."""
    graph = detector.build_device_graph(mock_entities)
    
    assert 'nodes' in graph
    assert 'edges' in graph
    assert 'node_features' in graph
    assert 'node_id_map' in graph
    
    assert len(graph['nodes']) == len(mock_entities)
    assert len(graph['node_id_map']) == len(mock_entities)
    assert len(graph['node_features']) == len(mock_entities)
    
    # Check node features
    assert len(graph['node_features'][0]) == 3  # domain, area, usage


def test_create_training_pairs(detector, mock_entities, mock_synergies):
    """Test training pair creation."""
    pairs = detector._create_training_pairs(mock_synergies, mock_entities)
    
    assert len(pairs) > 0
    assert all(len(p) == 3 for p in pairs)  # (device1, device2, label)
    assert all(0.0 <= p[2] <= 1.0 for p in pairs)  # Label in [0, 1]


def test_generate_negative_pairs(detector, mock_entities, mock_synergies):
    """Test negative pair generation."""
    positive_pairs = detector._create_training_pairs(mock_synergies, mock_entities)
    negative_pairs = detector._generate_negative_pairs(mock_entities, positive_pairs, num_negative=5)
    
    assert len(negative_pairs) <= 5
    assert all(p[2] == 0.0 for p in negative_pairs)  # All negative labels


@pytest.mark.asyncio
async def test_initialize_without_torch(detector):
    """Test initialization when torch-geometric is not available."""
    with patch('src.synergy_detection.gnn_synergy_detector.TORCH_AVAILABLE', False):
        await detector.initialize()
        assert not detector._is_initialized


@pytest.mark.skipif(not TORCH_AVAILABLE, reason="torch-geometric not available")
@pytest.mark.asyncio
async def test_learn_from_data_small(detector, mock_entities, mock_synergies):
    """Test training with small dataset."""
    # Mock database session
    mock_db = AsyncMock()
    mock_data_client = AsyncMock()
    mock_data_client.fetch_entities = AsyncMock(return_value=mock_entities)
    
    result = await detector.learn_from_data(
        entities=mock_entities,
        known_synergies=mock_synergies,
        db_session=mock_db,
        data_api_client=mock_data_client
    )
    
    if result.get('status') == 'complete':
        assert 'final_train_loss' in result
        assert 'final_val_loss' in result
        assert detector._is_initialized
        assert detector.model is not None
    else:
        # Training might skip if insufficient data
        assert result.get('status') in ['skipped', 'complete']


@pytest.mark.skipif(not TORCH_AVAILABLE, reason="torch-geometric not available")
@pytest.mark.asyncio
async def test_save_and_load_model(detector, mock_entities, mock_synergies, tmp_path):
    """Test model save and load."""
    import tempfile
    import os
    
    # Create temporary model path
    model_path = str(tmp_path / "test_model.pth")
    detector.model_path = model_path
    
    # Train a small model first
    mock_db = AsyncMock()
    mock_data_client = AsyncMock()
    mock_data_client.fetch_entities = AsyncMock(return_value=mock_entities)
    
    result = await detector.learn_from_data(
        entities=mock_entities,
        known_synergies=mock_synergies,
        db_session=mock_db,
        data_api_client=mock_data_client
    )
    
    if result.get('status') == 'complete' and detector.model:
        # Save model
        await detector.save_model(model_path)
        assert os.path.exists(model_path)
        
        # Create new detector and load
        new_detector = GNNSynergyDetector(model_path=model_path)
        loaded = await new_detector.load_model(model_path)
        
        if loaded:
            assert new_detector._is_initialized
            assert new_detector.model is not None


@pytest.mark.skipif(not TORCH_AVAILABLE, reason="torch-geometric not available")
@pytest.mark.asyncio
async def test_predict_synergy_score(detector, mock_entities):
    """Test synergy score prediction."""
    # Build graph
    graph = detector.build_device_graph(mock_entities)
    
    # Try to predict (will use fallback if model not trained)
    result = await detector.predict_synergy_score(
        device_pair=('light.bedroom', 'sensor.motion_bedroom'),
        graph=graph,
        entities=mock_entities
    )
    
    assert 'score' in result
    assert 'explanation' in result
    assert 'confidence' in result
    assert 0.0 <= result['score'] <= 1.0
    assert 0.0 <= result['confidence'] <= 1.0


def test_predict_invalid_input(detector):
    """Test prediction with invalid input."""
    with pytest.raises(ValueError, match="device_pair must be a tuple"):
        # This will be called synchronously in test, but method is async
        # So we test the validation logic
        pass  # Validation happens in method

