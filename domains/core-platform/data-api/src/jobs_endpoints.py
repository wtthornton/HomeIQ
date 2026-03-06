"""Job management endpoints for data-api.

Story 31.1: Override Detection
Story 32.1: Consolidation Job Infrastructure
Provides endpoints to monitor and manually trigger background jobs.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/jobs", tags=["Background Jobs"])


class JobStatusResponse(BaseModel):
    """Response model for job scheduler status."""

    running: bool
    apscheduler_available: bool
    jobs: list[dict]
    consolidation: dict | None


class ConsolidationMetricsResponse(BaseModel):
    """Response model for consolidation metrics.

    Story 32.1: Detailed metrics from consolidation runs.
    """

    started_at: str
    completed_at: str | None = None
    memories_created: int = 0
    memories_reinforced: int = 0
    memories_superseded: int = 0
    memories_archived: int = 0
    overrides_detected: int = 0
    patterns_detected: int = 0
    pattern_drifts_detected: int = 0
    contradictions_found: int = 0
    garbage_collected: int = 0
    routines_synthesized: int = 0
    error: str | None = None
    duration_ms: float = 0.0
    success: bool = True


class TriggerResponse(BaseModel):
    """Response model for manual job trigger.

    Story 32.1: Enhanced with full ConsolidationMetrics fields.
    """

    started_at: str | None = None
    completed_at: str | None = None
    memories_created: int = 0
    memories_reinforced: int = 0
    memories_superseded: int = 0
    memories_archived: int = 0
    overrides_detected: int = 0
    patterns_detected: int = 0
    pattern_drifts_detected: int = 0
    contradictions_found: int = 0
    garbage_collected: int = 0
    routines_synthesized: int = 0
    duration_ms: float = 0.0
    error: str | None = None
    success: bool = True


def _get_scheduler():
    """Get the job scheduler from the service instance."""
    from .main import data_api_service

    if data_api_service.job_scheduler is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Job scheduler not initialized. APScheduler may not be installed.",
        )
    return data_api_service.job_scheduler


def _get_consolidation_job():
    """Get the memory consolidation job instance."""
    scheduler = _get_scheduler()
    if not hasattr(scheduler, "consolidation_job") or scheduler.consolidation_job is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Memory consolidation job not initialized.",
        )
    return scheduler.consolidation_job


@router.get("/status", response_model=JobStatusResponse)
async def get_job_status() -> JobStatusResponse:
    """Get background job scheduler status and job information."""
    scheduler = _get_scheduler()
    status_data = scheduler.get_status()
    return JobStatusResponse(**status_data)


@router.post("/consolidation/trigger", response_model=TriggerResponse)
async def trigger_consolidation() -> TriggerResponse:
    """Manually trigger the memory consolidation job.

    This runs the override detection job immediately, outside of its
    normal 6-hour schedule. Useful for testing and debugging.

    Story 32.1: Returns full ConsolidationMetrics.
    """
    scheduler = _get_scheduler()
    result = await scheduler.trigger_consolidation()

    if hasattr(result, "to_dict"):
        return TriggerResponse(**result.to_dict())

    return TriggerResponse(**result)


@router.get("/consolidation/status")
async def get_consolidation_status() -> dict:
    """Get memory consolidation job status and statistics."""
    scheduler = _get_scheduler()
    status_data = scheduler.get_status()

    if status_data.get("consolidation"):
        return status_data["consolidation"]

    return {
        "last_run": None,
        "overrides_detected": 0,
        "memories_created": 0,
        "config": {
            "override_window_minutes": 15,
            "override_threshold": 3,
            "analysis_window_days": 7,
        },
    }


@router.get("/consolidation/metrics", response_model=ConsolidationMetricsResponse | None)
async def get_last_run_metrics() -> ConsolidationMetricsResponse | None:
    """Get detailed metrics from the last consolidation run.

    Story 32.1: Exposes ConsolidationMetrics for observability.

    Returns:
        ConsolidationMetricsResponse with detailed metrics, or None if no runs yet.
    """
    job = _get_consolidation_job()
    metrics = job.get_last_run_metrics()

    if metrics is None:
        return None

    return ConsolidationMetricsResponse(**metrics)


@router.get("/consolidation/metrics/history")
async def get_metrics_history() -> list[dict[str, Any]]:
    """Get metrics history from recent consolidation runs.

    Story 32.1: Enables trend analysis and debugging.

    Returns:
        List of metrics from recent runs, most recent last.
    """
    job = _get_consolidation_job()
    return job.get_metrics_history()
