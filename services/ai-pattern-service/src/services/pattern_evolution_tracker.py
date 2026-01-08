"""
Pattern Evolution Tracker Service

Tracks how patterns change over time to enable adaptive automation updates.
Implements Recommendation 5.1: Pattern Evolution Tracking.

Based on PATTERNS_SYNERGIES_IMPROVEMENT_RECOMMENDATIONS.md

Created: January 2026
Features:
- Detects pattern drift (time of pattern changing)
- Identifies new patterns emerging
- Flags patterns that are no longer valid
- Tracks confidence trends
- Supports automation update recommendations
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

import numpy as np

logger = logging.getLogger(__name__)


class EvolutionType(str, Enum):
    """Types of pattern evolution."""
    
    STABLE = "stable"           # Pattern unchanged
    EVOLVING = "evolving"       # Pattern changing (time drift, confidence change)
    NEW = "new"                 # Newly detected pattern
    DEPRECATED = "deprecated"   # Pattern no longer valid
    STRENGTHENING = "strengthening"  # Pattern becoming more reliable
    WEAKENING = "weakening"     # Pattern becoming less reliable


class TrendDirection(str, Enum):
    """Direction of trend changes."""
    
    INCREASING = "increasing"
    STABLE = "stable"
    DECREASING = "decreasing"


@dataclass
class PatternEvolution:
    """Track how a single pattern changes over time."""
    
    pattern_id: str
    device_id: str
    pattern_type: str
    evolution_type: EvolutionType
    
    # Time drift analysis
    time_drift_minutes: float = 0.0
    original_time: Optional[str] = None  # HH:MM format
    current_time: Optional[str] = None   # HH:MM format
    
    # Confidence analysis
    confidence_trend: float = 0.0  # -1.0 to 1.0 (declining to improving)
    original_confidence: float = 0.0
    current_confidence: float = 0.0
    
    # Occurrence analysis
    occurrences_trend: TrendDirection = TrendDirection.STABLE
    original_occurrences: int = 0
    current_occurrences: int = 0
    
    # Timestamps
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    days_tracked: int = 0
    
    # Recommendations
    automation_update_recommended: bool = False
    update_reason: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            'pattern_id': self.pattern_id,
            'device_id': self.device_id,
            'pattern_type': self.pattern_type,
            'evolution_type': self.evolution_type.value,
            'time_drift_minutes': round(self.time_drift_minutes, 1),
            'original_time': self.original_time,
            'current_time': self.current_time,
            'confidence_trend': round(self.confidence_trend, 3),
            'original_confidence': round(self.original_confidence, 3),
            'current_confidence': round(self.current_confidence, 3),
            'occurrences_trend': self.occurrences_trend.value,
            'original_occurrences': self.original_occurrences,
            'current_occurrences': self.current_occurrences,
            'first_seen': self.first_seen.isoformat() if self.first_seen else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'days_tracked': self.days_tracked,
            'automation_update_recommended': self.automation_update_recommended,
            'update_reason': self.update_reason,
        }


@dataclass
class EvolutionAnalysisResult:
    """Results of pattern evolution analysis."""
    
    stable_patterns: list[PatternEvolution] = field(default_factory=list)
    evolving_patterns: list[PatternEvolution] = field(default_factory=list)
    new_patterns: list[PatternEvolution] = field(default_factory=list)
    deprecated_patterns: list[PatternEvolution] = field(default_factory=list)
    strengthening_patterns: list[PatternEvolution] = field(default_factory=list)
    weakening_patterns: list[PatternEvolution] = field(default_factory=list)
    
    # Summary statistics
    total_patterns_analyzed: int = 0
    patterns_requiring_update: int = 0
    analysis_timestamp: datetime = field(default_factory=datetime.utcnow)
    lookback_days: int = 30
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            'stable_patterns': [p.to_dict() for p in self.stable_patterns],
            'evolving_patterns': [p.to_dict() for p in self.evolving_patterns],
            'new_patterns': [p.to_dict() for p in self.new_patterns],
            'deprecated_patterns': [p.to_dict() for p in self.deprecated_patterns],
            'strengthening_patterns': [p.to_dict() for p in self.strengthening_patterns],
            'weakening_patterns': [p.to_dict() for p in self.weakening_patterns],
            'summary': {
                'total_patterns_analyzed': self.total_patterns_analyzed,
                'patterns_requiring_update': self.patterns_requiring_update,
                'analysis_timestamp': self.analysis_timestamp.isoformat(),
                'lookback_days': self.lookback_days,
                'stable_count': len(self.stable_patterns),
                'evolving_count': len(self.evolving_patterns),
                'new_count': len(self.new_patterns),
                'deprecated_count': len(self.deprecated_patterns),
                'strengthening_count': len(self.strengthening_patterns),
                'weakening_count': len(self.weakening_patterns),
            }
        }


class PatternEvolutionTracker:
    """
    Track how patterns change over time.
    
    Detects:
    - Pattern drift (time of pattern changing)
    - New patterns emerging
    - Patterns becoming deprecated
    - Confidence trends (strengthening/weakening)
    
    Use cases:
    - Update automations when user behavior changes
    - Identify lifestyle changes
    - Recommend automation adjustments
    """
    
    # Thresholds for evolution detection
    STABILITY_THRESHOLD_MINUTES = 15  # Patterns within 15min are "same"
    MIN_HISTORY_DAYS = 7              # Need 7 days to assess evolution
    CONFIDENCE_CHANGE_THRESHOLD = 0.1  # 10% change is significant
    DRIFT_WARNING_THRESHOLD = 30      # 30 min drift triggers warning
    OCCURRENCE_CHANGE_THRESHOLD = 0.25  # 25% change is significant
    
    def __init__(
        self,
        stability_threshold_minutes: int = 15,
        min_history_days: int = 7,
        confidence_change_threshold: float = 0.1,
    ):
        """
        Initialize pattern evolution tracker.
        
        Args:
            stability_threshold_minutes: Time difference (minutes) to consider patterns "same"
            min_history_days: Minimum days of history needed for evolution analysis
            confidence_change_threshold: Minimum confidence change to flag as evolving
        """
        self.stability_threshold_minutes = stability_threshold_minutes
        self.min_history_days = min_history_days
        self.confidence_change_threshold = confidence_change_threshold
        
        logger.info(
            f"PatternEvolutionTracker initialized: "
            f"stability_threshold={stability_threshold_minutes}min, "
            f"min_history_days={min_history_days}, "
            f"confidence_threshold={confidence_change_threshold}"
        )
    
    def analyze_evolution(
        self,
        current_patterns: list[dict[str, Any]],
        historical_patterns: list[dict[str, Any]],
        lookback_days: int = 30,
    ) -> EvolutionAnalysisResult:
        """
        Analyze pattern evolution over time.
        
        Args:
            current_patterns: Currently detected patterns
            historical_patterns: Historical pattern data (from database/InfluxDB)
            lookback_days: Number of days to look back for comparison
            
        Returns:
            EvolutionAnalysisResult with categorized patterns
        """
        result = EvolutionAnalysisResult(lookback_days=lookback_days)
        
        # Index historical patterns by device_id
        historical_by_device = self._group_by_device(historical_patterns)
        current_by_device = self._group_by_device(current_patterns)
        
        all_device_ids = set(historical_by_device.keys()) | set(current_by_device.keys())
        result.total_patterns_analyzed = len(all_device_ids)
        
        # Analyze each device's patterns
        for device_id in all_device_ids:
            current = current_by_device.get(device_id, [])
            historical = historical_by_device.get(device_id, [])
            
            if current and not historical:
                # New pattern
                evolution = self._create_new_pattern_evolution(current[0])
                result.new_patterns.append(evolution)
                
            elif historical and not current:
                # Deprecated pattern
                evolution = self._create_deprecated_pattern_evolution(historical[-1])
                result.deprecated_patterns.append(evolution)
                result.patterns_requiring_update += 1
                
            elif current and historical:
                # Compare current to historical
                evolution = self._compare_patterns(current[0], historical)
                
                # Categorize based on evolution type
                if evolution.evolution_type == EvolutionType.STABLE:
                    result.stable_patterns.append(evolution)
                elif evolution.evolution_type == EvolutionType.EVOLVING:
                    result.evolving_patterns.append(evolution)
                    result.patterns_requiring_update += 1
                elif evolution.evolution_type == EvolutionType.STRENGTHENING:
                    result.strengthening_patterns.append(evolution)
                elif evolution.evolution_type == EvolutionType.WEAKENING:
                    result.weakening_patterns.append(evolution)
                    if evolution.current_confidence < 0.6:
                        result.patterns_requiring_update += 1
        
        logger.info(
            f"Evolution analysis complete: "
            f"stable={len(result.stable_patterns)}, "
            f"evolving={len(result.evolving_patterns)}, "
            f"new={len(result.new_patterns)}, "
            f"deprecated={len(result.deprecated_patterns)}, "
            f"strengthening={len(result.strengthening_patterns)}, "
            f"weakening={len(result.weakening_patterns)}"
        )
        
        return result
    
    def _group_by_device(
        self,
        patterns: list[dict[str, Any]],
    ) -> dict[str, list[dict[str, Any]]]:
        """Group patterns by device_id."""
        groups: dict[str, list[dict[str, Any]]] = {}
        
        for pattern in patterns:
            device_id = pattern.get('device_id', '')
            if device_id:
                if device_id not in groups:
                    groups[device_id] = []
                groups[device_id].append(pattern)
        
        # Sort each group by timestamp (oldest first)
        for device_id in groups:
            groups[device_id].sort(
                key=lambda p: p.get('detected_at', p.get('timestamp', ''))
            )
        
        return groups
    
    def _create_new_pattern_evolution(
        self,
        pattern: dict[str, Any],
    ) -> PatternEvolution:
        """Create evolution record for a new pattern."""
        hour = pattern.get('hour', 0)
        minute = pattern.get('minute', 0)
        
        return PatternEvolution(
            pattern_id=pattern.get('pattern_id', ''),
            device_id=pattern.get('device_id', ''),
            pattern_type=pattern.get('pattern_type', 'time_of_day'),
            evolution_type=EvolutionType.NEW,
            current_time=f"{hour:02d}:{minute:02d}",
            current_confidence=pattern.get('confidence', 0.0),
            current_occurrences=pattern.get('occurrences', 0),
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow(),
            days_tracked=0,
            automation_update_recommended=False,
            update_reason="New pattern detected - consider creating automation",
        )
    
    def _create_deprecated_pattern_evolution(
        self,
        pattern: dict[str, Any],
    ) -> PatternEvolution:
        """Create evolution record for a deprecated pattern."""
        hour = pattern.get('hour', 0)
        minute = pattern.get('minute', 0)
        
        # Calculate days since last seen
        detected_at = pattern.get('detected_at')
        if isinstance(detected_at, str):
            try:
                detected_at = datetime.fromisoformat(detected_at.replace('Z', '+00:00'))
            except ValueError:
                detected_at = None
        
        days_since = 0
        if detected_at:
            days_since = (datetime.utcnow() - detected_at.replace(tzinfo=None)).days
        
        return PatternEvolution(
            pattern_id=pattern.get('pattern_id', ''),
            device_id=pattern.get('device_id', ''),
            pattern_type=pattern.get('pattern_type', 'time_of_day'),
            evolution_type=EvolutionType.DEPRECATED,
            original_time=f"{hour:02d}:{minute:02d}",
            original_confidence=pattern.get('confidence', 0.0),
            original_occurrences=pattern.get('occurrences', 0),
            first_seen=detected_at,
            last_seen=detected_at,
            days_tracked=days_since,
            automation_update_recommended=True,
            update_reason=f"Pattern no longer detected (last seen {days_since} days ago) - consider disabling automation",
        )
    
    def _compare_patterns(
        self,
        current: dict[str, Any],
        historical: list[dict[str, Any]],
    ) -> PatternEvolution:
        """
        Compare current pattern to historical data.
        
        Args:
            current: Current pattern
            historical: List of historical patterns (sorted by time)
            
        Returns:
            PatternEvolution with analysis results
        """
        # Get time values
        current_hour = current.get('hour', 0)
        current_minute = current.get('minute', 0)
        current_time_decimal = current_hour + current_minute / 60.0
        
        # Calculate historical averages
        historical_times = []
        historical_confidences = []
        historical_occurrences = []
        
        for h in historical:
            h_hour = h.get('hour', 0)
            h_minute = h.get('minute', 0)
            historical_times.append(h_hour + h_minute / 60.0)
            historical_confidences.append(h.get('confidence', 0.0))
            historical_occurrences.append(h.get('occurrences', 0))
        
        # Calculate metrics
        avg_historical_time = np.mean(historical_times) if historical_times else current_time_decimal
        avg_historical_confidence = np.mean(historical_confidences) if historical_confidences else 0.0
        avg_historical_occurrences = np.mean(historical_occurrences) if historical_occurrences else 0
        
        # Time drift (in minutes)
        time_drift_minutes = abs(current_time_decimal - avg_historical_time) * 60
        
        # Confidence trend (-1.0 to 1.0)
        current_confidence = current.get('confidence', 0.0)
        if avg_historical_confidence > 0:
            confidence_change = current_confidence - avg_historical_confidence
            std_confidence = np.std(historical_confidences) if len(historical_confidences) > 1 else 0.1
            confidence_trend = confidence_change / max(std_confidence, 0.01)
            confidence_trend = float(np.clip(confidence_trend, -1.0, 1.0))
        else:
            confidence_trend = 0.0
        
        # Occurrences trend
        current_occurrences = current.get('occurrences', 0)
        if avg_historical_occurrences > 0:
            occurrence_change = (current_occurrences - avg_historical_occurrences) / avg_historical_occurrences
            if occurrence_change > self.OCCURRENCE_CHANGE_THRESHOLD:
                occurrences_trend = TrendDirection.INCREASING
            elif occurrence_change < -self.OCCURRENCE_CHANGE_THRESHOLD:
                occurrences_trend = TrendDirection.DECREASING
            else:
                occurrences_trend = TrendDirection.STABLE
        else:
            occurrences_trend = TrendDirection.STABLE
        
        # Determine evolution type
        evolution_type = self._determine_evolution_type(
            time_drift_minutes,
            confidence_trend,
            current_confidence,
            occurrences_trend,
        )
        
        # Determine if automation update is recommended
        update_recommended, update_reason = self._determine_update_recommendation(
            evolution_type,
            time_drift_minutes,
            confidence_trend,
            current_confidence,
        )
        
        # Get timestamps
        first_historical = historical[0] if historical else {}
        first_seen = first_historical.get('detected_at')
        if isinstance(first_seen, str):
            try:
                first_seen = datetime.fromisoformat(first_seen.replace('Z', '+00:00'))
            except ValueError:
                first_seen = None
        
        days_tracked = 0
        if first_seen:
            days_tracked = (datetime.utcnow() - first_seen.replace(tzinfo=None)).days
        
        # Format times
        original_hour = int(avg_historical_time)
        original_minute = int((avg_historical_time % 1) * 60)
        
        return PatternEvolution(
            pattern_id=current.get('pattern_id', ''),
            device_id=current.get('device_id', ''),
            pattern_type=current.get('pattern_type', 'time_of_day'),
            evolution_type=evolution_type,
            time_drift_minutes=float(time_drift_minutes),
            original_time=f"{original_hour:02d}:{original_minute:02d}",
            current_time=f"{current_hour:02d}:{current_minute:02d}",
            confidence_trend=confidence_trend,
            original_confidence=float(avg_historical_confidence),
            current_confidence=float(current_confidence),
            occurrences_trend=occurrences_trend,
            original_occurrences=int(avg_historical_occurrences),
            current_occurrences=current_occurrences,
            first_seen=first_seen,
            last_seen=datetime.utcnow(),
            days_tracked=days_tracked,
            automation_update_recommended=update_recommended,
            update_reason=update_reason,
        )
    
    def _determine_evolution_type(
        self,
        time_drift_minutes: float,
        confidence_trend: float,
        current_confidence: float,
        occurrences_trend: TrendDirection,
    ) -> EvolutionType:
        """Determine the type of pattern evolution."""
        # Check for significant time drift
        if time_drift_minutes > self.DRIFT_WARNING_THRESHOLD:
            return EvolutionType.EVOLVING
        
        # Check for confidence changes
        if confidence_trend > self.confidence_change_threshold:
            return EvolutionType.STRENGTHENING
        elif confidence_trend < -self.confidence_change_threshold:
            if current_confidence < 0.5:
                return EvolutionType.WEAKENING
            else:
                return EvolutionType.EVOLVING
        
        # Check for occurrence changes
        if occurrences_trend == TrendDirection.DECREASING:
            return EvolutionType.WEAKENING
        
        # Pattern is stable
        if time_drift_minutes <= self.stability_threshold_minutes:
            return EvolutionType.STABLE
        
        return EvolutionType.EVOLVING
    
    def _determine_update_recommendation(
        self,
        evolution_type: EvolutionType,
        time_drift_minutes: float,
        confidence_trend: float,
        current_confidence: float,
    ) -> tuple[bool, Optional[str]]:
        """Determine if automation update is recommended."""
        if evolution_type == EvolutionType.STABLE:
            return False, None
        
        if evolution_type == EvolutionType.EVOLVING:
            if time_drift_minutes > self.DRIFT_WARNING_THRESHOLD:
                return True, f"Pattern time has shifted by {time_drift_minutes:.0f} minutes - update automation trigger time"
            return True, "Pattern is changing - review automation settings"
        
        if evolution_type == EvolutionType.WEAKENING:
            if current_confidence < 0.5:
                return True, f"Pattern confidence dropped to {current_confidence:.0%} - consider disabling automation"
            return False, f"Pattern weakening (confidence: {current_confidence:.0%}) - monitor for further decline"
        
        if evolution_type == EvolutionType.STRENGTHENING:
            return False, f"Pattern strengthening (confidence: {current_confidence:.0%}) - no action needed"
        
        if evolution_type == EvolutionType.DEPRECATED:
            return True, "Pattern no longer detected - disable or remove automation"
        
        if evolution_type == EvolutionType.NEW:
            return False, "New pattern detected - consider creating automation"
        
        return False, None
    
    def get_automation_recommendations(
        self,
        analysis_result: EvolutionAnalysisResult,
    ) -> list[dict[str, Any]]:
        """
        Generate automation update recommendations from analysis.
        
        Args:
            analysis_result: Evolution analysis result
            
        Returns:
            List of recommendation dictionaries
        """
        recommendations = []
        
        # Deprecated patterns - high priority
        for pattern in analysis_result.deprecated_patterns:
            recommendations.append({
                'priority': 'high',
                'action': 'disable',
                'device_id': pattern.device_id,
                'pattern_id': pattern.pattern_id,
                'reason': pattern.update_reason,
                'original_time': pattern.original_time,
            })
        
        # Evolving patterns with significant drift - medium priority
        for pattern in analysis_result.evolving_patterns:
            if pattern.time_drift_minutes > self.DRIFT_WARNING_THRESHOLD:
                recommendations.append({
                    'priority': 'medium',
                    'action': 'update_time',
                    'device_id': pattern.device_id,
                    'pattern_id': pattern.pattern_id,
                    'reason': pattern.update_reason,
                    'original_time': pattern.original_time,
                    'new_time': pattern.current_time,
                    'time_drift_minutes': pattern.time_drift_minutes,
                })
        
        # Weakening patterns - low priority
        for pattern in analysis_result.weakening_patterns:
            if pattern.current_confidence < 0.5:
                recommendations.append({
                    'priority': 'low',
                    'action': 'review',
                    'device_id': pattern.device_id,
                    'pattern_id': pattern.pattern_id,
                    'reason': pattern.update_reason,
                    'confidence': pattern.current_confidence,
                })
        
        # New patterns - informational
        for pattern in analysis_result.new_patterns:
            recommendations.append({
                'priority': 'info',
                'action': 'create',
                'device_id': pattern.device_id,
                'pattern_id': pattern.pattern_id,
                'reason': pattern.update_reason,
                'suggested_time': pattern.current_time,
                'confidence': pattern.current_confidence,
            })
        
        # Sort by priority
        priority_order = {'high': 0, 'medium': 1, 'low': 2, 'info': 3}
        recommendations.sort(key=lambda r: priority_order.get(r['priority'], 99))
        
        return recommendations
