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
        self.periodic_tasks = []  # Epic 45.3: Periodic tasks (every N minutes)

    def schedule_daily(self, hour: int, minute: int, func: Callable, name: str):
        """Schedule a daily task"""
        self.tasks.append({
            'name': name,
            'hour': hour,
            'minute': minute,
            'func': func,
            'last_run': None
        })

        logger.info(f"Scheduled '{name}' daily at {hour:02d}:{minute:02d}")

    def schedule_periodic(self, interval_minutes: int, func: Callable, name: str):
        """Schedule a periodic task (Epic 45.3)"""
        self.periodic_tasks.append({
            'name': name,
            'interval_minutes': interval_minutes,
            'func': func,
            'last_run': None
        })

        logger.info(f"Scheduled '{name}' every {interval_minutes} minutes")

    async def run_scheduler(self):
        """Run scheduler loop"""

        logger.info("Starting retention scheduler...")

        while True:
            try:
                now = datetime.now()
                current_time = time(now.hour, now.minute)

                # Run daily tasks
                for task in self.tasks:
                    task_time = time(task['hour'], task['minute'])

                    # Check if it's time to run
                    if current_time.hour == task_time.hour and current_time.minute == task_time.minute:
                        # Check if already run today
                        if task['last_run']:
                            last_run_date = task['last_run'].date()
                            if last_run_date == now.date():
                                continue  # Already ran today

                        # Run task
                        logger.info(f"Running scheduled task: {task['name']}")
                        try:
                            await task['func']()
                            task['last_run'] = now
                            logger.info(f"Completed task: {task['name']}")
                        except Exception as e:
                            logger.error(f"Error in task {task['name']}: {e}")

                # Run periodic tasks (Epic 45.3)
                for task in self.periodic_tasks:
                    interval_seconds = task['interval_minutes'] * 60
                    
                    # Check if it's time to run
                    if task['last_run'] is None:
                        # First run - execute immediately
                        should_run = True
                    else:
                        time_since_last = (now - task['last_run']).total_seconds()
                        should_run = time_since_last >= interval_seconds
                    
                    if should_run:
                        logger.info(f"Running periodic task: {task['name']}")
                        try:
                            await task['func']()
                            task['last_run'] = now
                            logger.info(f"Completed periodic task: {task['name']}")
                        except Exception as e:
                            logger.error(f"Error in periodic task {task['name']}: {e}")

                # Sleep for 1 minute
                await asyncio.sleep(60)

            except Exception as e:
                logger.error(f"Error in scheduler: {e}")
                await asyncio.sleep(60)

