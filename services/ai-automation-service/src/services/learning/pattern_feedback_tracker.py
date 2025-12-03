"""
Pattern Feedback Tracker

Epic AI-13: ML-Based Pattern Quality & Active Learning
Story AI13.4: Active Learning Infrastructure

Track user feedback for patterns to enable active learning.
"""

import logging
from typing import Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from sqlalchemy.orm import selectinload

from ...database.models import Pattern, UserFeedback, Suggestion
from ...database.crud import store_feedback

logger = logging.getLogger(__name__)


class PatternFeedbackTracker:
    """
    Track user feedback for patterns to enable active learning.
    
    Tracks approvals, rejections, and entity selections for patterns
    to improve pattern quality predictions over time.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize pattern feedback tracker.
        
        Args:
            db: Database session
        """
        self.db = db
    
    async def track_approval(
        self,
        pattern_id: int,
        suggestion_id: int | None = None,
        feedback_text: str | None = None
    ) -> UserFeedback:
        """
        Track user approval of a pattern.
        
        Args:
            pattern_id: ID of the pattern
            suggestion_id: ID of the suggestion (if from suggestion)
            feedback_text: Optional feedback text
        
        Returns:
            Stored UserFeedback
        """
        # Get suggestion to ensure pattern_id matches
        if suggestion_id:
            suggestion = await self.db.get(Suggestion, suggestion_id)
            if suggestion and suggestion.pattern_id != pattern_id:
                logger.warning(
                    f"Suggestion {suggestion_id} pattern_id ({suggestion.pattern_id}) "
                    f"doesn't match provided pattern_id ({pattern_id})"
                )
        
        feedback_data = {
            'suggestion_id': suggestion_id,
            'action': 'approved',
            'feedback_text': feedback_text,
        }
        
        # Store feedback (pattern_id will be added via suggestion.pattern_id)
        feedback = await store_feedback(self.db, feedback_data)
        
        # Update pattern metadata if needed
        pattern = await self.db.get(Pattern, pattern_id)
        if pattern:
            # Pattern metadata can be updated to track feedback
            if not pattern.pattern_metadata:
                pattern.pattern_metadata = {}
            pattern.pattern_metadata['last_feedback'] = feedback.created_at.isoformat()
            pattern.pattern_metadata['last_feedback_action'] = 'approved'
            await self.db.commit()
        
        logger.info(f"Tracked approval for pattern {pattern_id} (suggestion {suggestion_id})")
        return feedback
    
    async def track_rejection(
        self,
        pattern_id: int,
        suggestion_id: int | None = None,
        feedback_text: str | None = None
    ) -> UserFeedback:
        """
        Track user rejection of a pattern.
        
        Args:
            pattern_id: ID of the pattern
            suggestion_id: ID of the suggestion (if from suggestion)
            feedback_text: Optional feedback text
        
        Returns:
            Stored UserFeedback
        """
        # Get suggestion to ensure pattern_id matches
        if suggestion_id:
            suggestion = await self.db.get(Suggestion, suggestion_id)
            if suggestion and suggestion.pattern_id != pattern_id:
                logger.warning(
                    f"Suggestion {suggestion_id} pattern_id ({suggestion.pattern_id}) "
                    f"doesn't match provided pattern_id ({pattern_id})"
                )
        
        feedback_data = {
            'suggestion_id': suggestion_id,
            'action': 'rejected',
            'feedback_text': feedback_text,
        }
        
        # Store feedback
        feedback = await store_feedback(self.db, feedback_data)
        
        # Update pattern metadata if needed
        pattern = await self.db.get(Pattern, pattern_id)
        if pattern:
            if not pattern.pattern_metadata:
                pattern.pattern_metadata = {}
            pattern.pattern_metadata['last_feedback'] = feedback.created_at.isoformat()
            pattern.pattern_metadata['last_feedback_action'] = 'rejected'
            await self.db.commit()
        
        logger.info(f"Tracked rejection for pattern {pattern_id} (suggestion {suggestion_id})")
        return feedback
    
    async def track_entity_selection(
        self,
        pattern_id: int,
        selected_entities: list[str],
        suggestion_id: int | None = None
    ) -> dict[str, Any]:
        """
        Track entity selections (preference signals).
        
        Args:
            pattern_id: ID of the pattern
            selected_entities: List of selected entity IDs
            suggestion_id: ID of the suggestion (if from suggestion)
        
        Returns:
            Tracking metadata
        """
        # Store entity selections in pattern metadata
        pattern = await self.db.get(Pattern, pattern_id)
        if not pattern:
            raise ValueError(f"Pattern {pattern_id} not found")
        
        if not pattern.pattern_metadata:
            pattern.pattern_metadata = {}
        
        # Track entity selections
        if 'entity_selections' not in pattern.pattern_metadata:
            pattern.pattern_metadata['entity_selections'] = []
        
        selection_entry = {
            'entities': selected_entities,
            'suggestion_id': suggestion_id,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        pattern.pattern_metadata['entity_selections'].append(selection_entry)
        await self.db.commit()
        
        logger.info(
            f"Tracked entity selection for pattern {pattern_id}: "
            f"{len(selected_entities)} entities"
        )
        
        return selection_entry
    
    async def get_pattern_feedback(
        self,
        pattern_id: int
    ) -> dict[str, Any]:
        """
        Get aggregated feedback for a pattern.
        
        Args:
            pattern_id: ID of the pattern
        
        Returns:
            Feedback statistics (approvals, rejections, approval_rate, etc.)
        """
        # Get all suggestions for this pattern
        suggestions_query = select(Suggestion.id).where(
            Suggestion.pattern_id == pattern_id
        )
        result = await self.db.execute(suggestions_query)
        suggestion_ids = [row[0] for row in result.all()]
        
        if not suggestion_ids:
            return {
                'pattern_id': pattern_id,
                'approvals': 0,
                'rejections': 0,
                'approval_rate': 0.0,
                'total_feedback': 0,
                'last_feedback': None,
                'entity_selections': []
            }
        
        # Aggregate feedback for these suggestions
        feedback_query = (
            select(
                func.sum(case((UserFeedback.action == 'approved', 1), else_=0)).label('approvals'),
                func.sum(case((UserFeedback.action == 'rejected', 1), else_=0)).label('rejections'),
                func.max(UserFeedback.created_at).label('last_feedback')
            )
            .where(UserFeedback.suggestion_id.in_(suggestion_ids))
        )
        
        result = await self.db.execute(feedback_query)
        row = result.first()
        
        approvals = row.approvals or 0
        rejections = row.rejections or 0
        total_feedback = approvals + rejections
        approval_rate = approvals / total_feedback if total_feedback > 0 else 0.0
        
        # Get entity selections from pattern metadata
        pattern = await self.db.get(Pattern, pattern_id)
        entity_selections = []
        if pattern and pattern.pattern_metadata:
            entity_selections = pattern.pattern_metadata.get('entity_selections', [])
        
        return {
            'pattern_id': pattern_id,
            'approvals': approvals,
            'rejections': rejections,
            'approval_rate': approval_rate,
            'total_feedback': total_feedback,
            'last_feedback': row.last_feedback,
            'entity_selections': entity_selections
        }
    
    async def get_feedback_statistics(
        self,
        pattern_ids: list[int] | None = None
    ) -> dict[str, Any]:
        """
        Get feedback statistics for patterns.
        
        Args:
            pattern_ids: Optional list of pattern IDs to filter
        
        Returns:
            Overall feedback statistics
        """
        # Build query for suggestions
        suggestions_query = select(Suggestion.id, Suggestion.pattern_id)
        if pattern_ids:
            suggestions_query = suggestions_query.where(
                Suggestion.pattern_id.in_(pattern_ids)
            )
        
        result = await self.db.execute(suggestions_query)
        suggestion_pattern_map = {row[0]: row[1] for row in result.all()}
        
        if not suggestion_pattern_map:
            return {
                'total_patterns': 0,
                'patterns_with_feedback': 0,
                'total_approvals': 0,
                'total_rejections': 0,
                'overall_approval_rate': 0.0,
                'average_feedback_per_pattern': 0.0
            }
        
        suggestion_ids = list(suggestion_pattern_map.keys())
        
        # Aggregate all feedback
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
        
        total_approvals = sum(row.approvals or 0 for row in feedback_data)
        total_rejections = sum(row.rejections or 0 for row in feedback_data)
        total_feedback = total_approvals + total_rejections
        
        # Count patterns with feedback
        patterns_with_feedback = len(set(
            suggestion_pattern_map[row.suggestion_id]
            for row in feedback_data
        ))
        
        # Count total patterns
        if pattern_ids:
            total_patterns = len(pattern_ids)
        else:
            pattern_count_query = select(func.count(Pattern.id))
            result = await self.db.execute(pattern_count_query)
            total_patterns = result.scalar() or 0
        
        overall_approval_rate = (
            total_approvals / total_feedback
            if total_feedback > 0 else 0.0
        )
        
        average_feedback_per_pattern = (
            total_feedback / patterns_with_feedback
            if patterns_with_feedback > 0 else 0.0
        )
        
        return {
            'total_patterns': total_patterns,
            'patterns_with_feedback': patterns_with_feedback,
            'total_approvals': total_approvals,
            'total_rejections': total_rejections,
            'overall_approval_rate': overall_approval_rate,
            'average_feedback_per_pattern': average_feedback_per_pattern
        }

