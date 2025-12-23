"""
Feedback Aggregator

Epic AI-13: ML-Based Pattern Quality & Active Learning
Story AI13.4: Active Learning Infrastructure

Aggregate and analyze pattern feedback.
"""

import logging
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case

from ...database.models import Pattern, Suggestion, UserFeedback
from .pattern_feedback_tracker import PatternFeedbackTracker

logger = logging.getLogger(__name__)


class PatternFeedbackAggregator:
    """
    Aggregate and analyze pattern feedback.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize feedback aggregator.
        
        Args:
            db: Database session
        """
        self.db = db
        self.tracker = PatternFeedbackTracker(db)
    
    async def aggregate_feedback(
        self,
        pattern_id: int
    ) -> dict[str, Any]:
        """
        Aggregate feedback for a pattern.
        
        Args:
            pattern_id: ID of the pattern
        
        Returns:
            {
                'pattern_id': int,
                'approvals': int,
                'rejections': int,
                'approval_rate': float,
                'total_feedback': int,
                'last_feedback': datetime,
                'entity_selections': list
            }
        """
        return await self.tracker.get_pattern_feedback(pattern_id)
    
    async def identify_high_quality_patterns(
        self,
        min_approval_rate: float = 0.8,
        min_feedback_count: int = 5
    ) -> list[int]:
        """
        Identify patterns with high approval rates.
        
        Args:
            min_approval_rate: Minimum approval rate (0.0-1.0)
            min_feedback_count: Minimum number of feedback samples
        
        Returns:
            List of pattern IDs
        """
        # Get all patterns with suggestions
        suggestions_query = (
            select(Suggestion.pattern_id, Suggestion.id)
            .where(Suggestion.pattern_id.isnot(None))
        )
        result = await self.db.execute(suggestions_query)
        suggestion_pattern_map = {row[1]: row[0] for row in result.all()}
        
        if not suggestion_pattern_map:
            return []
        
        suggestion_ids = list(suggestion_pattern_map.keys())
        
        # Aggregate feedback per suggestion
        feedback_query = (
            select(
                UserFeedback.suggestion_id,
                func.sum(case((UserFeedback.action == 'approved', 1), else_=0)).label('approvals'),
                func.sum(case((UserFeedback.action == 'rejected', 1), else_=0)).label('rejections')
            )
            .where(UserFeedback.suggestion_id.in_(suggestion_ids))
            .group_by(UserFeedback.suggestion_id)
        )
        
        result = await self.db.execute(feedback_query)
        feedback_data = result.all()
        
        # Aggregate by pattern
        pattern_feedback: dict[int, dict[str, int]] = {}
        for row in feedback_data:
            pattern_id = suggestion_pattern_map[row.suggestion_id]
            if pattern_id not in pattern_feedback:
                pattern_feedback[pattern_id] = {'approvals': 0, 'rejections': 0}
            
            pattern_feedback[pattern_id]['approvals'] += row.approvals or 0
            pattern_feedback[pattern_id]['rejections'] += row.rejections or 0
        
        # Filter by criteria
        high_quality_patterns = []
        for pattern_id, feedback in pattern_feedback.items():
            total = feedback['approvals'] + feedback['rejections']
            if total < min_feedback_count:
                continue
            
            approval_rate = feedback['approvals'] / total
            if approval_rate >= min_approval_rate:
                high_quality_patterns.append(pattern_id)
        
        logger.info(
            f"Identified {len(high_quality_patterns)} high-quality patterns "
            f"(approval_rate >= {min_approval_rate}, feedback >= {min_feedback_count})"
        )
        
        return high_quality_patterns
    
    async def identify_low_quality_patterns(
        self,
        max_approval_rate: float = 0.3,
        min_feedback_count: int = 5
    ) -> list[int]:
        """
        Identify patterns with low approval rates.
        
        Args:
            max_approval_rate: Maximum approval rate (0.0-1.0)
            min_feedback_count: Minimum number of feedback samples
        
        Returns:
            List of pattern IDs
        """
        # Get all patterns with suggestions
        suggestions_query = (
            select(Suggestion.pattern_id, Suggestion.id)
            .where(Suggestion.pattern_id.isnot(None))
        )
        result = await self.db.execute(suggestions_query)
        suggestion_pattern_map = {row[1]: row[0] for row in result.all()}
        
        if not suggestion_pattern_map:
            return []
        
        suggestion_ids = list(suggestion_pattern_map.keys())
        
        # Aggregate feedback per suggestion
        feedback_query = (
            select(
                UserFeedback.suggestion_id,
                func.sum(case((UserFeedback.action == 'approved', 1), else_=0)).label('approvals'),
                func.sum(case((UserFeedback.action == 'rejected', 1), else_=0)).label('rejections')
            )
            .where(UserFeedback.suggestion_id.in_(suggestion_ids))
            .group_by(UserFeedback.suggestion_id)
        )
        
        result = await self.db.execute(feedback_query)
        feedback_data = result.all()
        
        # Aggregate by pattern
        pattern_feedback: dict[int, dict[str, int]] = {}
        for row in feedback_data:
            pattern_id = suggestion_pattern_map[row.suggestion_id]
            if pattern_id not in pattern_feedback:
                pattern_feedback[pattern_id] = {'approvals': 0, 'rejections': 0}
            
            pattern_feedback[pattern_id]['approvals'] += row.approvals or 0
            pattern_feedback[pattern_id]['rejections'] += row.rejections or 0
        
        # Filter by criteria
        low_quality_patterns = []
        for pattern_id, feedback in pattern_feedback.items():
            total = feedback['approvals'] + feedback['rejections']
            if total < min_feedback_count:
                continue
            
            approval_rate = feedback['approvals'] / total
            if approval_rate <= max_approval_rate:
                low_quality_patterns.append(pattern_id)
        
        logger.info(
            f"Identified {len(low_quality_patterns)} low-quality patterns "
            f"(approval_rate <= {max_approval_rate}, feedback >= {min_feedback_count})"
        )
        
        return low_quality_patterns

