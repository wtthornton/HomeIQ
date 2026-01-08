"""
Execution Tracking API Routes

Provides endpoints for tracking and querying automation executions.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .execution_tracker import ExecutionTracker, ExecutionStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tracking", tags=["tracking"])

# Global instance (in production, use dependency injection)
execution_tracker = ExecutionTracker(retention_days=90)


# Request/Response Models
class RecordExecutionRequest(BaseModel):
    """Request model for recording execution."""
    
    automation_id: str = Field(..., description="Home Assistant automation entity ID")
    execution_id: str = Field(..., description="Unique execution identifier")
    status: str = Field(..., description="Execution status (success, failure, timeout, partial, skipped)")
    execution_time_ms: int | None = Field(None, description="Execution time in milliseconds")
    error_message: str | None = Field(None, description="Error message if failed")
    error_type: str | None = Field(None, description="Error type classification")
    trigger_type: str | None = Field(None, description="Trigger type (state, time, event)")
    trigger_entity: str | None = Field(None, description="Entity that triggered automation")
    actions_total: int = Field(0, description="Total actions in automation")
    actions_succeeded: int = Field(0, description="Successful actions")
    actions_failed: int = Field(0, description="Failed actions")
    synergy_id: str | None = Field(None, description="Synergy ID if applicable")
    blueprint_id: str | None = Field(None, description="Blueprint ID if applicable")


class ExecutionRecordResponse(BaseModel):
    """Response model for execution record."""
    
    automation_id: str
    execution_id: str
    status: str
    execution_time_ms: int | None
    success_rate: float


class SuccessRateResponse(BaseModel):
    """Response model for success rate."""
    
    period_days: int
    total_executions: int
    successful: int
    failed: int
    success_rate: float
    target: float
    achieved: bool
    progress_pct: float


class AutomationStatsResponse(BaseModel):
    """Response model for automation statistics."""
    
    automation_id: str
    total_executions: int
    successful_executions: int
    failed_executions: int
    success_rate: float
    avg_execution_time_ms: float
    last_error: str | None


class ProblematicAutomationResponse(BaseModel):
    """Response model for problematic automation."""
    
    automation_id: str
    total_executions: int
    success_rate: float
    last_error: str | None
    last_error_at: str | None


@router.post("/executions", response_model=ExecutionRecordResponse)
async def record_execution(request: RecordExecutionRequest) -> ExecutionRecordResponse:
    """
    Record an automation execution.
    """
    try:
        status = ExecutionStatus(request.status)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status: {request.status}. Valid values: {[s.value for s in ExecutionStatus]}",
        )
    
    record = execution_tracker.record_execution(
        automation_id=request.automation_id,
        execution_id=request.execution_id,
        status=status,
        execution_time_ms=request.execution_time_ms,
        error_message=request.error_message,
        error_type=request.error_type,
        trigger_type=request.trigger_type,
        trigger_entity=request.trigger_entity,
        actions_total=request.actions_total,
        actions_succeeded=request.actions_succeeded,
        actions_failed=request.actions_failed,
        synergy_id=request.synergy_id,
        blueprint_id=request.blueprint_id,
    )
    
    return ExecutionRecordResponse(
        automation_id=record.automation_id,
        execution_id=record.execution_id,
        status=record.status.value,
        execution_time_ms=record.execution_time_ms,
        success_rate=record.success_rate,
    )


@router.get("/success-rate", response_model=SuccessRateResponse)
async def get_success_rate(
    days: int = Query(default=30, ge=1, le=365),
) -> SuccessRateResponse:
    """
    Get overall success rate.
    
    Target: 85% (from RECOMMENDATIONS_FEASIBILITY_ANALYSIS.md)
    """
    summary = execution_tracker.get_overall_success_rate(days=days)
    return SuccessRateResponse(**summary)


@router.get("/automation/{automation_id}/stats", response_model=AutomationStatsResponse)
async def get_automation_stats(automation_id: str) -> AutomationStatsResponse:
    """
    Get statistics for a specific automation.
    """
    stats = execution_tracker.get_automation_stats(automation_id)
    
    if not stats:
        raise HTTPException(
            status_code=404,
            detail=f"No statistics found for automation {automation_id}",
        )
    
    return AutomationStatsResponse(
        automation_id=stats.automation_id,
        total_executions=stats.total_executions,
        successful_executions=stats.successful_executions,
        failed_executions=stats.failed_executions,
        success_rate=stats.success_rate,
        avg_execution_time_ms=stats.avg_execution_time_ms,
        last_error=stats.last_error,
    )


@router.get("/automation/{automation_id}/success-rate")
async def get_automation_success_rate(automation_id: str) -> dict[str, Any]:
    """
    Get success rate for a specific automation.
    """
    success_rate = execution_tracker.get_automation_success_rate(automation_id)
    
    if success_rate is None:
        raise HTTPException(
            status_code=404,
            detail=f"No executions found for automation {automation_id}",
        )
    
    return {
        "automation_id": automation_id,
        "success_rate": success_rate,
        "target": 85.0,
        "achieved": success_rate >= 85.0,
    }


@router.get("/synergy/{synergy_id}/success-rate")
async def get_synergy_success_rate(synergy_id: str) -> dict[str, Any]:
    """
    Get success rate for automations from a synergy.
    """
    success_rate = execution_tracker.get_synergy_success_rate(synergy_id)
    
    if success_rate is None:
        raise HTTPException(
            status_code=404,
            detail=f"No executions found for synergy {synergy_id}",
        )
    
    return {
        "synergy_id": synergy_id,
        "success_rate": success_rate,
        "target": 85.0,
        "achieved": success_rate >= 85.0,
    }


@router.get("/errors")
async def get_error_summary(
    days: int = Query(default=30, ge=1, le=365),
) -> dict[str, Any]:
    """
    Get summary of errors for the period.
    """
    return execution_tracker.get_error_summary(days=days)


@router.get("/performance")
async def get_performance_summary(
    days: int = Query(default=30, ge=1, le=365),
) -> dict[str, Any]:
    """
    Get performance summary for the period.
    """
    return execution_tracker.get_performance_summary(days=days)


@router.get("/problematic", response_model=list[ProblematicAutomationResponse])
async def get_problematic_automations(
    min_executions: int = Query(default=5, ge=1),
    max_success_rate: float = Query(default=80.0, ge=0.0, le=100.0),
) -> list[ProblematicAutomationResponse]:
    """
    Get automations with low success rates.
    
    These automations may need attention or should be disabled.
    """
    problematic = execution_tracker.get_problematic_automations(
        min_executions=min_executions,
        max_success_rate=max_success_rate,
    )
    
    return [
        ProblematicAutomationResponse(
            automation_id=p["automation_id"],
            total_executions=p["total_executions"],
            success_rate=p["success_rate"],
            last_error=p["last_error"],
            last_error_at=p["last_error_at"],
        )
        for p in problematic
    ]


@router.post("/cleanup")
async def cleanup_old_records(
    retention_days: int = Query(default=90, ge=30, le=365),
) -> dict[str, Any]:
    """
    Clean up old execution records.
    """
    removed = execution_tracker.cleanup_old_records()
    
    return {
        "status": "cleaned",
        "records_removed": removed,
    }


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """
    Check tracking service health.
    """
    summary = execution_tracker.get_overall_success_rate(days=1)
    
    return {
        "status": "healthy",
        "executions_24h": summary["total_executions"],
        "success_rate_24h": summary["success_rate"],
        "target_achieved": summary["achieved"],
    }
