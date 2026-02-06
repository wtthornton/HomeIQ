"""Unit tests for EnergyForecaster model."""

import json
import pickle
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest


class TestEnergyForecasterInit:
    """Tests for EnergyForecaster initialization."""

    def test_init_naive(self):
        """Test initializing a naive forecaster."""
        from src.models.energy_forecaster import EnergyForecaster

        forecaster = EnergyForecaster(
            model_type="naive",
            input_chunk_length=24,
            output_chunk_length=24,
        )
        assert forecaster.model_type == "naive"
        assert forecaster.input_chunk_length == 24
        assert forecaster.output_chunk_length == 24
        assert forecaster.model is not None
        assert forecaster.scaler is not None
        assert forecaster._is_fitted is False

    def test_init_invalid_model_type(self):
        """Test that invalid model type raises ValueError."""
        from src.models.energy_forecaster import EnergyForecaster

        with pytest.raises(ValueError, match="Model type must be one of"):
            EnergyForecaster(model_type="invalid_model")

    def test_supported_models_list(self):
        """Test that SUPPORTED_MODELS contains expected types."""
        from src.models.energy_forecaster import EnergyForecaster

        assert "nhits" in EnergyForecaster.SUPPORTED_MODELS
        assert "tft" in EnergyForecaster.SUPPORTED_MODELS
        assert "prophet" in EnergyForecaster.SUPPORTED_MODELS
        assert "arima" in EnergyForecaster.SUPPORTED_MODELS
        assert "naive" in EnergyForecaster.SUPPORTED_MODELS

    def test_init_stores_kwargs(self):
        """Test that extra kwargs are stored."""
        from src.models.energy_forecaster import EnergyForecaster

        forecaster = EnergyForecaster(
            model_type="naive",
            input_chunk_length=24,
            output_chunk_length=24,
            custom_param="value",
        )
        assert forecaster.model_kwargs == {"custom_param": "value"}


class TestEnergyForecasterFit:
    """Tests for EnergyForecaster fitting."""

    def test_fit_sets_is_fitted(self, sample_series):
        """Test that fitting sets the _is_fitted flag."""
        from src.models.energy_forecaster import EnergyForecaster

        forecaster = EnergyForecaster(
            model_type="naive", input_chunk_length=24, output_chunk_length=24
        )
        assert forecaster._is_fitted is False
        forecaster.fit(sample_series)
        assert forecaster._is_fitted is True

    def test_fit_returns_self(self, sample_series):
        """Test that fit returns self for method chaining."""
        from src.models.energy_forecaster import EnergyForecaster

        forecaster = EnergyForecaster(
            model_type="naive", input_chunk_length=24, output_chunk_length=24
        )
        result = forecaster.fit(sample_series)
        assert result is forecaster


class TestEnergyForecasterPredict:
    """Tests for EnergyForecaster prediction."""

    def test_predict_without_fit_raises(self):
        """Test that predicting without fitting raises RuntimeError."""
        from src.models.energy_forecaster import EnergyForecaster

        forecaster = EnergyForecaster(
            model_type="naive", input_chunk_length=24, output_chunk_length=24
        )
        with pytest.raises(RuntimeError, match="Model must be fitted"):
            forecaster.predict(n=24)

    def test_predict_returns_correct_length(self, trained_forecaster):
        """Test that prediction returns correct number of time steps."""
        forecast = trained_forecaster.predict(n=24)
        assert len(forecast) == 24

    def test_predict_default_length(self, trained_forecaster):
        """Test that prediction uses output_chunk_length as default."""
        forecast = trained_forecaster.predict()
        assert len(forecast) == trained_forecaster.output_chunk_length

    def test_predict_values_are_reasonable(self, trained_forecaster):
        """Test that predicted values are within reasonable bounds."""
        forecast = trained_forecaster.predict(n=24)
        values = forecast.values().flatten()

        # Values should be positive (energy consumption)
        # and within a reasonable range for the synthetic data
        assert all(np.isfinite(values))
        assert values.mean() > 0


