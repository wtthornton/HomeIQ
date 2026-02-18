"""Unit tests for sensor data loader."""

import numpy as np
import pytest

pytest.importorskip("polars")
from src.data.sensor_loader import ACTIVITY_LABELS, SensorDataLoader


def test_activity_labels_has_ten_classes() -> None:
    """ACTIVITY_LABELS maps 0-9 to names."""
    assert len(ACTIVITY_LABELS) == 10
    assert ACTIVITY_LABELS[0] == "sleeping"


def test_create_synthetic_data_shape() -> None:
    """Synthetic data has expected columns and length."""
    loader = SensorDataLoader()
    df = loader._create_synthetic_data(n_samples=100)
    assert len(df) == 100
    assert "timestamp" in df.columns
    assert "motion" in df.columns
    assert "activity_label" in df.columns


def test_generate_activity_labels_vectorized() -> None:
    """_generate_activity_labels produces 0-9 labels from hours."""
    loader = SensorDataLoader()
    rng = np.random.default_rng(42)
    hour_of_day = np.array([0, 6, 8, 12, 17, 23])
    n_samples = len(hour_of_day)
    labels = loader._generate_activity_labels(hour_of_day, n_samples, rng)
    assert labels.shape == (n_samples,)
    assert set(labels) <= set(range(10))
