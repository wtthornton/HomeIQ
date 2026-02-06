"""
Anomaly Detection Manager
Provides Isolation Forest for anomaly detection
"""

import logging

import numpy as np
from sklearn.ensemble import IsolationForest

from .utils import scale_features

logger = logging.getLogger(__name__)


class AnomalyDetectionManager:
    """
    Manages anomaly detection algorithms for pattern detection.

    Operations are synchronous and should be executed within an executor to keep
    the FastAPI event loop responsive under load.
    """

    def __init__(self):
        logger.info("AnomalyDetectionManager initialized")

    def detect_anomalies(
        self,
        data: list[list[float]],
        contamination: float = 0.1,
    ) -> tuple[list[int], list[float]]:
        """
        Detect anomalies using Isolation Forest.

        Args:
            data: List of data points to analyze
            contamination: Expected proportion of outliers (0.0 to 0.5)
        """
        if not data:
            return [], []

        X_scaled = scale_features(data)

        isolation_forest = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100,
        )

        # fit once, then predict and score separately to avoid redundant fitting
        isolation_forest.fit(X_scaled)
        labels = isolation_forest.predict(X_scaled)
        scores = isolation_forest.decision_function(X_scaled)

        n_anomalies = sum(1 for label in labels if label == -1)
        logger.info(
            "Anomaly detection completed",
            extra={"points": len(data), "anomalies": n_anomalies},
        )

        return labels.tolist(), scores.tolist()
