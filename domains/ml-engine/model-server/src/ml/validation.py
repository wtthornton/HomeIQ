"""Data validation helpers for ML Service."""

from __future__ import annotations

import math
import os

import numpy as np

MAX_PAYLOAD_BYTES = int(os.getenv("ML_MAX_PAYLOAD_BYTES", str(10 * 1024 * 1024)))
MAX_DIMENSIONS = int(os.getenv("ML_MAX_DIMENSIONS", "1000"))
MAX_DATA_POINTS = int(os.getenv("ML_MAX_DATA_POINTS", "50000"))


def _estimate_payload_bytes(num_points: int, num_dimensions: int) -> int:
    """Approximate payload size as float64 (8 bytes per value)."""
    return num_points * num_dimensions * 8


def _validate_row_sample(rows: list[list[float]], expected_length: int) -> None:
    """Type-check a sample of rows for correct structure and numeric values."""
    for row in rows:
        if not isinstance(row, list):
            raise ValueError("Each data row must be a list of floats.")
        if len(row) != expected_length:
            raise ValueError("All rows must have the same number of features.")
        for value in row:
            if not isinstance(value, (int, float)):
                raise ValueError("All feature values must be numbers.")
            if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                raise ValueError("Data contains NaN or Inf values which are not supported.")


def _validate_numpy_array(data: list[list[float]], expected_cols: int) -> None:
    """Convert to numpy and validate for NaN/Inf across the full dataset."""
    try:
        arr = np.array(data, dtype=np.float64)
    except (ValueError, TypeError) as exc:
        raise ValueError("All feature values must be numbers.") from exc

    if np.any(np.isnan(arr)) or np.any(np.isinf(arr)):
        raise ValueError("Data contains NaN or Inf values which are not supported.")

    if arr.ndim != 2 or arr.shape[1] != expected_cols:
        raise ValueError("All rows must have the same number of features.")


def _validate_data_matrix(data: list[list[float]]) -> tuple[int, int]:
    """Validate that *data* is a well-formed numeric matrix."""
    if not isinstance(data, list) or not data:
        raise ValueError("Data must contain at least one row.")

    first_row_length = len(data[0])
    if first_row_length == 0:
        raise ValueError("Data rows must contain at least one feature.")
    if first_row_length > MAX_DIMENSIONS:
        raise ValueError(f"Maximum supported dimensions is {MAX_DIMENSIONS}.")

    num_points = len(data)
    if num_points > MAX_DATA_POINTS:
        raise ValueError(f"Maximum supported data points is {MAX_DATA_POINTS}.")

    sample_size = min(num_points, 100)
    _validate_row_sample(data[:sample_size], first_row_length)
    _validate_numpy_array(data, first_row_length)

    estimated_size = _estimate_payload_bytes(num_points, first_row_length)
    if estimated_size > MAX_PAYLOAD_BYTES:
        max_mb = MAX_PAYLOAD_BYTES / (1024 * 1024)
        raise ValueError(f"Payload exceeds the maximum allowed size of {max_mb:.1f}MB.")

    return num_points, first_row_length


def _validate_contamination(contamination: float) -> None:
    """Validate contamination parameter for anomaly detection."""
    if contamination <= 0 or contamination >= 0.5:
        raise ValueError("Contamination must be between 0 and 0.5 (exclusive).")
