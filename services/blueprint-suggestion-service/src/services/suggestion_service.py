"""Main orchestration service for blueprint suggestions."""

import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.suggestion import BlueprintSuggestion
from .blueprint_matcher import BlueprintMatcher

logger = logging.getLogger(__name__)


class SuggestionService:
    """Main service for managing blueprint suggestions."""
    
    def __init__(self):
        """Initialize suggestion service."""
        self.matcher = BlueprintMatcher()
    
    async def generate_all_suggestions(
        self,
        db: AsyncSession,
        min_score: float = 0.6,
        max_per_blueprint: int = 5,
    ) -> int:
        """
        Generate suggestions for all blueprints and save to database.
        
        Args:
            db: Database session
            min_score: Minimum score threshold
            max_per_blueprint: Maximum suggestions per blueprint
            
        Returns:
            Number of suggestions generated
        """
        logger.info("Generating blueprint suggestions...")
        
        # Generate suggestions using matcher
        suggestions_data = await self.matcher.generate_suggestions(
            min_score=min_score,
            max_suggestions_per_blueprint=max_per_blueprint,
        )
        
        # Save to database
        count = 0
        for suggestion_data in suggestions_data:
            suggestion = BlueprintSuggestion(
                id=str(uuid.uuid4()),
                blueprint_id=suggestion_data["blueprint_id"],
                blueprint_name=suggestion_data.get("blueprint_name"),  # Store blueprint name
                blueprint_description=suggestion_data.get("blueprint_description"),  # Store blueprint description
                suggestion_score=suggestion_data["suggestion_score"],
                matched_devices=suggestion_data["matched_devices"],
                use_case=suggestion_data.get("use_case"),
                status="pending",
            )
            db.add(suggestion)
            count += 1
        
        await db.commit()
        logger.info(f"Generated and saved {count} suggestions")
        return count
    
    async def get_suggestions(
        self,
        db: AsyncSession,
        min_score: Optional[float] = None,
        use_case: Optional[str] = None,
        status: Optional[str] = None,
        blueprint_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[BlueprintSuggestion], int]:
        """
        Get suggestions with filters.
        
        Args:
            db: Database session
            min_score: Minimum score filter
            use_case: Use case filter
            status: Status filter (pending, accepted, declined)
            blueprint_id: Blueprint ID filter
            limit: Maximum results
            offset: Offset for pagination
            
        Returns:
            Tuple of (suggestions list, total count)
        """
        query = select(BlueprintSuggestion)
        
        # Apply filters
        if min_score is not None:
            query = query.where(BlueprintSuggestion.suggestion_score >= min_score)
        if use_case:
            query = query.where(BlueprintSuggestion.use_case == use_case)
        if status:
            query = query.where(BlueprintSuggestion.status == status)
        if blueprint_id:
            query = query.where(BlueprintSuggestion.blueprint_id == blueprint_id)
        
        # Get total count (before pagination)
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Apply pagination
        query = query.order_by(BlueprintSuggestion.suggestion_score.desc())
        query = query.limit(limit).offset(offset)
        
        result = await db.execute(query)
        suggestions = result.scalars().all()
        
        return list(suggestions), total
    
    async def accept_suggestion(
        self,
        db: AsyncSession,
        suggestion_id: str,
        conversation_id: Optional[str] = None,
    ) -> Optional[BlueprintSuggestion]:
        """
        Accept a suggestion.
        
        Args:
            db: Database session
            suggestion_id: Suggestion ID
            conversation_id: Optional conversation ID from Agent
            
        Returns:
            Updated suggestion or None if not found
        """
        query = select(BlueprintSuggestion).where(BlueprintSuggestion.id == suggestion_id)
        result = await db.execute(query)
        suggestion = result.scalar_one_or_none()
        
        if not suggestion:
            return None
        
        suggestion.status = "accepted"
        suggestion.accepted_at = datetime.utcnow()
        suggestion.updated_at = datetime.utcnow()
        if conversation_id:
            suggestion.conversation_id = conversation_id
        
        await db.commit()
        await db.refresh(suggestion)
        return suggestion
    
    async def decline_suggestion(
        self,
        db: AsyncSession,
        suggestion_id: str,
    ) -> Optional[BlueprintSuggestion]:
        """
        Decline a suggestion.
        
        Args:
            db: Database session
            suggestion_id: Suggestion ID
            
        Returns:
            Updated suggestion or None if not found
        """
        query = select(BlueprintSuggestion).where(BlueprintSuggestion.id == suggestion_id)
        result = await db.execute(query)
        suggestion = result.scalar_one_or_none()
        
        if not suggestion:
            return None
        
        suggestion.status = "declined"
        suggestion.declined_at = datetime.utcnow()
        suggestion.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(suggestion)
        return suggestion
    
    async def get_stats(self, db: AsyncSession) -> dict[str, Any]:
        """
        Get statistics about suggestions.
        
        Args:
            db: Database session
            
        Returns:
            Statistics dictionary
        """
        # Total count
        total_query = select(func.count(BlueprintSuggestion.id))
        total_result = await db.execute(total_query)
        total = total_result.scalar() or 0
        
        # Status counts
        pending_query = select(func.count(BlueprintSuggestion.id)).where(
            BlueprintSuggestion.status == "pending"
        )
        pending_result = await db.execute(pending_query)
        pending_count = pending_result.scalar() or 0
        
        accepted_query = select(func.count(BlueprintSuggestion.id)).where(
            BlueprintSuggestion.status == "accepted"
        )
        accepted_result = await db.execute(accepted_query)
        accepted_count = accepted_result.scalar() or 0
        
        declined_query = select(func.count(BlueprintSuggestion.id)).where(
            BlueprintSuggestion.status == "declined"
        )
        declined_result = await db.execute(declined_query)
        declined_count = declined_result.scalar() or 0
        
        # Score statistics
        score_query = select(
            func.avg(BlueprintSuggestion.suggestion_score),
            func.min(BlueprintSuggestion.suggestion_score),
            func.max(BlueprintSuggestion.suggestion_score),
        )
        score_result = await db.execute(score_query)
        score_row = score_result.first()
        avg_score = float(score_row[0] or 0.0) if score_row else 0.0
        min_score = float(score_row[1] or 0.0) if score_row else 0.0
        max_score = float(score_row[2] or 0.0) if score_row else 0.0
        
        return {
            "total_suggestions": total,
            "pending_count": pending_count,
            "accepted_count": accepted_count,
            "declined_count": declined_count,
            "average_score": avg_score,
            "min_score": min_score,
            "max_score": max_score,
        }
    
    async def generate_suggestions_with_params(
        self,
        db: AsyncSession,
        device_ids: Optional[list[str]] = None,
        complexity: Optional[str] = None,
        use_case: Optional[str] = None,
        min_score: float = 0.6,
        max_suggestions: int = 10,
        min_quality_score: Optional[float] = None,
        domain: Optional[str] = None,
    ) -> int:
        """
        Generate suggestions with user-defined parameters.
        
        Args:
            db: Database session
            device_ids: Specific device entity IDs to use, or None for all
            complexity: Filter by complexity (simple/medium/high), or None for all
            use_case: Filter by use case (convenience/security/energy/comfort), or None for all
            min_score: Minimum score threshold
            max_suggestions: Maximum number of suggestions to generate
            min_quality_score: Minimum blueprint quality score
            domain: Filter by device domain
            
        Returns:
            Number of suggestions generated
        """
        logger.info(
            f"Generating suggestions with params: "
            f"device_ids={len(device_ids) if device_ids else 'all'}, "
            f"complexity={complexity}, use_case={use_case}, "
            f"min_score={min_score}, max_suggestions={max_suggestions}"
        )
        
        # Generate suggestions using matcher with filters
        suggestions_data = await self.matcher.generate_suggestions_with_params(
            device_ids=device_ids,
            complexity=complexity,
            use_case=use_case,
            min_score=min_score,
            max_suggestions=max_suggestions,
            min_quality_score=min_quality_score,
            domain=domain,
        )
        
        # Save to database
        count = 0
        for suggestion_data in suggestions_data[:max_suggestions]:  # Limit to max_suggestions
            suggestion = BlueprintSuggestion(
                id=str(uuid.uuid4()),
                blueprint_id=suggestion_data["blueprint_id"],
                blueprint_name=suggestion_data.get("blueprint_name"),
                blueprint_description=suggestion_data.get("blueprint_description"),
                suggestion_score=suggestion_data["suggestion_score"],
                matched_devices=suggestion_data["matched_devices"],
                use_case=suggestion_data.get("use_case"),
                status="pending",
            )
            db.add(suggestion)
            count += 1
        
        await db.commit()
        logger.info(f"Generated and saved {count} suggestions")
        return count