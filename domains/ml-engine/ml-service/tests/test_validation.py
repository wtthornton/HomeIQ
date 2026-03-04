"""Tests for ML Service validation module."""

from __future__ import annotations

import pytest

from src.validation import (
    _estimate_payload_bytes,
    _validate_contamination,
    _validate_data_matrix,
)


def test_estimate_payload_bytes() -> None:
    assert _estimate_payload_bytes(100, 10) == 8000


def test_validate_contamination_valid() -> None:
    _validate_contamination(0.1)


def test_validate_contamination_too_low() -> None:
    with pytest.raises(ValueError, match="between 0 and 0.5"):
        _validate_contamination(0.0)


def test_validate_contamination_too_high() -> None:
    with pytest.raises(ValueError, match="between 0 and 0.5"):
        _validate_contamination(0.5)


def test_validate_data_matrix_valid() -> None:
    data = [[1.0, 2.0], [3.0, 4.0]]
    rows, cols = _validate_data_matrix(data)
    assert rows == 2
    assert cols == 2


def test_validate_data_matrix_empty() -> None:
    with pytest.raises(ValueError, match="at least one row"):
        _validate_data_matrix([])


def test_validate_data_matrix_nan() -> None:
    with pytest.raises(ValueError, match="NaN or Inf"):
        _validate_data_matrix([[float("nan"), 1.0]])
