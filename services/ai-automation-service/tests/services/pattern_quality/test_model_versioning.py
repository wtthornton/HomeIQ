"""
Unit tests for Model Versioning

Epic AI-13: ML-Based Pattern Quality & Active Learning
Story AI13.5: Incremental Model Updates
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

import sys
from pathlib import Path as PathLib

# Add src to path for imports
src_path = PathLib(__file__).parent.parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from services.pattern_quality.model_versioning import ModelVersionManager
from services.pattern_quality.quality_model import PatternQualityModel
import numpy as np


@pytest.fixture
def temp_models_dir():
    """Create temporary models directory."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def version_manager(temp_models_dir):
    """Create ModelVersionManager instance."""
    return ModelVersionManager(temp_models_dir)


@pytest.fixture
def sample_model():
    """Create sample trained model."""
    model = PatternQualityModel(n_estimators=10, max_depth=5, random_state=42)
    X = np.random.rand(50, 28)  # 28 features
    y = np.random.randint(0, 2, 50)
    model.train(X, y)
    return model


def test_version_manager_initialization(version_manager, temp_models_dir):
    """Test version manager initialization."""
    assert version_manager.models_dir == temp_models_dir
    assert version_manager.version_file.exists()


def test_save_version(version_manager, sample_model):
    """Test saving model version."""
    version = version_manager.save_version(sample_model)
    
    assert version is not None
    assert version.startswith('v')
    assert version in version_manager._versions
    
    # Check model file exists
    version_metadata = version_manager._versions[version]
    model_path = Path(version_metadata['model_path'])
    assert model_path.exists()


def test_save_version_with_custom_version(version_manager, sample_model):
    """Test saving model with custom version string."""
    custom_version = "v1.0.0"
    version = version_manager.save_version(sample_model, version=custom_version)
    
    assert version == custom_version
    assert version in version_manager._versions


def test_save_version_with_metadata(version_manager, sample_model):
    """Test saving model version with metadata."""
    metadata = {'test_key': 'test_value', 'accuracy': 0.95}
    version = version_manager.save_version(sample_model, metadata=metadata)
    
    version_metadata = version_manager._versions[version]
    assert version_metadata['test_key'] == 'test_value'
    assert version_metadata['accuracy'] == 0.95


def test_load_version(version_manager, sample_model):
    """Test loading model version."""
    version = version_manager.save_version(sample_model)
    
    loaded_model = version_manager.load_version(version)
    
    assert loaded_model is not None
    assert loaded_model.version == sample_model.version


def test_load_version_not_found(version_manager):
    """Test loading non-existent version."""
    with pytest.raises(ValueError, match="Version v1.0.0 not found"):
        version_manager.load_version("v1.0.0")


def test_get_current_version(version_manager, sample_model):
    """Test getting current version."""
    # No versions yet
    assert version_manager.get_current_version() is None
    
    # Save a version
    version1 = version_manager.save_version(sample_model)
    assert version_manager.get_current_version() == version1
    
    # Save another version (should be latest)
    version2 = version_manager.save_version(sample_model)
    assert version_manager.get_current_version() == version2


def test_rollback(version_manager, sample_model, temp_models_dir):
    """Test rolling back to a version."""
    version = version_manager.save_version(sample_model)
    
    target_path = temp_models_dir / "current_model.joblib"
    success = version_manager.rollback(version, target_path)
    
    assert success is True
    assert target_path.exists()
    
    # Verify model can be loaded
    loaded_model = PatternQualityModel.load(target_path)
    assert loaded_model is not None


def test_list_versions(version_manager, sample_model):
    """Test listing all versions."""
    # No versions initially
    versions = version_manager.list_versions()
    assert len(versions) == 0
    
    # Save multiple versions
    version1 = version_manager.save_version(sample_model)
    version2 = version_manager.save_version(sample_model)
    version3 = version_manager.save_version(sample_model)
    
    versions = version_manager.list_versions()
    assert len(versions) == 3
    
    # Should be sorted by created_at (newest first)
    assert versions[0]['version'] == version3
    assert versions[1]['version'] == version2
    assert versions[2]['version'] == version1


def test_delete_version(version_manager, sample_model):
    """Test deleting a version."""
    version = version_manager.save_version(sample_model)
    
    # Verify version exists
    assert version in version_manager._versions
    
    # Delete version
    success = version_manager.delete_version(version)
    assert success is True
    
    # Verify version removed
    assert version not in version_manager._versions
    
    # Verify model file deleted
    version_metadata = version_manager._versions.get(version)
    if version_metadata:
        model_path = Path(version_metadata['model_path'])
        assert not model_path.exists()


def test_delete_version_not_found(version_manager):
    """Test deleting non-existent version."""
    success = version_manager.delete_version("v1.0.0")
    assert success is False


def test_get_version_metadata(version_manager, sample_model):
    """Test getting version metadata."""
    version = version_manager.save_version(sample_model, metadata={'test': 'value'})
    
    metadata = version_manager.get_version_metadata(version)
    
    assert metadata is not None
    assert metadata['version'] == version
    assert metadata['test'] == 'value'


def test_get_version_metadata_not_found(version_manager):
    """Test getting metadata for non-existent version."""
    metadata = version_manager.get_version_metadata("v1.0.0")
    assert metadata is None


def test_version_persistence(version_manager, sample_model, temp_models_dir):
    """Test that versions persist across manager instances."""
    version = version_manager.save_version(sample_model)
    
    # Create new manager instance
    new_manager = ModelVersionManager(temp_models_dir)
    
    # Should load existing versions
    assert version in new_manager._versions
    assert new_manager.get_current_version() == version

