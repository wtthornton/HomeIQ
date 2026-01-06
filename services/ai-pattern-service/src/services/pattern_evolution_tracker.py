"""
Pattern Evolution Tracker Service

Tracks how patterns change over time to detect pattern drift, identify new patterns,
and flag patterns that are no longer valid.

Based on PATTERNS_SYNERGIES_IMPROVEMENT_RECOMMENDATIONS.md - Recommendation 5.1
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..crud.patterns import get_patterns

logger = logging.getLogger(__name__)


# Constants for stability thresholds
CONFIDENCE_STABILITY_THRESHOLD = 0.1  # 10% confidence change
OCCURRENCE_STABILITY_THRESHOLD = 0.2  # 20% occurrence change
DEFAULT_PATTERN_LIMIT = 10000


@dataclass
class EvolutionMetadata:
    """Metadata for pattern evolution."""
    
    previous_confidence: float = 0.0
    current_confidence: float = 0.0
    confidence_delta: float = 0.0
    previous_occurrences: int = 0
    current_occurrences: int = 0
    occurrences_delta: int = 0
    first_detected: Optional[str] = None
    last_seen: Optional[str] = None
    is_new: bool = False
    is_deprecated: bool = False
    deprecation_reason: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        result = {}
        if self.is_new:
            result['first_detected'] = self.first_detected
            result['is_new'] = self.is_new
        elif self.is_deprecated:
            result['last_seen'] = self.last_seen
            result['is_deprecated'] = self.is_deprecated
            result['deprecation_reason'] = self.deprecation_reason
        else:
            result = {
                'previous_confidence': self.previous_confidence,
                'current_confidence': self.current_confidence,
                'confidence_delta': self.confidence_delta,
                'previous_occurrences': self.previous_occurrences,
                'current_occurrences': self.current_occurrences,
                'occurrences_delta': self.occurrences_delta
            }
        return result


@dataclass
class EvolutionResults:
    """Results of pattern evolution analysis."""
    
    stable_patterns: list[dict[str, Any]] = field(default_factory=list)
    evolving_patterns: list[dict[str, Any]] = field(default_factory=list)
    new_patterns: list[dict[str, Any]] = field(default_factory=list)
    deprecated_patterns: list[dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self, total_current: int, total_historical: int) -> dict[str, Any]:
        """Convert to dictionary with summary."""
        return {
            'stable_patterns': self.stable_patterns,
            'evolving_patterns': self.evolving_patterns,
            'new_patterns': self.new_patterns,
            'deprecated_patterns': self.deprecated_patterns,
            'summary': {
                'total_current': total_current,
                'total_historical': total_historical,
                'stable_count': len(self.stable_patterns),
                'evolving_count': len(self.evolving_patterns),
                'new_count': len(self.new_patterns),
                'deprecated_count': len(self.deprecated_patterns)
            }
        }


class PatternEvolutionTracker:
    """
    Track how patterns change over time.
    
    Features:
        - Detect pattern drift (patterns changing)
        - Identify new patterns emerging
        - Flag patterns that are no longer valid
    
    Example:
        >>> tracker = PatternEvolutionTracker(db)
        >>> results = await tracker.track_pattern_evolution(current_patterns)
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize pattern evolution tracker.
        
        Args:
            db: Database session for retrieving historical patterns
        """
        self.db = db
        logger.info("PatternEvolutionTracker initialized")
    
    async def track_pattern_evolution(
        self,
        current_patterns: list[dict[str, Any]],
        historical_window_days: int = 30
    ) -> dict[str, Any]:
        """
        Compare current patterns to historical patterns.
        
        Recommendation 5.1: Pattern Evolution Tracking
        - Detect pattern drift (patterns changing)
        - Identify new patterns emerging
        - Flag patterns that are no longer valid
        
        Args:
            current_patterns: List of currently detected patterns
            historical_window_days: Number of days to look back for historical patterns
            
        Returns:
            Dictionary with stable, evolving, new, and deprecated patterns
        """
        logger.info(f"Tracking pattern evolution for {len(current_patterns)} current patterns")
        
        historical_patterns = await self._get_historical_patterns(historical_window_days)
        logger.info(f"Found {len(historical_patterns)} historical patterns")
        
        current_map = self._create_pattern_map(current_patterns)
        historical_map = self._create_pattern_map(historical_patterns)
        
        results = self._analyze_evolution(current_map, historical_map)
        
        self._log_results(results)
        
        return results.to_dict(len(current_patterns), len(historical_patterns))
    
    def _analyze_evolution(
        self,
        current_map: dict[str, dict[str, Any]],
        historical_map: dict[str, dict[str, Any]]
    ) -> EvolutionResults:
        """Analyze pattern evolution by comparing current and historical patterns."""
        results = EvolutionResults()
        
        # Analyze current patterns
        for pattern_key, current_pattern in current_map.items():
            if pattern_key in historical_map:
                self._classify_existing_pattern(
                    current_pattern,
                    historical_map[pattern_key],
                    results
                )
            else:
                self._add_new_pattern(current_pattern, results)
        
        # Find deprecated patterns
        for pattern_key, historical_pattern in historical_map.items():
            if pattern_key not in current_map:
                self._add_deprecated_pattern(historical_pattern, results)
        
        return results
    
    def _classify_existing_pattern(
        self,
        current: dict[str, Any],
        historical: dict[str, Any],
        results: EvolutionResults
    ) -> None:
        """Classify an existing pattern as stable or evolving."""
        if self._is_pattern_stable(current, historical):
            results.stable_patterns.append(current)
        else:
            results.evolving_patterns.append(
                self._create_evolving_pattern(current, historical)
            )
    
    def _add_new_pattern(
        self,
        pattern: dict[str, Any],
        results: EvolutionResults
    ) -> None:
        """Add a new pattern to results."""
        new_pattern = pattern.copy()
        metadata = EvolutionMetadata(
            first_detected=datetime.now(timezone.utc).isoformat(),
            is_new=True
        )
        new_pattern['evolution_metadata'] = metadata.to_dict()
        results.new_patterns.append(new_pattern)
    
    def _add_deprecated_pattern(
        self,
        pattern: dict[str, Any],
        results: EvolutionResults
    ) -> None:
        """Add a deprecated pattern to results."""
        deprecated = pattern.copy()
        metadata = EvolutionMetadata(
            last_seen=pattern.get('updated_at') or pattern.get('last_seen'),
            is_deprecated=True,
            deprecation_reason='No longer detected in current analysis'
        )
        deprecated['evolution_metadata'] = metadata.to_dict()
        results.deprecated_patterns.append(deprecated)
    
    def _create_evolving_pattern(
        self,
        current: dict[str, Any],
        historical: dict[str, Any]
    ) -> dict[str, Any]:
        """Create an evolving pattern with evolution metadata."""
        evolving = current.copy()
        
        current_conf = current.get('confidence', 0.0)
        historical_conf = historical.get('confidence', 0.0)
        current_occ = current.get('occurrences', 0)
        historical_occ = historical.get('occurrences', 0)
        
        metadata = EvolutionMetadata(
            previous_confidence=historical_conf,
            current_confidence=current_conf,
            confidence_delta=current_conf - historical_conf,
            previous_occurrences=historical_occ,
            current_occurrences=current_occ,
            occurrences_delta=current_occ - historical_occ
        )
        evolving['evolution_metadata'] = metadata.to_dict()
        
        return evolving
    
    async def _get_historical_patterns(self, window_days: int) -> list[dict[str, Any]]:
        """Get historical patterns from database."""
        try:
            patterns = await get_patterns(self.db, limit=DEFAULT_PATTERN_LIMIT)
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=window_days)
            
            return [
                self._pattern_to_dict(p)
                for p in patterns
                if self._is_within_window(p, cutoff_date)
            ]
        except Exception as e:
            logger.error(f"Failed to get historical patterns: {e}", exc_info=True)
            return []
    
    def _pattern_to_dict(self, pattern: Any) -> dict[str, Any]:
        """Convert pattern to dictionary."""
        if isinstance(pattern, dict):
            return pattern
        
        return {
            'id': getattr(pattern, 'id', None),
            'pattern_type': getattr(pattern, 'pattern_type', None),
            'device_id': getattr(pattern, 'device_id', None),
            'pattern_metadata': getattr(pattern, 'pattern_metadata', {}),
            'confidence': getattr(pattern, 'confidence', 0.0),
            'occurrences': getattr(pattern, 'occurrences', 0),
            'created_at': getattr(pattern, 'created_at', None),
            'updated_at': getattr(pattern, 'updated_at', None),
            'last_seen': getattr(pattern, 'last_seen', None)
        }
    
    def _is_within_window(self, pattern: Any, cutoff_date: datetime) -> bool:
        """Check if pattern is within the time window."""
        pattern_dict = pattern if isinstance(pattern, dict) else self._pattern_to_dict(pattern)
        pattern_date = self._get_pattern_date(pattern_dict)
        
        if pattern_date is None:
            return True  # Include patterns without dates
        
        return pattern_date >= cutoff_date
    
    def _get_pattern_date(self, pattern_dict: dict[str, Any]) -> Optional[datetime]:
        """Extract and parse pattern date."""
        date_str = (
            pattern_dict.get('updated_at') or
            pattern_dict.get('last_seen') or
            pattern_dict.get('created_at')
        )
        
        if date_str is None:
            return None
        
        if isinstance(date_str, datetime):
            return date_str
        
        try:
            return datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return None
    
    def _create_pattern_map(
        self,
        patterns: list[dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        """Create a lookup map from patterns."""
        return {
            f"{p.get('pattern_type', 'unknown')}:{p.get('device_id', 'unknown')}": p
            for p in patterns
        }
    
    def _is_pattern_stable(
        self,
        current: dict[str, Any],
        historical: dict[str, Any]
    ) -> bool:
        """Check if a pattern is stable (hasn't changed significantly)."""
        if not self._is_confidence_stable(current, historical):
            return False
        
        return self._is_occurrences_stable(current, historical)
    
    def _is_confidence_stable(
        self,
        current: dict[str, Any],
        historical: dict[str, Any]
    ) -> bool:
        """Check if confidence is stable."""
        current_conf = current.get('confidence', 0.0)
        historical_conf = historical.get('confidence', 0.0)
        
        return abs(current_conf - historical_conf) <= CONFIDENCE_STABILITY_THRESHOLD
    
    def _is_occurrences_stable(
        self,
        current: dict[str, Any],
        historical: dict[str, Any]
    ) -> bool:
        """Check if occurrences are stable."""
        current_occ = current.get('occurrences', 0)
        historical_occ = historical.get('occurrences', 0)
        
        if historical_occ == 0:
            return True
        
        change_pct = abs(current_occ - historical_occ) / historical_occ
        return change_pct <= OCCURRENCE_STABILITY_THRESHOLD
    
    def _log_results(self, results: EvolutionResults) -> None:
        """Log evolution analysis results."""
        logger.info(
            f"✅ Pattern evolution analysis complete: "
            f"{len(results.stable_patterns)} stable, "
            f"{len(results.evolving_patterns)} evolving, "
            f"{len(results.new_patterns)} new, "
            f"{len(results.deprecated_patterns)} deprecated"
        )
