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

import pytest
from unittest.mock import AsyncMock

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
        sched.start()
        assert sched.is_running is True

        sched.stop()
        assert sched.is_running is False

    def test_start_idempotent(self) -> None:
        sched = ServiceScheduler(service_name="test")
        sched.start()
        sched.start()  # Should not raise
        assert sched.is_running is True
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
        sched.start()

        jobs = sched.get_jobs()
        assert len(jobs) == 2
        job_ids = {j["id"] for j in jobs}
        assert "a" in job_ids
        assert "b" in job_ids

        sched.stop()

    def test_get_job_history_empty(self) -> None:
        sched = ServiceScheduler(service_name="test")
        assert sched.get_job_history() == []

    def test_record_job_history(self) -> None:
        sched = ServiceScheduler(service_name="test")
        from datetime import datetime, timezone

        sched._record_job("test-job", "Test Job", datetime.now(timezone.utc), success=True)
        history = sched.get_job_history()
        assert len(history) == 1
        assert history[0]["job_id"] == "test-job"
        assert history[0]["success"] is True
