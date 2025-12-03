"""
Unit tests for RetrainingManager.
"""

import tempfile
from pathlib import Path

import pytest

from src.retraining.retraining_manager import RetrainingManager
from src.retraining.data_sufficiency import DataSufficiencyChecker


@pytest.fixture
def temp_dirs():
    """Create temporary directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        training_dir = Path(tmpdir) / "training_data"
        model_dir = Path(tmpdir) / "models"
        training_dir.mkdir()
        model_dir.mkdir()
        yield training_dir, model_dir


@pytest.fixture
def manager(temp_dirs):
    """Create retraining manager."""
    training_dir, model_dir = temp_dirs
    return RetrainingManager(
        training_data_directory=training_dir,
        model_directory=model_dir
    )


def test_check_retraining_trigger(manager):
    """Test retraining trigger check."""
    data_counts = {
        "gnn_synergy": 150,  # Above minimum
        "soft_prompt": 30,  # Below minimum
        "pattern_detection": 250  # Above minimum
    }
    
    triggers = manager.check_retraining_trigger(data_counts)
    
    assert triggers["gnn_synergy"] is True
    assert triggers["soft_prompt"] is False
    assert triggers["pattern_detection"] is True


def test_get_retraining_history(manager):
    """Test retraining history."""
    history = manager.get_retraining_history()
    assert isinstance(history, list)

