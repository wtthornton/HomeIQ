"""
Feedback Tracker for Entity Resolution

Epic AI-12, Story AI12.4: Active Learning Infrastructure
Tracks user feedback on entity resolution to enable active learning.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ...database.models import Base

logger = logging.getLogger(__name__)


class FeedbackType(str, Enum):
    """Types of feedback for entity resolution"""
    APPROVE = "approve"  # User approved the suggested entity
    REJECT = "reject"  # User rejected the suggested entity
    CORRECT = "correct"  # User selected a different entity (correction)
    CUSTOM_MAPPING = "custom_mapping"  # User created custom entity mapping


@dataclass
class EntityResolutionFeedback:
    """Feedback data for entity resolution"""
    feedback_id: str
    query: str
    device_name: str
    suggested_entity_id: Optional[str]
    actual_entity_id: Optional[str]  # What user selected/corrected to
    feedback_type: FeedbackType
    confidence_score: Optional[float] = None
    area_id: Optional[str] = None
    context: Optional[dict[str, Any]] = None
    created_at: Optional[datetime] = None


class FeedbackTracker:
    """
    Tracks user feedback on entity resolution.
    
    Features:
    - Track approve/reject actions
    - Track entity corrections
    - Track custom entity mappings
    - Store feedback in database
    - Aggregate feedback for analysis
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize feedback tracker.
        
        Args:
            db: Database session
        """
        self.db = db
        logger.info("FeedbackTracker initialized")
    
    async def track_feedback(
        self,
        query: str,
        device_name: str,
        suggested_entity_id: Optional[str],
        actual_entity_id: Optional[str],
        feedback_type: FeedbackType,
        confidence_score: Optional[float] = None,
        area_id: Optional[str] = None,
        context: Optional[dict[str, Any]] = None
    ) -> str:
        """
        Track user feedback on entity resolution.
        
        Args:
            query: Original natural language query
            device_name: Device name from query
            suggested_entity_id: Entity ID suggested by system
            actual_entity_id: Entity ID user selected/corrected to
            feedback_type: Type of feedback
            confidence_score: Confidence score of suggestion
            area_id: Optional area ID
            context: Optional additional context
        
        Returns:
            Feedback ID
        """
        feedback_id = str(uuid4())
        
        try:
            # Create feedback record
            feedback = EntityResolutionFeedback(
                feedback_id=feedback_id,
                query=query,
                device_name=device_name,
                suggested_entity_id=suggested_entity_id,
                actual_entity_id=actual_entity_id,
                feedback_type=feedback_type,
                confidence_score=confidence_score,
                area_id=area_id,
                context=context or {},
                created_at=datetime.utcnow()
            )
            
            # Store in database
            await self._store_feedback(feedback)
            
            logger.info(
                f"Tracked feedback: {feedback_type.value} for '{device_name}' "
                f"(suggested: {suggested_entity_id}, actual: {actual_entity_id})"
            )
            
            return feedback_id
            
        except Exception as e:
            logger.error(f"Failed to track feedback: {e}", exc_info=True)
            raise
    
    async def _store_feedback(self, feedback: EntityResolutionFeedback) -> None:
        """Store feedback in database"""
        try:
            # Check if EntityResolutionFeedback table exists
            # If not, we'll use a simple JSON storage approach
            from ...database.models import UserFeedback
            
            # For now, store as JSON in UserFeedback table
            # In future, we can create a dedicated EntityResolutionFeedback table
            user_feedback = UserFeedback(
                suggestion_id=None,  # Not tied to a suggestion
                action=feedback.feedback_type.value,
                feedback_text=self._serialize_feedback(feedback)
            )
            
            self.db.add(user_feedback)
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to store feedback: {e}", exc_info=True)
            await self.db.rollback()
            raise
    
    def _serialize_feedback(self, feedback: EntityResolutionFeedback) -> str:
        """Serialize feedback to JSON string"""
        import json
        
        data = {
            "feedback_id": feedback.feedback_id,
            "query": feedback.query,
            "device_name": feedback.device_name,
            "suggested_entity_id": feedback.suggested_entity_id,
            "actual_entity_id": feedback.actual_entity_id,
            "feedback_type": feedback.feedback_type.value,
            "confidence_score": feedback.confidence_score,
            "area_id": feedback.area_id,
            "context": feedback.context,
            "created_at": feedback.created_at.isoformat() if feedback.created_at else None
        }
        
        return json.dumps(data)
    
    async def get_feedback_for_device(
        self,
        device_name: str,
        limit: int = 100
    ) -> list[EntityResolutionFeedback]:
        """
        Get feedback history for a device name.
        
        Args:
            device_name: Device name to get feedback for
            limit: Maximum number of feedback records to return
        
        Returns:
            List of feedback records
        """
        try:
            from ...database.models import UserFeedback
            
            # Query UserFeedback table for relevant feedback
            query = select(UserFeedback).where(
                UserFeedback.feedback_text.like(f'%"device_name": "{device_name}"%')
            ).order_by(UserFeedback.created_at.desc()).limit(limit)
            
            result = await self.db.execute(query)
            feedback_records = result.scalars().all()
            
            # Deserialize feedback
            feedbacks = []
            for record in feedback_records:
                try:
                    feedback = self._deserialize_feedback(record.feedback_text)
                    if feedback:
                        feedbacks.append(feedback)
                except Exception as e:
                    logger.warning(f"Failed to deserialize feedback: {e}")
                    continue
            
            return feedbacks
            
        except Exception as e:
            logger.error(f"Failed to get feedback for device: {e}", exc_info=True)
            return []
    
    def _deserialize_feedback(self, feedback_text: str) -> Optional[EntityResolutionFeedback]:
        """Deserialize feedback from JSON string"""
        import json
        
        try:
            data = json.loads(feedback_text)
            
            # Check if this is entity resolution feedback
            if "feedback_id" not in data or "device_name" not in data:
                return None
            
            return EntityResolutionFeedback(
                feedback_id=data.get("feedback_id"),
                query=data.get("query", ""),
                device_name=data.get("device_name"),
                suggested_entity_id=data.get("suggested_entity_id"),
                actual_entity_id=data.get("actual_entity_id"),
                feedback_type=FeedbackType(data.get("feedback_type", "approve")),
                confidence_score=data.get("confidence_score"),
                area_id=data.get("area_id"),
                context=data.get("context", {}),
                created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None
            )
        except Exception as e:
            logger.warning(f"Failed to deserialize feedback: {e}")
            return None
    
    async def get_feedback_stats(
        self,
        device_name: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Get aggregated feedback statistics.
        
        Args:
            device_name: Optional device name filter
        
        Returns:
            Dictionary with feedback statistics
        """
        try:
            from ...database.models import UserFeedback
            
            # Build query
            query = select(UserFeedback)
            
            if device_name:
                query = query.where(
                    UserFeedback.feedback_text.like(f'%"device_name": "{device_name}"%')
                )
            
            result = await self.db.execute(query)
            all_feedback = result.scalars().all()
            
            # Aggregate statistics
            stats = {
                "total_feedback": 0,
                "approve_count": 0,
                "reject_count": 0,
                "correct_count": 0,
                "custom_mapping_count": 0,
                "avg_confidence": 0.0,
                "device_names": {}
            }
            
            total_confidence = 0.0
            confidence_count = 0
            
            for record in all_feedback:
                feedback = self._deserialize_feedback(record.feedback_text)
                if not feedback:
                    continue
                
                stats["total_feedback"] += 1
                
                # Count by type
                if feedback.feedback_type == FeedbackType.APPROVE:
                    stats["approve_count"] += 1
                elif feedback.feedback_type == FeedbackType.REJECT:
                    stats["reject_count"] += 1
                elif feedback.feedback_type == FeedbackType.CORRECT:
                    stats["correct_count"] += 1
                elif feedback.feedback_type == FeedbackType.CUSTOM_MAPPING:
                    stats["custom_mapping_count"] += 1
                
                # Track confidence
                if feedback.confidence_score is not None:
                    total_confidence += feedback.confidence_score
                    confidence_count += 1
                
                # Track device names
                if feedback.device_name not in stats["device_names"]:
                    stats["device_names"][feedback.device_name] = 0
                stats["device_names"][feedback.device_name] += 1
            
            # Calculate average confidence
            if confidence_count > 0:
                stats["avg_confidence"] = total_confidence / confidence_count
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get feedback stats: {e}", exc_info=True)
            return {
                "total_feedback": 0,
                "approve_count": 0,
                "reject_count": 0,
                "correct_count": 0,
                "custom_mapping_count": 0,
                "avg_confidence": 0.0,
                "device_names": {}
            }

