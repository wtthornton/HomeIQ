"""
Feedback Processor for Entity Resolution

Epic AI-12, Story AI12.5: Index Update from User Feedback
Processes feedback patterns and generates update recommendations.
"""

import logging
from typing import Any, Optional
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession

from .feedback_tracker import FeedbackTracker, FeedbackType, EntityResolutionFeedback
from ..entity.index_updater import IndexUpdater
from ..entity.personalized_index import PersonalizedEntityIndex

logger = logging.getLogger(__name__)


class FeedbackProcessor:
    """
    Processes user feedback patterns and generates update recommendations.
    
    Features:
    - Analyze feedback patterns
    - Identify learning opportunities
    - Generate update recommendations
    - Process feedback in batches
    """
    
    def __init__(
        self,
        db: AsyncSession,
        personalized_index: PersonalizedEntityIndex,
        index_updater: Optional[IndexUpdater] = None
    ):
        """
        Initialize feedback processor.
        
        Args:
            db: Database session
            personalized_index: PersonalizedEntityIndex
            index_updater: Optional IndexUpdater (will create if not provided)
        """
        self.db = db
        self.index = personalized_index
        self.feedback_tracker = FeedbackTracker(db)
        self.index_updater = index_updater or IndexUpdater(personalized_index, self.feedback_tracker)
        
        logger.info("FeedbackProcessor initialized")
    
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
            
            # Get feedback details
            if device_name:
                feedbacks = await self.feedback_tracker.get_feedback_for_device(device_name)
            else:
                feedbacks = []
            
            # Analyze patterns
            analysis = {
                "total_feedback": stats["total_feedback"],
                "approval_rate": 0.0,
                "correction_rate": 0.0,
                "common_corrections": [],
                "frequent_mappings": [],
                "low_confidence_issues": [],
                "recommendations": []
            }
            
            if stats["total_feedback"] > 0:
                # Calculate rates
                analysis["approval_rate"] = stats["approve_count"] / stats["total_feedback"]
                analysis["correction_rate"] = stats["correct_count"] / stats["total_feedback"]
                
                # Find common corrections
                corrections = [
                    f for f in feedbacks
                    if f.feedback_type == FeedbackType.CORRECT and f.actual_entity_id
                ]
                
                # Group by actual entity
                entity_counts = defaultdict(int)
                entity_mappings = defaultdict(list)
                
                for correction in corrections:
                    if correction.actual_entity_id:
                        entity_counts[correction.actual_entity_id] += 1
                        entity_mappings[correction.actual_entity_id].append(correction.device_name)
                
                # Get top corrections
                analysis["common_corrections"] = sorted(
                    entity_counts.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10]
                
                # Find frequent mappings (approved multiple times)
                approvals = [
                    f for f in feedbacks
                    if f.feedback_type == FeedbackType.APPROVE and f.suggested_entity_id
                ]
                
                approval_counts = defaultdict(int)
                for approval in approvals:
                    if approval.suggested_entity_id:
                        key = f"{approval.device_name} -> {approval.suggested_entity_id}"
                        approval_counts[key] += 1
                
                analysis["frequent_mappings"] = sorted(
                    approval_counts.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10]
                
                # Find low confidence issues
                low_confidence = [
                    f for f in feedbacks
                    if f.confidence_score is not None and f.confidence_score < 0.7
                ]
                
                analysis["low_confidence_issues"] = [
                    {
                        "device_name": f.device_name,
                        "entity_id": f.suggested_entity_id,
                        "confidence": f.confidence_score
                    }
                    for f in low_confidence[:10]
                ]
                
                # Generate recommendations
                if analysis["correction_rate"] > 0.3:
                    analysis["recommendations"].append(
                        f"High correction rate ({analysis['correction_rate']:.1%}) detected. "
                        "Consider reviewing entity mappings for common corrections."
                    )
                
                if stats["avg_confidence"] < 0.7:
                    analysis["recommendations"].append(
                        f"Low average confidence ({stats['avg_confidence']:.2f}). "
                        "Consider improving entity resolution accuracy."
                    )
                
                if len(analysis["common_corrections"]) > 0:
                    top_correction = analysis["common_corrections"][0]
                    analysis["recommendations"].append(
                        f"Frequent correction: '{device_name or 'multiple'}' -> {top_correction[0]} "
                        f"({top_correction[1]} times). Consider adding as preferred mapping."
                    )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze feedback patterns: {e}", exc_info=True)
            return {
                "total_feedback": 0,
                "approval_rate": 0.0,
                "correction_rate": 0.0,
                "common_corrections": [],
                "frequent_mappings": [],
                "low_confidence_issues": [],
                "recommendations": []
            }
    
    async def process_feedback_and_update(
        self,
        device_name: Optional[str] = None,
        limit: int = 100
    ) -> dict[str, Any]:
        """
        Process feedback and update index.
        
        Args:
            device_name: Optional device name filter
            limit: Maximum number of feedback records to process
        
        Returns:
            Dictionary with processing results
        """
        try:
            # Process feedback batch
            update_stats = await self.index_updater.process_feedback_batch(device_name, limit)
            
            # Get update statistics
            index_stats = self.index_updater.get_update_stats()
            
            return {
                "feedback_processed": update_stats["processed"],
                "index_updated": update_stats["updated"],
                "errors": update_stats["errors"],
                "by_type": dict(update_stats["by_type"]),
                "index_stats": index_stats
            }
            
        except Exception as e:
            logger.error(f"Failed to process feedback and update: {e}", exc_info=True)
            return {
                "feedback_processed": 0,
                "index_updated": 0,
                "errors": 1,
                "by_type": {},
                "index_stats": {}
            }
    
    async def get_learning_opportunities(
        self,
        min_corrections: int = 3
    ) -> list[dict[str, Any]]:
        """
        Get learning opportunities based on feedback patterns.
        
        Args:
            min_corrections: Minimum number of corrections to consider
        
        Returns:
            List of learning opportunities
        """
        try:
            # Get all feedback
            stats = await self.feedback_tracker.get_feedback_stats()
            
            opportunities = []
            
            # Check each device with feedback
            for device_name in stats["device_names"].keys():
                feedbacks = await self.feedback_tracker.get_feedback_for_device(device_name)
                
                # Find corrections
                corrections = [
                    f for f in feedbacks
                    if f.feedback_type == FeedbackType.CORRECT and f.actual_entity_id
                ]
                
                if len(corrections) >= min_corrections:
                    # Group by actual entity
                    entity_counts = defaultdict(int)
                    for correction in corrections:
                        entity_counts[correction.actual_entity_id] += 1
                    
                    # Find most common correction
                    if entity_counts:
                        most_common = max(entity_counts.items(), key=lambda x: x[1])
                        
                        opportunities.append({
                            "device_name": device_name,
                            "current_mapping": corrections[0].suggested_entity_id,
                            "preferred_mapping": most_common[0],
                            "correction_count": most_common[1],
                            "total_feedback": len(feedbacks),
                            "confidence": most_common[1] / len(feedbacks)
                        })
            
            # Sort by confidence
            opportunities.sort(key=lambda x: x["confidence"], reverse=True)
            
            return opportunities
            
        except Exception as e:
            logger.error(f"Failed to get learning opportunities: {e}", exc_info=True)
            return []

