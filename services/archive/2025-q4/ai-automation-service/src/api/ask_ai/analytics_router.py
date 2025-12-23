"""
Analytics Router

Epic 39, Story 39.13: Router Modularization
Extracted from ask_ai_router.py for better organization.
Handles analytics and metrics endpoints.
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...database.models import AskAIQuery as AskAIQueryModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ask-ai", tags=["Analytics"])


@router.get("/analytics/reverse-engineering")
async def get_reverse_engineering_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get analytics and insights for reverse engineering performance.
    
    Provides aggregated metrics including:
    - Similarity improvements
    - Performance metrics (iterations, time, cost)
    - Automation success rates
    - Value indicators and KPIs
    
    Args:
        days: Number of days to analyze (default: 30)
        db: Database session
        
    Returns:
        Dictionary with comprehensive analytics
    """
    try:
        from ...services.reverse_engineering_metrics import get_reverse_engineering_analytics

        analytics = await get_reverse_engineering_analytics(db_session=db, days=days)

        return {
            "status": "success",
            "analytics": analytics
        }
    except Exception as e:
        logger.error(f"❌ Failed to get reverse engineering analytics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve analytics: {str(e)}"
        ) from e


@router.get("/pattern-synergy/metrics")
async def get_pattern_synergy_metrics() -> dict[str, Any]:
    """
    Get pattern and synergy integration metrics for monitoring.
    
    Returns metrics for:
    - Pattern query performance (latency, cache hit rate)
    - Synergy query performance (latency, cache hit rate)
    - Confidence boost statistics
    
    Example:
        GET /api/v1/ask-ai/pattern-synergy/metrics
        {
            "patterns": {
                "query_count": 150,
                "cache_hit_rate": 65.3,
                "avg_latency_ms": 45.2,
                "p50_latency_ms": 38.1,
                "p95_latency_ms": 89.5,
                "p99_latency_ms": 125.3,
                "avg_patterns_retrieved": 7.2,
                "errors": 2
            },
            "synergies": {
                "query_count": 150,
                "cache_hit_rate": 62.7,
                "avg_latency_ms": 78.4,
                "p50_latency_ms": 65.2,
                "p95_latency_ms": 145.8,
                "p99_latency_ms": 198.3,
                "avg_synergies_retrieved": 3.8,
                "errors": 1
            },
            "confidence_boosts": {
                "total_suggestions": 500,
                "boosts_applied": 150,
                "boost_rate": 30.0,
                "avg_boost_amount": 0.092,
                "avg_base_confidence": 0.78,
                "avg_final_confidence": 0.85
            }
        }
    """
    try:
        from ...services.pattern_context_service import PatternContextService
        from ...services.synergy_context_service import SynergyContextService
        
        # Get pattern metrics
        pattern_metrics = PatternContextService.get_metrics()
        
        # Get synergy metrics
        synergy_metrics = SynergyContextService.get_metrics()
        
        # Calculate confidence boost metrics
        # Note: _confidence_boost_metrics is a global variable in ask_ai_router.py
        # For now, we'll need to import it or refactor to a service
        # This is a temporary solution - should be refactored to a service
        try:
            from ...api.ask_ai_router import _confidence_boost_metrics
            boost_metrics = _confidence_boost_metrics.copy()
        except ImportError:
            # Fallback if not available
            boost_metrics = {
                "total_suggestions": 0,
                "boosts_applied": 0,
                "boost_amounts": [],
                "base_confidences": [],
                "final_confidences": []
            }
        
        total_suggestions = boost_metrics["total_suggestions"]
        
        if total_suggestions > 0:
            boost_rate = (boost_metrics["boosts_applied"] / total_suggestions) * 100
            avg_boost = (
                sum(boost_metrics["boost_amounts"]) / len(boost_metrics["boost_amounts"])
                if boost_metrics["boost_amounts"] else 0.0
            )
            avg_base = (
                sum(boost_metrics["base_confidences"]) / len(boost_metrics["base_confidences"])
                if boost_metrics["base_confidences"] else 0.0
            )
            avg_final = (
                sum(boost_metrics["final_confidences"]) / len(boost_metrics["final_confidences"])
                if boost_metrics["final_confidences"] else 0.0
            )
        else:
            boost_rate = 0.0
            avg_boost = 0.0
            avg_base = 0.0
            avg_final = 0.0
        
        confidence_boost_stats = {
            "total_suggestions": total_suggestions,
            "boosts_applied": boost_metrics["boosts_applied"],
            "boost_rate": round(boost_rate, 2),
            "avg_boost_amount": round(avg_boost, 3),
            "avg_base_confidence": round(avg_base, 3),
            "avg_final_confidence": round(avg_final, 3)
        }
        
        return {
            "patterns": pattern_metrics,
            "synergies": synergy_metrics,
            "confidence_boosts": confidence_boost_stats
        }
    except Exception as e:
        logger.error(f"Error getting pattern/synergy metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/failure-stats")
async def get_failure_stats(
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Get failure statistics for Ask AI queries.
    
    Returns breakdown of failure reasons to identify main causes of failures.
    
    Example:
        GET /api/v1/ask-ai/failure-stats
        {
            "total_queries": 1000,
            "success_count": 460,
            "failure_count": 540,
            "failure_rate": 54.0,
            "failure_breakdown": {
                "clarification_needed": 300,
                "entity_mapping_failed": 150,
                "empty_suggestions": 80,
                "pattern_fallback_used": 10
            },
            "failure_percentages": {
                "clarification_needed": 55.6,
                "entity_mapping_failed": 27.8,
                "empty_suggestions": 14.8,
                "pattern_fallback_used": 1.9
            }
        }
    """
    try:
        # Get total queries
        total_result = await db.execute(
            select(func.count(AskAIQueryModel.query_id))
        )
        total_queries = total_result.scalar() or 0
        
        # Get failure reason breakdown
        failure_result = await db.execute(
            select(
                AskAIQueryModel.failure_reason,
                func.count(AskAIQueryModel.query_id).label('count')
            )
            .where(AskAIQueryModel.failure_reason.isnot(None))
            .group_by(AskAIQueryModel.failure_reason)
        )
        failure_breakdown = {row[0]: row[1] for row in failure_result.all()}
        
        # Get success count
        success_result = await db.execute(
            select(func.count(AskAIQueryModel.query_id))
            .where(AskAIQueryModel.failure_reason == 'success')
        )
        success_count = success_result.scalar() or 0
        
        # Calculate failure count (total - success)
        failure_count = total_queries - success_count
        
        # Calculate percentages
        failure_percentages = {}
        if failure_count > 0:
            for reason, count in failure_breakdown.items():
                if reason != 'success':
                    failure_percentages[reason] = round((count / failure_count) * 100, 1)
        
        failure_rate = round((failure_count / total_queries * 100), 1) if total_queries > 0 else 0.0
        
        return {
            "total_queries": total_queries,
            "success_count": success_count,
            "failure_count": failure_count,
            "failure_rate": failure_rate,
            "failure_breakdown": failure_breakdown,
            "failure_percentages": failure_percentages,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get failure stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get failure stats: {str(e)}"
        ) from e

