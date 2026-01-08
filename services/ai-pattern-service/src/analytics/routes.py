"""
Analytics API Routes

Provides endpoints for viewing analytics metrics and progress toward targets.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .blueprint_analytics import BlueprintAnalytics, AnalyticsSummary
from .metrics_collector import MetricsCollector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])

# Global instances (in production, use dependency injection)
analytics = BlueprintAnalytics(retention_days=90)
metrics_collector = MetricsCollector()


# Response Models
class TargetProgressResponse(BaseModel):
    """Response model for target progress."""
    
    adoption_rate: dict[str, Any] = Field(
        ..., description="Adoption rate progress (target: 30%)"
    )
    success_rate: dict[str, Any] = Field(
        ..., description="Success rate progress (target: 85%)"
    )
    pattern_quality: dict[str, Any] = Field(
        ..., description="Pattern quality progress (target: 90%)"
    )
    user_satisfaction: dict[str, Any] = Field(
        ..., description="User satisfaction progress (target: 4.0+)"
    )


class AnalyticsSummaryResponse(BaseModel):
    """Response model for analytics summary."""
    
    period_start: str
    period_end: str
    adoption_rate: float
    success_rate: float
    pattern_quality: float
    average_rating: float
    total_deployments: int
    blueprint_utilization_rate: float


class TrendingBlueprintResponse(BaseModel):
    """Response model for trending blueprint."""
    
    blueprint_id: str
    deployment_count: int
    success_rate: float | None
    average_rating: float | None


class DeploymentRecordRequest(BaseModel):
    """Request model for recording deployment."""
    
    automation_id: str = Field(..., description="Home Assistant automation entity ID")
    blueprint_id: str | None = Field(None, description="Blueprint ID if applicable")
    synergy_id: str | None = Field(None, description="Synergy ID if applicable")
    source: str = Field("synergy", description="Deployment source")


class ExecutionRecordRequest(BaseModel):
    """Request model for recording execution."""
    
    automation_id: str = Field(..., description="Home Assistant automation entity ID")
    success: bool = Field(..., description="Whether execution was successful")
    error_message: str | None = Field(None, description="Error message if failed")
    execution_time_ms: int | None = Field(None, description="Execution time in ms")


class RatingRecordRequest(BaseModel):
    """Request model for recording rating."""
    
    automation_id: str = Field(..., description="Home Assistant automation entity ID")
    rating: float = Field(..., ge=1.0, le=5.0, description="User rating (1-5)")
    feedback: str | None = Field(None, description="Optional text feedback")


@router.get("/target-progress", response_model=TargetProgressResponse)
async def get_target_progress(
    total_synergies: int = Query(
        default=0,
        ge=0,
        description="Total synergies for adoption rate calculation",
    ),
) -> TargetProgressResponse:
    """
    Get progress toward target metrics from RECOMMENDATIONS_FEASIBILITY_ANALYSIS.md.
    
    Targets:
    - Adoption Rate: 30%
    - Success Rate: 85%
    - Pattern Quality: 90%
    - User Satisfaction: 4.0+
    """
    progress = analytics.get_target_progress(total_synergies=total_synergies)
    return TargetProgressResponse(**progress)


@router.get("/summary", response_model=AnalyticsSummaryResponse)
async def get_summary(
    days: int = Query(default=30, ge=1, le=365, description="Number of days to analyze"),
    total_synergies: int = Query(default=0, ge=0, description="Total synergies"),
) -> AnalyticsSummaryResponse:
    """
    Get analytics summary for the specified period.
    """
    summary = analytics.get_summary(days=days, total_synergies=total_synergies)
    return AnalyticsSummaryResponse(
        period_start=summary.period_start.isoformat(),
        period_end=summary.period_end.isoformat(),
        adoption_rate=summary.adoption_rate,
        success_rate=summary.success_rate,
        pattern_quality=summary.pattern_quality,
        average_rating=summary.average_rating,
        total_deployments=summary.synergies_deployed + summary.yaml_fallback_deployments,
        blueprint_utilization_rate=summary.blueprint_utilization_rate,
    )


@router.get("/trending-blueprints", response_model=list[TrendingBlueprintResponse])
async def get_trending_blueprints(
    limit: int = Query(default=10, ge=1, le=100, description="Maximum blueprints to return"),
) -> list[TrendingBlueprintResponse]:
    """
    Get most deployed blueprints with success rates and ratings.
    """
    trending = analytics.get_trending_blueprints(limit=limit)
    return [TrendingBlueprintResponse(**bp) for bp in trending]


@router.post("/deployments")
async def record_deployment(request: DeploymentRecordRequest) -> dict[str, Any]:
    """
    Record a new automation deployment.
    """
    metric = analytics.record_deployment(
        automation_id=request.automation_id,
        blueprint_id=request.blueprint_id,
        synergy_id=request.synergy_id,
        source=request.source,
    )
    
    # Also record in metrics collector for InfluxDB
    await metrics_collector.record_deployment(
        automation_id=request.automation_id,
        blueprint_id=request.blueprint_id,
        synergy_id=request.synergy_id,
        source=request.source,
    )
    
    return {
        "status": "recorded",
        "automation_id": metric.automation_id,
        "deployed_at": metric.deployed_at.isoformat(),
    }


@router.post("/executions")
async def record_execution(request: ExecutionRecordRequest) -> dict[str, Any]:
    """
    Record an automation execution result.
    """
    analytics.record_execution(
        automation_id=request.automation_id,
        success=request.success,
        error_message=request.error_message,
    )
    
    # Also record in metrics collector
    await metrics_collector.record_execution(
        automation_id=request.automation_id,
        success=request.success,
        execution_time_ms=request.execution_time_ms,
        error_type=request.error_message.split(":")[0] if request.error_message else None,
    )
    
    return {
        "status": "recorded",
        "automation_id": request.automation_id,
        "success": request.success,
    }


@router.post("/ratings")
async def record_rating(request: RatingRecordRequest) -> dict[str, Any]:
    """
    Record a user rating for an automation.
    """
    analytics.record_rating(
        automation_id=request.automation_id,
        rating=request.rating,
        feedback=request.feedback,
    )
    
    # Also record in metrics collector
    await metrics_collector.record_rating(
        automation_id=request.automation_id,
        rating=request.rating,
    )
    
    return {
        "status": "recorded",
        "automation_id": request.automation_id,
        "rating": request.rating,
    }


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """
    Check analytics service health.
    """
    summary = analytics.get_summary(days=1)
    
    return {
        "status": "healthy",
        "deployments_24h": summary.synergies_deployed + summary.blueprint_utilization_rate,
        "metrics_available": True,
    }


@router.post("/cleanup")
async def cleanup_old_metrics(
    retention_days: int = Query(default=90, ge=30, le=365),
) -> dict[str, Any]:
    """
    Clean up metrics older than retention period.
    """
    analytics_removed = analytics.cleanup_old_metrics()
    collector_removed = metrics_collector.cleanup_old_metrics(days=retention_days)
    
    return {
        "status": "cleaned",
        "analytics_metrics_removed": analytics_removed,
        "collector_metrics_removed": collector_removed,
    }
