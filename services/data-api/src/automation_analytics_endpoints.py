"""
Automation analytics endpoints — query automation performance,
frequency, errors, and improvement opportunities.

All data sourced from SQLite (automations + automation_executions tables)
with optional InfluxDB queries for time-series aggregation.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db
from .models import Automation, AutomationExecution

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/automations")


@router.get("")
async def list_automations(
    enabled_only: bool = Query(False, description="Filter to enabled automations only"),
    sort_by: str = Query("alias", description="Sort field: alias, total_executions, success_rate, last_triggered"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """List all automations with summary stats."""
    query = select(Automation)
    if enabled_only:
        query = query.where(Automation.enabled.is_(True))

    sort_map = {
        "alias": Automation.alias,
        "total_executions": desc(Automation.total_executions),
        "success_rate": Automation.success_rate,
        "last_triggered": desc(Automation.last_triggered),
        "errors": desc(Automation.total_errors),
    }
    query = query.order_by(sort_map.get(sort_by, Automation.alias)).limit(limit)

    result = await db.execute(query)
    automations = result.scalars().all()

    return {
        "count": len(automations),
        "automations": [_automation_to_dict(a) for a in automations],
    }


@router.get("/stats/overview")
async def stats_overview(
    db: AsyncSession = Depends(get_db),
):
    """Dashboard overview: totals, error rate, top failures."""
    result = await db.execute(
        select(
            func.count(Automation.automation_id).label("total_automations"),
            func.sum(Automation.total_executions).label("total_executions"),
            func.sum(Automation.total_errors).label("total_errors"),
            func.avg(Automation.success_rate).label("avg_success_rate"),
            func.avg(Automation.avg_duration_seconds).label("avg_duration"),
        ).where(Automation.enabled.is_(True))
    )
    row = result.one()

    total_exec = row.total_executions or 0
    total_err = row.total_errors or 0
    error_rate = (total_err / total_exec * 100) if total_exec > 0 else 0

    # Top 5 most error-prone
    error_result = await db.execute(
        select(Automation)
        .where(Automation.total_errors > 0)
        .order_by(desc(Automation.total_errors))
        .limit(5)
    )
    top_errors = error_result.scalars().all()

    # Top 5 most active
    active_result = await db.execute(
        select(Automation)
        .where(Automation.total_executions > 0)
        .order_by(desc(Automation.total_executions))
        .limit(5)
    )
    top_active = active_result.scalars().all()

    return {
        "total_automations": row.total_automations or 0,
        "total_executions": total_exec,
        "total_errors": total_err,
        "error_rate_percent": round(error_rate, 1),
        "avg_success_rate": round(row.avg_success_rate or 0, 1),
        "avg_duration_seconds": round(row.avg_duration or 0, 3),
        "top_errors": [_automation_to_dict(a) for a in top_errors],
        "top_active": [_automation_to_dict(a) for a in top_active],
    }


@router.get("/stats/errors")
async def stats_errors(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Automations sorted by error count."""
    result = await db.execute(
        select(Automation)
        .where(Automation.total_errors > 0)
        .order_by(desc(Automation.total_errors))
        .limit(limit)
    )
    automations = result.scalars().all()
    return {"count": len(automations), "automations": [_automation_to_dict(a) for a in automations]}


@router.get("/stats/slow")
async def stats_slow(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Slowest automations by average duration."""
    result = await db.execute(
        select(Automation)
        .where(Automation.avg_duration_seconds > 0)
        .order_by(desc(Automation.avg_duration_seconds))
        .limit(limit)
    )
    automations = result.scalars().all()
    return {"count": len(automations), "automations": [_automation_to_dict(a) for a in automations]}


@router.get("/stats/inactive")
async def stats_inactive(
    days: int = Query(30, ge=1, le=365, description="Inactivity threshold in days"),
    db: AsyncSession = Depends(get_db),
):
    """Automations that haven't run in N days."""
    threshold = datetime.utcnow() - timedelta(days=days)
    result = await db.execute(
        select(Automation)
        .where(
            Automation.enabled.is_(True),
            (Automation.last_triggered < threshold) | (Automation.last_triggered.is_(None)),
        )
        .order_by(Automation.last_triggered)
    )
    automations = result.scalars().all()
    return {
        "threshold_days": days,
        "count": len(automations),
        "automations": [_automation_to_dict(a) for a in automations],
    }


@router.get("/{automation_id}")
async def get_automation(
    automation_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get single automation detail with recent executions."""
    result = await db.execute(
        select(Automation).where(Automation.automation_id == automation_id)
    )
    automation = result.scalar_one_or_none()
    if not automation:
        raise HTTPException(status_code=404, detail=f"Automation '{automation_id}' not found")

    # Recent executions
    exec_result = await db.execute(
        select(AutomationExecution)
        .where(AutomationExecution.automation_id == automation_id)
        .order_by(desc(AutomationExecution.started_at))
        .limit(20)
    )
    executions = exec_result.scalars().all()

    data = _automation_to_dict(automation)
    data["recent_executions"] = [_execution_to_dict(e) for e in executions]
    return data


@router.get("/{automation_id}/executions")
async def list_executions(
    automation_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    result_filter: str | None = Query(None, description="Filter by execution_result"),
    db: AsyncSession = Depends(get_db),
):
    """Paginated execution history for an automation."""
    query = (
        select(AutomationExecution)
        .where(AutomationExecution.automation_id == automation_id)
    )
    if result_filter:
        query = query.where(AutomationExecution.execution_result == result_filter)

    query = query.order_by(desc(AutomationExecution.started_at)).offset(offset).limit(limit)

    result = await db.execute(query)
    executions = result.scalars().all()

    # Get total count
    count_query = select(func.count(AutomationExecution.id)).where(
        AutomationExecution.automation_id == automation_id
    )
    if result_filter:
        count_query = count_query.where(AutomationExecution.execution_result == result_filter)
    total = (await db.execute(count_query)).scalar() or 0

    return {
        "automation_id": automation_id,
        "total": total,
        "offset": offset,
        "limit": limit,
        "executions": [_execution_to_dict(e) for e in executions],
    }


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def _automation_to_dict(a: Automation) -> dict[str, Any]:
    return {
        "automation_id": a.automation_id,
        "alias": a.alias,
        "description": a.description,
        "mode": a.mode,
        "enabled": a.enabled,
        "total_executions": a.total_executions or 0,
        "total_errors": a.total_errors or 0,
        "avg_duration_seconds": a.avg_duration_seconds or 0,
        "success_rate": a.success_rate or 0,
        "last_triggered": a.last_triggered.isoformat() if a.last_triggered else None,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }


def _execution_to_dict(e: AutomationExecution) -> dict[str, Any]:
    return {
        "id": e.id,
        "automation_id": e.automation_id,
        "run_id": e.run_id,
        "started_at": e.started_at.isoformat() if e.started_at else None,
        "finished_at": e.finished_at.isoformat() if e.finished_at else None,
        "duration_seconds": e.duration_seconds,
        "execution_result": e.execution_result,
        "trigger_type": e.trigger_type,
        "trigger_entity": e.trigger_entity,
        "error_message": e.error_message,
        "step_count": e.step_count,
        "last_step": e.last_step,
        "context_id": e.context_id,
    }
