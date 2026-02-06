"""Shared test fixtures for energy forecasting service."""

import json
import pickle
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import polars as pl
import pytest


@pytest.fixture
def sample_polars_df():
    """Create a sample Polars DataFrame with energy data."""
    np.random.seed(42)
    n = 24 * 14  # 2 weeks of hourly data
    timestamps = pd.date_range("2024-01-01", periods=n, freq="h")
    values = 200 + 100 * np.sin(2 * np.pi * np.arange(n) / 24) + np.random.normal(0, 10, n)

    return pl.DataFrame({
        "timestamp": timestamps.to_pydatetime().tolist(),
        "power": values,
    })


@pytest.fixture
def sample_series():
    """Create a sample Darts TimeSeries for testing."""
    from darts import TimeSeries

    np.random.seed(42)
    n = 24 * 14  # 2 weeks
    timestamps = pd.date_range("2024-01-01", periods=n, freq="h")
    values = 200 + 100 * np.sin(2 * np.pi * np.arange(n) / 24) + np.random.normal(0, 10, n)

    return TimeSeries.from_dataframe(
        pd.DataFrame({"timestamp": timestamps, "power": values}),
        time_col="timestamp",
        value_cols="power",
    )


@pytest.fixture
def trained_forecaster(sample_series):
    """Create a trained naive forecaster for testing."""
    from src.models.energy_forecaster import EnergyForecaster

    forecaster = EnergyForecaster(
        model_type="naive", input_chunk_length=24, output_chunk_length=24
    )
    train, _ = sample_series.split_after(0.8)
    forecaster.fit(train)
    return forecaster


@pytest.fixture
def test_client(trained_forecaster):
    """Create a test client with a loaded model."""
    from fastapi.testclient import TestClient

    from src.api.routes import model_registry
    from src.main import app

    model_registry.set_forecaster(trained_forecaster)
    client = TestClient(app)
    yield client
    # Cleanup: reset model after tests
    model_registry.set_forecaster(None)


@pytest.fixture
def test_client_no_model():
    """Create a test client without a loaded model."""
    from fastapi.testclient import TestClient

    from src.api.routes import model_registry
    from src.main import app

    model_registry.set_forecaster(None)
    client = TestClient(app)
    yield client


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def model_save_path(temp_dir):
    """Provide a path for saving/loading models."""
    return temp_dir / "test_model"
