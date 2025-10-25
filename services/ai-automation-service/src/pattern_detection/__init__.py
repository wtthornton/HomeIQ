"""
Pattern Detection Module
Enhanced with ML-Powered Pattern Detection

This module implements advanced pattern detection algorithms using
scikit-learn and pandas optimizations to identify recurring behaviors
in Home Assistant events.
"""

# Existing detectors
from .time_of_day import TimeOfDayPatternDetector
from .co_occurrence import CoOccurrencePatternDetector

# New ML-enhanced detectors
from .ml_pattern_detector import MLPatternDetector
from .sequence_detector import SequenceDetector
from .contextual_detector import ContextualDetector

# Additional detectors
from .room_based_detector import RoomBasedDetector
from .session_detector import SessionDetector
from .duration_detector import DurationDetector
from .day_type_detector import DayTypeDetector
from .seasonal_detector import SeasonalDetector
from .anomaly_detector import AnomalyDetector

__all__ = [
    # Base classes
    'MLPatternDetector',
    
    # Existing detectors
    'TimeOfDayPatternDetector',
    'CoOccurrencePatternDetector',
    
    # New ML-enhanced detectors
    'SequenceDetector',
    'ContextualDetector',
    
    # Additional detectors
    'RoomBasedDetector',
    'SessionDetector', 
    'DurationDetector',
    'DayTypeDetector',
    'SeasonalDetector',
    'AnomalyDetector'
]
