"""
Pattern Detection Module
Enhanced with ML-Powered Pattern Detection

This module implements advanced pattern detection algorithms using
scikit-learn and pandas optimizations to identify recurring behaviors
in Home Assistant events.
"""

# Existing detectors (imported from pattern_analyzer)
from src.pattern_analyzer.co_occurrence import CoOccurrencePatternDetector
from src.pattern_analyzer.time_of_day import TimeOfDayPatternDetector

from .anomaly_detector import AnomalyDetector
from .contextual_detector import ContextualDetector
from .day_type_detector import DayTypeDetector
from .duration_detector import DurationDetector

# New ML-enhanced detectors
from .ml_pattern_detector import MLPatternDetector

# Additional detectors
from .room_based_detector import RoomBasedDetector
from .seasonal_detector import SeasonalDetector
from .sequence_detector import SequenceDetector
from .session_detector import SessionDetector

__all__ = [
    "AnomalyDetector",
    "CoOccurrencePatternDetector",
    "ContextualDetector",
    "DayTypeDetector",
    "DurationDetector",
    # Base classes
    "MLPatternDetector",
    # Additional detectors
    "RoomBasedDetector",
    "SeasonalDetector",
    # New ML-enhanced detectors
    "SequenceDetector",
    "SessionDetector",
    # Existing detectors
    "TimeOfDayPatternDetector",
]
