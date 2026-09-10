"""
Shared utility functions for ML algorithms.
"""

import numpy as np
from sklearn.preprocessing import StandardScaler


def scale_features(data: list[list[float]]) -> np.ndarray:
    """Scale features using a per-request StandardScaler.

    Using per-request scalers prevents data leakage between different calls
    and ensures garbage collection can reclaim memory when the call exits.
    """
    scaler = StandardScaler()
    return scaler.fit_transform(np.array(data, dtype=np.float64))
