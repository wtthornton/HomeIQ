"""
ML-Enhanced Pattern Detector Base Class

Provides machine learning capabilities for pattern detection using scikit-learn
and pandas optimizations. This is the foundation for all advanced pattern detectors.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import uuid

# Scikit-learn imports
from sklearn.cluster import DBSCAN, KMeans, SpectralClustering, MiniBatchKMeans
from sklearn.neighbors import LocalOutlierFactor
from sklearn.ensemble import IsolationForest
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
from sklearn.model_selection import TimeSeriesSplit

logger = logging.getLogger(__name__)


class MLPatternDetector(ABC):
    """
    Base class for ML-enhanced pattern detection.
    
    Provides common functionality for all pattern detectors including:
    - ML clustering and anomaly detection
    - Pandas optimizations for time series analysis
    - Performance monitoring and validation
    - Standardized pattern output format
    """
    
    def __init__(
        self,
        min_confidence: float = 0.7,
        min_occurrences: int = 5,
        max_patterns: int = 100,
        enable_ml: bool = True
    ):
        """
        Initialize ML pattern detector.
        
        Args:
            min_confidence: Minimum confidence threshold for patterns
            min_occurrences: Minimum occurrences required for valid patterns
            max_patterns: Maximum number of patterns to return
            enable_ml: Whether to use ML algorithms (vs rule-based)
        """
        self.min_confidence = min_confidence
        self.min_occurrences = min_occurrences
        self.max_patterns = max_patterns
        self.enable_ml = enable_ml
        
        # ML models (lazy initialization)
        self._clustering_model = None
        self._anomaly_model = None
        self._scaler = StandardScaler()
        
        # Performance tracking
        self.detection_stats = {
            'total_patterns': 0,
            'ml_patterns': 0,
            'rule_patterns': 0,
            'processing_time': 0.0
        }
        
        logger.info(f"MLPatternDetector initialized: confidence={min_confidence}, occurrences={min_occurrences}")
    
    @abstractmethod
    def detect_patterns(self, events_df: pd.DataFrame) -> List[Dict]:
        """
        Detect patterns in events DataFrame.
        
        Args:
            events_df: Events DataFrame with columns: time, entity_id, state, area, etc.
            
        Returns:
            List of pattern dictionaries
        """
        pass
    
    def _validate_pattern(self, pattern: Dict) -> bool:
        """
        Validate pattern meets minimum requirements.
        
        Args:
            pattern: Pattern dictionary to validate
            
        Returns:
            True if pattern is valid, False otherwise
        """
        return (
            pattern.get('confidence', 0) >= self.min_confidence and
            pattern.get('occurrences', 0) >= self.min_occurrences and
            pattern.get('pattern_type') is not None
        )
    
    def _calculate_confidence(self, pattern_data: Dict) -> float:
        """
        Calculate pattern confidence score.
        
        Args:
            pattern_data: Pattern data dictionary
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Base confidence from occurrences
        occurrences = pattern_data.get('occurrences', 0)
        base_confidence = min(occurrences / 20.0, 1.0)  # Max confidence at 20 occurrences
        
        # ML confidence boost if available
        ml_confidence = pattern_data.get('ml_confidence', 0.0)
        if ml_confidence > 0:
            base_confidence = (base_confidence + ml_confidence) / 2
        
        # Time consistency boost
        time_consistency = pattern_data.get('time_consistency', 0.0)
        if time_consistency > 0:
            base_confidence = (base_confidence + time_consistency) / 2
        
        return min(base_confidence, 1.0)
    
    def _cluster_patterns(self, patterns: List[Dict], features: np.ndarray) -> List[Dict]:
        """
        Cluster similar patterns using ML algorithms.
        
        Args:
            patterns: List of pattern dictionaries
            features: Feature matrix for clustering
            
        Returns:
            List of clustered patterns with cluster_id
        """
        if not self.enable_ml or len(patterns) < 3:
            return patterns
        
        try:
            # Scale features
            features_scaled = self._scaler.fit_transform(features)
            
            # Determine optimal number of clusters
            n_clusters = self._find_optimal_clusters(features_scaled)
            
            if n_clusters > 1:
                # Use MiniBatchKMeans for efficiency
                clustering_model = MiniBatchKMeans(
                    n_clusters=n_clusters,
                    random_state=42,
                    batch_size=100
                )
                cluster_labels = clustering_model.fit_predict(features_scaled)
                
                # Add cluster information to patterns
                for i, pattern in enumerate(patterns):
                    pattern['cluster_id'] = int(cluster_labels[i])
                    pattern['cluster_size'] = int(np.sum(cluster_labels == cluster_labels[i]))
                    pattern['ml_confidence'] = self._calculate_cluster_confidence(
                        features_scaled[i], clustering_model
                    )
                
                logger.info(f"Clustered {len(patterns)} patterns into {n_clusters} clusters")
            
        except Exception as e:
            logger.warning(f"Clustering failed: {e}, using original patterns")
        
        return patterns
    
    def _find_optimal_clusters(self, features: np.ndarray) -> int:
        """
        Find optimal number of clusters using silhouette score.
        
        Args:
            features: Scaled feature matrix
            
        Returns:
            Optimal number of clusters
        """
        if len(features) < 4:
            return 1
        
        max_clusters = min(len(features) // 2, 10)
        if max_clusters < 2:
            return 1
        
        best_score = -1
        best_k = 1
        
        for k in range(2, max_clusters + 1):
            try:
                kmeans = MiniBatchKMeans(n_clusters=k, random_state=42, batch_size=100)
                cluster_labels = kmeans.fit_predict(features)
                score = silhouette_score(features, cluster_labels)
                
                if score > best_score:
                    best_score = score
                    best_k = k
            except Exception:
                continue
        
        return best_k if best_score > 0.3 else 1
    
    def _calculate_cluster_confidence(self, feature_vector: np.ndarray, model) -> float:
        """
        Calculate confidence based on distance to cluster center.
        
        Args:
            feature_vector: Feature vector for pattern
            model: Fitted clustering model
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        try:
            # Calculate distance to cluster center
            center = model.cluster_centers_[model.predict([feature_vector])[0]]
            distance = np.linalg.norm(feature_vector - center)
            
            # Convert distance to confidence (closer = higher confidence)
            max_distance = np.max([np.linalg.norm(center - c) for c in model.cluster_centers_])
            confidence = 1.0 - (distance / max_distance) if max_distance > 0 else 1.0
            
            return max(0.0, min(1.0, confidence))
        except Exception:
            return 0.5
    
    def _detect_anomalies(self, features: np.ndarray) -> np.ndarray:
        """
        Detect anomalies in feature data.
        
        Args:
            features: Feature matrix
            
        Returns:
            Array of anomaly scores (-1 for outliers, 1 for inliers)
        """
        if not self.enable_ml or len(features) < 10:
            return np.ones(len(features))
        
        try:
            # Use LocalOutlierFactor for anomaly detection
            anomaly_model = LocalOutlierFactor(
                n_neighbors=min(10, len(features) - 1),
                contamination=0.1
            )
            anomaly_scores = anomaly_model.fit_predict(features)
            return anomaly_scores
        except Exception as e:
            logger.warning(f"Anomaly detection failed: {e}")
            return np.ones(len(features))
    
    def _extract_time_features(self, events_df: pd.DataFrame) -> pd.DataFrame:
        """
        Extract time-based features from events.
        
        Args:
            events_df: Events DataFrame
            
        Returns:
            DataFrame with time features
        """
        features_df = events_df.copy()
        
        # Extract time components
        features_df['hour'] = features_df['time'].dt.hour
        features_df['dayofweek'] = features_df['time'].dt.dayofweek
        features_df['dayofyear'] = features_df['time'].dt.dayofyear
        features_df['month'] = features_df['time'].dt.month
        features_df['is_weekend'] = features_df['dayofweek'].isin([5, 6]).astype(int)
        
        # Time since last event
        features_df['time_since_last'] = features_df['time'].diff().dt.total_seconds()
        
        return features_df
    
    def _create_pattern_dict(
        self,
        pattern_type: str,
        pattern_id: str,
        confidence: float,
        occurrences: int,
        devices: List[str],
        metadata: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create standardized pattern dictionary.
        
        Args:
            pattern_type: Type of pattern detected
            pattern_id: Unique pattern identifier
            confidence: Pattern confidence score
            occurrences: Number of occurrences
            devices: List of device entity IDs
            metadata: Additional pattern metadata
            **kwargs: Additional pattern fields
            
        Returns:
            Standardized pattern dictionary
        """
        pattern = {
            'pattern_type': pattern_type,
            'pattern_id': pattern_id,
            'confidence': confidence,
            'occurrences': occurrences,
            'devices': devices,
            'metadata': metadata,
            'created_at': datetime.utcnow().isoformat(),
            **kwargs
        }
        
        # Add ML-specific fields if available
        if 'cluster_id' in kwargs:
            pattern['cluster_id'] = kwargs['cluster_id']
        if 'ml_confidence' in kwargs:
            pattern['ml_confidence'] = kwargs['ml_confidence']
        if 'anomaly_score' in kwargs:
            pattern['anomaly_score'] = kwargs['anomaly_score']
        
        return pattern
    
    def _generate_pattern_id(self, pattern_type: str) -> str:
        """Generate unique pattern ID."""
        return f"{pattern_type}_{uuid.uuid4().hex[:8]}"
    
    def _optimize_dataframe(self, events_df: pd.DataFrame) -> pd.DataFrame:
        """
        Optimize DataFrame for ML processing.
        
        Args:
            events_df: Events DataFrame
            
        Returns:
            Optimized DataFrame
        """
        # Convert categorical columns to category dtype for memory efficiency
        categorical_columns = ['entity_id', 'state', 'area']
        for col in categorical_columns:
            if col in events_df.columns:
                events_df[col] = events_df[col].astype('category')
        
        # Ensure time column is datetime
        if 'time' in events_df.columns:
            events_df['time'] = pd.to_datetime(events_df['time'])
        
        # Sort by time for efficient processing
        events_df = events_df.sort_values('time').reset_index(drop=True)
        
        return events_df
    
    def _validate_events_dataframe(self, events_df: pd.DataFrame) -> bool:
        """
        Validate events DataFrame has required columns.
        
        Args:
            events_df: Events DataFrame to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_columns = ['time', 'entity_id', 'state']
        missing_columns = [col for col in required_columns if col not in events_df.columns]
        
        if missing_columns:
            logger.error(f"Missing required columns: {missing_columns}")
            return False
        
        if events_df.empty:
            logger.warning("Empty events DataFrame")
            return False
        
        return True
    
    def get_detection_stats(self) -> Dict[str, Any]:
        """Get pattern detection statistics."""
        return self.detection_stats.copy()
    
    def reset_stats(self):
        """Reset detection statistics."""
        self.detection_stats = {
            'total_patterns': 0,
            'ml_patterns': 0,
            'rule_patterns': 0,
            'processing_time': 0.0
        }
