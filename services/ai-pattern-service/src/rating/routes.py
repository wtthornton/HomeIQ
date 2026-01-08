"""
Rating API Routes

Provides endpoints for submitting and retrieving ratings.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .rating_service import RatingService, AutomationRating, BlueprintRating

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ratings", tags=["ratings"])

# Global instance (in production, use dependency injection)
rating_service = RatingService(min_ratings_for_confidence=5)


# Request/Response Models
class SubmitRatingRequest(BaseModel):
    """Request model for submitting a rating."""
    
    automation_id: str = Field(..., description="Home Assistant automation entity ID")
    overall_rating: float = Field(..., ge=1.0, le=5.0, description="Overall rating (1-5)")
    synergy_id: str | None = Field(None, description="Synergy ID if applicable")
    blueprint_id: str | None = Field(None, description="Blueprint ID if applicable")
    relevance_rating: float | None = Field(None, ge=1.0, le=5.0, description="Relevance rating")
    reliability_rating: float | None = Field(None, ge=1.0, le=5.0, description="Reliability rating")
    ease_of_use_rating: float | None = Field(None, ge=1.0, le=5.0, description="Ease of use rating")
    feedback_text: str | None = Field(None, max_length=1000, description="Text feedback")
    would_recommend: bool | None = Field(None, description="Would recommend this automation")


class RatingResponse(BaseModel):
    """Response model for a rating."""
    
    automation_id: str
    synergy_id: str | None
    blueprint_id: str | None
    overall_rating: float
    average_rating: float
    rated_at: str


class BlueprintRatingResponse(BaseModel):
    """Response model for blueprint rating."""
    
    blueprint_id: str
    total_ratings: int
    average_overall: float
    average_relevance: float
    average_reliability: float
    average_ease_of_use: float
    recommendation_rate: float
    composite_score: float


class SatisfactionSummaryResponse(BaseModel):
    """Response model for satisfaction summary."""
    
    period_days: int
    total_ratings: int
    average_overall: float
    average_relevance: float | None
    average_reliability: float | None
    average_ease_of_use: float | None
    recommendation_rate: float | None
    target: float
    achieved: bool
    progress_pct: float


class DeviceFeedbackRequest(BaseModel):
    """Request model for device feedback."""
    
    device_id: str = Field(..., description="Device entity ID")
    rating: float = Field(..., ge=1.0, le=5.0, description="Rating (1-5)")


@router.post("/submit", response_model=RatingResponse)
async def submit_rating(request: SubmitRatingRequest) -> RatingResponse:
    """
    Submit a rating for an automation.
    
    Ratings are used to:
    - Improve blueprint recommendations
    - Train the RL optimizer
    - Adjust pattern confidence
    """
    rating = rating_service.submit_rating(
        automation_id=request.automation_id,
        overall_rating=request.overall_rating,
        synergy_id=request.synergy_id,
        blueprint_id=request.blueprint_id,
        relevance_rating=request.relevance_rating,
        reliability_rating=request.reliability_rating,
        ease_of_use_rating=request.ease_of_use_rating,
        feedback_text=request.feedback_text,
        would_recommend=request.would_recommend,
    )
    
    return RatingResponse(
        automation_id=rating.automation_id,
        synergy_id=rating.synergy_id,
        blueprint_id=rating.blueprint_id,
        overall_rating=rating.overall_rating,
        average_rating=rating.average_rating,
        rated_at=rating.rated_at.isoformat(),
    )


@router.get("/automation/{automation_id}")
async def get_automation_ratings(automation_id: str) -> dict[str, Any]:
    """
    Get all ratings for an automation.
    """
    ratings = rating_service.get_automation_ratings(automation_id)
    avg_rating = rating_service.get_automation_average_rating(automation_id)
    
    return {
        "automation_id": automation_id,
        "average_rating": avg_rating,
        "total_ratings": len(ratings),
        "ratings": [
            {
                "overall_rating": r.overall_rating,
                "relevance_rating": r.relevance_rating,
                "reliability_rating": r.reliability_rating,
                "ease_of_use_rating": r.ease_of_use_rating,
                "feedback_text": r.feedback_text,
                "would_recommend": r.would_recommend,
                "rated_at": r.rated_at.isoformat(),
            }
            for r in ratings
        ],
    }


@router.get("/blueprint/{blueprint_id}", response_model=BlueprintRatingResponse)
async def get_blueprint_rating(blueprint_id: str) -> BlueprintRatingResponse:
    """
    Get aggregated rating for a blueprint.
    """
    bp_rating = rating_service.get_blueprint_rating(blueprint_id)
    
    if not bp_rating:
        raise HTTPException(status_code=404, detail=f"No ratings found for blueprint {blueprint_id}")
    
    return BlueprintRatingResponse(
        blueprint_id=bp_rating.blueprint_id,
        total_ratings=bp_rating.total_ratings,
        average_overall=bp_rating.average_overall,
        average_relevance=bp_rating.average_relevance,
        average_reliability=bp_rating.average_reliability,
        average_ease_of_use=bp_rating.average_ease_of_use,
        recommendation_rate=bp_rating.recommendation_rate,
        composite_score=bp_rating.composite_score,
    )


@router.get("/blueprint/{blueprint_id}/score")
async def get_blueprint_score(blueprint_id: str) -> dict[str, Any]:
    """
    Get blueprint score for ranking.
    
    Returns 0 if not enough ratings for confidence.
    """
    score = rating_service.get_blueprint_score(blueprint_id)
    bp_rating = rating_service.get_blueprint_rating(blueprint_id)
    
    return {
        "blueprint_id": blueprint_id,
        "score": score,
        "total_ratings": bp_rating.total_ratings if bp_rating else 0,
        "has_confidence": bp_rating.total_ratings >= rating_service.min_ratings_for_confidence if bp_rating else False,
    }


@router.get("/top-blueprints", response_model=list[BlueprintRatingResponse])
async def get_top_rated_blueprints(
    limit: int = Query(default=10, ge=1, le=100),
) -> list[BlueprintRatingResponse]:
    """
    Get top-rated blueprints.
    """
    top_blueprints = rating_service.get_top_rated_blueprints(limit=limit)
    
    return [
        BlueprintRatingResponse(
            blueprint_id=bp.blueprint_id,
            total_ratings=bp.total_ratings,
            average_overall=bp.average_overall,
            average_relevance=bp.average_relevance,
            average_reliability=bp.average_reliability,
            average_ease_of_use=bp.average_ease_of_use,
            recommendation_rate=bp.recommendation_rate,
            composite_score=bp.composite_score,
        )
        for bp in top_blueprints
    ]


@router.get("/satisfaction-summary", response_model=SatisfactionSummaryResponse)
async def get_satisfaction_summary(
    days: int = Query(default=30, ge=1, le=365),
) -> SatisfactionSummaryResponse:
    """
    Get user satisfaction summary.
    
    Target: 4.0+ average rating
    """
    summary = rating_service.get_satisfaction_summary(days=days)
    return SatisfactionSummaryResponse(**summary)


@router.post("/device-feedback")
async def record_device_feedback(request: DeviceFeedbackRequest) -> dict[str, Any]:
    """
    Record feedback for a device.
    
    Used to adjust pattern confidence for devices.
    """
    rating_service.record_device_feedback(
        device_id=request.device_id,
        rating=request.rating,
    )
    
    feedback_score = rating_service.get_device_feedback_score(request.device_id)
    
    return {
        "device_id": request.device_id,
        "rating_recorded": request.rating,
        "current_feedback_score": feedback_score,
    }


@router.get("/device/{device_id}/feedback-score")
async def get_device_feedback_score(device_id: str) -> dict[str, Any]:
    """
    Get feedback score for a device.
    
    Score ranges from 0.5 (negative) to 1.5 (positive), 1.0 is neutral.
    Used by pattern detection to adjust confidence.
    """
    score = rating_service.get_device_feedback_score(device_id)
    
    return {
        "device_id": device_id,
        "feedback_score": score,
        "interpretation": (
            "positive" if score > 1.1 else
            "negative" if score < 0.9 else
            "neutral"
        ),
    }


@router.get("/synergy/{synergy_id}/rl-feedback")
async def get_rl_feedback(synergy_id: str) -> dict[str, Any]:
    """
    Get feedback data for RL optimizer.
    
    Returns reward signal and context for reinforcement learning.
    """
    feedback = rating_service.get_feedback_for_rl_optimizer(synergy_id)
    
    if not feedback:
        raise HTTPException(status_code=404, detail=f"No feedback found for synergy {synergy_id}")
    
    return feedback
