"""
Anomaly Detection Manager
Provides Isolation Forest for anomaly detection
"""

import logging
import numpy as np
from typing import List, Tuple
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

class AnomalyDetectionManager:
    """
    Manages anomaly detection algorithms for pattern detection
    """
    
    def __init__(self):
        self.scaler = StandardScaler()
        logger.info("AnomalyDetectionManager initialized")
    
    async def detect_anomalies(self, data: List[List[float]], contamination: float = 0.1) -> Tuple[List[int], List[float]]:
        """
        Detect anomalies using Isolation Forest
        
        Args:
            data: List of data points to analyze
            contamination: Expected proportion of outliers (0.0 to 0.5)
        
        Returns:
            Tuple of (labels, scores) where labels: 1=normal, -1=anomaly
        """
        if not data:
            return [], []
        
        # Convert to numpy array
        X = np.array(data)
        
        # Standardize features
        X_scaled = self.scaler.fit_transform(X)
        
        # Perform anomaly detection
        isolation_forest = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )
        
        labels = isolation_forest.fit_predict(X_scaled)
        scores = isolation_forest.decision_function(X_scaled)
        
        n_anomalies = sum(1 for label in labels if label == -1)
        logger.info(f"Anomaly detection completed: {n_anomalies} anomalies found in {len(data)} points")
        
        return labels.tolist(), scores.tolist()
