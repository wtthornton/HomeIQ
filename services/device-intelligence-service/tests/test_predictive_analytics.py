"""
Tests for Predictive Analytics Engine

This module contains comprehensive tests for the predictive analytics functionality
including model training, failure prediction, and API endpoints.
"""

import os
import sys
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from src.api.predictions_router import router
from src.core.predictive_analytics import PredictiveAnalyticsEngine


class TestPredictiveAnalyticsEngine:
    """Test cases for PredictiveAnalyticsEngine."""

    @pytest.fixture
    def analytics_engine(self):
        """Create analytics engine instance for testing."""
        return PredictiveAnalyticsEngine()

    @pytest.fixture
    def sample_metrics(self):
        """Sample device metrics for testing."""
        return {
            "response_time": 500,
            "error_rate": 0.05,
            "battery_level": 75,
            "signal_strength": -60,
            "usage_frequency": 0.8,
            "temperature": 25,
            "humidity": 50,
            "uptime_hours": 100,
            "restart_count": 2,
            "connection_drops": 1,
            "data_transfer_rate": 1000,
        }

    @pytest.fixture
    def sample_training_data(self):
        """Sample training data for testing."""
        np.random.seed(42)
        data = []
        for _i in range(200):
            data.append({
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
                "data_transfer_rate": np.random.normal(1000, 200),
            })
        return data

    def test_feature_extraction(self, analytics_engine, sample_metrics):
        """Test feature extraction from device metrics."""
        features = analytics_engine._extract_features(sample_metrics)

        assert len(features) == len(analytics_engine.feature_columns)
        assert all(isinstance(f, float) for f in features)
        assert features[0] == 500.0  # response_time
        assert features[1] == 0.05  # error_rate
        assert features[2] == 75.0  # battery_level

    def test_risk_level_classification(self, analytics_engine):
        """Test risk level classification."""
        assert analytics_engine._get_risk_level(0.9) == "critical"
        assert analytics_engine._get_risk_level(0.7) == "high"
        assert analytics_engine._get_risk_level(0.5) == "medium"
        assert analytics_engine._get_risk_level(0.3) == "low"
        assert analytics_engine._get_risk_level(0.1) == "minimal"

    def test_confidence_calculation(self, analytics_engine):
        """Test confidence calculation."""
        confidence = analytics_engine._calculate_confidence(0.9, 0.8)
        assert 0.8 <= confidence <= 1.0

        confidence = analytics_engine._calculate_confidence(0.5, 0.0)
        assert confidence == 0.8

    @pytest.mark.asyncio
    async def test_rule_based_prediction(self, analytics_engine, sample_metrics):
        """Test rule-based prediction fallback."""
        prediction = await analytics_engine._rule_based_prediction("test_device", sample_metrics)

        assert prediction["device_id"] == "test_device"
        assert "failure_probability" in prediction
        assert "risk_level" in prediction
        assert "recommendations" in prediction
        assert "predicted_at" in prediction
        assert prediction["model_version"] == "rule-based"

    @pytest.mark.asyncio
    async def test_maintenance_recommendations(self, analytics_engine):
        """Test maintenance recommendation generation."""
        high_risk_metrics = {
            "battery_level": 15,
            "error_rate": 0.15,
            "signal_strength": -85,
            "response_time": 1500,
        }

        recommendations = await analytics_engine._generate_maintenance_recommendations(
            "test_device", high_risk_metrics, 0.7, -0.8,
        )

        assert len(recommendations) > 0
        assert any("battery" in rec.lower() for rec in recommendations)
        assert any("error" in rec.lower() for rec in recommendations)

    @pytest.mark.asyncio
    async def test_training_data_preparation(self, analytics_engine, sample_training_data):
        """Test training data preparation."""
        df = pd.DataFrame(sample_training_data)
        X, y_failure, y_anomaly = analytics_engine._prepare_training_data(df)

        assert X.shape[0] == len(sample_training_data)
        assert X.shape[1] == len(analytics_engine.feature_columns)
        assert len(y_failure) == len(sample_training_data)
        assert len(y_anomaly) == len(sample_training_data)
        assert all(label in [0, 1] for label in y_failure)
        assert all(label in [0, 1] for label in y_anomaly)

    @pytest.mark.asyncio
    async def test_model_training(self, analytics_engine, sample_training_data):
        """Test model training functionality."""
        await analytics_engine.train_models(sample_training_data)

        assert analytics_engine.is_trained
        assert analytics_engine.models["failure_prediction"] is not None
        assert analytics_engine.models["anomaly_detection"] is not None
        assert "accuracy" in analytics_engine.model_performance

    @pytest.mark.asyncio
    async def test_device_failure_prediction(self, analytics_engine, sample_metrics):
        """Test device failure prediction."""
        # Test with trained models
        analytics_engine.is_trained = True
        analytics_engine.models["failure_prediction"] = Mock()
        analytics_engine.models["anomaly_detection"] = Mock()
        analytics_engine.scalers["failure_prediction"] = Mock()

        # Mock model predictions
        analytics_engine.models["failure_prediction"].predict_proba.return_value = [[0.3, 0.7]]
        analytics_engine.models["anomaly_detection"].decision_function.return_value = [-0.5]
        analytics_engine.models["anomaly_detection"].predict.return_value = [-1]
        analytics_engine.scalers["failure_prediction"].transform.return_value = [[0.1, 0.2, 0.3]]

        prediction = await analytics_engine.predict_device_failure("test_device", sample_metrics)

        assert prediction["device_id"] == "test_device"
        assert prediction["failure_probability"] == 70.0
        assert prediction["risk_level"] == "high"
        assert prediction["is_anomaly"] is True
        assert "recommendations" in prediction

    @pytest.mark.asyncio
    async def test_predict_all_devices(self, analytics_engine):
        """Test prediction for multiple devices."""
        devices_metrics = {
            "device1": {"response_time": 500, "error_rate": 0.05, "battery_level": 75},
            "device2": {"response_time": 2000, "error_rate": 0.15, "battery_level": 15},
        }

        # Mock the predict_device_failure method
        with patch.object(analytics_engine, "predict_device_failure") as mock_predict:
            mock_predict.side_effect = [
                {"device_id": "device1", "failure_probability": 20.0, "risk_level": "low"},
                {"device_id": "device2", "failure_probability": 80.0, "risk_level": "critical"},
            ]

            predictions = await analytics_engine.predict_all_devices(devices_metrics)

            assert len(predictions) == 2
            assert predictions[0]["device_id"] == "device1"
            assert predictions[1]["device_id"] == "device2"

    def test_model_status(self, analytics_engine):
        """Test model status retrieval."""
        analytics_engine.is_trained = True
        analytics_engine.model_performance = {"accuracy": 0.85, "precision": 0.80}

        status = analytics_engine.get_model_status()

        assert status["is_trained"] is True
        assert status["model_performance"]["accuracy"] == 0.85
        assert "feature_columns" in status
        assert "last_updated" in status


