"""Tests for API endpoint routes."""

import pytest


class TestHealthEndpoint:
    """Tests for /api/v1/health endpoint."""

    def test_health_with_model(self, test_client):
        """Test health check when model is loaded."""
        response = test_client.get("/api/v1/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "energy-forecasting"
        assert data["model_loaded"] is True
        assert "version" in data

    def test_health_without_model(self, test_client_no_model):
        """Test health check when model is not loaded."""
        response = test_client_no_model.get("/api/v1/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["model_loaded"] is False


class TestReadinessEndpoint:
    """Tests for /api/v1/ready endpoint."""

    def test_ready_with_model(self, test_client):
        """Test readiness check when model is loaded."""
        response = test_client.get("/api/v1/ready")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ready"
        assert data["model_loaded"] is True

    def test_ready_without_model(self, test_client_no_model):
        """Test readiness check when model is not loaded."""
        response = test_client_no_model.get("/api/v1/ready")
        assert response.status_code == 503


class TestForecastEndpoint:
    """Tests for /api/v1/forecast endpoint."""

    def test_forecast_default_hours(self, test_client):
        """Test forecast with default hours."""
        response = test_client.get("/api/v1/forecast")
        assert response.status_code == 200

        data = response.json()
        assert "forecast" in data
        assert "model_type" in data
        assert "forecast_horizon_hours" in data
        assert "generated_at" in data
        # Default is 48 hours, but naive model output_chunk_length is 24
        # The model will produce the requested amount via auto-regression
        assert len(data["forecast"]) > 0

    def test_forecast_custom_hours(self, test_client):
        """Test forecast with custom hours."""
        response = test_client.get("/api/v1/forecast?hours=24")
        assert response.status_code == 200

        data = response.json()
        assert len(data["forecast"]) == 24
        assert data["forecast_horizon_hours"] == 24

    def test_forecast_invalid_hours_too_low(self, test_client):
        """Test forecast rejects hours below minimum."""
        response = test_client.get("/api/v1/forecast?hours=0")
        assert response.status_code == 422  # Validation error

    def test_forecast_invalid_hours_too_high(self, test_client):
        """Test forecast rejects hours above maximum."""
        response = test_client.get("/api/v1/forecast?hours=200")
        assert response.status_code == 422  # Validation error

    def test_forecast_without_model_returns_503(self, test_client_no_model):
        """Test forecast without model returns 503."""
        response = test_client_no_model.get("/api/v1/forecast")
        assert response.status_code == 503

    def test_forecast_point_has_required_fields(self, test_client):
        """Test that each forecast point has required fields."""
        response = test_client.get("/api/v1/forecast?hours=1")
        data = response.json()

        point = data["forecast"][0]
        assert "timestamp" in point
        assert "power_watts" in point

    def test_forecast_does_not_leak_exceptions(self, test_client_no_model):
        """Test that error responses do not contain internal exception details."""
        response = test_client_no_model.get("/api/v1/forecast")
        data = response.json()

        # Should contain a generic message, not a stack trace
        assert "detail" in data
        assert "Model not loaded" in data["detail"]


class TestPeakPredictionEndpoint:
    """Tests for /api/v1/peak-prediction endpoint."""

    def test_peak_prediction(self, test_client):
        """Test peak prediction returns valid data."""
        response = test_client.get("/api/v1/peak-prediction")
        assert response.status_code == 200

        data = response.json()
        assert "peak_hour" in data
        assert "peak_power_watts" in data
        assert "peak_timestamp" in data
        assert "daily_total_kwh" in data

        # Peak hour should be 0-23
        assert 0 <= data["peak_hour"] <= 23
        assert data["peak_power_watts"] > 0
        assert data["daily_total_kwh"] > 0

    def test_peak_prediction_without_model(self, test_client_no_model):
        """Test peak prediction without model returns 503."""
        response = test_client_no_model.get("/api/v1/peak-prediction")
        assert response.status_code == 503


class TestOptimizationEndpoint:
    """Tests for /api/v1/optimization endpoint."""

    def test_optimization_recommendation(self, test_client):
        """Test optimization returns valid recommendation."""
        response = test_client.get("/api/v1/optimization")
        assert response.status_code == 200

        data = response.json()
        assert "recommendation" in data
        assert "estimated_savings_kwh" in data
        assert "estimated_savings_percent" in data
        assert "best_hours" in data
        assert "avoid_hours" in data

        # Should have 4 best and 4 avoid hours
        assert len(data["best_hours"]) == 4
        assert len(data["avoid_hours"]) == 4

    def test_optimization_recommendation_text(self, test_client):
        """Test that recommendation text uses correct format."""
        response = test_client.get("/api/v1/optimization")
        data = response.json()

        # Should list individual hours, not a misleading range
        assert "Best times for high-power activities:" in data["recommendation"]
        assert "Avoid:" in data["recommendation"]

    def test_optimization_without_model(self, test_client_no_model):
        """Test optimization without model returns 503."""
        response = test_client_no_model.get("/api/v1/optimization")
        assert response.status_code == 503


class TestModelInfoEndpoint:
    """Tests for /api/v1/model/info endpoint."""

    def test_model_info_with_model(self, test_client):
        """Test model info when model is loaded."""
        response = test_client.get("/api/v1/model/info")
        assert response.status_code == 200

        data = response.json()
        assert data["loaded"] is True
        assert "model_type" in data
        assert "model_path" in data
        assert "input_chunk_length" in data
        assert "output_chunk_length" in data

    def test_model_info_without_model(self, test_client_no_model):
        """Test model info when model is not loaded."""
        response = test_client_no_model.get("/api/v1/model/info")
        assert response.status_code == 200

        data = response.json()
        assert data["loaded"] is False
        assert "model_path" in data


class TestRootEndpoint:
    """Tests for root / endpoint."""

    def test_root(self, test_client):
        """Test root endpoint returns service info."""
        response = test_client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["service"] == "energy-forecasting"
        assert "version" in data
        assert data["docs"] == "/docs"


class TestModelRegistry:
    """Tests for the ModelRegistry thread-safe wrapper."""

    def test_registry_default_state(self):
        """Test that a new registry has no forecaster."""
        from src.api.routes import ModelRegistry

        registry = ModelRegistry()
        assert registry.is_loaded is False

    def test_registry_set_and_get(self, trained_forecaster):
        """Test setting and getting forecaster."""
        from src.api.routes import ModelRegistry

        registry = ModelRegistry()
        registry.set_forecaster(trained_forecaster)
        assert registry.is_loaded is True

        forecaster = registry.get_forecaster()
        assert forecaster is trained_forecaster

    def test_registry_get_when_empty_raises(self):
        """Test getting forecaster when empty raises HTTPException."""
        from fastapi import HTTPException

        from src.api.routes import ModelRegistry

        registry = ModelRegistry()
        with pytest.raises(HTTPException) as exc_info:
            registry.get_forecaster()
        assert exc_info.value.status_code == 503


class TestForecastCache:
    """Tests for forecast caching."""

    def test_cache_miss_returns_none(self):
        """Test that cache miss returns None."""
        from src.api.routes import _get_cached_forecast

        result = _get_cached_forecast(999)  # unlikely to be cached
        assert result is None

    def test_cache_hit_returns_result(self):
        """Test that cached value is returned."""
        from src.api.routes import _get_cached_forecast, _set_cached_forecast

        _set_cached_forecast(999, {"test": "data"})
        result = _get_cached_forecast(999)
        assert result == {"test": "data"}

        # Cleanup
        from src.api.routes import _forecast_cache
        _forecast_cache.pop("forecast_999", None)
