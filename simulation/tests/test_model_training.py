"""
Unit tests for Model Training Integration

Tests for model loading and training integration.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from engine.model_training import ModelTrainingIntegration
from engine.model_loader import ModelLoader


class TestModelTrainingIntegration:
    """Tests for ModelTrainingIntegration."""

    @pytest.mark.asyncio
    async def test_load_models_pretrained_mode(self, tmp_path):
        """Test loading pre-trained models."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        
        # Create mock model file
        (models_dir / "test_model.pkl").write_bytes(b"mock model data")
        
        integration = ModelTrainingIntegration(models_dir, mode="pretrained")
        models = await integration.load_models()
        
        assert len(models) > 0
        assert integration.models_loaded

    @pytest.mark.asyncio
    async def test_train_models_train_during_mode(self, tmp_path):
        """Test training models during simulation."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        
        integration = ModelTrainingIntegration(models_dir, mode="train_during")
        training_data = {"events": [], "patterns": []}
        
        models = await integration.train_models(training_data)
        
        assert len(models) > 0

    def test_validate_models(self, tmp_path):
        """Test model validation."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        
        integration = ModelTrainingIntegration(models_dir, mode="pretrained")
        integration.models = {
            "test_model": {"loaded": True}
        }
        
        results = integration.validate_models(min_accuracy=0.7)
        
        assert "test_model" in results
        assert results["test_model"]["passed"] is True

    def test_get_model_performance_metrics(self, tmp_path):
        """Test getting model performance metrics."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        
        integration = ModelTrainingIntegration(models_dir, mode="pretrained")
        integration.models = {
            "test_model": {"loaded": True}
        }
        
        metrics = integration.get_model_performance_metrics()
        
        assert "test_model" in metrics
        assert "inference_latency_ms" in metrics["test_model"]


class TestModelLoader:
    """Tests for ModelLoader."""

    @pytest.mark.asyncio
    async def test_load_all_models(self, tmp_path):
        """Test loading all models."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        
        # Create mock model files
        (models_dir / "model1.pkl").write_bytes(b"data1")
        (models_dir / "model2.joblib").write_bytes(b"data2")
        
        loader = ModelLoader(models_dir)
        models = await loader.load_all_models()
        
        assert len(models) == 2

    def test_validate_model_initialization(self, tmp_path):
        """Test model initialization validation."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        
        loader = ModelLoader(models_dir)
        loader.models = {
            "test_model": {"loaded": True}
        }
        
        assert loader.validate_model_initialization() is True

    def test_validate_model_initialization_fails(self, tmp_path):
        """Test validation fails for unloaded models."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        
        loader = ModelLoader(models_dir)
        loader.models = {
            "test_model": {"loaded": False}
        }
        
        assert loader.validate_model_initialization() is False

