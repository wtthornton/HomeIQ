"""Periodic refresh scheduler for the blueprint catalogue.

Wires ``index_refresh_interval_hours`` to an actual job: without this, the
catalogue never grows past what a manual POST to ``/index/refresh`` produces.
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .config import settings

logger = logging.getLogger(__name__)

REFRESH_JOB_ID = "blueprint_index_refresh"


class IndexRefreshScheduler:
    """Periodically triggers a full blueprint catalogue refresh."""

    def __init__(self, refresh_interval_hours: int | None = None) -> None:
        self.refresh_interval_hours = (
            refresh_interval_hours
            if refresh_interval_hours is not None
            else settings.index_refresh_interval_hours
        )
        self.scheduler = AsyncIOScheduler()

    def start(self) -> None:
        """Register and start the periodic refresh job.

        ``max_instances=1`` combined with ``IndexManager.start_indexing_job``'s
        own running-job check keeps a slow refresh from overlapping the next
        tick and hammering GitHub/Discourse in parallel.
        """
        self.scheduler.add_job(
            self._run_refresh,
            IntervalTrigger(hours=self.refresh_interval_hours),
            id=REFRESH_JOB_ID,
            name="Blueprint catalogue refresh",
            replace_existing=True,
            max_instances=1,
        )
        self.scheduler.start()
        logger.info(
            "Blueprint index refresh scheduler started (interval=%sh)",
            self.refresh_interval_hours,
        )

    def stop(self) -> None:
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
        logger.info("Blueprint index refresh scheduler stopped")

    async def _run_refresh(self) -> None:
        """Run a full indexing job using a fresh database session."""
        from .database import get_db_context
        from .indexer.index_manager import IndexManager

        logger.info("Scheduled blueprint index refresh starting")
        try:
            async with get_db_context() as db:
                index_manager = IndexManager(db)
                job = await index_manager.start_indexing_job(job_type="full")
                logger.info("Scheduled blueprint index refresh queued job %s", job.id)
        except Exception:
            logger.error("Scheduled blueprint index refresh failed", exc_info=True)
