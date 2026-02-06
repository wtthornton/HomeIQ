"""
Energy Forecasting Model using Darts

Modern time series forecasting using the Darts library with:
- N-HiTS: Fast and accurate neural forecasting
- TFT: Temporal Fusion Transformer for interpretability
- Statistical baselines for comparison
"""

import json
import pickle
from pathlib import Path
from typing import Any

import numpy as np
import structlog

logger = structlog.get_logger(__name__)


class EnergyForecaster:
    """
    Energy forecasting using Darts library.

    Supports multiple models:
    - N-HiTS: Neural Hierarchical Interpolation for Time Series
    - TFT: Temporal Fusion Transformer
    - Prophet: Facebook's forecasting model
    - ARIMA: Statistical baseline
    """

    SUPPORTED_MODELS = ["nhits", "tft", "prophet", "arima", "naive"]

    def __init__(
        self,
        model_type: str = "nhits",
        input_chunk_length: int = 168,  # 1 week of hourly data
        output_chunk_length: int = 48,  # 2 days forecast
        **model_kwargs,
    ):
        """
        Initialize the energy forecaster.

        Args:
            model_type: Type of model ('nhits', 'tft', 'prophet', 'arima', 'naive')
            input_chunk_length: Number of past time steps to use
            output_chunk_length: Number of future time steps to predict
            **model_kwargs: Additional model-specific parameters
        """
        if model_type not in self.SUPPORTED_MODELS:
            raise ValueError(f"Model type must be one of {self.SUPPORTED_MODELS}")

        self.model_type = model_type
        self.input_chunk_length = input_chunk_length
        self.output_chunk_length = output_chunk_length
        self.model_kwargs = model_kwargs

        self.model = None
        self.scaler = None
        self._is_fitted = False

        # Initialize model
        self._init_model()

    def _init_model(self) -> None:
        """Initialize the forecasting model."""
        try:
            from darts.dataprocessing.transformers import Scaler
        except ImportError:
            raise ImportError("Please install darts: pip install darts>=0.30.0")

        self.scaler = Scaler()

        if self.model_type == "nhits":
            self._init_nhits()
        elif self.model_type == "tft":
            self._init_tft()
        elif self.model_type == "prophet":
            self._init_prophet()
        elif self.model_type == "arima":
            self._init_arima()
        elif self.model_type == "naive":
            self._init_naive()

    def _init_nhits(self) -> None:
        """Initialize N-HiTS model."""
        from darts.models import NHiTSModel

        default_kwargs = {
            "num_stacks": 3,
            "num_blocks": 1,
            "num_layers": 2,
            "layer_widths": 256,
            "pooling_kernel_sizes": None,
            "n_freq_downsample": None,
            "dropout": 0.1,
            "activation": "ReLU",
            "batch_size": 32,
            "n_epochs": 100,
            "random_state": 42,
            "pl_trainer_kwargs": {"accelerator": "cpu"},
        }
        default_kwargs.update(self.model_kwargs)

        self.model = NHiTSModel(
            input_chunk_length=self.input_chunk_length,
            output_chunk_length=self.output_chunk_length,
            **default_kwargs,
        )

        logger.info("Initialized N-HiTS model")

    def _init_tft(self) -> None:
        """Initialize Temporal Fusion Transformer model."""
        from darts.models import TFTModel

        default_kwargs = {
            "hidden_size": 64,
            "lstm_layers": 1,
            "num_attention_heads": 4,
            "dropout": 0.1,
            "batch_size": 32,
            "n_epochs": 100,
            "random_state": 42,
            "pl_trainer_kwargs": {"accelerator": "cpu"},
        }
        default_kwargs.update(self.model_kwargs)

        self.model = TFTModel(
            input_chunk_length=self.input_chunk_length,
            output_chunk_length=self.output_chunk_length,
            **default_kwargs,
        )

        logger.info("Initialized TFT model")

    def _init_prophet(self) -> None:
        """Initialize Prophet model."""
        from darts.models import Prophet

        default_kwargs = {
            "yearly_seasonality": True,
            "weekly_seasonality": True,
            "daily_seasonality": True,
        }
        default_kwargs.update(self.model_kwargs)

        self.model = Prophet(**default_kwargs)

        logger.info("Initialized Prophet model")

    def _init_arima(self) -> None:
        """Initialize ARIMA model."""
        from darts.models import AutoARIMA

        default_kwargs = {
            "start_p": 1,
            "start_q": 1,
            "max_p": 5,
            "max_q": 5,
            "seasonal": True,
            "m": 24,  # Hourly seasonality
        }
        default_kwargs.update(self.model_kwargs)

        self.model = AutoARIMA(**default_kwargs)

        logger.info("Initialized AutoARIMA model")

    def _init_naive(self) -> None:
        """Initialize Naive baseline model."""
        from darts.models import NaiveSeasonal

        self.model = NaiveSeasonal(K=24)  # Use same hour yesterday

        logger.info("Initialized Naive Seasonal model")

    def fit(self, series, val_series=None) -> "EnergyForecaster":
        """
        Train the forecasting model.

        Args:
            series: Darts TimeSeries for training
            val_series: Optional validation series

        Returns:
            Self for method chaining
        """
        logger.info("Training model", model_type=self.model_type)

        # Scale data
        scaled_series = self.scaler.fit_transform(series)

        # Train model
        if val_series is not None:
            scaled_val = self.scaler.transform(val_series)
            if self.model_type in ["nhits", "tft"]:
                self.model.fit(scaled_series, val_series=scaled_val)
            else:
                self.model.fit(scaled_series)
        else:
            self.model.fit(scaled_series)

        self._is_fitted = True
        logger.info("Model training complete")

        return self

    def predict(self, n: int | None = None, series=None):
        """
        Generate forecast.

        Args:
            n: Number of time steps to forecast (default: output_chunk_length)
            series: Optional series to forecast from (for models that need it)

        Returns:
            Darts TimeSeries with forecast
        """
        if not self._is_fitted:
            raise RuntimeError("Model must be fitted before predicting")

        n = n or self.output_chunk_length

        # Generate forecast
        if series is not None:
            scaled_series = self.scaler.transform(series)
            forecast = self.model.predict(n=n, series=scaled_series)
        else:
            forecast = self.model.predict(n=n)

        # Inverse transform
        forecast = self.scaler.inverse_transform(forecast)

        return forecast

    def evaluate(self, test_series, metrics: list[str] | None = None) -> dict[str, float]:
        """
        Evaluate model on test data.

        Args:
            test_series: Darts TimeSeries for testing
            metrics: List of metrics to compute

        Returns:
            Dictionary of metric values
        """
        from darts.metrics import mape, rmse, mae

        if metrics is None:
            metrics = ["mape", "rmse", "mae"]

        # Generate forecast for test period
        n = len(test_series)
        if n > self.output_chunk_length:
            logger.warning(
                "Test series length exceeds output_chunk_length. "
                "Model will auto-regress, which may reduce accuracy.",
                test_length=n,
                output_chunk_length=self.output_chunk_length,
            )
        forecast = self.predict(n=n)

        results = {}

        if "mape" in metrics:
            results["mape"] = mape(test_series, forecast)
        if "rmse" in metrics:
            results["rmse"] = rmse(test_series, forecast)
        if "mae" in metrics:
            results["mae"] = mae(test_series, forecast)

        logger.info("Evaluation results", **{k: round(v, 4) for k, v in results.items()})

        return results

    def save(self, path: Path | str) -> None:
        """Save model to disk."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Save config as JSON (not pickle) for security
        config = {
            "model_type": self.model_type,
            "input_chunk_length": self.input_chunk_length,
            "output_chunk_length": self.output_chunk_length,
            "model_kwargs": self.model_kwargs,
        }
        with open(path.with_suffix(".config.json"), "w") as f:
            json.dump(config, f, indent=2)

        # Save model
        if self.model_type in ["nhits", "tft"]:
            self.model.save(str(path.with_suffix(".pt")))
        else:
            # Model and scaler still use pickle (Darts objects are complex),
            # but should only be loaded from trusted sources
            with open(path.with_suffix(".pkl"), "wb") as f:
                pickle.dump(self.model, f)

        # Save scaler
        with open(path.with_suffix(".scaler.pkl"), "wb") as f:
            pickle.dump(self.scaler, f)

        logger.info("Saved model", path=str(path))

    @classmethod
    def load(cls, path: Path | str) -> "EnergyForecaster":
        """Load model from disk."""
        path = Path(path)

        # Load config from JSON instead of pickle
        config_path_json = path.with_suffix(".config.json")
        config_path_pkl = path.with_suffix(".config.pkl")

        if config_path_json.exists():
            with open(config_path_json, "r") as f:
                config = json.load(f)
        elif config_path_pkl.exists():
            # Fallback to pickle for backward compatibility, but log warning
            logger.warning(
                "Loading config from pickle (deprecated). "
                "Re-save model to migrate to JSON config."
            )
            with open(config_path_pkl, "rb") as f:
                config = pickle.load(f)
        else:
            raise FileNotFoundError(f"No model config found at {path}")

        # Validate config keys
        required_keys = {"model_type", "input_chunk_length", "output_chunk_length"}
        if not required_keys.issubset(config.keys()):
            raise ValueError(
                f"Invalid model config. Missing keys: {required_keys - config.keys()}"
            )

        if config["model_type"] not in cls.SUPPORTED_MODELS:
            raise ValueError(f"Unknown model_type in config: {config['model_type']}")

        # Create instance
        instance = cls(
            model_type=config["model_type"],
            input_chunk_length=config["input_chunk_length"],
            output_chunk_length=config["output_chunk_length"],
            **config.get("model_kwargs", {}),
        )

        # Load model
        if config["model_type"] in ["nhits", "tft"]:
            from darts.models import NHiTSModel, TFTModel
            model_class = NHiTSModel if config["model_type"] == "nhits" else TFTModel
            instance.model = model_class.load(str(path.with_suffix(".pt")))
        else:
            with open(path.with_suffix(".pkl"), "rb") as f:
                instance.model = pickle.load(f)

        # Load scaler
        with open(path.with_suffix(".scaler.pkl"), "rb") as f:
            instance.scaler = pickle.load(f)

        instance._is_fitted = True

        logger.info("Loaded model", path=str(path))

        return instance

    def get_model_info(self) -> dict[str, Any]:
        """Get model information."""
        from .. import __version__
        return {
            "model_type": self.model_type,
            "input_chunk_length": self.input_chunk_length,
            "output_chunk_length": self.output_chunk_length,
            "is_fitted": self._is_fitted,
            "version": __version__,
        }
