"""
Retention Scheduler
Schedules automated retention operations
"""

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime, time

logger = logging.getLogger(__name__)


class RetentionScheduler:
    """Schedule retention operations"""

    def __init__(self):
        self.tasks = []

    def schedule_daily(self, hour: int, minute: int, func: Callable, name: str):
        """Schedule a daily task"""
        self.tasks.append({
            "name": name,
            "hour": hour,
            "minute": minute,
            "func": func,
            "last_run": None,
        })

        logger.info(f"Scheduled '{name}' daily at {hour:02d}:{minute:02d}")

    async def run_scheduler(self):
        """Run scheduler loop"""

        logger.info("Starting retention scheduler...")

        while True:
            try:
                now = datetime.now()
                current_time = time(now.hour, now.minute)

                for task in self.tasks:
                    task_time = time(task["hour"], task["minute"])

                    # Check if it's time to run
                    if current_time.hour == task_time.hour and current_time.minute == task_time.minute:
                        # Check if already run today
                        if task["last_run"]:
                            last_run_date = task["last_run"].date()
                            if last_run_date == now.date():
                                continue  # Already ran today

                        # Run task
                        logger.info(f"Running scheduled task: {task['name']}")
                        try:
                            await task["func"]()
                            task["last_run"] = now
                            logger.info(f"Completed task: {task['name']}")
                        except Exception as e:
                            logger.exception(f"Error in task {task['name']}: {e}")

                # Sleep for 1 minute
                await asyncio.sleep(60)

            except Exception as e:
                logger.exception(f"Error in scheduler: {e}")
                await asyncio.sleep(60)

