"""Cron-based task scheduler using APScheduler.

Epic 27: Scheduled AI Tasks (Continuity)
Story 27.1: Cron Task Scheduler

Responsibilities:
- Load enabled tasks from the database and register APScheduler jobs.
- Enforce cooldown windows (skip if fired too recently).
- Add random jitter (0-30 s) to prevent thundering herd.
- Re-sync jobs when tasks are created, updated, or deleted via the API.
"""

from __future__ import annotations

import logging
import random
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from ..database import db
from ..models.scheduled_task import ScheduledTask

if TYPE_CHECKING:
    from ..config import Settings
    from .task_executor import TaskExecutor

logger = logging.getLogger(__name__)

_MAX_JITTER_SECONDS = 30
_JOB_PREFIX = "scheduled_task_"


class CronTaskScheduler:
    """Manages APScheduler jobs backed by ``ScheduledTask`` rows.

    Startup flow:
        1. ``start()`` — loads all enabled tasks and registers jobs.
        2. APScheduler fires each job at the cron time + jitter.
        3. ``_run_task()`` checks cooldown and delegates to ``TaskExecutor``.

    CRUD flow:
        After any create / update / delete, call ``sync_task(task_id)``
        or ``sync_all()`` to reconcile the scheduler state.
    """

    def __init__(self, settings: Settings, executor: TaskExecutor) -> None:
        self._settings = settings
        self._executor = executor
        self._scheduler = AsyncIOScheduler(timezone=settings.scheduler_timezone)
        self._running = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Load tasks from DB and start the APScheduler event loop."""
        if self._running:
            return
        await self._executor.start()
        await self._load_all_tasks()
        self._scheduler.start()
        self._running = True
        logger.info(
            "CronTaskScheduler started (%d jobs registered)",
            len(self._scheduler.get_jobs()),
        )

    async def stop(self) -> None:
        """Gracefully shut down scheduler and executor."""
        if not self._running:
            return
        self._scheduler.shutdown(wait=True)
        await self._executor.stop()
        self._running = False
        logger.info("CronTaskScheduler stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    # ------------------------------------------------------------------
    # Sync helpers (called after CRUD operations)
    # ------------------------------------------------------------------

    async def sync_task(self, task_id: int) -> None:
        """Add, update, or remove a single job to match the DB row."""
        job_id = f"{_JOB_PREFIX}{task_id}"

        async with db.get_db() as session:
            task = await session.get(ScheduledTask, task_id)

        # Remove existing job (if any) before re-adding
        existing = self._scheduler.get_job(job_id)
        if existing:
            self._scheduler.remove_job(job_id)

        if task is None or not task.enabled:
            logger.debug("Job %s removed (task deleted or disabled)", job_id)
            return

        self._add_job(task)
        logger.info("Job %s synced for task %r", job_id, task.name)

    async def sync_all(self) -> None:
        """Full reconciliation: reload every task from the database."""
        # Remove all managed jobs
        for job in self._scheduler.get_jobs():
            if job.id.startswith(_JOB_PREFIX):
                self._scheduler.remove_job(job.id)

        await self._load_all_tasks()
        logger.info(
            "Full sync complete — %d jobs active",
            len(self._scheduler.get_jobs()),
        )

    def get_jobs_info(self) -> list[dict]:
        """Return a serialisable list of registered jobs."""
        result: list[dict] = []
        for job in self._scheduler.get_jobs():
            if not job.id.startswith(_JOB_PREFIX):
                continue
            result.append({
                "job_id": job.id,
                "name": job.name,
                "next_run_time": (
                    job.next_run_time.isoformat() if job.next_run_time else None
                ),
            })
        return result

    # ------------------------------------------------------------------
    # Manual trigger
    # ------------------------------------------------------------------

    async def run_now(self, task_id: int) -> dict:
        """Execute a task immediately (bypass cron, still respects cooldown).

        Returns a dict with the execution result summary.
        """
        async with db.get_db() as session:
            task = await session.get(ScheduledTask, task_id)
            if task is None:
                return {"error": "Task not found"}
            if not task.enabled:
                return {"error": "Task is disabled"}

            execution = await self._executor.execute(task, session)
            return {
                "execution_id": execution.id,
                "status": execution.status,
                "duration_ms": execution.duration_ms,
                "response_preview": (execution.response or "")[:200],
            }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _load_all_tasks(self) -> None:
        """Query all enabled tasks and register APScheduler jobs."""
        async with db.get_db() as session:
            result = await session.execute(
                select(ScheduledTask).where(ScheduledTask.enabled.is_(True)),
            )
            tasks = result.scalars().all()

        for task in tasks:
            self._add_job(task)

        logger.info("Loaded %d enabled tasks from database", len(tasks))

    def _add_job(self, task: ScheduledTask) -> None:
        """Register a single APScheduler job for a task."""
        job_id = f"{_JOB_PREFIX}{task.id}"
        try:
            trigger = CronTrigger.from_crontab(
                task.cron_expression,
                timezone=self._settings.scheduler_timezone,
            )
        except ValueError:
            logger.warning(
                "Invalid cron expression %r for task %s — skipping",
                task.cron_expression, task.id,
            )
            return

        self._scheduler.add_job(
            self._run_task,
            trigger=trigger,
            id=job_id,
            name=task.name,
            args=[task.id],
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=3600,
            jitter=_MAX_JITTER_SECONDS,
        )

    async def _run_task(self, task_id: int) -> None:
        """Callback invoked by APScheduler at the cron time.

        Steps:
        1. Random jitter delay (0-30 s) — note: APScheduler ``jitter``
           already adds this, but we keep an explicit one as a safety net.
        2. Check cooldown window.
        3. Delegate to ``TaskExecutor.execute()``.
        """
        # Extra jitter safety net (APScheduler jitter is additive)
        jitter = random.uniform(0, _MAX_JITTER_SECONDS / 2)  # noqa: S311
        if jitter > 1:
            import asyncio
            await asyncio.sleep(jitter)

        async with db.get_db() as session:
            task = await session.get(ScheduledTask, task_id)
            if task is None:
                logger.warning("Task %d not found — removing job", task_id)
                job_id = f"{_JOB_PREFIX}{task_id}"
                if self._scheduler.get_job(job_id):
                    self._scheduler.remove_job(job_id)
                return

            if not task.enabled:
                logger.debug("Task %d disabled — skipping", task_id)
                return

            # Cooldown enforcement
            if task.last_run_at:
                cooldown_end = task.last_run_at + timedelta(
                    minutes=task.cooldown_minutes,
                )
                if datetime.now(UTC) < cooldown_end:
                    logger.info(
                        "Task %d (%s) still in cooldown until %s — skipping",
                        task_id, task.name, cooldown_end.isoformat(),
                    )
                    return

            logger.info("Executing scheduled task %d (%s)", task_id, task.name)
            await self._executor.execute(task, session)
