"""Pydantic schemas for scheduled task API.

Epic 27: Scheduled AI Tasks (Continuity)
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

_CRON_FIELD_COUNT = 5


class TaskCreate(BaseModel):
    """Request body for creating a scheduled task."""

    name: str = Field(..., min_length=1, max_length=255)
    cron_expression: str = Field(..., min_length=5, max_length=100)
    prompt: str = Field(..., min_length=1, max_length=5000)
    enabled: bool = True
    notification_preference: str = Field(
        default="never", pattern=r"^(always|on_alert|never)$",
    )
    cooldown_minutes: int = Field(default=60, ge=0, le=10080)
    max_execution_seconds: int = Field(default=120, ge=10, le=600)

    @field_validator("cron_expression")
    @classmethod
    def validate_cron(cls, v: str) -> str:
        """Validate standard 5-field cron expression."""
        v = v.strip()
        parts = v.split()
        if len(parts) != _CRON_FIELD_COUNT:
            msg = "Cron expression must have exactly 5 fields (min hour dom month dow)"
            raise ValueError(msg)
        return v


class TaskUpdate(BaseModel):
    """Request body for updating a scheduled task."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    cron_expression: str | None = Field(default=None, min_length=5, max_length=100)
    prompt: str | None = Field(default=None, min_length=1, max_length=5000)
    enabled: bool | None = None
    notification_preference: str | None = Field(
        default=None, pattern=r"^(always|on_alert|never)$",
    )
    cooldown_minutes: int | None = Field(default=None, ge=0, le=10080)
    max_execution_seconds: int | None = Field(default=None, ge=10, le=600)

    @field_validator("cron_expression")
    @classmethod
    def validate_cron(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        parts = v.split()
        if len(parts) != _CRON_FIELD_COUNT:
            msg = "Cron expression must have exactly 5 fields"
            raise ValueError(msg)
        return v


class TaskResponse(BaseModel):
    """Serialised scheduled task."""

    id: int
    name: str
    cron_expression: str
    prompt: str
    enabled: bool
    notification_preference: str
    cooldown_minutes: int
    max_execution_seconds: int
    last_run_at: datetime | None
    next_run_at: datetime | None
    run_count: int
    is_template: bool
    template_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ExecutionResponse(BaseModel):
    """Serialised task execution record."""

    id: int
    task_id: int
    started_at: datetime
    completed_at: datetime | None
    status: str
    prompt: str
    response: str | None
    tools_used: str | None
    error: str | None
    duration_ms: int | None
    notification_sent: bool

    model_config = {"from_attributes": True}


class TemplateResponse(BaseModel):
    """Serialised task template."""

    id: str
    name: str
    cron_expression: str
    prompt: str
    notification_preference: str
    cooldown_minutes: int
    max_execution_seconds: int
    description: str


class TaskListResponse(BaseModel):
    """Paginated task list."""

    tasks: list[TaskResponse]
    total: int


class ExecutionListResponse(BaseModel):
    """Paginated execution history."""

    executions: list[ExecutionResponse]
    total: int


class SchedulerStatusResponse(BaseModel):
    """Scheduler status with job info."""

    running: bool
    jobs: list[dict]
