"""
Model Comparison Router

Epic 39, Story 39.13: Router Modularization
Extracted from ask_ai_router.py for better organization.
Handles model comparison metrics and summary endpoints.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...database.models import ModelComparisonMetrics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ask-ai/model-comparison", tags=["Model Comparison"])


@router.get("/metrics")
async def get_model_comparison_metrics(
    task_type: str | None = Query(None, description="Filter by task type: 'suggestion' or 'yaml'"),
    days: int = Query(7, ge=1, le=30, description="Number of days to look back"),
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Get model comparison metrics for parallel testing.
    
    Returns aggregated metrics comparing model performance, cost, and quality.
    """
    try:
        # Build query
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = select(ModelComparisonMetrics).where(
            ModelComparisonMetrics.created_at >= cutoff_date
        )

        if task_type:
            query = query.where(ModelComparisonMetrics.task_type == task_type)

        result = await db.execute(query)
        metrics = result.scalars().all()

        if not metrics:
            return {
                "total_comparisons": 0,
                "task_type": task_type or "all",
                "days": days,
                "summary": {},
                "model_stats": {}
            }

        # Aggregate statistics
        total_comparisons = len(metrics)
        model1_total_cost = sum(m.model1_cost_usd for m in metrics)
        model2_total_cost = sum(m.model2_cost_usd for m in metrics)
        model1_avg_latency = sum(m.model1_latency_ms for m in metrics) / total_comparisons
        model2_avg_latency = sum(m.model2_latency_ms for m in metrics) / total_comparisons

        # Quality metrics (only for metrics with approval/validation data)
        model1_approved = sum(1 for m in metrics if m.model1_approved is True)
        model2_approved = sum(1 for m in metrics if m.model2_approved is True)
        model1_yaml_valid = sum(1 for m in metrics if m.model1_yaml_valid is True)
        model2_yaml_valid = sum(1 for m in metrics if m.model2_yaml_valid is True)

        approved_total = sum(1 for m in metrics if m.model1_approved is not None or m.model2_approved is not None)
        yaml_valid_total = sum(1 for m in metrics if m.model1_yaml_valid is not None or m.model2_yaml_valid is not None)

        return {
            "total_comparisons": total_comparisons,
            "task_type": task_type or "all",
            "days": days,
            "summary": {
                "cost_difference_usd": abs(model1_total_cost - model2_total_cost),
                "cost_savings_percentage": ((model2_total_cost - model1_total_cost) / model1_total_cost * 100) if model1_total_cost > 0 else 0,
                "latency_difference_ms": abs(model1_avg_latency - model2_avg_latency),
                "model1_total_cost": round(model1_total_cost, 4),
                "model2_total_cost": round(model2_total_cost, 4),
                "model1_avg_latency_ms": round(model1_avg_latency, 2),
                "model2_avg_latency_ms": round(model2_avg_latency, 2)
            },
            "model_stats": {
                "model1": {
                    "name": metrics[0].model1_name if metrics else "unknown",
                    "total_cost_usd": round(model1_total_cost, 4),
                    "avg_cost_per_comparison": round(model1_total_cost / total_comparisons, 4),
                    "avg_latency_ms": round(model1_avg_latency, 2),
                    "approval_rate": round(model1_approved / approved_total * 100, 2) if approved_total > 0 else None,
                    "yaml_validation_rate": round(model1_yaml_valid / yaml_valid_total * 100, 2) if yaml_valid_total > 0 else None
                },
                "model2": {
                    "name": metrics[0].model2_name if metrics else "unknown",
                    "total_cost_usd": round(model2_total_cost, 4),
                    "avg_cost_per_comparison": round(model2_total_cost / total_comparisons, 4),
                    "avg_latency_ms": round(model2_avg_latency, 2),
                    "approval_rate": round(model2_approved / approved_total * 100, 2) if approved_total > 0 else None,
                    "yaml_validation_rate": round(model2_yaml_valid / yaml_valid_total * 100, 2) if yaml_valid_total > 0 else None
                }
            }
        }
    except Exception as e:
        logger.error(f"Error fetching model comparison metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/summary")
async def get_model_comparison_summary(
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Get summary of model comparison results with recommendations.
    
    Returns high-level summary and recommendations for which model performs better.
    """
    try:
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=30)

        query = select(ModelComparisonMetrics).where(
            ModelComparisonMetrics.created_at >= cutoff_date
        )
        result = await db.execute(query)
        metrics = result.scalars().all()

        if not metrics:
            return {
                "message": "No model comparison data available",
                "recommendation": "Start parallel testing to collect comparison data"
            }

        # Aggregate metrics
        total = len(metrics)
        model1_wins = sum(1 for m in metrics if m.model1_approved is True and (m.model2_approved is None or m.model2_approved is False))
        model2_wins = sum(1 for m in metrics if m.model2_approved is True and (m.model1_approved is None or m.model1_approved is False))
        
        model1_cost = sum(m.model1_cost_usd for m in metrics)
        model2_cost = sum(m.model2_cost_usd for m in metrics)
        model1_latency = sum(m.model1_latency_ms for m in metrics) / total
        model2_latency = sum(m.model2_latency_ms for m in metrics) / total

        # Generate recommendation
        recommendation = {
            "model1_name": metrics[0].model1_name if metrics else "Model 1",
            "model2_name": metrics[0].model2_name if metrics else "Model 2",
            "preferred_model": None,
            "reason": ""
        }

        if model1_wins > model2_wins and model1_cost < model2_cost:
            recommendation["preferred_model"] = recommendation["model1_name"]
            recommendation["reason"] = "Better approval rate and lower cost"
        elif model2_wins > model1_wins and model2_cost < model1_cost:
            recommendation["preferred_model"] = recommendation["model2_name"]
            recommendation["reason"] = "Better approval rate and lower cost"
        elif model1_latency < model2_latency:
            recommendation["preferred_model"] = recommendation["model1_name"]
            recommendation["reason"] = "Lower latency"
        else:
            recommendation["preferred_model"] = recommendation["model2_name"]
            recommendation["reason"] = "Lower latency"

        return {
            "total_comparisons": total,
            "model1_wins": model1_wins,
            "model2_wins": model2_wins,
            "cost_comparison": {
                "model1_total_usd": round(model1_cost, 4),
                "model2_total_usd": round(model2_cost, 4),
                "savings_usd": round(abs(model1_cost - model2_cost), 4)
            },
            "latency_comparison": {
                "model1_avg_ms": round(model1_latency, 2),
                "model2_avg_ms": round(model2_latency, 2),
                "difference_ms": round(abs(model1_latency - model2_latency), 2)
            },
            "recommendation": recommendation
        }
    except Exception as e:
        logger.error(f"Error getting model comparison summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e

