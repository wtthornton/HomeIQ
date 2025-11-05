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

# Import Phase 1 improvements
from .confidence_calibrator import PatternConfidenceCalibrator
from .utility_scorer import PatternUtilityScorer

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
        enable_ml: bool = True,
        enable_incremental: bool = True,
        window_days: int = 30
    ):
        """
        Initialize ML pattern detector.
        
        Args:
            min_confidence: Minimum confidence threshold for patterns
            min_occurrences: Minimum occurrences required for valid patterns
            max_patterns: Maximum number of patterns to return
            enable_ml: Whether to use ML algorithms (vs rule-based)
            enable_incremental: Whether to support incremental learning updates
            window_days: Time window in days for pattern detection
        """
        self.min_confidence = min_confidence
        self.min_occurrences = min_occurrences
        self.max_patterns = max_patterns
        self.enable_ml = enable_ml
        self.enable_incremental = enable_incremental
        self.window_days = window_days
        
        # ML models (lazy initialization)
        self._clustering_model = None
        self._anomaly_model = None
        self._scaler = StandardScaler()
        
        # Incremental learning state
        self._last_update_time: Optional[datetime] = None
        self._incremental_models: Dict[str, Any] = {}
        self._pattern_cache: List[Dict] = []
        
        # Phase 1 improvements: Confidence calibration and utility scoring
        self.calibrator: Optional[PatternConfidenceCalibrator] = None
        self.utility_scorer: Optional[PatternUtilityScorer] = None
        
        # Performance tracking
        self.detection_stats = {
            'total_patterns': 0,
            'ml_patterns': 0,
            'rule_patterns': 0,
            'processing_time': 0.0,
            'incremental_updates': 0,
            'full_analyses': 0
        }
        
        # Initialize Phase 1 improvements
        if enable_incremental:
            try:
                self.calibrator = PatternConfidenceCalibrator()
                self.calibrator.load()  # Try to load existing model
                self.utility_scorer = PatternUtilityScorer()
                logger.info("Confidence calibrator and utility scorer initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Phase 1 improvements: {e}")
        
        logger.info(f"MLPatternDetector initialized: confidence={min_confidence}, occurrences={min_occurrences}, incremental={enable_incremental}")
    
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
    
    def _calculate_confidence(self, pattern_data: Dict, use_calibration: bool = True) -> float:
        """
        Calculate pattern confidence score with optional calibration.
        
        Args:
            pattern_data: Pattern data dictionary
            use_calibration: Whether to use calibrated confidence if available
            
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
        
        raw_confidence = min(base_confidence, 1.0)
        
        # Apply calibration if available and enabled
        if use_calibration and self.calibrator and self.calibrator.is_fitted:
            try:
                pattern_data['confidence'] = raw_confidence  # Set base confidence for calibration
                calibrated = self.calibrator.calibrate_confidence(pattern_data)
                return calibrated
            except Exception as e:
                logger.warning(f"Calibration failed, using raw confidence: {e}")
        
        return raw_confidence
    
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
        Create standardized pattern dictionary with utility scoring.
        
        Args:
            pattern_type: Type of pattern detected
            pattern_id: Unique pattern identifier
            confidence: Pattern confidence score
            occurrences: Number of occurrences
            devices: List of device entity IDs
            metadata: Additional pattern metadata
            **kwargs: Additional pattern fields
            
        Returns:
            Standardized pattern dictionary with utility scores
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
        
        # Add device_id if not present (for compatibility)
        if 'device_id' not in pattern and devices:
            pattern['device_id'] = devices[0] if isinstance(devices, list) else devices
        
        # Add ML-specific fields if available
        if 'cluster_id' in kwargs:
            pattern['cluster_id'] = kwargs['cluster_id']
        if 'ml_confidence' in kwargs:
            pattern['ml_confidence'] = kwargs['ml_confidence']
        if 'anomaly_score' in kwargs:
            pattern['anomaly_score'] = kwargs['anomaly_score']
        
        # Add utility scores using utility scorer
        if self.utility_scorer:
            try:
                utility_scores = self.utility_scorer.score_pattern(pattern)
                if 'metadata' not in pattern:
                    pattern['metadata'] = {}
                pattern['metadata']['utility'] = utility_scores
                pattern['utility_score'] = utility_scores['total_utility']
            except Exception as e:
                logger.warning(f"Failed to calculate utility scores: {e}")
        
        return pattern
    
    def _generate_pattern_id(self, pattern_type: str) -> str:
        """Generate unique pattern ID."""
        return f"{pattern_type}_{uuid.uuid4().hex[:8]}"
    
    def _normalize_column_names(self, events_df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize column names to standard format.
        
        Args:
            events_df: Events DataFrame with potentially different column names
            
        Returns:
            DataFrame with normalized column names
        """
        df = events_df.copy()
        
        # Normalize timestamp column
        if 'timestamp' in df.columns and 'time' not in df.columns:
            df['time'] = df['timestamp']
        elif '_time' in df.columns and 'time' not in df.columns:
            df['time'] = df['_time']
        elif 'last_changed' in df.columns and 'time' not in df.columns:
            df['time'] = df['last_changed']
        
        # Normalize entity/device column
        if 'device_id' in df.columns and 'entity_id' not in df.columns:
            df['entity_id'] = df['device_id']
        
        # Ensure state column exists (default to 'unknown' if missing)
        if 'state' not in df.columns:
            df['state'] = 'unknown'
        
        return df
    
    def _optimize_dataframe(self, events_df: pd.DataFrame) -> pd.DataFrame:
        """
        Optimize DataFrame for ML processing.
        
        Args:
            events_df: Events DataFrame
            
        Returns:
            Optimized DataFrame
        """
        # First normalize column names
        events_df = self._normalize_column_names(events_df)
        
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
        # First normalize column names
        df = self._normalize_column_names(events_df)
        
        # Check for time column (required)
        if 'time' not in df.columns:
            logger.error("Missing required 'time' column (checked: timestamp, _time, last_changed)")
            return False
        
        # Check for entity/device column (required)
        if 'entity_id' not in df.columns and 'device_id' not in df.columns:
            logger.error("Missing required 'entity_id' or 'device_id' column")
            return False
        
        if df.empty:
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
            'processing_time': 0.0,
            'incremental_updates': 0,
            'full_analyses': 0
        }
    
    def incremental_update(self, events_df: pd.DataFrame, last_update_time: Optional[datetime] = None) -> List[Dict]:
        """
        Perform incremental pattern update using only new events since last update.
        
        Args:
            events_df: Events DataFrame (should contain all events in window)
            last_update_time: Timestamp of last update (if None, uses stored time)
            
        Returns:
            Updated list of patterns
        """
        if not self.enable_incremental:
            # Fall back to full analysis
            return self.detect_patterns(events_df)
        
        update_time = last_update_time or self._last_update_time
        
        if update_time is None or events_df.empty:
            # First run or no data: perform full analysis
            logger.info("Performing initial full analysis (no previous state)")
            self.detection_stats['full_analyses'] += 1
            patterns = self.detect_patterns(events_df)
            self._last_update_time = datetime.utcnow()
            self._pattern_cache = patterns
            return patterns
        
        # Extract only new events since last update
        # Handle different possible column names for timestamp
        time_col = None
        for col in ['timestamp', '_time', 'last_changed', 'time']:
            if col in events_df.columns:
                time_col = col
                break
        
        if time_col is None:
            logger.warning("No timestamp column found in events DataFrame, performing full analysis")
            patterns = self.detect_patterns(events_df)
            self._last_update_time = datetime.utcnow()
            self._pattern_cache = patterns
            return patterns
        
        events_df[time_col] = pd.to_datetime(events_df[time_col])
        new_events = events_df[events_df[time_col] > update_time].copy()
        
        if new_events.empty:
            logger.info("No new events since last update, returning cached patterns")
            return self._pattern_cache
        
        logger.info(f"Incremental update: {len(new_events)} new events since {update_time}")
        self.detection_stats['incremental_updates'] += 1
        
        # Merge new events with recent history (last window_days)
        cutoff_time = datetime.utcnow() - timedelta(days=self.window_days)
        recent_events = events_df[events_df[time_col] > cutoff_time].copy()
        
        # Perform incremental pattern detection
        patterns = self._incremental_detect_patterns(recent_events, new_events)
        
        # Update state
        self._last_update_time = datetime.utcnow()
        self._pattern_cache = patterns
        
        return patterns
    
    def _incremental_detect_patterns(
        self, 
        all_events_df: pd.DataFrame, 
        new_events_df: pd.DataFrame
    ) -> List[Dict]:
        """
        Incremental pattern detection using partial_fit capabilities.
        
        Args:
            all_events_df: All events in current window
            new_events_df: Only new events since last update
            
        Returns:
            Updated patterns list
        """
        # For most detectors, we'll do a lightweight update:
        # 1. Keep existing patterns from cache
        # 2. Detect new patterns from new events only
        # 3. Merge and deduplicate
        
        existing_patterns = self._pattern_cache.copy()
        
        # Detect patterns from new events (this will be faster than full analysis)
        new_patterns = self.detect_patterns(new_events_df)
        
        # Merge patterns: update occurrences for existing, add new ones
        merged_patterns = self._merge_patterns(existing_patterns, new_patterns)
        
        # Filter by confidence and occurrences
        filtered_patterns = [
            p for p in merged_patterns 
            if self._validate_pattern(p)
        ]
        
        # Limit to max_patterns, sorted by confidence
        filtered_patterns.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        return filtered_patterns[:self.max_patterns]
    
    def _merge_patterns(self, existing: List[Dict], new: List[Dict]) -> List[Dict]:
        """
        Merge existing and new patterns, updating occurrences and confidence.
        
        Args:
            existing: Existing patterns from cache
            new: Newly detected patterns
            
        Returns:
            Merged pattern list
        """
        # Create lookup by pattern_id or device_id + pattern_type
        pattern_map = {}
        
        for pattern in existing:
            key = self._get_pattern_key(pattern)
            pattern_map[key] = pattern.copy()
        
        # Merge new patterns
        for pattern in new:
            key = self._get_pattern_key(pattern)
            
            if key in pattern_map:
                # Update existing pattern
                existing_pattern = pattern_map[key]
                existing_pattern['occurrences'] = existing_pattern.get('occurrences', 0) + pattern.get('occurrences', 0)
                # Recalculate confidence with updated occurrences
                existing_pattern['confidence'] = self._calculate_confidence(existing_pattern)
                # Update metadata to reflect latest occurrence
                if 'last_seen' in pattern.get('metadata', {}):
                    existing_pattern['metadata']['last_seen'] = pattern['metadata']['last_seen']
            else:
                # New pattern
                pattern_map[key] = pattern.copy()
        
        return list(pattern_map.values())
    
    def _get_pattern_key(self, pattern: Dict) -> str:
        """Generate unique key for pattern matching."""
        pattern_type = pattern.get('pattern_type', 'unknown')
        device_id = pattern.get('device_id', pattern.get('devices', ['unknown'])[0] if pattern.get('devices') else 'unknown')
        
        # For co-occurrence patterns, include both devices
        if pattern_type == 'co_occurrence' and 'devices' in pattern and len(pattern['devices']) >= 2:
            devices = sorted(pattern['devices'][:2])
            return f"{pattern_type}:{devices[0]}+{devices[1]}"
        
        # Include metadata for sequence patterns
        if pattern_type == 'sequence' and 'metadata' in pattern:
            sequence = pattern['metadata'].get('sequence', [])
            if sequence:
                return f"{pattern_type}:{device_id}:{','.join(sequence[:3])}"
        
        return f"{pattern_type}:{device_id}"
    
    def _incremental_cluster_patterns(
        self, 
        patterns: List[Dict], 
        features: np.ndarray,
        update_only: bool = False
    ) -> List[Dict]:
        """
        Incremental clustering using partial_fit if update_only=True.
        
        Args:
            patterns: Pattern list to cluster
            features: Feature matrix
            update_only: If True, use partial_fit for incremental update
            
        Returns:
            Clustered patterns
        """
        if not self.enable_ml or len(patterns) < 3:
            return patterns
        
        try:
            features_scaled = self._scaler.fit_transform(features) if not update_only else self._scaler.transform(features)
            
            # Use MiniBatchKMeans for incremental learning
            n_clusters = self._find_optimal_clusters(features_scaled)
            
            if n_clusters > 1:
                model_key = 'clustering_model'
                
                if update_only and model_key in self._incremental_models:
                    # Incremental update using partial_fit
                    model = self._incremental_models[model_key]
                    if hasattr(model, 'partial_fit'):
                        model.partial_fit(features_scaled)
                    else:
                        # Re-fit if partial_fit not available
                        model.fit(features_scaled)
                else:
                    # Initial fit or full refit
                    model = MiniBatchKMeans(
                        n_clusters=n_clusters,
                        random_state=42,
                        batch_size=100
                    )
                    model.fit(features_scaled)
                    self._incremental_models[model_key] = model
                
                cluster_labels = model.predict(features_scaled)
                
                # Add cluster information
                for i, pattern in enumerate(patterns):
                    pattern['cluster_id'] = int(cluster_labels[i])
                    pattern['cluster_size'] = int(np.sum(cluster_labels == cluster_labels[i]))
                    pattern['ml_confidence'] = self._calculate_cluster_confidence(
                        features_scaled[i], model
                    )
                
                logger.info(f"Incremental clustering: {len(patterns)} patterns in {n_clusters} clusters")
            
        except Exception as e:
            logger.warning(f"Incremental clustering failed: {e}, using original patterns")
        
        return patterns
