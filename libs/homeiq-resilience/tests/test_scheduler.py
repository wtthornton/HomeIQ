"""Tests for ServiceScheduler.

Covers:
  - Cron job registration
  - Interval job registration
  - Start/stop lifecycle
  - Job listing
  - Job history tracking
  - Idempotent start/stop
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from homeiq_resilience.scheduler import ServiceScheduler


class TestServiceScheduler:
    def test_init(self) -> None:
        sched = ServiceScheduler(service_name="test", timezone="UTC")
        assert sched.service_name == "test"
        assert sched.is_running is False

    def test_add_cron_job(self) -> None:
        sched = ServiceScheduler(service_name="test")

        async def my_job() -> None:
            pass

        sched.add_cron_job(my_job, cron="0 3 * * *", job_id="daily", name="Daily Job")
        # Job is registered but scheduler not started yet
        assert sched.is_running is False

    def test_add_interval_job(self) -> None:
        sched = ServiceScheduler(service_name="test")

        async def my_job() -> None:
            pass

        sched.add_interval_job(my_job, minutes=5, job_id="poll", name="Poller")
        assert sched.is_running is False

    def test_start_and_stop(self) -> None:
        sched = ServiceScheduler(service_name="test")

        async def my_job() -> None:
            pass

        sched.add_cron_job(my_job, cron="0 3 * * *")

        with patch.object(sched._scheduler, "start"):
            sched.start()
            assert sched.is_running is True

        with patch.object(sched._scheduler, "shutdown"):
            sched.stop()
            assert sched.is_running is False

    def test_start_idempotent(self) -> None:
        sched = ServiceScheduler(service_name="test")

        with patch.object(sched._scheduler, "start"):
            sched.start()
            sched.start()  # Should not raise
            assert sched.is_running is True

        with patch.object(sched._scheduler, "shutdown"):
            sched.stop()

    def test_stop_idempotent(self) -> None:
        sched = ServiceScheduler(service_name="test")
        sched.stop()  # Should not raise when not running

    def test_get_jobs(self) -> None:
        sched = ServiceScheduler(service_name="test")

        async def job_a() -> None:
            pass

        async def job_b() -> None:
            pass

        sched.add_cron_job(job_a, cron="0 3 * * *", job_id="a", name="Job A")
        sched.add_cron_job(job_b, cron="0 6 * * *", job_id="b", name="Job B")

        mock_job_a = MagicMock()
        mock_job_a.id = "a"
        mock_job_a.name = "Job A"
        mock_job_a.next_run_time = datetime.now(UTC)
        mock_job_b = MagicMock()
        mock_job_b.id = "b"
        mock_job_b.name = "Job B"
        mock_job_b.next_run_time = datetime.now(UTC)

        with patch.object(sched._scheduler, "start"):
            sched.start()

        with patch.object(sched._scheduler, "get_jobs", return_value=[mock_job_a, mock_job_b]):
            jobs = sched.get_jobs()
            assert len(jobs) == 2
            job_ids = {j["id"] for j in jobs}
            assert "a" in job_ids
            assert "b" in job_ids

        with patch.object(sched._scheduler, "shutdown"):
            sched.stop()

    def test_get_job_history_empty(self) -> None:
        sched = ServiceScheduler(service_name="test")
        assert sched.get_job_history() == []

    def test_record_job_history(self) -> None:
        sched = ServiceScheduler(service_name="test")

        sched._record_job("test-job", "Test Job", datetime.now(UTC), success=True)
        history = sched.get_job_history()
        assert len(history) == 1
        assert history[0]["job_id"] == "test-job"
        assert history[0]["success"] is True