class TestEnergyForecasterSaveLoad:
    """Tests for model save/load round-trip."""

    def test_save_creates_json_config(self, trained_forecaster, model_save_path):
        """Test that save creates a JSON config file (not pickle)."""
        trained_forecaster.save(model_save_path)

        config_path = model_save_path.with_suffix(".config.json")
        assert config_path.exists()

        with open(config_path, "r") as f:
            config = json.load(f)

        assert config["model_type"] == "naive"
        assert config["input_chunk_length"] == 24
        assert config["output_chunk_length"] == 24

    def test_save_creates_scaler_file(self, trained_forecaster, model_save_path):
        """Test that save creates scaler pickle file."""
        trained_forecaster.save(model_save_path)
        assert model_save_path.with_suffix(".scaler.pkl").exists()

    def test_save_creates_model_file_for_non_neural(self, trained_forecaster, model_save_path):
        """Test that save creates model pickle file for non-neural models."""
        trained_forecaster.save(model_save_path)
        assert model_save_path.with_suffix(".pkl").exists()

    def test_load_from_json_config(self, trained_forecaster, model_save_path):
        """Test loading a model saved with JSON config."""
        from src.models.energy_forecaster import EnergyForecaster

        trained_forecaster.save(model_save_path)
        loaded = EnergyForecaster.load(model_save_path)

        assert loaded.model_type == trained_forecaster.model_type
        assert loaded.input_chunk_length == trained_forecaster.input_chunk_length
        assert loaded.output_chunk_length == trained_forecaster.output_chunk_length
        assert loaded._is_fitted is True

    def test_load_from_pkl_config_backward_compat(self, trained_forecaster, model_save_path):
        """Test backward compatibility loading from pickle config."""
        from src.models.energy_forecaster import EnergyForecaster

        # Save normally (creates JSON config)
        trained_forecaster.save(model_save_path)

        # Remove JSON config and create pickle config instead
        json_path = model_save_path.with_suffix(".config.json")
        with open(json_path, "r") as f:
            config = json.load(f)
        json_path.unlink()

        pkl_path = model_save_path.with_suffix(".config.pkl")
        with open(pkl_path, "wb") as f:
            pickle.dump(config, f)

        # Should load from pickle with warning
        loaded = EnergyForecaster.load(model_save_path)
        assert loaded.model_type == "naive"

    def test_load_missing_config_raises(self, temp_dir):
        """Test that loading with no config file raises FileNotFoundError."""
        from src.models.energy_forecaster import EnergyForecaster

        with pytest.raises(FileNotFoundError, match="No model config found"):
            EnergyForecaster.load(temp_dir / "nonexistent_model")

    def test_load_invalid_model_type_raises(self, trained_forecaster, model_save_path):
        """Test that loading with invalid model_type in config raises ValueError."""
        from src.models.energy_forecaster import EnergyForecaster

        trained_forecaster.save(model_save_path)

        # Tamper with config
        config_path = model_save_path.with_suffix(".config.json")
        with open(config_path, "r") as f:
            config = json.load(f)
        config["model_type"] = "invalid"
        with open(config_path, "w") as f:
            json.dump(config, f)

        with pytest.raises(ValueError, match="Unknown model_type"):
            EnergyForecaster.load(model_save_path)

    def test_load_missing_config_keys_raises(self, trained_forecaster, model_save_path):
        """Test that loading with missing config keys raises ValueError."""
        from src.models.energy_forecaster import EnergyForecaster

        trained_forecaster.save(model_save_path)

        # Tamper with config - remove required key
        config_path = model_save_path.with_suffix(".config.json")
        with open(config_path, "w") as f:
            json.dump({"model_type": "naive"}, f)  # missing input/output chunk lengths

        with pytest.raises(ValueError, match="Invalid model config"):
            EnergyForecaster.load(model_save_path)

    def test_save_load_round_trip_predictions_match(self, trained_forecaster, model_save_path):
        """Test that predictions match after save/load round-trip."""
        from src.models.energy_forecaster import EnergyForecaster

        # Get prediction before save
        original_forecast = trained_forecaster.predict(n=24)

        # Save and reload
        trained_forecaster.save(model_save_path)
        loaded = EnergyForecaster.load(model_save_path)

        # Get prediction after load
        loaded_forecast = loaded.predict(n=24)

        np.testing.assert_array_almost_equal(
            original_forecast.values(),
            loaded_forecast.values(),
            decimal=5,
        )


class TestEnergyForecasterEvaluate:
    """Tests for model evaluation."""

    def test_evaluate_returns_metrics(self, trained_forecaster, sample_series):
        """Test that evaluate returns expected metrics."""
        _, test = sample_series.split_after(0.8)
        # Use only output_chunk_length points to avoid auto-regression warning
        test_subset = test[:trained_forecaster.output_chunk_length]

        results = trained_forecaster.evaluate(test_subset)

        assert "mape" in results
        assert "rmse" in results
        assert "mae" in results
        assert all(v >= 0 for v in results.values())

    def test_evaluate_custom_metrics(self, trained_forecaster, sample_series):
        """Test evaluate with custom metric list."""
        _, test = sample_series.split_after(0.8)
        test_subset = test[:trained_forecaster.output_chunk_length]

        results = trained_forecaster.evaluate(test_subset, metrics=["rmse"])
        assert "rmse" in results
        assert "mape" not in results


class TestEnergyForecasterModelInfo:
    """Tests for model info."""

    def test_get_model_info(self, trained_forecaster):
        """Test that get_model_info returns expected fields."""
        info = trained_forecaster.get_model_info()

        assert info["model_type"] == "naive"
        assert info["input_chunk_length"] == 24
        assert info["output_chunk_length"] == 24
        assert info["is_fitted"] is True
        assert "version" in info