class TestPredictionsAPI:
    """Test cases for predictions API endpoints."""

    @pytest.fixture
    def mock_repository(self):
        """Mock device repository."""
        repository = Mock()
        repository.get_devices.return_value = [
            Mock(id="device1", name="Test Device 1"),
            Mock(id="device2", name="Test Device 2"),
        ]
        repository.get_device.return_value = Mock(id="device1", name="Test Device 1")
        repository.get_all_devices.return_value = [
            Mock(id="device1", name="Test Device 1"),
            Mock(id="device2", name="Test Device 2"),
        ]
        repository.get_device_metrics.return_value = {
            "response_time": 500,
            "error_rate": 0.05,
            "battery_level": 75,
        }
        return repository

    @pytest.fixture
    def mock_analytics_engine(self):
        """Mock analytics engine."""
        engine = Mock()
        engine.predict_all_devices.return_value = [
            {"device_id": "device1", "failure_probability": 20.0, "risk_level": "low"},
            {"device_id": "device2", "failure_probability": 80.0, "risk_level": "critical"},
        ]
        engine.predict_device_failure.return_value = {
            "device_id": "device1",
            "failure_probability": 20.0,
            "risk_level": "low",
            "recommendations": ["Device operating normally"],
        }
        engine.is_trained = True
        engine.get_model_status.return_value = {
            "is_trained": True,
            "model_performance": {"accuracy": 0.85},
        }
        return engine

    @pytest.mark.asyncio
    async def test_get_failure_predictions(self, mock_repository, mock_analytics_engine):
        """Test getting failure predictions for all devices."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(router)

        with patch("src.api.predictions_router.get_device_repository", return_value=mock_repository):
            with patch("src.api.predictions_router.get_analytics_engine", return_value=mock_analytics_engine):
                client = TestClient(app)
                response = client.get("/api/predictions/failures")

                assert response.status_code == 200
                data = response.json()
                assert "total_predictions" in data
                assert "predictions" in data
                assert len(data["predictions"]) == 2

    @pytest.mark.asyncio
    async def test_get_device_failure_prediction(self, mock_repository, mock_analytics_engine):
        """Test getting failure prediction for specific device."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(router)

        with patch("src.api.predictions_router.get_device_repository", return_value=mock_repository):
            with patch("src.api.predictions_router.get_analytics_engine", return_value=mock_analytics_engine):
                client = TestClient(app)
                response = client.get("/api/predictions/failures/device1")

                assert response.status_code == 200
                data = response.json()
                assert data["device_id"] == "device1"
                assert "failure_probability" in data
                assert "risk_level" in data

    @pytest.mark.asyncio
    async def test_get_maintenance_recommendations(self, mock_repository, mock_analytics_engine):
        """Test getting maintenance recommendations."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(router)

        with patch("src.api.predictions_router.get_device_repository", return_value=mock_repository):
            with patch("src.api.predictions_router.get_analytics_engine", return_value=mock_analytics_engine):
                client = TestClient(app)
                response = client.get("/api/predictions/maintenance")

                assert response.status_code == 200
                data = response.json()
                assert "total_recommendations" in data
                assert "recommendations" in data

    @pytest.mark.asyncio
    async def test_get_model_status(self, mock_analytics_engine):
        """Test getting model status."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(router)

        with patch("src.api.predictions_router.get_analytics_engine", return_value=mock_analytics_engine):
            client = TestClient(app)
            response = client.get("/api/predictions/models/status")

            assert response.status_code == 200
            data = response.json()
            assert data["is_trained"] is True
            assert "model_performance" in data

    @pytest.mark.asyncio
    async def test_trigger_model_training(self, mock_analytics_engine):
        """Test triggering model training."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(router)

        with patch("src.api.predictions_router.get_analytics_engine", return_value=mock_analytics_engine):
            client = TestClient(app)
            response = client.post("/api/predictions/train", json={"force_retrain": False})

            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert "status" in data

    @pytest.mark.asyncio
    async def test_predict_device_failure_custom(self, mock_analytics_engine):
        """Test custom device failure prediction."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(router)

        with patch("src.api.predictions_router.get_analytics_engine", return_value=mock_analytics_engine):
            client = TestClient(app)
            response = client.post("/api/predictions/predict", json={
                "device_id": "test_device",
                "metrics": {"response_time": 1000, "error_rate": 0.1},
            })

            assert response.status_code == 200
            data = response.json()
            assert data["device_id"] == "device1"

    @pytest.mark.asyncio
    async def test_get_predictions_health(self):
        """Test predictions service health endpoint."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(router)

        client = TestClient(app)
        response = client.get("/api/predictions/health")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Predictive Analytics"
        assert "status" in data


@pytest.mark.asyncio
async def test_integration_scenario():
    """Integration test for complete predictive analytics workflow."""
    # Create analytics engine
    engine = PredictiveAnalyticsEngine()

    # Generate sample training data
    np.random.seed(42)
    training_data = []
    for _i in range(200):
        training_data.append({
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
            "data_transfer_rate": np.random.normal(1000, 200),
        })

    # Train models
    await engine.train_models(training_data)

    # Test predictions
    test_metrics = {
        "response_time": 1500,
        "error_rate": 0.12,
        "battery_level": 15,
        "signal_strength": -75,
        "usage_frequency": 0.6,
        "temperature": 30,
        "humidity": 60,
        "uptime_hours": 50,
        "restart_count": 5,
        "connection_drops": 8,
        "data_transfer_rate": 800,
    }

    prediction = await engine.predict_device_failure("test_device", test_metrics)

    # Verify prediction structure
    assert "device_id" in prediction
    assert "failure_probability" in prediction
    assert "risk_level" in prediction
    assert "recommendations" in prediction
    assert "predicted_at" in prediction

    # Verify model status
    status = engine.get_model_status()
    assert status["is_trained"] is True
    assert "model_performance" in status
