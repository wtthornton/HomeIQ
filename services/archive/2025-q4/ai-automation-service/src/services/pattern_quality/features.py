"""
Pattern Features Data Model

Epic AI-13: ML-Based Pattern Quality & Active Learning
Story AI13.1: Pattern Quality Feature Engineering

Defines the feature structure for pattern quality prediction.
"""

from dataclasses import dataclass, field
from typing import Any
from datetime import datetime


@dataclass
class PatternFeatures:
    """
    Extracted features from a pattern for quality prediction.
    
    All features are normalized to numerical values suitable for ML models.
    """
    
    # Pattern Type Features (categorical, one-hot encoded)
    pattern_type_time_of_day: float = 0.0
    pattern_type_co_occurrence: float = 0.0
    pattern_type_anomaly: float = 0.0
    pattern_type_seasonal: float = 0.0
    pattern_type_synergy: float = 0.0
    
    # Confidence Features (numerical, 0.0-1.0)
    confidence_raw: float = 0.0
    confidence_calibrated: float = 0.0
    confidence_normalized: float = 0.0
    
    # Device Count Features (numerical)
    device_count_total: int = 0
    device_count_unique: int = 0
    device_count_per_area: float = 0.0
    area_count: int = 0
    
    # Occurrence Features (numerical)
    occurrence_count_total: int = 0
    occurrence_frequency: float = 0.0  # occurrences per day
    occurrence_trend_direction: float = 0.0  # -1.0 (decreasing), 0.0 (stable), 1.0 (increasing)
    occurrence_trend_strength: float = 0.0  # 0.0-1.0
    
    # Time Span Features (numerical, days)
    time_span_days: float = 0.0  # last_seen - first_seen
    recency_days: float = 0.0  # days since last_seen
    age_days: float = 0.0  # days since first_seen
    
    # Pattern Metadata Features (extracted from pattern_metadata JSON)
    metadata_complexity: float = 0.0  # number of keys in metadata
    metadata_has_conditions: float = 0.0  # 1.0 if has conditions, 0.0 otherwise
    metadata_has_actions: float = 0.0  # 1.0 if has actions, 0.0 otherwise
    
    # Quality Indicators (from existing fields)
    is_deprecated: float = 0.0  # 1.0 if deprecated, 0.0 otherwise
    needs_review: float = 0.0  # 1.0 if needs_review, 0.0 otherwise
    calibrated: float = 0.0  # 1.0 if calibrated, 0.0 otherwise
    
    def to_dict(self) -> dict[str, Any]:
        """Convert features to dictionary for serialization."""
        return {
            'pattern_type_time_of_day': self.pattern_type_time_of_day,
            'pattern_type_co_occurrence': self.pattern_type_co_occurrence,
            'pattern_type_anomaly': self.pattern_type_anomaly,
            'pattern_type_seasonal': self.pattern_type_seasonal,
            'pattern_type_synergy': self.pattern_type_synergy,
            'confidence_raw': self.confidence_raw,
            'confidence_calibrated': self.confidence_calibrated,
            'confidence_normalized': self.confidence_normalized,
            'device_count_total': self.device_count_total,
            'device_count_unique': self.device_count_unique,
            'device_count_per_area': self.device_count_per_area,
            'area_count': self.area_count,
            'occurrence_count_total': self.occurrence_count_total,
            'occurrence_frequency': self.occurrence_frequency,
            'occurrence_trend_direction': self.occurrence_trend_direction,
            'occurrence_trend_strength': self.occurrence_trend_strength,
            'time_span_days': self.time_span_days,
            'recency_days': self.recency_days,
            'age_days': self.age_days,
            'metadata_complexity': self.metadata_complexity,
            'metadata_has_conditions': self.metadata_has_conditions,
            'metadata_has_actions': self.metadata_has_actions,
            'is_deprecated': self.is_deprecated,
            'needs_review': self.needs_review,
            'calibrated': self.calibrated,
        }
    
    def to_list(self) -> list[float]:
        """Convert features to list for ML model input."""
        return list(self.to_dict().values())
    
    @classmethod
    def feature_names(cls) -> list[str]:
        """Get list of feature names in order."""
        return list(cls().to_dict().keys())
    
    @classmethod
    def feature_count(cls) -> int:
        """Get total number of features."""
        return len(cls.feature_names())

