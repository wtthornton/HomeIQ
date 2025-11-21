"""
Learning Router

API endpoints for Q&A learning features:
- User preferences management
- Question quality metrics
- Q&A outcome statistics

Created: January 2025
Story: Q&A Learning Enhancement Plan
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import get_db_session, SystemSettings
from ..services.learning import (
    QAOutcomeTracker,
    UserPreferenceLearner,
    QuestionQualityTracker,
)
from .dependencies.auth import require_authenticated_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/learning",
    tags=["learning"],
    dependencies=[Depends(require_authenticated_user)]
)


class PreferenceResponse(BaseModel):
    """User preference response"""
    id: int
    question_category: str
    question_pattern: str
    answer_pattern: str
    consistency_score: float
    usage_count: int
    last_used: str


class QuestionQualityResponse(BaseModel):
    """Question quality metrics response"""
    question_id: str
    question_text: str
    question_category: str | None
    times_asked: int
    times_led_to_success: int
    confusion_count: int
    unnecessary_count: int
    avg_confidence_impact: float | None
    success_rate: float | None


@router.get("/preferences")
async def get_user_preferences(
    user_id: str = Query(..., description="User ID"),
    question_category: str | None = Query(None, description="Filter by category"),
    min_consistency: float = Query(0.9, description="Minimum consistency score"),
    db: AsyncSession = Depends(get_db_session)
) -> list[PreferenceResponse]:
    """
    Get user preferences.
    
    Returns learned preferences for the user, optionally filtered by category.
    """
    try:
        preference_learner = UserPreferenceLearner()
        preferences = await preference_learner.get_user_preferences(
            db=db,
            user_id=user_id,
            question_category=question_category,
            min_consistency=min_consistency
        )
        
        return [
            PreferenceResponse(
                id=p['id'],
                question_category=p['question_category'],
                question_pattern=p['question_pattern'],
                answer_pattern=p['answer_pattern'],
                consistency_score=p['consistency_score'],
                usage_count=p['usage_count'],
                last_used=p['last_used']
            )
            for p in preferences
        ]
    except Exception as e:
        logger.error(f"Failed to get user preferences: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/preferences")
async def clear_user_preferences(
    user_id: str = Query(..., description="User ID"),
    question_category: str | None = Query(None, description="Category to clear (all if not specified)"),
    db: AsyncSession = Depends(get_db_session)
) -> dict[str, Any]:
    """
    Clear user preferences (privacy control).
    
    Deletes learned preferences for the user, optionally filtered by category.
    """
    try:
        preference_learner = UserPreferenceLearner()
        deleted_count = await preference_learner.clear_user_preferences(
            db=db,
            user_id=user_id,
            question_category=question_category
        )
        
        return {
            "success": True,
            "message": f"Cleared {deleted_count} preferences",
            "deleted_count": deleted_count
        }
    except Exception as e:
        logger.error(f"Failed to clear user preferences: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/question-quality")
async def get_question_quality(
    question_id: str | None = Query(None, description="Specific question ID"),
    db: AsyncSession = Depends(get_db_session)
) -> QuestionQualityResponse | dict[str, Any]:
    """
    Get question quality metrics.
    
    Returns quality metrics for a specific question or overall statistics.
    """
    try:
        quality_tracker = QuestionQualityTracker()
        
        if question_id:
            # Get specific question quality
            quality = await quality_tracker.get_question_quality(db=db, question_id=question_id)
            if not quality:
                raise HTTPException(status_code=404, detail="Question quality not found")
            
            return QuestionQualityResponse(
                question_id=quality['question_id'],
                question_text=quality['question_text'],
                question_category=quality['question_category'],
                times_asked=quality['times_asked'],
                times_led_to_success=quality['times_led_to_success'],
                confusion_count=quality['confusion_count'],
                unnecessary_count=quality['unnecessary_count'],
                avg_confidence_impact=quality['avg_confidence_impact'],
                success_rate=quality['success_rate']
            )
        else:
            # Get overall statistics
            stats = await quality_tracker.get_question_quality_statistics(db=db)
            return stats
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get question quality: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/outcomes")
async def get_outcome_statistics(
    user_id: str | None = Query(None, description="Filter by user ID"),
    days: int = Query(30, description="Number of days to look back"),
    db: AsyncSession = Depends(get_db_session)
) -> dict[str, Any]:
    """
    Get Q&A outcome statistics.
    
    Returns statistics about Q&A session outcomes and automation success.
    """
    try:
        outcome_tracker = QAOutcomeTracker()
        stats = await outcome_tracker.get_outcome_statistics(
            db=db,
            user_id=user_id,
            days=days
        )
        return stats
    except Exception as e:
        logger.error(f"Failed to get outcome statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/high-quality-questions")
async def get_high_quality_questions(
    min_success_rate: float = Query(0.8, description="Minimum success rate"),
    min_times_asked: int = Query(5, description="Minimum times asked"),
    limit: int = Query(100, description="Maximum number to return"),
    db: AsyncSession = Depends(get_db_session)
) -> list[dict[str, Any]]:
    """
    Get high-quality questions for learning.
    
    Returns questions with high success rates for use in improving question generation.
    """
    try:
        quality_tracker = QuestionQualityTracker()
        questions = await quality_tracker.get_high_quality_questions(
            db=db,
            min_success_rate=min_success_rate,
            min_times_asked=min_times_asked,
            limit=limit
        )
        return questions
    except Exception as e:
        logger.error(f"Failed to get high-quality questions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


