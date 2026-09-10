"""
TAP-7308: ``_fetch_events`` capped the Data API request at ``limit=50000``.
The live 7-day window holds ~139K rows, newest-first, so the cap silently
truncated detectors to roughly the newest 2.5 days instead of the full
7-day window the detectors are documented to analyze.

This test uses a fixture of 60,000 events (deliberately above the old cap)
so a passing result proves the window is no longer capped — a fixture
under 50,000 would pass the old, broken code too and prove nothing.
"""

import pandas as pd
import pytest
from src.scheduler.pattern_analysis import PatternAnalysisScheduler


class _FakeDataAPIClient:
    """Mimics DataAPIClient.fetch_events: returns up to `limit` rows from a
    fixed-size pool, or the whole pool when limit is None (full pagination)."""

    def __init__(self, total_events: int):
        self.total_events = total_events
        self.last_limit = "unset"

    async def fetch_events(self, start_time=None, end_time=None, limit=10000, **kwargs):
        self.last_limit = limit
        count = self.total_events if limit is None else min(limit, self.total_events)
        return pd.DataFrame(
            {
                "device_id": ["light.test"] * count,
                "timestamp": pd.date_range("2026-01-01", periods=count, freq="1min", tz="UTC"),
                "state": ["on"] * count,
            }
        )


@pytest.mark.unit
@pytest.mark.scheduler
async def test_fetch_events_covers_full_seven_day_window():
    fixture_size = 60_000  # deliberately > the old 50,000 cap
    fake_client = _FakeDataAPIClient(total_events=fixture_size)
    scheduler = PatternAnalysisScheduler()

    events_df = await scheduler._fetch_events(fake_client)

    assert len(events_df) >= fixture_size
