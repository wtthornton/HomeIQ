"""
Pattern History Validator

Phase 1: Pattern history tracking and trend analysis.

Provides functionality to:
- Store pattern history snapshots
- Analyze pattern trends over time
- Retrieve pattern history for validation
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List, Dict, Optional
from datetime import datetime, timedelta, timezone
import logging
import json
import numpy as np
from scipy import stats

from ..database.models import Pattern, PatternHistory

logger = logging.getLogger(__name__)


class PatternHistoryValidator:
    """
    Validates and tracks pattern history for trend analysis.
    
    Phase 1: Foundation for pattern history tracking.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize pattern history validator.
        
        Args:
            db: Database session
        """
        self.db = db
    
    async def store_snapshot(
        self,
        pattern_id: int,
        confidence: float,
        occurrences: int
    ) -> PatternHistory:
        """
        Store a pattern history snapshot.
        
        Args:
            pattern_id: Pattern ID
            confidence: Pattern confidence at this point
            occurrences: Number of occurrences
            
        Returns:
            Created PatternHistory instance
        """
        try:
            snapshot = PatternHistory(
                pattern_id=pattern_id,
                confidence=confidence,
                occurrences=occurrences,
                recorded_at=datetime.now(timezone.utc)
            )
            self.db.add(snapshot)
            await self.db.commit()
            await self.db.refresh(snapshot)
            
            logger.debug(f"Stored pattern history snapshot for pattern {pattern_id}")
            return snapshot
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to store pattern history snapshot: {e}", exc_info=True)
            raise
    
    async def get_pattern_history(
        self,
        pattern_id: int,
        days: int = 90
    ) -> List[PatternHistory]:
        """
        Get pattern history for a specific pattern.
        
        Args:
            pattern_id: Pattern ID
            days: Number of days to look back (default: 90)
            
        Returns:
            List of PatternHistory instances, ordered by recorded_at
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            query = select(PatternHistory).where(
                and_(
                    PatternHistory.pattern_id == pattern_id,
                    PatternHistory.recorded_at >= cutoff_date
                )
            ).order_by(PatternHistory.recorded_at.asc())
            
            result = await self.db.execute(query)
            history = result.scalars().all()
            
            logger.debug(f"Retrieved {len(history)} history records for pattern {pattern_id}")
            return list(history)
            
        except Exception as e:
            logger.error(f"Failed to get pattern history: {e}", exc_info=True)
            raise
    
    async def analyze_trend(
        self,
        pattern_id: int,
        days: int = 90
    ) -> Dict[str, any]:
        """
        Analyze pattern trend over time using linear regression.
        
        Args:
            pattern_id: Pattern ID
            days: Number of days to analyze (default: 90)
            
        Returns:
            Dictionary with trend analysis:
            {
                'trend': 'increasing' | 'stable' | 'decreasing' | 'insufficient_data',
                'trend_strength': float (0.0-1.0),
                'slope': float,
                'first_confidence': float,
                'last_confidence': float,
                'confidence_change': float,
                'data_points': int
            }
        """
        try:
            history = await self.get_pattern_history(pattern_id, days)
            
            if len(history) < 2:
                return {
                    'trend': 'insufficient_data',
                    'trend_strength': 0.0,
                    'slope': 0.0,
                    'first_confidence': history[0].confidence if history else 0.0,
                    'last_confidence': history[-1].confidence if history else 0.0,
                    'confidence_change': 0.0,
                    'data_points': len(history)
                }
            
            # Extract confidence values and timestamps
            confidences = [h.confidence for h in history]
            timestamps = [h.recorded_at.timestamp() for h in history]
            
            # Normalize timestamps to days from first
            first_timestamp = timestamps[0]
            days_from_first = [(ts - first_timestamp) / 86400.0 for ts in timestamps]
            
            # Perform linear regression
            x = np.array(days_from_first)
            y = np.array(confidences)
            
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
            
            # Determine trend direction
            # Use a threshold to determine if slope is significant
            # For confidence values (0-1), a slope of 0.01 per day is meaningful
            slope_threshold = 0.001  # 0.1% per day
            
            if abs(slope) < slope_threshold:
                trend = 'stable'
                trend_strength = min(1.0, abs(slope) / slope_threshold)
            elif slope > 0:
                trend = 'increasing'
                trend_strength = min(1.0, abs(slope) / (slope_threshold * 5))  # Scale to 0-1
            else:
                trend = 'decreasing'
                trend_strength = min(1.0, abs(slope) / (slope_threshold * 5))
            
            # Calculate confidence change
            confidence_change = confidences[-1] - confidences[0]
            
            result = {
                'trend': trend,
                'trend_strength': float(trend_strength),
                'slope': float(slope),
                'r_squared': float(r_value ** 2),
                'first_confidence': float(confidences[0]),
                'last_confidence': float(confidences[-1]),
                'confidence_change': float(confidence_change),
                'data_points': len(history)
            }
            
            logger.debug(f"Pattern {pattern_id} trend: {trend} (strength: {trend_strength:.2f}, slope: {slope:.4f})")
            return result
            
        except Exception as e:
            logger.error(f"Failed to analyze pattern trend: {e}", exc_info=True)
            return {
                'trend': 'error',
                'trend_strength': 0.0,
                'slope': 0.0,
                'first_confidence': 0.0,
                'last_confidence': 0.0,
                'confidence_change': 0.0,
                'data_points': 0,
                'error': str(e)
            }
    
    async def update_pattern_trend_cache(self, pattern_id: int, days: int = 90) -> Dict[str, any]:
        """
        Update cached trend data in the patterns table.
        
        Args:
            pattern_id: Pattern ID
            days: Number of days to analyze
            
        Returns:
            Trend analysis result
        """
        try:
            # Get trend analysis
            trend_result = await self.analyze_trend(pattern_id, days)
            
            # Update pattern record with cached trend data
            query = select(Pattern).where(Pattern.id == pattern_id)
            result = await self.db.execute(query)
            pattern = result.scalar_one_or_none()
            
            if pattern:
                pattern.trend_direction = trend_result['trend']
                pattern.trend_strength = trend_result['trend_strength']
                pattern.confidence_history_count = trend_result['data_points']
                
                await self.db.commit()
                logger.debug(f"Updated trend cache for pattern {pattern_id}")
            
            return trend_result
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update pattern trend cache: {e}", exc_info=True)
            raise




