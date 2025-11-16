"""
Tests for Model Training and Validation

This module contains tests for model training, validation, versioning, and metadata tracking.
"""

import pytest
import asyncio
import os
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.core.predictive_analytics import PredictiveAnalyticsEngine


class TestModelTraining:
    """Test cases for model training functionality."""
    
    @pytest.fixture
    def temp_models_dir(self):
        """Create temporary models directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def analytics_engine(self, temp_models_dir):
        """Create analytics engine with temporary models directory."""
        engine = PredictiveAnalyticsEngine()
        engine.models_dir = temp_models_dir
        os.makedirs(temp_models_dir, exist_ok=True)
        return engine
    
    @pytest.fixture
    def sample_training_data(self):
        """Generate sample training data."""
        import numpy as np
        data = []
        np.random.seed(42)
        for i in range(200):
            data.append({
                "device_id": f"device_{i}",
                "response_time": np.random.normal(500, 200),
                "error_rate": np.random.exponential(0.05),
                "battery_level": np.random.normal(70, 20),
                "signal_strength": np.random.normal(-60, 15),
                "usage_frequency": np.random.uniform(0.1, 1.0),
                "temperature": np.random.normal(25, 5),
                "humidity": np.random.normal(50, 10),
                "uptime_hours": np.random.exponential(100),
                "restart_count": np.random.poisson(2),
                "connection_drops": np.random.poisson(1),
                "data_transfer_rate": np.random.normal(1000, 200)
            })
        return data
    
    @pytest.mark.asyncio
    async def test_train_models_with_sample_data(self, analytics_engine, sample_training_data):
        """Test model training with sample data."""
        await analytics_engine.train_models(historical_data=sample_training_data)
        
        assert analytics_engine.is_trained == True
        assert analytics_engine.model_metadata["version"] is not None
        assert analytics_engine.model_metadata["training_date"] is not None
        assert analytics_engine.model_metadata["data_source"] == "database"
    
    @pytest.mark.asyncio
    async def test_model_validation_passes(self, analytics_engine, sample_training_data):
        """Test that model validation passes for good models."""
        await analytics_engine.train_models(historical_data=sample_training_data)
        
        # Check validation results
        validation = analytics_engine.model_metadata.get("validation", {})
        assert validation.get("valid") == True
        assert "All validation checks passed" in validation.get("reason", "")
    
    @pytest.mark.asyncio
    async def test_model_versioning(self, analytics_engine, sample_training_data):
        """Test that model versions are incremented correctly."""
        # First training
        await analytics_engine.train_models(historical_data=sample_training_data)
        version1 = analytics_engine.model_metadata["version"]
        
        # Second training
        await analytics_engine.train_models(historical_data=sample_training_data)
        version2 = analytics_engine.model_metadata["version"]
        
        # Version should be incremented
        assert version2 != version1
        # Parse versions and check patch version incremented
        v1_parts = version1.split(".")
        v2_parts = version2.split(".")
        assert int(v2_parts[2]) > int(v1_parts[2])
    
    @pytest.mark.asyncio
    async def test_model_metadata_saved(self, analytics_engine, sample_training_data, temp_models_dir):
        """Test that model metadata is saved correctly."""
        await analytics_engine.train_models(historical_data=sample_training_data)
        
        metadata_path = os.path.join(temp_models_dir, "model_metadata.json")
        assert os.path.exists(metadata_path)
        
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        assert metadata["version"] is not None
        assert metadata["training_date"] is not None
        assert "model_performance" in metadata
        assert "training_data_stats" in metadata
    
    @pytest.mark.asyncio
    async def test_model_backup_created(self, analytics_engine, sample_training_data, temp_models_dir):
        """Test that existing models are backed up before overwriting."""
        # First training
        await analytics_engine.train_models(historical_data=sample_training_data)
        
        # Second training should create backup
        await analytics_engine.train_models(historical_data=sample_training_data)
        
        # Check for backup files
        backup_files = list(Path(temp_models_dir).glob("*.backup_*"))
        assert len(backup_files) > 0
    
    @pytest.mark.asyncio
    async def test_model_verification(self, analytics_engine, sample_training_data):
        """Test that saved models can be verified."""
        await analytics_engine.train_models(historical_data=sample_training_data)
        
        # Verification should pass
        result = await analytics_engine._verify_saved_models()
        assert result == True
    
    @pytest.mark.asyncio
    async def test_training_data_validation(self, analytics_engine):
        """Test training data validation."""
        # Test with insufficient data
        insufficient_data = [{"device_id": f"device_{i}"} for i in range(10)]
        result = analytics_engine._validate_training_data(insufficient_data)
        assert result == False
        
        # Test with sufficient data
        import numpy as np
        sufficient_data = []
        np.random.seed(42)
        for i in range(100):
            sufficient_data.append({
                "device_id": f"device_{i}",
                "response_time": np.random.normal(500, 200),
                "error_rate": np.random.exponential(0.05),
                "battery_level": np.random.normal(70, 20),
                "signal_strength": np.random.normal(-60, 15),
                "usage_frequency": np.random.uniform(0.1, 1.0),
                "temperature": np.random.normal(25, 5),
                "humidity": np.random.normal(50, 10),
                "uptime_hours": np.random.exponential(100),
                "restart_count": np.random.poisson(2),
                "connection_drops": np.random.poisson(1),
                "data_transfer_rate": np.random.normal(1000, 200)
            })
        result = analytics_engine._validate_training_data(sufficient_data)
        assert result == True
    
    @pytest.mark.asyncio
    async def test_model_status_includes_metadata(self, analytics_engine, sample_training_data):
        """Test that model status includes metadata."""
        await analytics_engine.train_models(historical_data=sample_training_data)
        
        status = analytics_engine.get_model_status()
        assert "model_metadata" in status
        assert status["model_metadata"]["version"] is not None
        assert "model_performance" in status["model_metadata"]


class TestModelValidation:
    """Test cases for model validation."""
    
    @pytest.fixture
    def analytics_engine(self):
        """Create analytics engine instance."""
        return PredictiveAnalyticsEngine()
    
    @pytest.mark.asyncio
    async def test_validation_checks_performance_thresholds(self, analytics_engine):
        """Test that validation checks performance thresholds."""
        import numpy as np
        from sklearn.ensemble import RandomForestClassifier, IsolationForest
        from sklearn.preprocessing import StandardScaler
        
        # Create models with known performance
        X_test = np.random.rand(20, 11)
        y_test = np.random.randint(0, 2, 20)
        
        # Train models
        scaler = StandardScaler()
        X_test_scaled = scaler.fit_transform(X_test)
        
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(X_test_scaled, y_test)
        
        analytics_engine.models["failure_prediction"] = model
        analytics_engine.models["anomaly_detection"] = IsolationForest(random_state=42)
        analytics_engine.models["anomaly_detection"].fit(X_test_scaled)
        analytics_engine.scalers["failure_prediction"] = scaler
        
        # Set performance metrics
        analytics_engine.model_performance = {
            "accuracy": 0.6,  # Above threshold
            "precision": 0.5,  # Above threshold
            "recall": 0.4,     # Above threshold
            "f1_score": 0.45
        }
        
        # Validate
        result = await analytics_engine._validate_models(X_test_scaled, y_test)
        assert result["valid"] == True
    
    @pytest.mark.asyncio
    async def test_validation_fails_below_thresholds(self, analytics_engine):
        """Test that validation fails when performance is below thresholds."""
        import numpy as np
        from sklearn.ensemble import RandomForestClassifier, IsolationForest
        from sklearn.preprocessing import StandardScaler
        
        X_test = np.random.rand(20, 11)
        y_test = np.random.randint(0, 2, 20)
        
        scaler = StandardScaler()
        X_test_scaled = scaler.fit_transform(X_test)
        
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(X_test_scaled, y_test)
        
        analytics_engine.models["failure_prediction"] = model
        analytics_engine.models["anomaly_detection"] = IsolationForest(random_state=42)
        analytics_engine.models["anomaly_detection"].fit(X_test_scaled)
        analytics_engine.scalers["failure_prediction"] = scaler
        
        # Set low performance metrics
        analytics_engine.model_performance = {
            "accuracy": 0.3,  # Below threshold
            "precision": 0.2,  # Below threshold
            "recall": 0.1,     # Below threshold
            "f1_score": 0.15
        }
        
        # Validate
        result = await analytics_engine._validate_models(X_test_scaled, y_test)
        assert result["valid"] == False
        assert "below threshold" in result["reason"].lower()

