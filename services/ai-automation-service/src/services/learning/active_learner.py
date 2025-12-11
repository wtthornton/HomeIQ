"""
Active Learner for Entity Resolution

Epic AI-12, Story AI12.4: Active Learning Infrastructure
Learns from user feedback to improve entity resolution accuracy.
"""

import logging
from typing import Any, Optional
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession

from ...services.entity.personalized_index import PersonalizedEntityIndex
from ...services.entity.personalized_resolver import PersonalizedEntityResolver
from ...services.entity.index_updater import IndexUpdater
from .feedback_tracker import FeedbackTracker, FeedbackType, EntityResolutionFeedback

logger = logging.getLogger(__name__)


class ActiveLearner:
    """
    Active learning system for entity resolution.
    
    Features:
    - Analyze user feedback patterns
    - Learn from corrections
    - Update entity mappings based on feedback
    - Boost confidence for frequently selected entities
    - Learn user's preferred naming conventions
    """
    
    def __init__(
        self,
        db: AsyncSession,
        personalized_index: PersonalizedEntityIndex,
        personalized_resolver: Optional[PersonalizedEntityResolver] = None,
        index_updater: Optional[IndexUpdater] = None
    ):
        """
        Initialize active learner.
        
        Args:
            db: Database session
            personalized_index: PersonalizedEntityIndex to update
            personalized_resolver: Optional PersonalizedEntityResolver
            index_updater: Optional IndexUpdater (will create if not provided)
        """
        self.db = db
        self.personalized_index = personalized_index
        self.personalized_resolver = personalized_resolver
        self.feedback_tracker = FeedbackTracker(db)
        self.index_updater = index_updater or IndexUpdater(personalized_index, self.feedback_tracker)
        
        logger.info("ActiveLearner initialized")
    
    async def process_feedback(
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
        Process user feedback and learn from it.
        
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
        # Track feedback
        feedback_id = await self.feedback_tracker.track_feedback(
            query=query,
            device_name=device_name,
            suggested_entity_id=suggested_entity_id,
            actual_entity_id=actual_entity_id,
            feedback_type=feedback_type,
            confidence_score=confidence_score,
            area_id=area_id,
            context=context
        )
        
        # Learn from feedback using IndexUpdater
        await self.index_updater.update_from_feedback(
            device_name=device_name,
            entity_id=actual_entity_id or suggested_entity_id or "",
            feedback_type=feedback_type,
            area_id=area_id
        )
        
        return feedback_id
    
    
    async def analyze_feedback_patterns(
        self,
        device_name: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Analyze feedback patterns to identify learning opportunities.
        
        Args:
            device_name: Optional device name filter
        
        Returns:
            Dictionary with analysis results
        """
        try:
            # Get feedback statistics
            stats = await self.feedback_tracker.get_feedback_stats(device_name)
            
            # Analyze patterns
            analysis = {
                "total_feedback": stats["total_feedback"],
                "approval_rate": 0.0,
                "correction_rate": 0.0,
                "common_corrections": [],
                "low_confidence_issues": [],
                "recommendations": []
            }
            
            if stats["total_feedback"] > 0:
                # Calculate rates
                analysis["approval_rate"] = stats["approve_count"] / stats["total_feedback"]
                analysis["correction_rate"] = stats["correct_count"] / stats["total_feedback"]
                
                # Get common corrections
                if device_name:
                    feedbacks = await self.feedback_tracker.get_feedback_for_device(device_name)
                    corrections = [
                        f for f in feedbacks
                        if f.feedback_type == FeedbackType.CORRECT
                    ]
                    
                    # Group by actual entity
                    entity_counts = defaultdict(int)
                    for correction in corrections:
                        if correction.actual_entity_id:
                            entity_counts[correction.actual_entity_id] += 1
                    
                    # Get top corrections
                    analysis["common_corrections"] = sorted(
                        entity_counts.items(),
                        key=lambda x: x[1],
                        reverse=True
                    )[:5]
                
                # Generate recommendations
                if analysis["correction_rate"] > 0.3:
                    analysis["recommendations"].append(
                        "High correction rate detected. Consider reviewing entity mappings."
                    )
                
                if stats["avg_confidence"] < 0.7:
                    analysis["recommendations"].append(
                        "Low average confidence. Consider improving entity resolution."
                    )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze feedback patterns: {e}", exc_info=True)
            return {
                "total_feedback": 0,
                "approval_rate": 0.0,
                "correction_rate": 0.0,
                "common_corrections": [],
                "low_confidence_issues": [],
                "recommendations": []
            }
    
    async def get_learning_summary(self) -> dict[str, Any]:
        """
        Get summary of learning progress.
        
        Returns:
            Dictionary with learning summary
        """
        try:
            stats = await self.feedback_tracker.get_feedback_stats()
            analysis = await self.analyze_feedback_patterns()
            
            return {
                "total_feedback": stats["total_feedback"],
                "feedback_by_type": {
                    "approve": stats["approve_count"],
                    "reject": stats["reject_count"],
                    "correct": stats["correct_count"],
                    "custom_mapping": stats["custom_mapping_count"]
                },
                "approval_rate": analysis["approval_rate"],
                "correction_rate": analysis["correction_rate"],
                "avg_confidence": stats["avg_confidence"],
                "recommendations": analysis["recommendations"],
                "device_count": len(stats["device_names"])
            }
            
        except Exception as e:
            logger.error(f"Failed to get learning summary: {e}", exc_info=True)
            return {
                "total_feedback": 0,
                "feedback_by_type": {
                    "approve": 0,
                    "reject": 0,
                    "correct": 0,
                    "custom_mapping": 0
                },
                "approval_rate": 0.0,
                "correction_rate": 0.0,
                "avg_confidence": 0.0,
                "recommendations": [],
                "device_count": 0
            }

