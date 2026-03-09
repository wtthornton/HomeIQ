"""Pattern analysis package

Epic 39, Story 39.5: Pattern Service Foundation
Extracted from ai-automation-service.

Epic 37: Pattern Detection Expansion
- Story 37.1: SequencePatternDetector
- Story 37.2: DurationPatternDetector
- Story 37.3: DayTypePatternDetector
- Story 37.4: RoomBasedPatternDetector
- Story 37.6: AnomalyPatternDetector
- Story 37.7: FrequencyPatternDetector
- Story 37.5: SeasonalPatternDetector
- Story 37.8: ContextualPatternDetector
"""

from .anomaly import AnomalyPatternDetector
from .co_occurrence import CoOccurrencePatternDetector, FPGrowthDetector
from .contextual import ContextualPatternDetector
from .day_type import DayTypePatternDetector
from .duration import DurationPatternDetector
from .frequency import FrequencyPatternDetector
from .room_based import RoomBasedPatternDetector
from .seasonal import SeasonalPatternDetector
from .sequence import SequencePatternDetector
from .time_of_day import TimeOfDayPatternDetector

__all__ = [
    "TimeOfDayPatternDetector",
    "CoOccurrencePatternDetector",
    "FPGrowthDetector",
    "SequencePatternDetector",
    "DurationPatternDetector",
    "AnomalyPatternDetector",
    "RoomBasedPatternDetector",
    "DayTypePatternDetector",
    "FrequencyPatternDetector",
    "SeasonalPatternDetector",
    "ContextualPatternDetector",
]
