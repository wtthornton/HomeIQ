"""
API Routes for Rule Recommendation ML Service

Provides REST API endpoints for:
- Getting personalized rule recommendations
- Getting recommendations based on device inventory
- Submitting feedback for model improvement
- Getting popular rules
"""

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["recommendations"])


# ============================================================================
# Pydantic Models
# ============================================================================

class RuleRecommendation(BaseModel):
    """A single rule recommendation."""
    
    rule_pattern: str = Field(..., description="Rule pattern (e.g., 'binary_sensor_to_light')")
    score: float = Field(..., description="Recommendation confidence score")
    trigger_domain: str = Field(..., description="Home Assistant trigger domain")
    action_domain: str = Field(..., description="Home Assistant action domain")
    description: str = Field(..., description="Human-readable description")


class RecommendationResponse(BaseModel):
    """Response containing rule recommendations."""
    
    recommendations: list[RuleRecommendation]
    user_id: str | None = Field(None, description="User ID if personalized")
    method: str = Field(..., description="Method used (collaborative, device-based, popular)")
    count: int = Field(..., description="Number of recommendations returned")


class RecommendationFeedback(BaseModel):
    """Feedback on a recommendation."""
    
    rule_pattern: str = Field(..., description="The recommended rule pattern")
    user_id: str | None = Field(None, description="User who received the recommendation")
    feedback_type: str = Field(
        ...,
        description="Type of feedback",
        pattern="^(accepted|rejected|ignored|created)$"
    )
    automation_id: str | None = Field(
        None, description="ID of created automation if feedback_type is 'created'"
    )
    rating: int | None = Field(
        None, ge=1, le=5, description="Optional 1-5 rating"
    )
    comment: str | None = Field(None, description="Optional feedback comment")


class FeedbackResponse(BaseModel):
    """Response after submitting feedback."""
    
    success: bool
    message: str
    feedback_id: str


class ModelInfoResponse(BaseModel):
    """Model information and statistics."""
    
    is_fitted: bool
    factors: int
    iterations: int
    num_users: int
    num_patterns: int
    matrix_shape: list[int] | None
    matrix_nnz: int


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str
    service: str
    version: str
    model_loaded: bool


# ============================================================================
# Global Model Instance (loaded on startup)
# ============================================================================

_recommender = None
_model_path = Path("./models/rule_recommender.pkl")


def get_recommender():
    """Get the loaded recommender model."""
    global _recommender
    if _recommender is None:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Please ensure the model is trained and loaded."
        )
    return _recommender


def load_model(path: Path | str | None = None) -> bool:
    """Load the trained model from disk."""
    global _recommender, _model_path
    
    from ..models.rule_recommender import RuleRecommender
    
    if path is not None:
        _model_path = Path(path)
    
    if not _model_path.exists():
        logger.warning(f"Model file not found at {_model_path}")
        return False
    
    try:
        _recommender = RuleRecommender.load(_model_path)
        logger.info(f"Loaded model from {_model_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        return False


# ============================================================================
# Helper Functions
# ============================================================================

def pattern_to_recommendation(pattern: str, score: float) -> RuleRecommendation:
    """Convert a pattern string to a RuleRecommendation object."""
    parts = pattern.split("_to_")
    
    if len(parts) == 2:
        trigger_domain, action_domain = parts
    else:
        trigger_domain = "unknown"
        action_domain = "unknown"
    
    # Generate human-readable description
    trigger_names = {
        "binary_sensor": "motion or door sensor",
        "sensor": "sensor value",
        "light": "light state",
        "switch": "switch state",
        "climate": "thermostat",
        "sun": "sunrise/sunset",
        "time": "time",
    }
    
    action_names = {
        "light": "turn lights on/off",
        "switch": "control switches",
        "climate": "adjust thermostat",
        "cover": "control blinds/garage",
        "lock": "lock/unlock doors",
        "fan": "control fans",
        "scene": "activate scene",
    }
    
    trigger_desc = trigger_names.get(trigger_domain, trigger_domain)
    action_desc = action_names.get(action_domain, action_domain)
    description = f"When {trigger_desc} triggers, {action_desc}"
    
    return RuleRecommendation(
        rule_pattern=pattern,
        score=score,
        trigger_domain=trigger_domain,
        action_domain=action_domain,
        description=description,
    )


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        service="rule-recommendation-ml",
        version="1.0.0",
        model_loaded=_recommender is not None and _recommender._is_fitted,
    )


