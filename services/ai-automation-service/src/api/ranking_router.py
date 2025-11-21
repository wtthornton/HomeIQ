"""
Ranking Router - POST /rank endpoint
"""

import logging
from typing import Any

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

from src.ranking.score import rank_automations

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/rank", tags=["ranking"])


class RankRequest(BaseModel):
    """Request to rank automation plans"""
    automations: list[dict[str, Any]]  # List of automation plans
    capabilities: dict[str, Any]  # Available capabilities
    top_k: int = 10  # Number of top results to return
    reliability_history: dict[str, float] | None = None  # Reliability scores by entity_id
    user_preferences: dict[str, float] | None = None  # User preferences by device_type


class RankResponse(BaseModel):
    """Response from ranking"""
    ranked: list[dict[str, Any]]  # Ranked automations with scores
    total_count: int
    excluded_count: int


@router.post("", response_model=RankResponse)
async def rank_automation_plans(request: RankRequest = Body(...)):
    """
    Rank automation plans using heuristic scoring.

    Returns top-K automations sorted by score with feature breakdown.
    Excludes automations missing mandatory capabilities.

    Returns:
        Ranked automations with scores and feature breakdown
    """
    try:
        ranked = rank_automations(
            automations=request.automations,
            capabilities=request.capabilities,
            top_k=request.top_k,
            reliability_history=request.reliability_history,
            user_preferences=request.user_preferences,
        )

        # Convert to response format
        ranked_dicts = []
        for ranked_automation in ranked:
            ranked_dicts.append({
                "automation": ranked_automation.automation,
                "rank": ranked_automation.rank,
                "score": {
                    "total_score": ranked_automation.score.total_score,
                    "capability_match_ratio": ranked_automation.score.capability_match_ratio,
                    "reliability_score": ranked_automation.score.reliability_score,
                    "predicted_latency_sec": ranked_automation.score.predicted_latency_sec,
                    "energy_cost_bucket": ranked_automation.score.energy_cost_bucket,
                    "user_recent_preference": ranked_automation.score.user_recent_preference,
                    "feature_breakdown": ranked_automation.score.feature_breakdown,
                    "excluded": ranked_automation.score.excluded,
                    "exclusion_reason": ranked_automation.score.exclusion_reason,
                },
            })

        return RankResponse(
            ranked=ranked_dicts,
            total_count=len(request.automations),
            excluded_count=len(request.automations) - len(ranked),
        )

    except Exception as e:
        logger.error(f"Ranking error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ranking failed: {e!s}") from e

