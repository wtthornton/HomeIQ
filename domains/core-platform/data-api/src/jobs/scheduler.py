"""Job scheduler for data-api background tasks.

Manages APScheduler for periodic jobs like memory consolidation.
Integrates with the service lifecycle (startup/shutdown).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.interval import IntervalTrigger

    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    AsyncIOScheduler = None  # type: ignore[assignment,misc]
    IntervalTrigger = None  # type: ignore[assignment,misc]

if TYPE_CHECKING:
    from homeiq_data.influxdb_query_client import InfluxDBQueryClient

    from .memory_consolidation import MemoryConsolidationJob

logger = logging.getLogger(__name__)

CONSOLIDATION_INTERVAL_HOURS = 6
CONSOLIDATION_JOB_ID = "memory_consolidation"


class JobScheduler:
    """Manages scheduled background jobs for data-api.

    Jobs:
    - Memory consolidation: Runs every 6 hours to detect user overrides
    """

    def __init__(self, influxdb: InfluxDBQueryClient) -> None:
        """Initialize scheduler with required dependencies.

        Args:
            influxdb: InfluxDB client for job queries
        """
        self._influxdb = influxdb
        self._scheduler: AsyncIOScheduler | None = None
        self._consolidation_job: MemoryConsolidationJob | None = None
        self._running = False

    async def start(self) -> bool:
        """Start the job scheduler.

        Returns:
            True if scheduler started successfully, False otherwise.
        """
        if not APSCHEDULER_AVAILABLE:
            logger.warning(
                "APScheduler not installed - background jobs disabled. "
                "Install with: pip install apscheduler"
            )
            return False

        if self._running:
            logger.debug("Scheduler already running")
            return True

        try:
            self._scheduler = AsyncIOScheduler()
            self._setup_jobs()
            self._scheduler.start()
            self._running = True

            jobs = self._scheduler.get_jobs()
            logger.info(
                "Job scheduler started with %d jobs: %s",
                len(jobs),
                ", ".join(j.id for j in jobs),
            )
            return True

        except Exception as e:
            logger.error("Failed to start job scheduler: %s", e, exc_info=True)
            return False

    async def stop(self) -> None:
        """Stop the job scheduler gracefully."""
        if not self._running or not self._scheduler:
            return

        try:
            self._scheduler.shutdown(wait=True)
            logger.info("Job scheduler stopped")
        except Exception as e:
            logger.error("Error stopping scheduler: %s", e)
        finally:
            self._scheduler = None
            self._running = False

    def _setup_jobs(self) -> None:
        """Configure and register all scheduled jobs."""
        if not self._scheduler:
            return

        from .memory_consolidation import MemoryConsolidationJob

        self._consolidation_job = MemoryConsolidationJob(
            influxdb=self._influxdb,
            memory_client=None,
            consolidator=None,
        )

        self._scheduler.add_job(
            self._run_consolidation,
            IntervalTrigger(hours=CONSOLIDATION_INTERVAL_HOURS),
            id=CONSOLIDATION_JOB_ID,
            name="Memory Consolidation (Override Detection)",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=3600,
        )

        logger.debug(
            "Registered %s job (every %d hours)",
            CONSOLIDATION_JOB_ID,
            CONSOLIDATION_INTERVAL_HOURS,
        )

    async def _run_consolidation(self) -> None:
        """Wrapper to run consolidation job with error handling."""
        if not self._consolidation_job:
            return

        try:
            await self._consolidation_job.run()
        except Exception as e:
            logger.error("Consolidation job failed: %s", e, exc_info=True)

    async def trigger_consolidation(self) -> dict:
        """Manually trigger the consolidation job.

        Returns:
            Job execution result.
        """
        if not self._consolidation_job:
            from .memory_consolidation import MemoryConsolidationJob

            self._consolidation_job = MemoryConsolidationJob(
                influxdb=self._influxdb,
                memory_client=None,
                consolidator=None,
            )

        return await self._consolidation_job.run()

    def get_status(self) -> dict:
        """Get scheduler status and job information.

        Returns:
            Status dict with scheduler state and job details.
        """
        jobs_info = []
        if self._scheduler and self._running:
            for job in self._scheduler.get_jobs():
                jobs_info.append(
                    {
                        "id": job.id,
                        "name": job.name,
                        "next_run": (
                            job.next_run_time.isoformat() if job.next_run_time else None
                        ),
                    }
                )

        consolidation_status = None
        if self._consolidation_job:
            consolidation_status = self._consolidation_job.get_status()

        return {
            "running": self._running,
            "apscheduler_available": APSCHEDULER_AVAILABLE,
            "jobs": jobs_info,
            "consolidation": consolidation_status,
        }


_scheduler_instance: JobScheduler | None = None


def get_job_scheduler(influxdb: InfluxDBQueryClient) -> JobScheduler:
    """Get or create the singleton job scheduler.

    Args:
        influxdb: InfluxDB client for job queries

    Returns:
        JobScheduler instance
    """
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = JobScheduler(influxdb)
    return _scheduler_instance
