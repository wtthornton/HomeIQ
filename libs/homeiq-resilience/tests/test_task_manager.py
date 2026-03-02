"""Tests for TaskManager.

Covers:
  - Task creation and tracking
  - Task completion callback
  - Task cancellation
  - Graceful shutdown
  - Error handling in tasks
"""

from __future__ import annotations

import asyncio

import pytest
from homeiq_resilience.task_manager import TaskManager


class TestTaskManager:
    def test_init(self) -> None:
        tm = TaskManager(service_name="test")
        assert tm.service_name == "test"
        assert tm.task_count == 0
        assert tm.active_tasks == []

    @pytest.mark.asyncio
    async def test_create_task(self) -> None:
        tm = TaskManager(service_name="test")

        async def noop() -> None:
            pass

        task = tm.create_task(noop(), name="my-task")
        assert "my-task" in tm.active_tasks
        await task  # Let it complete
        await asyncio.sleep(0.01)  # Allow callback to fire
        assert tm.task_count == 0

    @pytest.mark.asyncio
    async def test_auto_name(self) -> None:
        tm = TaskManager(service_name="test")

        async def noop() -> None:
            pass

        tm.create_task(noop())
        assert "task-1" in tm.active_tasks
        await tm.shutdown()

    @pytest.mark.asyncio
    async def test_cancel_task(self) -> None:
        tm = TaskManager(service_name="test")

        async def long_running() -> None:
            await asyncio.sleep(100)

        tm.create_task(long_running(), name="slow")
        assert tm.cancel_task("slow") is True
        assert tm.cancel_task("nonexistent") is False
        await tm.shutdown()

    @pytest.mark.asyncio
    async def test_shutdown_cancels_all(self) -> None:
        tm = TaskManager(service_name="test")

        async def long_running() -> None:
            await asyncio.sleep(100)

        tm.create_task(long_running(), name="t1")
        tm.create_task(long_running(), name="t2")
        assert tm.task_count == 2
        await tm.shutdown(timeout=1.0)
        assert tm.task_count == 0

    @pytest.mark.asyncio
    async def test_failed_task_logged(self) -> None:
        tm = TaskManager(service_name="test")

        async def failing() -> None:
            raise ValueError("boom")

        task = tm.create_task(failing(), name="fail")
        # Wait for the task to complete (it will fail)
        with pytest.raises(ValueError):
            await task
        await asyncio.sleep(0.01)
        assert tm.task_count == 0

    @pytest.mark.asyncio
    async def test_shutdown_empty(self) -> None:
        tm = TaskManager(service_name="test")
        await tm.shutdown()  # Should not raise
