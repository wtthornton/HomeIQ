"""
Feedback Client Service

Retrieves user feedback on synergies and devices to influence pattern detection.
Implements Recommendation 2.1: Integrate Feedback into Pattern Detection.

Based on PATTERNS_SYNERGIES_IMPROVEMENT_RECOMMENDATIONS.md
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class DeviceFeedbackStats:
    """Statistics for device feedback."""
    
    avg_rating: float = 3.0  # Neutral default
    total_feedback: int = 0
    positive_count: int = 0
    negative_count: int = 0
    acceptance_rate: float = 0.5
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            'avg_rating': self.avg_rating,
            'total_feedback': self.total_feedback,
            'positive_count': self.positive_count,
            'negative_count': self.negative_count,
            'acceptance_rate': self.acceptance_rate
        }


@dataclass
class FeedbackAggregator:
    """Aggregates feedback data for a device."""
    
    ratings: list[float] = field(default_factory=list)
    total_feedback: int = 0
    positive_count: int = 0
    negative_count: int = 0
    accepted_count: int = 0
    total_synergies: int = 0
    
    def add_rating(self, rating: float) -> None:
        """Add a rating to the aggregator."""
        if 0.0 <= rating <= 5.0:
            self.ratings.append(rating)
            self.total_feedback += 1
            
            if rating >= 4.0:
                self.positive_count += 1
            elif rating < 2.0:
                self.negative_count += 1
    
    def add_acceptance(self, accepted: bool) -> None:
        """Track acceptance of a synergy."""
        if accepted:
            self.accepted_count += 1
    
    def increment_synergy_count(self) -> None:
        """Increment total synergy count."""
        self.total_synergies += 1
    
    def calculate_stats(self) -> DeviceFeedbackStats:
        """Calculate final statistics."""
        avg_rating = sum(self.ratings) / len(self.ratings) if self.ratings else 3.0
        acceptance_rate = self.accepted_count / self.total_synergies if self.total_synergies > 0 else 0.5
        
        return DeviceFeedbackStats(
            avg_rating=float(avg_rating),
            total_feedback=self.total_feedback,
            positive_count=self.positive_count,
            negative_count=self.negative_count,
            acceptance_rate=float(acceptance_rate)
        )


class FeedbackClient:
    """
    Client for retrieving user feedback on synergies and devices.
    
    Aggregates feedback from synergy_feedback table to provide device-level
    feedback statistics for pattern detection enhancement.
    """
    
    # SQL query for fetching feedback data
    _FEEDBACK_QUERY = text("""
        SELECT 
            sf.feedback_type,
            sf.feedback_data,
            so.device_ids
        FROM synergy_feedback sf
        JOIN synergy_opportunities so ON sf.synergy_id = so.synergy_id
        WHERE sf.feedback_data IS NOT NULL
    """)
    
    def __init__(self, db: Optional[AsyncSession] = None):
        """
        Initialize feedback client.
        
        Args:
            db: Optional database session for querying feedback
        """
        self.db = db
        self._feedback_cache: dict[str, dict[str, Any]] = {}
        logger.info("FeedbackClient initialized")
    
    async def get_device_feedback(
        self,
        device_id: str,
        db: Optional[AsyncSession] = None
    ) -> dict[str, Any]:
        """
        Get aggregated feedback for a device.
        
        Aggregates feedback from synergies that involve this device.
        
        Args:
            device_id: Device identifier (e.g., "light.bedroom")
            db: Optional database session (uses self.db if not provided)
        
        Returns:
            Dictionary with keys:
                - avg_rating: Average rating (0.0-5.0)
                - total_feedback: Total number of feedback entries
                - positive_count: Number of positive feedbacks (rating >= 4.0)
                - negative_count: Number of negative feedbacks (rating < 2.0)
                - acceptance_rate: Rate of accepted synergies (0.0-1.0)
        """
        # Check cache first
        if device_id in self._feedback_cache:
            return self._feedback_cache[device_id]
        
        session = db or self.db
        if not session:
            logger.debug(f"No database session available for device feedback: {device_id}")
            return DeviceFeedbackStats().to_dict()
        
        try:
            feedback_stats = await self._fetch_and_aggregate_feedback(session, device_id)
            self._feedback_cache[device_id] = feedback_stats
            return feedback_stats
        except Exception as e:
            logger.warning(f"Failed to get device feedback for {device_id}: {e}")
            return DeviceFeedbackStats().to_dict()
    
    async def _fetch_and_aggregate_feedback(
        self,
        session: AsyncSession,
        device_id: str
    ) -> dict[str, Any]:
        """
        Fetch feedback from database and aggregate for device.
        
        Args:
            session: Database session
            device_id: Device identifier
            
        Returns:
            Aggregated feedback statistics
        """
        result = await session.execute(self._FEEDBACK_QUERY)
        rows = result.fetchall()
        
        aggregator = FeedbackAggregator()
        
        for row in rows:
            self._process_feedback_row(row, device_id, aggregator)
        
        stats = aggregator.calculate_stats()
        
        logger.debug(
            f"Device feedback for {device_id}: "
            f"avg_rating={stats.avg_rating:.2f}, total={stats.total_feedback}, "
            f"acceptance_rate={stats.acceptance_rate:.2f}"
        )
        
        return stats.to_dict()
    
    def _process_feedback_row(
        self,
        row: tuple[Any, ...],
        device_id: str,
        aggregator: FeedbackAggregator
    ) -> None:
        """
        Process a single feedback row.
        
        Args:
            row: Database row (feedback_type, feedback_data, device_ids)
            device_id: Device identifier to filter by
            aggregator: Aggregator to collect statistics
        """
        feedback_type, feedback_data_json, device_ids = row
        
        # Check if this synergy involves the device
        if not device_ids or device_id not in device_ids:
            return
        
        aggregator.increment_synergy_count()
        feedback_data = self._parse_feedback_data(feedback_data_json)
        
        if feedback_data is None:
            return
        
        # Extract and add rating
        rating = self._extract_rating(feedback_data)
        if rating is not None:
            aggregator.add_rating(rating)
        
        # Track acceptance
        is_accepted = feedback_data.get('accepted', False) or feedback_type == 'accept'
        aggregator.add_acceptance(is_accepted)
    
    def _parse_feedback_data(self, feedback_data_json: Any) -> Optional[dict[str, Any]]:
        """
        Parse feedback data from JSON.
        
        Args:
            feedback_data_json: JSON string or dict
            
        Returns:
            Parsed dictionary or None if parsing fails
        """
        try:
            if isinstance(feedback_data_json, str):
                return json.loads(feedback_data_json)
            return feedback_data_json
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.debug(f"Failed to parse feedback data: {e}")
            return None
    
    def _extract_rating(self, feedback_data: dict[str, Any]) -> Optional[float]:
        """
        Extract rating from feedback data.
        
        Args:
            feedback_data: Parsed feedback dictionary
            
        Returns:
            Rating value (0.0-5.0) or None if not available
        """
        rating = feedback_data.get('rating') or feedback_data.get('user_rating')
        if rating is None:
            return None
        
        try:
            rating_float = float(rating)
            if 0.0 <= rating_float <= 5.0:
                return rating_float
        except (ValueError, TypeError):
            pass
        
        return None
    
    def clear_cache(self) -> None:
        """Clear the feedback cache."""
        self._feedback_cache.clear()
        logger.debug("Feedback cache cleared")
