"""
Learning Scheduler

Schedules weekly batch retraining for Q&A learning improvements.

2025 Best Practices:
- Full type hints (PEP 484/526)
- Async/await for all database operations
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from ..database.models import get_db_session
from ..services.learning.continuous_improvement import ContinuousImprovement

logger = logging.getLogger(__name__)


class LearningScheduler:
    """
    Schedules weekly learning improvement cycles.
    
    Runs continuous improvement on a configurable schedule (default: weekly).
    """

    def __init__(self, schedule: str = "0 2 * * 0"):  # Default: Sunday 2 AM
        """
        Initialize learning scheduler.
        
        Args:
            schedule: Cron expression for schedule (default: weekly on Sunday 2 AM)
        """
        self.scheduler = AsyncIOScheduler()
        self.schedule = schedule
        self.improvement = ContinuousImprovement()

    async def run_improvement_job(self):
        """Run the improvement job."""
        logger.info("🔄 Starting scheduled learning improvement cycle...")
        
        try:
            async with get_db_session() as db:
                stats = await self.improvement.run_improvement_cycle(db)
                logger.info(f"✅ Improvement cycle completed: {stats.get('status')}")
        except Exception as e:
            logger.error(f"❌ Scheduled improvement cycle failed: {e}", exc_info=True)

    def start(self):
        """Start the scheduler."""
        try:
            # Parse schedule (format: "day hour" or cron expression)
            # Default: weekly on Sunday 2 AM
            if self.schedule == "weekly":
                trigger = CronTrigger(day_of_week=0, hour=2, minute=0)  # Sunday 2 AM
            elif self.schedule == "daily":
                trigger = CronTrigger(hour=2, minute=0)  # Daily 2 AM
            elif self.schedule == "monthly":
                trigger = CronTrigger(day=1, hour=2, minute=0)  # First day of month 2 AM
            else:
                # Assume it's a cron expression
                # Parse "day hour" format or use as-is
                parts = self.schedule.split()
                if len(parts) == 2:
                    # "day hour" format
                    day = int(parts[0]) if parts[0].isdigit() else 0
                    hour = int(parts[1]) if parts[1].isdigit() else 2
                    trigger = CronTrigger(day_of_week=day, hour=hour, minute=0)
                else:
                    # Full cron expression
                    trigger = CronTrigger.from_crontab(self.schedule)

            self.scheduler.add_job(
                self.run_improvement_job,
                trigger=trigger,
                id='learning_improvement',
                name='Q&A Learning Improvement Cycle',
                replace_existing=True
            )

            self.scheduler.start()
            logger.info(f"✅ Learning scheduler started (schedule: {self.schedule})")

        except Exception as e:
            logger.error(f"❌ Failed to start learning scheduler: {e}", exc_info=True)

    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("✅ Learning scheduler stopped")


