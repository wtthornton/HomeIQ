"""
Home Type Feature Extractor

Extract ML-ready features from home profile for training RandomForest classifier.
"""

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class HomeTypeFeatureExtractor:
    """
    Extract ML-ready features from home profile.
    
    Features (15-20 total):
    - Device counts (by type, category)
    - Device ratios (security, climate, lighting)
    - Event frequencies (total, per day, peak hours)
    - Spatial metrics (area count, indoor/outdoor ratio)
    - Behavior metrics (pattern counts, confidence)
    """
    
    def __init__(self):
        """Initialize feature extractor."""
        self.feature_names = []
        logger.info("HomeTypeFeatureExtractor initialized")
    
    def extract(self, profile: dict[str, Any]) -> np.ndarray:
        """
        Extract feature vector for ML model.
        
        Args:
            profile: Home profile from HomeTypeProfiler
        
        Returns:
            NumPy array of feature values
        """
        features = []
        feature_names = []
        
        # Device composition features (5-7 features)
        device_comp = profile.get('device_composition', {})
        features.append(device_comp.get('total_devices', 0))
        feature_names.append('total_devices')
        
        ratios = device_comp.get('ratios', {})
        features.append(ratios.get('security_ratio', 0.0))
        feature_names.append('security_ratio')
        features.append(ratios.get('climate_ratio', 0.0))
        feature_names.append('climate_ratio')
        features.append(ratios.get('lighting_ratio', 0.0))
        feature_names.append('lighting_ratio')
        features.append(ratios.get('appliance_ratio', 0.0))
        feature_names.append('appliance_ratio')
        features.append(ratios.get('monitoring_ratio', 0.0))
        feature_names.append('monitoring_ratio')
        
        # Device type counts (top 5 types)
        by_type = device_comp.get('by_type', {})
        top_types = sorted(by_type.items(), key=lambda x: x[1], reverse=True)[:5]
        type_counts = dict(top_types)
        
        # Add device type counts (pad with zeros if less than 5)
        common_types = ['light', 'binary_sensor', 'sensor', 'switch', 'climate']
        for dtype in common_types:
            features.append(type_counts.get(dtype, 0))
            feature_names.append(f'device_count_{dtype}')
        
        # Event pattern features (4-5 features)
        event_patterns = profile.get('event_patterns', {})
        features.append(event_patterns.get('total_events', 0))
        feature_names.append('total_events')
        features.append(event_patterns.get('events_per_day', 0.0))
        feature_names.append('events_per_day')
        
        # Peak hour features (top 3 hours)
        peak_hours = event_patterns.get('peak_hours', [])
        for i in range(3):
            features.append(peak_hours[i] if i < len(peak_hours) else 0)
            feature_names.append(f'peak_hour_{i+1}')
        
        # Spatial layout features (3-4 features)
        spatial = profile.get('spatial_layout', {})
        features.append(spatial.get('area_count', 0))
        feature_names.append('area_count')
        features.append(spatial.get('indoor_ratio', 0.0))
        feature_names.append('indoor_ratio')
        features.append(spatial.get('devices_per_area', 0.0))
        feature_names.append('devices_per_area')
        
        # Behavior pattern features (3-4 features)
        behavior = profile.get('behavior_patterns', {})
        features.append(behavior.get('pattern_count', 0))
        feature_names.append('pattern_count')
        features.append(behavior.get('avg_pattern_confidence', 0.0))
        feature_names.append('avg_pattern_confidence')
        features.append(behavior.get('diversity_ratio', 0.0))
        feature_names.append('diversity_ratio')
        
        # Store feature names for reference
        self.feature_names = feature_names
        
        # Convert to numpy array
        feature_vector = np.array(features, dtype=np.float32)
        
        logger.debug(f"Extracted {len(feature_vector)} features")
        return feature_vector
    
    def get_feature_names(self) -> list[str]:
        """
        Get list of feature names.
        
        Returns:
            List of feature name strings
        """
        return self.feature_names.copy()

