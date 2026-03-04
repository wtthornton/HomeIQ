"""SQLAlchemy models for scheduled tasks and execution history.

Epic 27: Scheduled AI Tasks (Continuity)
Story 27.1 / 27.2
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class ScheduledTask(Base):
    """A user-defined task that runs on a cron schedule.

    Each task stores a prompt that is sent to ha-ai-agent-service for
    execution.  Cooldown enforcement prevents re-fire within a window,
    and jitter (0-30 s) is added at trigger time to avoid thundering herd.
    """

    __tablename__ = "scheduled_tasks"
    __table_args__ = {"schema": "energy"}

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    cron_expression: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    notification_preference: Mapped[str] = mapped_column(
        String(20), default="never", nullable=False,
    )  # always / on_alert / never
    cooldown_minutes: Mapped[int] = mapped_column(default=60, nullable=False)
    max_execution_seconds: Mapped[int] = mapped_column(default=120, nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    next_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    run_count: Mapped[int] = mapped_column(default=0, nullable=False)
    is_template: Mapped[bool] = mapped_column(default=False, nullable=False)
    template_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    executions: Mapped[list[TaskExecution]] = relationship(
        "TaskExecution", back_populates="task", cascade="all, delete-orphan",
        order_by="TaskExecution.started_at.desc()",
    )

    def __repr__(self) -> str:
        return (
            f"<ScheduledTask(id={self.id}, name={self.name!r}, "
            f"cron={self.cron_expression!r}, enabled={self.enabled})>"
        )


class TaskExecution(Base):
    """Record of a single execution of a scheduled task."""

    __tablename__ = "task_executions"
    __table_args__ = {"schema": "energy"}

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("energy.scheduled_tasks.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20), default="running", nullable=False,
    )  # running / completed / failed / timeout
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str | None] = mapped_column(Text, nullable=True)
    tools_used: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(nullable=True)
    notification_sent: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Relationships
    task: Mapped[ScheduledTask] = relationship(
        "ScheduledTask", back_populates="executions",
    )

    def __repr__(self) -> str:
        return (
            f"<TaskExecution(id={self.id}, task_id={self.task_id}, "
            f"status={self.status!r})>"
        )


# Composite indexes for query performance
Index("idx_sched_tasks_enabled", ScheduledTask.enabled)
Index(
    "idx_sched_tasks_next_run",
    ScheduledTask.enabled,
    ScheduledTask.next_run_at,
)
Index(
    "idx_task_exec_task_started",
    TaskExecution.task_id,
    TaskExecution.started_at,
)
Index("idx_task_exec_status", TaskExecution.status)
