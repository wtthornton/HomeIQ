"""Unit tests for activity classifier model and ONNX helpers."""

import numpy as np
import pytest

pytest.importorskip("torch")
import torch
from src.models.activity_classifier import ACTIVITIES, ActivityLSTM


def test_activities_has_ten_classes() -> None:
    """ACTIVITIES maps 0-9 to activity names."""
    assert len(ACTIVITIES) == 10
    assert ACTIVITIES[0] == "sleeping"
    assert ACTIVITIES[9] == "other"


def test_activity_lstm_forward_shape() -> None:
    """Forward pass returns (batch, num_classes)."""
    model = ActivityLSTM(input_size=5, hidden_size=8, num_layers=1, num_classes=10)
    x = np.random.randn(2, 10, 5).astype(np.float32)
    t = torch.from_numpy(x)
    out = model(t)
    assert out.shape == (2, 10)
