"""
Scheduler Service for Proactive Agent Service

APScheduler integration for daily suggestion generation.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from ..config import Settings
from ..services.suggestion_pipeline_service import SuggestionPipelineService

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service for scheduling suggestion generation jobs"""

    def __init__(
        self,
        settings: Settings,
        pipeline_service: SuggestionPipelineService | None = None,
    ):
        """
        Initialize Scheduler Service.

        Args:
            settings: Application settings
            pipeline_service: Suggestion Pipeline Service (creates default if None)
        """
        self.settings = settings
        self.pipeline_service = pipeline_service or SuggestionPipelineService()
        self.scheduler = AsyncIOScheduler()
        self._is_running = False

        logger.info("Scheduler Service initialized")

    def start(self):
        """
        Start the scheduler and register the daily suggestion generation job.
        """
        if not self.settings.scheduler_enabled:
            logger.info("Scheduler is disabled in settings")
            return

        try:
            # Parse schedule time (format: "HH:MM")
            schedule_time = self.settings.scheduler_time.split(":")
            hour = int(schedule_time[0])
            minute = int(schedule_time[1]) if len(schedule_time) > 1 else 0

            # Add daily suggestion generation job
            self.scheduler.add_job(
                self._run_daily_suggestions,
                CronTrigger(hour=hour, minute=minute, timezone=self.settings.scheduler_timezone),
                id="daily_suggestion_generation",
                name="Daily Proactive Suggestion Generation",
                replace_existing=True,
                max_instances=1,  # Prevent overlap
                coalesce=True,  # Skip if previous run still active
                misfire_grace_time=3600,  # Allow 1 hour delay if server was down
            )

            self.scheduler.start()
            self._is_running = True

            job = self.scheduler.get_job("daily_suggestion_generation")
            next_run = job.next_run_time if job else None

            logger.info(
                f"Scheduler started: daily suggestions at {self.settings.scheduler_time} "
                f"({self.settings.scheduler_timezone})"
            )
            if next_run:
                logger.info(f"Next run: {next_run}")

        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}", exc_info=True)
            raise

    def stop(self):
        """
        Stop the scheduler gracefully.
        """
        try:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=True)
                self._is_running = False
                logger.info("Scheduler stopped")
        except Exception as e:
            logger.error(f"Failed to stop scheduler: {e}", exc_info=True)

    async def _run_daily_suggestions(self) -> dict[str, Any]:
        """
        Execute daily suggestion generation job.

        This method is called by APScheduler at the scheduled time.

        Returns:
            Dictionary with pipeline results
        """
        logger.info("Starting daily suggestion generation job")

        try:
            results = await self.pipeline_service.generate_suggestions()

            logger.info(
                f"Daily suggestion generation complete: "
                f"{results['suggestions_created']} created, "
                f"{results['suggestions_sent']} sent, "
                f"{results['suggestions_failed']} failed"
            )

            if not results.get("success", False):
                logger.warning("Daily suggestion generation completed with errors")

            return results

        except Exception as e:
            logger.error(f"Error in daily suggestion generation job: {e}", exc_info=True)
            return {
                "success": False,
                "suggestions_created": 0,
                "suggestions_sent": 0,
                "suggestions_failed": 0,
                "details": [{"step": "pipeline", "error": str(e)}],
            }

    async def trigger_manual(self) -> dict[str, Any]:
        """
        Manually trigger suggestion generation (for testing/debugging).

        Returns:
            Dictionary with job results
        """
        logger.info("Manual suggestion generation triggered")
        return await self._run_daily_suggestions()

    def is_running(self) -> bool:
        """Check if scheduler is running"""
        return self._is_running and self.scheduler.running

    def get_next_run_time(self) -> datetime | None:
        """Get next scheduled run time"""
        job = self.scheduler.get_job("daily_suggestion_generation")
        return job.next_run_time if job else None

