"""Tests for the blueprint catalogue refresh scheduler (TAP-7311).

`index_refresh_interval_hours` had no reader anywhere in the service, so the
catalogue stayed at 0 rows unless someone manually POSTed /index/refresh.
These tests assert the scheduler actually registers a periodic job at that
interval.
"""

import pytest
from apscheduler.triggers.interval import IntervalTrigger
from src.config import settings
from src.scheduler import REFRESH_JOB_ID, IndexRefreshScheduler


class TestIndexRefreshScheduler:
    def test_defaults_to_configured_interval(self):
        scheduler = IndexRefreshScheduler()
        assert scheduler.refresh_interval_hours == settings.index_refresh_interval_hours

    def test_accepts_explicit_interval_override(self):
        scheduler = IndexRefreshScheduler(refresh_interval_hours=6)
        assert scheduler.refresh_interval_hours == 6

    @pytest.mark.asyncio
    async def test_start_registers_the_refresh_job(self):
        scheduler = IndexRefreshScheduler(refresh_interval_hours=6)
        scheduler.start()
        try:
            job = scheduler.scheduler.get_job(REFRESH_JOB_ID)
            assert job is not None
            assert isinstance(job.trigger, IntervalTrigger)
            assert job.trigger.interval.total_seconds() == 6 * 3600
        finally:
            scheduler.stop()

    @pytest.mark.asyncio
    async def test_start_uses_config_interval_by_default(self):
        scheduler = IndexRefreshScheduler()
        scheduler.start()
        try:
            job = scheduler.scheduler.get_job(REFRESH_JOB_ID)
            assert job is not None
            expected_seconds = settings.index_refresh_interval_hours * 3600
            assert job.trigger.interval.total_seconds() == expected_seconds
        finally:
            scheduler.stop()

    @pytest.mark.asyncio
    async def test_job_prevents_overlapping_runs(self):
        """max_instances=1 keeps a slow refresh from stacking with the next tick."""
        scheduler = IndexRefreshScheduler(refresh_interval_hours=1)
        scheduler.start()
        try:
            job = scheduler.scheduler.get_job(REFRESH_JOB_ID)
            assert job.max_instances == 1
        finally:
            scheduler.stop()
