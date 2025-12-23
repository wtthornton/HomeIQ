"""
Long-term Pattern Detection

Epic 37, Story 37.4: Long-term Pattern Detection
Uses state history to detect seasonal and long-term correlation patterns.

Single-home NUC optimized:
- Memory: <10MB (pattern cache)
- Performance: <5s for 90-day analysis
- Batch processing: Analyzes patterns in background
"""

import logging
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np

from .state_history_client import StateHistoryClient

from shared.logging_config import get_logger

logger = get_logger(__name__)


class LongTermPatternDetector:
    """
    Detects long-term correlation patterns using state history.
    
    Analyzes:
    - Seasonal patterns (summer vs winter correlations)
    - Weekly patterns (weekday vs weekend)
    - Long-term trends (correlation strength over time)
    - Historical validation (validate correlations against past data)
    
    Single-home NUC optimization:
    - Processes 30-90 days of history
    - In-memory pattern cache
    - Batch analysis (not real-time)
    """
    
    def __init__(
        self,
        state_history_client: StateHistoryClient,
        min_history_days: int = 30,
        max_history_days: int = 90
    ):
        """
        Initialize long-term pattern detector.
        
        Args:
            state_history_client: State history API client
            min_history_days: Minimum days of history required (default: 30)
            max_history_days: Maximum days of history to analyze (default: 90)
        """
        self.state_history_client = state_history_client
        self.min_history_days = min_history_days
        self.max_history_days = max_history_days
        
        # Pattern cache: (entity1_id, entity2_id) -> pattern data
        self.pattern_cache: Dict[Tuple[str, str], Dict] = {}
        
        logger.info(
            "LongTermPatternDetector initialized (min_days=%d, max_days=%d)",
            min_history_days, max_history_days
        )
    
    async def analyze_correlation_pattern(
        self,
        entity1_id: str,
        entity2_id: str,
        days: Optional[int] = None
    ) -> Optional[Dict]:
        """
        Analyze long-term correlation pattern for an entity pair.
        
        Args:
            entity1_id: Entity 1 ID
            entity2_id: Entity 2 ID
            days: Number of days to analyze (default: max_history_days)
        
        Returns:
            Dict with pattern analysis:
            - seasonal_pattern: Seasonal correlation strength
            - weekly_pattern: Weekday vs weekend patterns
            - trend: Long-term trend (increasing/decreasing)
            - historical_correlation: Average correlation over period
            - confidence: Pattern confidence score
        """
        if days is None:
            days = self.max_history_days
        
        # Check cache
        cache_key = (entity1_id, entity2_id, days)
        if cache_key in self.pattern_cache:
            logger.debug("Cache hit for pattern analysis: %s <-> %s", entity1_id, entity2_id)
            return self.pattern_cache[cache_key]
        
        try:
            # Get state history for both entities
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days)
            
            history = await self.state_history_client.get_correlation_history(
                entity1_id, entity2_id, start_time, end_time
            )
            
            entity1_history = history.get('entity1', [])
            entity2_history = history.get('entity2', [])
            
            if not entity1_history or not entity2_history:
                logger.debug("Insufficient history for pattern analysis: %s <-> %s", entity1_id, entity2_id)
                return None
            
            # Analyze patterns
            pattern = self._analyze_patterns(
                entity1_id, entity2_id,
                entity1_history, entity2_history,
                start_time, end_time
            )
            
            # Cache result
            self.pattern_cache[cache_key] = pattern
            
            logger.debug(
                "Analyzed pattern for %s <-> %s: confidence=%.2f",
                entity1_id, entity2_id, pattern.get('confidence', 0.0)
            )
            
            return pattern
            
        except Exception as e:
            logger.error("Error analyzing pattern for %s <-> %s: %s", entity1_id, entity2_id, e)
            return None
    
    def _analyze_patterns(
        self,
        entity1_id: str,
        entity2_id: str,
        entity1_history: List[Dict],
        entity2_history: List[Dict],
        start_time: datetime,
        end_time: datetime
    ) -> Dict:
        """
        Analyze patterns from state history.
        
        Args:
            entity1_id: Entity 1 ID
            entity2_id: Entity 2 ID
            entity1_history: Entity 1 state history
            entity2_history: Entity 2 state history
            start_time: Analysis start time
            end_time: Analysis end time
        
        Returns:
            Pattern analysis dict
        """
        # Convert history to time series
        entity1_ts = self._history_to_timeseries(entity1_history)
        entity2_ts = self._history_to_timeseries(entity2_history)
        
        # Calculate historical correlation
        historical_correlation = self._calculate_historical_correlation(
            entity1_ts, entity2_ts
        )
        
        # Detect seasonal patterns
        seasonal_pattern = self._detect_seasonal_pattern(
            entity1_ts, entity2_ts, start_time, end_time
        )
        
        # Detect weekly patterns
        weekly_pattern = self._detect_weekly_pattern(
            entity1_ts, entity2_ts
        )
        
        # Detect long-term trend
        trend = self._detect_trend(
            entity1_ts, entity2_ts, start_time, end_time
        )
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            historical_correlation, seasonal_pattern, weekly_pattern, trend
        )
        
        return {
            "entity1_id": entity1_id,
            "entity2_id": entity2_id,
            "historical_correlation": historical_correlation,
            "seasonal_pattern": seasonal_pattern,
            "weekly_pattern": weekly_pattern,
            "trend": trend,
            "confidence": confidence,
            "analysis_period_days": (end_time - start_time).days,
            "entity1_state_changes": len(entity1_history),
            "entity2_state_changes": len(entity2_history)
        }
    
    def _history_to_timeseries(self, history: List[Dict]) -> List[Tuple[datetime, str]]:
        """
        Convert state history to time series.
        
        Args:
            history: List of state change dicts
        
        Returns:
            List of (timestamp, state) tuples
        """
        timeseries = []
        for entry in history:
            # Parse timestamp
            last_changed = entry.get("last_changed")
            if isinstance(last_changed, str):
                try:
                    timestamp = datetime.fromisoformat(last_changed.replace('Z', '+00:00'))
                except:
                    continue
            elif isinstance(last_changed, datetime):
                timestamp = last_changed
            else:
                continue
            
            state = entry.get("state", "")
            timeseries.append((timestamp, state))
        
        # Sort by timestamp
        timeseries.sort(key=lambda x: x[0])
        
        return timeseries
    
    def _calculate_historical_correlation(
        self,
        entity1_ts: List[Tuple[datetime, str]],
        entity2_ts: List[Tuple[datetime, str]]
    ) -> float:
        """
        Calculate historical correlation coefficient.
        
        Uses co-occurrence analysis: how often entities change state together.
        
        Args:
            entity1_ts: Entity 1 time series
            entity2_ts: Entity 2 time series
        
        Returns:
            Correlation coefficient (-1.0 to 1.0)
        """
        if not entity1_ts or not entity2_ts:
            return 0.0
        
        # Create time windows (15-minute windows)
        window_size = timedelta(minutes=15)
        
        # Group state changes by time windows
        entity1_windows = defaultdict(list)
        entity2_windows = defaultdict(list)
        
        for timestamp, state in entity1_ts:
            window = timestamp.replace(second=0, microsecond=0)
            window = window.replace(minute=(window.minute // 15) * 15)
            entity1_windows[window].append(state)
        
        for timestamp, state in entity2_ts:
            window = timestamp.replace(second=0, microsecond=0)
            window = window.replace(minute=(window.minute // 15) * 15)
            entity2_windows[window].append(state)
        
        # Find overlapping windows
        all_windows = set(entity1_windows.keys()) | set(entity2_windows.keys())
        co_occurrences = 0
        total_windows = 0
        
        for window in all_windows:
            if window in entity1_windows and window in entity2_windows:
                co_occurrences += 1
            total_windows += 1
        
        if total_windows == 0:
            return 0.0
        
        # Simple correlation: co-occurrence rate
        correlation = (co_occurrences / total_windows) * 2.0 - 1.0  # Normalize to -1 to 1
        
        return max(-1.0, min(1.0, correlation))
    
    def _detect_seasonal_pattern(
        self,
        entity1_ts: List[Tuple[datetime, str]],
        entity2_ts: List[Tuple[datetime, str]],
        start_time: datetime,
        end_time: datetime
    ) -> Dict:
        """
        Detect seasonal patterns (summer vs winter, etc.).
        
        Args:
            entity1_ts: Entity 1 time series
            entity2_ts: Entity 2 time series
            start_time: Analysis start time
            end_time: Analysis end time
        
        Returns:
            Dict with seasonal pattern info
        """
        # Group by month
        monthly_correlations = defaultdict(list)
        
        for timestamp, _ in entity1_ts + entity2_ts:
            month = timestamp.month
            # Simple: summer (6-8) vs winter (12-2)
            season = "summer" if 6 <= month <= 8 else "winter" if month in [12, 1, 2] else "other"
            monthly_correlations[season].append(timestamp)
        
        # Calculate correlation per season
        seasonal_strength = {}
        for season, timestamps in monthly_correlations.items():
            if len(timestamps) > 10:  # Minimum data points
                # Count co-occurrences in this season
                season_entity1 = [ts for ts, _ in entity1_ts if ts.month in self._get_season_months(season)]
                season_entity2 = [ts for ts, _ in entity2_ts if ts.month in self._get_season_months(season)]
                
                if season_entity1 and season_entity2:
                    # Simple co-occurrence rate
                    co_occur = len(set(season_entity1) & set(season_entity2))
                    total = len(set(season_entity1) | set(season_entity2))
                    strength = co_occur / total if total > 0 else 0.0
                    seasonal_strength[season] = strength
        
        return {
            "seasonal_strength": seasonal_strength,
            "strongest_season": max(seasonal_strength.items(), key=lambda x: x[1])[0] if seasonal_strength else None
        }
    
    def _get_season_months(self, season: str) -> List[int]:
        """Get month numbers for a season."""
        if season == "summer":
            return [6, 7, 8]
        elif season == "winter":
            return [12, 1, 2]
        elif season == "spring":
            return [3, 4, 5]
        elif season == "fall":
            return [9, 10, 11]
        return list(range(1, 13))
    
    def _detect_weekly_pattern(
        self,
        entity1_ts: List[Tuple[datetime, str]],
        entity2_ts: List[Tuple[datetime, str]]
    ) -> Dict:
        """
        Detect weekly patterns (weekday vs weekend).
        
        Args:
            entity1_ts: Entity 1 time series
            entity2_ts: Entity 2 time series
        
        Returns:
            Dict with weekly pattern info
        """
        weekday_changes = 0
        weekend_changes = 0
        
        for timestamp, _ in entity1_ts + entity2_ts:
            if timestamp.weekday() < 5:  # Monday-Friday
                weekday_changes += 1
            else:  # Saturday-Sunday
                weekend_changes += 1
        
        total = weekday_changes + weekend_changes
        if total == 0:
            return {"weekday_ratio": 0.5, "weekend_ratio": 0.5}
        
        return {
            "weekday_ratio": weekday_changes / total,
            "weekend_ratio": weekend_changes / total,
            "prefers_weekday": weekday_changes > weekend_changes
        }
    
    def _detect_trend(
        self,
        entity1_ts: List[Tuple[datetime, str]],
        entity2_ts: List[Tuple[datetime, str]],
        start_time: datetime,
        end_time: datetime
    ) -> Dict:
        """
        Detect long-term trend (increasing/decreasing correlation).
        
        Args:
            entity1_ts: Entity 1 time series
            entity2_ts: Entity 2 time series
            start_time: Analysis start time
            end_time: Analysis end time
        
        Returns:
            Dict with trend info
        """
        # Split into early and late periods
        mid_time = start_time + (end_time - start_time) / 2
        
        early_entity1 = [ts for ts, _ in entity1_ts if start_time <= ts < mid_time]
        late_entity1 = [ts for ts, _ in entity1_ts if mid_time <= ts <= end_time]
        early_entity2 = [ts for ts, _ in entity2_ts if start_time <= ts < mid_time]
        late_entity2 = [ts for ts, _ in entity2_ts if mid_time <= ts <= end_time]
        
        # Calculate correlation in each period
        early_corr = self._calculate_historical_correlation(
            [(ts, "") for ts in early_entity1],
            [(ts, "") for ts in early_entity2]
        )
        late_corr = self._calculate_historical_correlation(
            [(ts, "") for ts in late_entity1],
            [(ts, "") for ts in late_entity2]
        )
        
        trend_direction = "increasing" if late_corr > early_corr else "decreasing" if late_corr < early_corr else "stable"
        trend_strength = abs(late_corr - early_corr)
        
        return {
            "direction": trend_direction,
            "strength": trend_strength,
            "early_correlation": early_corr,
            "late_correlation": late_corr
        }
    
    def _calculate_confidence(
        self,
        historical_correlation: float,
        seasonal_pattern: Dict,
        weekly_pattern: Dict,
        trend: Dict
    ) -> float:
        """
        Calculate overall pattern confidence.
        
        Args:
            historical_correlation: Historical correlation coefficient
            seasonal_pattern: Seasonal pattern dict
            weekly_pattern: Weekly pattern dict
            trend: Trend dict
        
        Returns:
            Confidence score (0.0 to 1.0)
        """
        # Base confidence from correlation strength
        base_confidence = abs(historical_correlation)
        
        # Boost if seasonal pattern is strong
        seasonal_boost = 0.0
        if seasonal_pattern.get("strongest_season"):
            max_seasonal = max(seasonal_pattern.get("seasonal_strength", {}).values(), default=0.0)
            seasonal_boost = max_seasonal * 0.1
        
        # Boost if weekly pattern is clear
        weekly_boost = 0.0
        if weekly_pattern.get("weekday_ratio", 0.5) > 0.7 or weekly_pattern.get("weekend_ratio", 0.5) > 0.7:
            weekly_boost = 0.1
        
        # Boost if trend is clear
        trend_boost = 0.0
        if trend.get("strength", 0.0) > 0.2:
            trend_boost = 0.1
        
        confidence = min(1.0, base_confidence + seasonal_boost + weekly_boost + trend_boost)
        
        return confidence
    
    def clear_cache(self) -> None:
        """Clear pattern cache."""
        self.pattern_cache.clear()
        logger.info("Long-term pattern cache cleared")
    
    def get_cache_size(self) -> int:
        """Get number of cached patterns."""
        return len(self.pattern_cache)
    
    def get_memory_usage_mb(self) -> float:
        """Get approximate memory usage in MB."""
        return len(self.pattern_cache) * 0.1  # ~100KB per pattern

