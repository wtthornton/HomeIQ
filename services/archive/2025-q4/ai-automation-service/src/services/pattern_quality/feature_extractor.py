"""
Pattern Feature Extractor

Epic AI-13: ML-Based Pattern Quality & Active Learning
Story AI13.1: Pattern Quality Feature Engineering

Extracts features from patterns for quality prediction using ML models.
"""

import logging
from typing import Any
from datetime import datetime, timezone
import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler

from .features import PatternFeatures

logger = logging.getLogger(__name__)


class PatternFeatureExtractor:
    """
    Extract features from patterns for quality prediction.
    
    Converts Pattern model or pattern dict into numerical features
    suitable for ML model training.
    """
    
    # Pattern type mapping
    PATTERN_TYPES = {
        'time_of_day': 'pattern_type_time_of_day',
        'co_occurrence': 'pattern_type_co_occurrence',
        'anomaly': 'pattern_type_anomaly',
        'seasonal': 'pattern_type_seasonal',
        'synergy': 'pattern_type_synergy',
    }
    
    # Trend direction mapping
    TREND_DIRECTIONS = {
        'decreasing': -1.0,
        'stable': 0.0,
        'increasing': 1.0,
    }
    
    def __init__(self):
        """Initialize feature extractor."""
        self.scaler = StandardScaler()
        self.minmax_scaler = MinMaxScaler()
        self._fitted = False
    
    def extract_features(
        self,
        pattern: Any,  # Pattern model or dict[str, Any]
    ) -> PatternFeatures:
        """
        Extract features from a pattern.
        
        Args:
            pattern: Pattern model instance or pattern dict
        
        Returns:
            PatternFeatures with all extracted features
        """
        features = PatternFeatures()
        
        # Pattern type (one-hot encoding)
        pattern_type = self._get_pattern_type(pattern)
        self._set_pattern_type_features(features, pattern_type)
        
        # Confidence features
        features.confidence_raw = self._get_confidence(pattern, 'raw')
        features.confidence_calibrated = self._get_confidence(pattern, 'calibrated')
        features.confidence_normalized = self._normalize_confidence(
            features.confidence_raw
        )
        
        # Device count features
        devices = self._get_devices(pattern)
        features.device_count_total = len(devices)
        features.device_count_unique = len(set(devices))
        features.area_count = self._count_areas(devices)
        features.device_count_per_area = (
            features.device_count_total / features.area_count
            if features.area_count > 0 else 0.0
        )
        
        # Occurrence features
        features.occurrence_count_total = self._get_occurrences(pattern)
        features.occurrence_frequency = self._calculate_frequency(pattern)
        features.occurrence_trend_direction = self._get_trend_direction(pattern)
        features.occurrence_trend_strength = self._get_trend_strength(pattern)
        
        # Time span features
        first_seen = self._get_first_seen(pattern)
        last_seen = self._get_last_seen(pattern)
        now = datetime.now(timezone.utc)
        
        if last_seen and first_seen:
            time_delta = last_seen - first_seen
            features.time_span_days = time_delta.total_seconds() / 86400.0
        else:
            features.time_span_days = 0.0
        
        if last_seen:
            recency_delta = now - last_seen
            features.recency_days = recency_delta.total_seconds() / 86400.0
        else:
            features.recency_days = 0.0
        
        if first_seen:
            age_delta = now - first_seen
            features.age_days = age_delta.total_seconds() / 86400.0
        else:
            features.age_days = 0.0
        
        # Metadata features
        metadata = self._get_metadata(pattern)
        features.metadata_complexity = len(metadata) if metadata else 0.0
        features.metadata_has_conditions = 1.0 if self._has_conditions(metadata) else 0.0
        features.metadata_has_actions = 1.0 if self._has_actions(metadata) else 0.0
        
        # Quality indicators
        features.is_deprecated = 1.0 if self._is_deprecated(pattern) else 0.0
        features.needs_review = 1.0 if self._needs_review(pattern) else 0.0
        features.calibrated = 1.0 if self._is_calibrated(pattern) else 0.0
        
        return features
    
    def extract_features_batch(
        self,
        patterns: list[Any],  # list[Pattern] | list[dict[str, Any]]
    ) -> list[PatternFeatures]:
        """
        Extract features from multiple patterns.
        
        Args:
            patterns: List of Pattern models or pattern dicts
        
        Returns:
            List of PatternFeatures
        """
        return [self.extract_features(pattern) for pattern in patterns]
    
    def to_numpy_array(
        self,
        features: PatternFeatures | list[PatternFeatures]
    ) -> np.ndarray:
        """
        Convert features to numpy array for ML model.
        
        Args:
            features: Single PatternFeatures or list
        
        Returns:
            Numpy array of shape (n_samples, n_features)
        """
        if isinstance(features, PatternFeatures):
            features = [features]
        
        # Convert to list of lists
        feature_arrays = [f.to_list() for f in features]
        
        # Convert to numpy array
        return np.array(feature_arrays)
    
    def fit_scalers(
        self,
        features: list[PatternFeatures]
    ) -> None:
        """
        Fit scalers on training data.
        
        Args:
            features: List of PatternFeatures for training
        """
        if not features:
            logger.warning("No features provided for scaler fitting")
            return
        
        feature_array = self.to_numpy_array(features)
        
        # Fit scalers
        self.scaler.fit(feature_array)
        self.minmax_scaler.fit(feature_array)
        self._fitted = True
        
        logger.info(f"Fitted scalers on {len(features)} patterns")
    
    def transform_features(
        self,
        features: PatternFeatures | list[PatternFeatures],
        use_standard_scaler: bool = True
    ) -> np.ndarray:
        """
        Transform features using fitted scalers.
        
        Args:
            features: Single PatternFeatures or list
            use_standard_scaler: If True, use StandardScaler; else use MinMaxScaler
        
        Returns:
            Scaled numpy array
        """
        if not self._fitted:
            logger.warning("Scalers not fitted, returning unscaled features")
            return self.to_numpy_array(features)
        
        feature_array = self.to_numpy_array(features)
        
        if use_standard_scaler:
            return self.scaler.transform(feature_array)
        else:
            return self.minmax_scaler.transform(feature_array)
    
    # Helper methods
    
    def _get_pattern_type(self, pattern: Any) -> str:
        """Get pattern type from pattern model or dict."""
        if hasattr(pattern, 'pattern_type'):
            return pattern.pattern_type
        elif isinstance(pattern, dict):
            return pattern.get('pattern_type', '')
        else:
            return ''
    
    def _set_pattern_type_features(
        self,
        features: PatternFeatures,
        pattern_type: str
    ) -> None:
        """Set one-hot encoded pattern type features."""
        feature_name = self.PATTERN_TYPES.get(pattern_type)
        if feature_name:
            setattr(features, feature_name, 1.0)
    
    def _get_confidence(self, pattern: Any, conf_type: str) -> float:
        """Get confidence value (raw or calibrated)."""
        if conf_type == 'raw':
            if hasattr(pattern, 'raw_confidence') and pattern.raw_confidence is not None:
                return float(pattern.raw_confidence)
            elif hasattr(pattern, 'confidence'):
                return float(pattern.confidence)
            elif isinstance(pattern, dict):
                return float(pattern.get('raw_confidence') or pattern.get('confidence', 0.0))
        elif conf_type == 'calibrated':
            if hasattr(pattern, 'confidence'):
                return float(pattern.confidence)
            elif isinstance(pattern, dict):
                return float(pattern.get('confidence', 0.0))
        
        return 0.0
    
    def _normalize_confidence(self, confidence: float) -> float:
        """Normalize confidence to 0.0-1.0 range."""
        return max(0.0, min(1.0, confidence))
    
    def _get_devices(self, pattern: Any) -> list[str]:
        """Extract device IDs from pattern."""
        devices = []
        
        # From device_id field
        if hasattr(pattern, 'device_id'):
            devices.append(pattern.device_id)
        elif isinstance(pattern, dict):
            device_id = pattern.get('device_id')
            if device_id:
                devices.append(device_id)
        
        # From metadata
        metadata = self._get_metadata(pattern)
        if metadata:
            # Check for device lists in metadata
            if isinstance(metadata, dict):
                if 'devices' in metadata and isinstance(metadata['devices'], list):
                    devices.extend(metadata['devices'])
                if 'device_ids' in metadata and isinstance(metadata['device_ids'], list):
                    devices.extend(metadata['device_ids'])
        
        return devices
    
    def _count_areas(self, devices: list[str]) -> int:
        """
        Count unique areas from device IDs.
        
        Assumes device IDs may contain area information or extracts from entity IDs.
        """
        areas = set()
        
        for device in devices:
            # Try to extract area from entity ID format (e.g., "light.kitchen_light")
            # This is a simple heuristic - may need enhancement based on actual data
            parts = device.split('.')
            if len(parts) > 1:
                # Check if area is embedded in entity name
                entity_name = parts[1]
                # Simple heuristic: if name contains common area words
                area_keywords = ['kitchen', 'bedroom', 'living', 'bathroom', 'office', 'garage']
                for keyword in area_keywords:
                    if keyword in entity_name.lower():
                        areas.add(keyword)
                        break
        
        return len(areas) if areas else 1  # Default to 1 if no areas found
    
    def _get_occurrences(self, pattern: Any) -> int:
        """Get occurrence count from pattern."""
        if hasattr(pattern, 'occurrences'):
            return int(pattern.occurrences)
        elif isinstance(pattern, dict):
            return int(pattern.get('occurrences', 0))
        return 0
    
    def _calculate_frequency(self, pattern: Any) -> float:
        """Calculate occurrence frequency (occurrences per day)."""
        occurrences = self._get_occurrences(pattern)
        age_days = self._get_age_days(pattern)
        
        if age_days > 0:
            return occurrences / age_days
        return 0.0
    
    def _get_age_days(self, pattern: Any) -> float:
        """Get pattern age in days."""
        first_seen = self._get_first_seen(pattern)
        if first_seen:
            now = datetime.now(timezone.utc)
            age_delta = now - first_seen
            return age_delta.total_seconds() / 86400.0
        return 1.0  # Default to 1 day to avoid division by zero
    
    def _get_trend_direction(self, pattern: Any) -> float:
        """Get trend direction as numerical value."""
        if hasattr(pattern, 'trend_direction'):
            trend = pattern.trend_direction
        elif isinstance(pattern, dict):
            trend = pattern.get('trend_direction')
        else:
            trend = None
        
        return self.TREND_DIRECTIONS.get(trend, 0.0) if trend else 0.0
    
    def _get_trend_strength(self, pattern: Any) -> float:
        """Get trend strength (0.0-1.0)."""
        if hasattr(pattern, 'trend_strength'):
            return float(pattern.trend_strength)
        elif isinstance(pattern, dict):
            return float(pattern.get('trend_strength', 0.0))
        return 0.0
    
    def _get_first_seen(self, pattern: Any) -> datetime | None:
        """Get first_seen datetime."""
        if hasattr(pattern, 'first_seen'):
            return pattern.first_seen
        elif isinstance(pattern, dict):
            first_seen = pattern.get('first_seen')
            if isinstance(first_seen, datetime):
                return first_seen
            elif isinstance(first_seen, str):
                # Try to parse ISO format
                try:
                    return datetime.fromisoformat(first_seen.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    pass
        return None
    
    def _get_last_seen(self, pattern: Any) -> datetime | None:
        """Get last_seen datetime."""
        if hasattr(pattern, 'last_seen'):
            return pattern.last_seen
        elif isinstance(pattern, dict):
            last_seen = pattern.get('last_seen')
            if isinstance(last_seen, datetime):
                return last_seen
            elif isinstance(last_seen, str):
                # Try to parse ISO format
                try:
                    return datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    pass
        return None
    
    def _get_metadata(self, pattern: Any) -> dict[str, Any] | None:
        """Get pattern metadata."""
        if hasattr(pattern, 'pattern_metadata'):
            return pattern.pattern_metadata
        elif isinstance(pattern, dict):
            return pattern.get('pattern_metadata') or pattern.get('metadata')
        return None
    
    def _has_conditions(self, metadata: dict[str, Any] | None) -> bool:
        """Check if metadata has conditions."""
        if not metadata or not isinstance(metadata, dict):
            return False
        return 'conditions' in metadata or 'condition' in metadata
    
    def _has_actions(self, metadata: dict[str, Any] | None) -> bool:
        """Check if metadata has actions."""
        if not metadata or not isinstance(metadata, dict):
            return False
        return 'actions' in metadata or 'action' in metadata
    
    def _is_deprecated(self, pattern: Any) -> bool:
        """Check if pattern is deprecated."""
        if hasattr(pattern, 'deprecated'):
            return bool(pattern.deprecated)
        elif isinstance(pattern, dict):
            return bool(pattern.get('deprecated', False))
        return False
    
    def _needs_review(self, pattern: Any) -> bool:
        """Check if pattern needs review."""
        if hasattr(pattern, 'needs_review'):
            return bool(pattern.needs_review)
        elif isinstance(pattern, dict):
            return bool(pattern.get('needs_review', False))
        return False
    
    def _is_calibrated(self, pattern: Any) -> bool:
        """Check if pattern confidence is calibrated."""
        if hasattr(pattern, 'calibrated'):
            return bool(pattern.calibrated)
        elif isinstance(pattern, dict):
            return bool(pattern.get('calibrated', False))
        return False