@router.get("/model/info", response_model=ModelInfoResponse)
async def get_model_info():
    """Get information about the loaded model."""
    recommender = get_recommender()
    info = recommender.get_model_info()
    
    return ModelInfoResponse(
        is_fitted=info["is_fitted"],
        factors=info["factors"],
        iterations=info["iterations"],
        num_users=info["num_users"],
        num_patterns=info["num_patterns"],
        matrix_shape=list(info["matrix_shape"]) if info["matrix_shape"] else None,
        matrix_nnz=info["matrix_nnz"],
    )


@router.get("/rule-recommendations", response_model=RecommendationResponse)
async def get_recommendations(
    user_id: str | None = Query(None, description="User ID for personalized recommendations"),
    device_domains: list[str] = Query(
        default=[],
        description="Device domains to match (e.g., 'light', 'switch', 'climate')"
    ),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of recommendations"),
):
    """
    Get personalized rule recommendations.
    
    If user_id is provided, returns personalized recommendations based on
    the user's history. If device_domains is provided, returns recommendations
    matching those domains. Falls back to popular rules if neither is provided.
    """
    recommender = get_recommender()
    
    if user_id:
        # Personalized recommendations
        try:
            results = recommender.recommend(user_id=user_id, n=limit)
            method = "collaborative"
        except Exception as e:
            logger.warning(f"Collaborative filtering failed for {user_id}: {e}")
            results = recommender.get_popular_rules(n=limit)
            method = "popular_fallback"
    elif device_domains:
        # Device-based recommendations
        results = recommender.recommend_for_devices(device_domains, n=limit)
        method = "device_based"
    else:
        # Popular rules fallback
        results = recommender.get_popular_rules(n=limit)
        method = "popular"
    
    recommendations = [
        pattern_to_recommendation(pattern, score)
        for pattern, score in results
    ]
    
    return RecommendationResponse(
        recommendations=recommendations,
        user_id=user_id,
        method=method,
        count=len(recommendations),
    )


@router.get("/rule-recommendations/similar", response_model=RecommendationResponse)
async def get_similar_rules(
    rule_pattern: str = Query(..., description="Rule pattern to find similar rules for"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of similar rules"),
):
    """Get rules similar to a given rule pattern."""
    recommender = get_recommender()
    
    results = recommender.get_similar_rules(rule_pattern, n=limit)
    
    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"Rule pattern '{rule_pattern}' not found in model"
        )
    
    recommendations = [
        pattern_to_recommendation(pattern, score)
        for pattern, score in results
    ]
    
    return RecommendationResponse(
        recommendations=recommendations,
        user_id=None,
        method="similar_items",
        count=len(recommendations),
    )


@router.get("/rule-recommendations/popular", response_model=RecommendationResponse)
async def get_popular_rules(
    limit: int = Query(10, ge=1, le=50, description="Maximum number of popular rules"),
):
    """Get the most popular rule patterns overall."""
    recommender = get_recommender()
    
    results = recommender.get_popular_rules(n=limit)
    
    recommendations = [
        pattern_to_recommendation(pattern, score)
        for pattern, score in results
    ]
    
    return RecommendationResponse(
        recommendations=recommendations,
        user_id=None,
        method="popular",
        count=len(recommendations),
    )


@router.post("/rule-recommendations/feedback", response_model=FeedbackResponse)
async def submit_feedback(feedback: RecommendationFeedback):
    """
    Submit feedback on a recommendation.
    
    This feedback is used to improve future recommendations through:
    - Retraining with updated interaction data
    - Adjusting recommendation weights
    - Identifying low-quality patterns
    """
    import uuid
    
    # In production, this would store feedback in a database
    # and potentially trigger model retraining
    
    feedback_id = str(uuid.uuid4())
    
    logger.info(
        f"Received feedback: {feedback.feedback_type} for pattern '{feedback.rule_pattern}' "
        f"from user {feedback.user_id or 'anonymous'} (feedback_id={feedback_id})"
    )
    
    # TODO: Store feedback in database
    # TODO: Trigger incremental model update if enough feedback accumulated
    
    return FeedbackResponse(
        success=True,
        message=f"Feedback recorded successfully",
        feedback_id=feedback_id,
    )


@router.get("/patterns", response_model=dict[str, Any])
async def list_patterns(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of patterns to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """List all known rule patterns with their statistics."""
    recommender = get_recommender()
    
    patterns = list(recommender.pattern_to_idx.keys())
    total = len(patterns)
    
    # Paginate
    paginated = patterns[offset:offset + limit]
    
    return {
        "patterns": paginated,
        "total": total,
        "offset": offset,
        "limit": limit,
    }
