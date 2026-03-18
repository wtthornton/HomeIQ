"""Unit tests for JobScheduler — Story 85.9

Tests scheduler lifecycle, job registration, and error handling.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.jobs.scheduler import (
    CONSOLIDATION_INTERVAL_HOURS,
    CONSOLIDATION_JOB_ID,
    JobScheduler,
    get_job_scheduler,
)


class TestJobSchedulerStart:

    def _make_scheduler(self):
        mock_influxdb = MagicMock()
        return JobScheduler(mock_influxdb)

    @pytest.mark.asyncio
    async def test_start_without_apscheduler_returns_false(self):
        sched = self._make_scheduler()
        with patch("src.jobs.scheduler.APSCHEDULER_AVAILABLE", False):
            assert await sched.start() is False

    @pytest.mark.asyncio
    async def test_start_already_running_returns_true(self):
        sched = self._make_scheduler()
        sched._running = True
        assert await sched.start() is True

    @pytest.mark.asyncio
    async def test_start_creates_scheduler_and_jobs(self):
        sched = self._make_scheduler()
        mock_async_sched = MagicMock()
        mock_job = MagicMock()
        mock_job.id = CONSOLIDATION_JOB_ID
        mock_async_sched.get_jobs.return_value = [mock_job]

        with patch("src.jobs.scheduler.APSCHEDULER_AVAILABLE", True), \
             patch("src.jobs.scheduler.AsyncIOScheduler", return_value=mock_async_sched), \
             patch("src.jobs.scheduler.IntervalTrigger"), \
             patch("src.jobs.scheduler.MemoryConsolidationJob", create=True):
            result = await sched.start()
            assert result is True
            assert sched._running is True
            mock_async_sched.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_exception_returns_false(self):
        sched = self._make_scheduler()
        with patch("src.jobs.scheduler.APSCHEDULER_AVAILABLE", True), \
             patch("src.jobs.scheduler.AsyncIOScheduler", side_effect=Exception("init fail")):
            result = await sched.start()
            assert result is False
            assert sched._running is False


class TestJobSchedulerStop:

    @pytest.mark.asyncio
    async def test_stop_when_not_running(self):
        sched = JobScheduler(MagicMock())
        await sched.stop()  # Should not raise

    @pytest.mark.asyncio
    async def test_stop_shuts_down_scheduler(self):
        sched = JobScheduler(MagicMock())
        mock_async_sched = MagicMock()
        sched._scheduler = mock_async_sched
        sched._running = True

        await sched.stop()
        mock_async_sched.shutdown.assert_called_once_with(wait=True)
        assert sched._running is False
        assert sched._scheduler is None

    @pytest.mark.asyncio
    async def test_stop_handles_exception(self):
        sched = JobScheduler(MagicMock())
        mock_async_sched = MagicMock()
        mock_async_sched.shutdown.side_effect = Exception("shutdown error")
        sched._scheduler = mock_async_sched
        sched._running = True

        await sched.stop()
        assert sched._running is False


class TestRunConsolidation:

    @pytest.mark.asyncio
    async def test_no_job_does_nothing(self):
        sched = JobScheduler(MagicMock())
        await sched._run_consolidation()  # Should not raise

    @pytest.mark.asyncio
    async def test_delegates_to_job(self):
        sched = JobScheduler(MagicMock())
        mock_job = AsyncMock()
        sched._consolidation_job = mock_job
        await sched._run_consolidation()
        mock_job.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_job_exception(self):
        sched = JobScheduler(MagicMock())
        mock_job = AsyncMock()
        mock_job.run.side_effect = Exception("consolidation failed")
        sched._consolidation_job = mock_job
        await sched._run_consolidation()  # Should not raise


class TestTriggerConsolidation:

    @pytest.mark.asyncio
    async def test_creates_job_if_needed(self):
        sched = JobScheduler(MagicMock())
        with patch("src.jobs.memory_consolidation.MemoryConsolidationJob") as MockJob:
            mock_instance = AsyncMock()
            mock_instance.run.return_value = {"status": "ok"}
            MockJob.return_value = mock_instance

            result = await sched.trigger_consolidation()
            assert result == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_uses_existing_job(self):
        sched = JobScheduler(MagicMock())
        mock_job = AsyncMock()
        mock_job.run.return_value = {"count": 5}
        sched._consolidation_job = mock_job

        result = await sched.trigger_consolidation()
        assert result == {"count": 5}


class TestGetStatus:

    def test_status_not_running(self):
        sched = JobScheduler(MagicMock())
        status = sched.get_status()
        assert status["running"] is False
        assert status["jobs"] == []

    def test_status_running_with_jobs(self):
        sched = JobScheduler(MagicMock())
        sched._running = True
        mock_async_sched = MagicMock()
        mock_job = MagicMock()
        mock_job.id = CONSOLIDATION_JOB_ID
        mock_job.name = "Memory Consolidation"
        mock_job.next_run_time = None
        mock_async_sched.get_jobs.return_value = [mock_job]
        sched._scheduler = mock_async_sched

        status = sched.get_status()
        assert status["running"] is True
        assert len(status["jobs"]) == 1
        assert status["jobs"][0]["id"] == CONSOLIDATION_JOB_ID

    def test_status_includes_consolidation_info(self):
        sched = JobScheduler(MagicMock())
        mock_job = MagicMock()
        mock_job.get_status.return_value = {"last_run": "2025-01-01"}
        sched._consolidation_job = mock_job

        status = sched.get_status()
        assert status["consolidation"] == {"last_run": "2025-01-01"}


class TestSingleton:

    def test_returns_same_instance(self):
        import src.jobs.scheduler as mod
        mod._scheduler_instance = None
        mock_influxdb = MagicMock()
        s1 = get_job_scheduler(mock_influxdb)
        s2 = get_job_scheduler(mock_influxdb)
        assert s1 is s2
        mod._scheduler_instance = None  # cleanup
