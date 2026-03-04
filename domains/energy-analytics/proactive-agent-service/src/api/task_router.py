"""REST API for scheduled task CRUD and execution.

Epic 27: Scheduled AI Tasks (Continuity)
Stories 27.1 - 27.3

Endpoints:
    GET    /api/v1/tasks              -- list tasks
    POST   /api/v1/tasks              -- create task
    GET    /api/v1/tasks/{id}         -- get task
    PUT    /api/v1/tasks/{id}         -- update task
    DELETE /api/v1/tasks/{id}         -- delete task
    PATCH  /api/v1/tasks/{id}/toggle  -- enable/disable
    POST   /api/v1/tasks/{id}/run     -- run now
    GET    /api/v1/tasks/{id}/history -- execution history
    GET    /api/v1/tasks/templates    -- built-in templates
    POST   /api/v1/tasks/templates/{template_id}/install -- install template
    GET    /api/v1/tasks/scheduler/status -- scheduler status
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func, select

from ..database import get_db

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
from ..models.scheduled_task import ScheduledTask, TaskExecution
from ..services.task_templates import BUILT_IN_TEMPLATES, get_template
from .task_schemas import (
    ExecutionListResponse,
    ExecutionResponse,
    SchedulerStatusResponse,
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    TaskUpdate,
    TemplateResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/tasks", tags=["scheduled-tasks"])

# Scheduler reference (set by main.py at startup)
_cron_scheduler = None


def set_cron_scheduler(scheduler) -> None:  # noqa: ANN001
    """Wire the CronTaskScheduler instance (called from main.py)."""
    global _cron_scheduler  # noqa: PLW0603
    _cron_scheduler = scheduler


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    enabled: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> TaskListResponse:
    """List all scheduled tasks with optional enabled filter."""
    stmt = select(ScheduledTask)
    count_stmt = select(func.count(ScheduledTask.id))

    if enabled is not None:
        stmt = stmt.where(ScheduledTask.enabled == enabled)
        count_stmt = count_stmt.where(ScheduledTask.enabled == enabled)

    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0

    stmt = stmt.order_by(ScheduledTask.created_at.desc()).offset(offset).limit(limit)
    result = await session.execute(stmt)
    tasks = result.scalars().all()

    return TaskListResponse(
        tasks=[TaskResponse.model_validate(t) for t in tasks],
        total=total,
    )


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    body: TaskCreate,
    session: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Create a new scheduled task."""
    task = ScheduledTask(
        name=body.name,
        cron_expression=body.cron_expression,
        prompt=body.prompt,
        enabled=body.enabled,
        notification_preference=body.notification_preference,
        cooldown_minutes=body.cooldown_minutes,
        max_execution_seconds=body.max_execution_seconds,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)

    if _cron_scheduler:
        await _cron_scheduler.sync_task(task.id)

    logger.info("Created scheduled task %d: %s", task.id, task.name)
    return TaskResponse.model_validate(task)


@router.get("/templates", response_model=list[TemplateResponse])
async def list_templates() -> list[TemplateResponse]:
    """List available built-in task templates."""
    return [
        TemplateResponse(
            id=t.id,
            name=t.name,
            cron_expression=t.cron_expression,
            prompt=t.prompt,
            notification_preference=t.notification_preference,
            cooldown_minutes=t.cooldown_minutes,
            max_execution_seconds=t.max_execution_seconds,
            description=t.description,
        )
        for t in BUILT_IN_TEMPLATES
    ]


@router.post(
    "/templates/{template_id}/install",
    response_model=TaskResponse,
    status_code=201,
)
async def install_template(
    template_id: str,
    session: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Install a built-in template as a new scheduled task."""
    template = get_template(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")

    existing = await session.execute(
        select(ScheduledTask).where(ScheduledTask.template_id == template_id),
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=409,
            detail=f"Template '{template_id}' is already installed",
        )

    task = ScheduledTask(
        name=template.name,
        cron_expression=template.cron_expression,
        prompt=template.prompt,
        enabled=True,
        notification_preference=template.notification_preference,
        cooldown_minutes=template.cooldown_minutes,
        max_execution_seconds=template.max_execution_seconds,
        is_template=True,
        template_id=template_id,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)

    if _cron_scheduler:
        await _cron_scheduler.sync_task(task.id)

    logger.info("Installed template '%s' as task %d", template_id, task.id)
    return TaskResponse.model_validate(task)


@router.get("/scheduler/status", response_model=SchedulerStatusResponse)
async def scheduler_status() -> SchedulerStatusResponse:
    """Get current scheduler status and registered jobs."""
    if _cron_scheduler is None:
        return SchedulerStatusResponse(running=False, jobs=[])
    return SchedulerStatusResponse(
        running=_cron_scheduler.is_running,
        jobs=_cron_scheduler.get_jobs_info(),
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    session: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Get a scheduled task by ID."""
    task = await session.get(ScheduledTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse.model_validate(task)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    body: TaskUpdate,
    session: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Update a scheduled task."""
    task = await session.get(ScheduledTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(task, field, value)

    await session.commit()
    await session.refresh(task)

    if _cron_scheduler:
        await _cron_scheduler.sync_task(task.id)

    logger.info("Updated scheduled task %d: %s", task.id, task.name)
    return TaskResponse.model_validate(task)


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: int,
    session: AsyncSession = Depends(get_db),
) -> None:
    """Delete a scheduled task and all its execution history."""
    task = await session.get(ScheduledTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    await session.execute(
        delete(TaskExecution).where(TaskExecution.task_id == task_id),
    )
    await session.delete(task)
    await session.commit()

    if _cron_scheduler:
        await _cron_scheduler.sync_task(task_id)

    logger.info("Deleted scheduled task %d", task_id)


@router.patch("/{task_id}/toggle", response_model=TaskResponse)
async def toggle_task(
    task_id: int,
    session: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Toggle enabled/disabled state of a scheduled task."""
    task = await session.get(ScheduledTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    task.enabled = not task.enabled
    await session.commit()
    await session.refresh(task)

    if _cron_scheduler:
        await _cron_scheduler.sync_task(task.id)

    state = "enabled" if task.enabled else "disabled"
    logger.info("Task %d (%s) %s", task.id, task.name, state)
    return TaskResponse.model_validate(task)


@router.post("/{task_id}/run")
async def run_task_now(task_id: int) -> dict:
    """Manually trigger a task execution (bypasses cron schedule)."""
    if _cron_scheduler is None:
        raise HTTPException(status_code=503, detail="Scheduler not initialized")

    result = await _cron_scheduler.run_now(task_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/{task_id}/history", response_model=ExecutionListResponse)
async def get_task_history(
    task_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> ExecutionListResponse:
    """Get execution history for a scheduled task."""
    task = await session.get(ScheduledTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    stmt = select(TaskExecution).where(TaskExecution.task_id == task_id)
    count_stmt = select(func.count(TaskExecution.id)).where(
        TaskExecution.task_id == task_id,
    )

    if status:
        stmt = stmt.where(TaskExecution.status == status)
        count_stmt = count_stmt.where(TaskExecution.status == status)

    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0

    stmt = (
        stmt.order_by(TaskExecution.started_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(stmt)
    executions = result.scalars().all()

    return ExecutionListResponse(
        executions=[ExecutionResponse.model_validate(e) for e in executions],
        total=total,
    )
