"""Standard scheduler for HomeIQ services.

Wraps APScheduler's ``AsyncIOScheduler`` with common patterns used
across 11+ services: cron job registration, error handling, graceful
shutdown, and job status tracking.

Usage::

    from homeiq_resilience import ServiceScheduler

    scheduler = ServiceScheduler(service_name="my-service")

    scheduler.add_cron_job(
        func=my_daily_task,
        cron="0 3 * * *",
        job_id="daily-analysis",
        name="Daily Analysis",
    )

    scheduler.start()

    # In shutdown:
    scheduler.stop()
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


class ServiceScheduler:
    """Managed APScheduler wrapper with standard patterns.

    Parameters
    ----------
    service_name:
        Human-readable service name for log messages.
    timezone:
        Timezone string for cron triggers (default UTC).
    """

    def __init__(
        self,
        service_name: str = "",
        *,
        timezone: str = "UTC",
    ) -> None:
        self.service_name = service_name
        self.timezone = timezone
        self._scheduler = AsyncIOScheduler()
        self._is_running = False
        self._job_history: list[dict[str, Any]] = []

    @property
    def is_running(self) -> bool:
        """Whether the scheduler is currently running."""
        return self._is_running

    def add_cron_job(
        self,
        func: Callable[..., Awaitable[Any]],
        cron: str,
        *,
        job_id: str | None = None,
        name: str | None = None,
        max_instances: int = 1,
        coalesce: bool = True,
        misfire_grace_time: int = 3600,
        args: tuple[Any, ...] | None = None,
        kwargs: dict[str, Any] | None = None,
    ) -> None:
        """Register a cron job.

        Parameters
        ----------
        func:
            Async callable to run on schedule.
        cron:
            Cron expression (e.g. ``"0 3 * * *"`` for 3 AM daily).
        job_id:
            Unique job identifier (auto-generated if omitted).
        name:
            Human-readable job name.
        max_instances:
            Prevent overlapping runs (default 1).
        coalesce:
            Skip missed runs if previous still active.
        misfire_grace_time:
            Seconds to allow delayed execution (default 1 hour).
        args:
            Positional args for the job function.
        kwargs:
            Keyword args for the job function.
        """
        job_id = job_id or f"{self.service_name}-{func.__name__}"
        name = name or func.__name__

        async def _wrapped_job(*a: Any, **kw: Any) -> None:
            """Wrapper that catches and logs job errors."""
            start_time = datetime.now(UTC)
            try:
                await func(*a, **kw)
                self._record_job(job_id, name, start_time, success=True)
            except Exception:
                self._record_job(job_id, name, start_time, success=False)
                logger.exception("[%s] Job '%s' failed", self.service_name, name)

        self._scheduler.add_job(
            _wrapped_job,
            CronTrigger.from_crontab(cron, timezone=self.timezone),
            id=job_id,
            name=name,
            replace_existing=True,
            max_instances=max_instances,
            coalesce=coalesce,
            misfire_grace_time=misfire_grace_time,
            args=args,
            kwargs=kwargs,
        )
        logger.info(
            "[%s] Job '%s' registered: cron=%s tz=%s",
            self.service_name,
            name,
            cron,
            self.timezone,
        )

    def add_interval_job(
        self,
        func: Callable[..., Awaitable[Any]],
        *,
        seconds: int = 0,
        minutes: int = 0,
        hours: int = 0,
        job_id: str | None = None,
        name: str | None = None,
        max_instances: int = 1,
    ) -> None:
        """Register an interval job.

        Parameters
        ----------
        func:
            Async callable to run on interval.
        seconds, minutes, hours:
            Interval components.
        """
        job_id = job_id or f"{self.service_name}-{func.__name__}"
        name = name or func.__name__

        async def _wrapped_job() -> None:
            start_time = datetime.now(UTC)
            try:
                await func()
                self._record_job(job_id, name, start_time, success=True)
            except Exception:
                self._record_job(job_id, name, start_time, success=False)
                logger.exception("[%s] Job '%s' failed", self.service_name, name)

        self._scheduler.add_job(
            _wrapped_job,
            "interval",
            id=job_id,
            name=name,
            replace_existing=True,
            max_instances=max_instances,
            seconds=seconds,
            minutes=minutes,
            hours=hours,
        )
        logger.info(
            "[%s] Interval job '%s' registered: %dh %dm %ds",
            self.service_name,
            name,
            hours,
            minutes,
            seconds,
        )

    def start(self) -> None:
        """Start the scheduler."""
        if self._is_running:
            logger.warning("[%s] Scheduler already running", self.service_name)
            return

        self._scheduler.start()
        self._is_running = True
        logger.info("[%s] Scheduler started", self.service_name)

    def stop(self) -> None:
        """Stop the scheduler gracefully."""
        if not self._is_running:
            return

        try:
            self._scheduler.shutdown(wait=True)
        except Exception:
            logger.warning("[%s] Scheduler shutdown error", self.service_name, exc_info=True)
        finally:
            self._is_running = False
            logger.info("[%s] Scheduler stopped", self.service_name)

    def get_jobs(self) -> list[dict[str, Any]]:
        """Return info about registered jobs."""
        jobs = []
        for job in self._scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            })
        return jobs

    def get_job_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return recent job execution history."""
        return self._job_history[-limit:]

    def _record_job(
        self,
        job_id: str,
        name: str | None,
        start_time: datetime,
        *,
        success: bool,
    ) -> None:
        """Record a job execution in history."""
        end_time = datetime.now(UTC)
        self._job_history.append({
            "job_id": job_id,
            "name": name,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": (end_time - start_time).total_seconds(),
            "success": success,
        })
        # Keep history bounded
        if len(self._job_history) > 100:
            self._job_history = self._job_history[-50:]
