"""Lifecycle-managed background task manager for HomeIQ services.

Replaces 10+ ad-hoc ``asyncio.create_task()`` patterns with a
manager that tracks tasks, handles errors, and ensures graceful
shutdown.

Usage::

    from homeiq_resilience import TaskManager

    task_manager = TaskManager(service_name="my-service")

    # Register tasks
    task_manager.create_task(my_background_coroutine(), name="data-sync")

    # In shutdown:
    await task_manager.shutdown(timeout=10.0)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


class TaskManager:
    """Registry and lifecycle manager for background asyncio tasks.

    Parameters
    ----------
    service_name:
        Human-readable service name for log messages.
    """

    def __init__(self, service_name: str = "") -> None:
        self.service_name = service_name
        self._tasks: dict[str, asyncio.Task[Any]] = {}
        self._counter = 0

    def create_task(
        self,
        coro: Any,
        *,
        name: str | None = None,
    ) -> asyncio.Task[Any]:
        """Create and register a background task.

        Parameters
        ----------
        coro:
            Coroutine to run as a background task.
        name:
            Optional human-readable name.  Auto-generated if omitted.

        Returns
        -------
        asyncio.Task
            The created task.
        """
        if name is None:
            self._counter += 1
            name = f"task-{self._counter}"

        task = asyncio.create_task(coro, name=name)
        self._tasks[name] = task
        task.add_done_callback(lambda t: self._task_done(name, t))
        logger.debug("[%s] Task '%s' started", self.service_name, name)
        return task

    def _task_done(self, name: str, task: asyncio.Task[Any]) -> None:
        """Callback invoked when a task completes."""
        self._tasks.pop(name, None)

        if task.cancelled():
            logger.debug("[%s] Task '%s' was cancelled", self.service_name, name)
        elif task.exception():
            logger.error(
                "[%s] Task '%s' failed with exception: %s",
                self.service_name,
                name,
                task.exception(),
                exc_info=task.exception(),
            )
        else:
            logger.debug("[%s] Task '%s' completed", self.service_name, name)

    @property
    def active_tasks(self) -> list[str]:
        """Return names of currently running tasks."""
        return [name for name, task in self._tasks.items() if not task.done()]

    @property
    def task_count(self) -> int:
        """Return number of active tasks."""
        return len(self.active_tasks)

    def cancel_task(self, name: str) -> bool:
        """Cancel a task by name. Returns True if found and cancelled."""
        task = self._tasks.get(name)
        if task and not task.done():
            task.cancel()
            return True
        return False

    async def shutdown(self, *, timeout: float = 10.0) -> None:
        """Cancel all tasks and wait for them to finish.

        Parameters
        ----------
        timeout:
            Maximum seconds to wait for tasks to complete after
            cancellation.
        """
        if not self._tasks:
            return

        task_names = list(self._tasks.keys())
        logger.info(
            "[%s] Shutting down %d tasks: %s",
            self.service_name,
            len(task_names),
            task_names,
        )

        # Cancel all tasks
        for task in self._tasks.values():
            if not task.done():
                task.cancel()

        # Wait for all tasks to complete or timeout
        if self._tasks:
            tasks = list(self._tasks.values())
            done, pending = await asyncio.wait(tasks, timeout=timeout)

            if pending:
                logger.warning(
                    "[%s] %d tasks did not finish within %.1fs timeout",
                    self.service_name,
                    len(pending),
                    timeout,
                )

        self._tasks.clear()
        logger.info("[%s] Task manager shutdown complete", self.service_name)
