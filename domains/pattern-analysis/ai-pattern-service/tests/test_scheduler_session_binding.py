"""
TAP-7306: the daily scheduler crashed every run with
``TypeError: 'NoneType' object is not callable`` at the DB-session line,
because ``AsyncSessionLocal`` was imported as a bare name at module-import
time (a snapshot of ``None``) instead of resolved live at call time. Real
startup order is: import the scheduler module, THEN call ``init_db()`` —
so a bare-name import can never see the post-init value.
"""

from unittest.mock import MagicMock

import pandas as pd
import pytest
from src import database as db_module
from src.scheduler import pattern_analysis as sched_module


class _FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False

    async def commit(self):
        pass


class _FakeDataAPIClient:
    """Stands in for DataAPIClient so the test never hits a network."""

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False

    async def fetch_events(self, **kwargs):
        return pd.DataFrame(
            {
                "device_id": ["light.test"],
                "entity_id": ["light.test"],
                "timestamp": [pd.Timestamp("2026-01-01T12:00:00Z")],
                "state": ["on"],
            }
        )

    async def fetch_ha_timezone(self):
        return "UTC"


async def _no_patterns(self, *args, **kwargs):
    return []


async def _no_synergies(self, *args, **kwargs):
    return []


async def _no_alignment(self, *args, **kwargs):
    return None


@pytest.mark.unit
@pytest.mark.scheduler
async def test_scheduler_session_bound_after_init_db(monkeypatch):
    """A DB session factory installed by init_db() AFTER import must be
    visible to the scheduler's next run — not shadowed by a stale None
    captured at import time."""
    mock_session_factory = MagicMock(return_value=_FakeSession())

    # Simulate init_db() populating the module-level factory after the
    # scheduler module has already been imported (the real startup order).
    monkeypatch.setattr(db_module, "AsyncSessionLocal", mock_session_factory)

    monkeypatch.setattr(sched_module, "DataAPIClient", _FakeDataAPIClient)
    monkeypatch.setattr(
        sched_module.EventFilter, "filter_events", staticmethod(lambda df, **_kw: df)
    )
    monkeypatch.setattr(sched_module.PatternAnalysisScheduler, "_detect_patterns", _no_patterns)
    monkeypatch.setattr(
        sched_module.PatternAnalysisScheduler,
        "_generate_synergies_from_patterns",
        _no_synergies,
    )
    monkeypatch.setattr(sched_module.PatternAnalysisScheduler, "_detect_synergies", _no_synergies)
    monkeypatch.setattr(
        sched_module.PatternAnalysisScheduler,
        "_enrich_synergies_with_activity",
        _no_synergies,
    )
    monkeypatch.setattr(
        sched_module.PatternAnalysisScheduler,
        "_validate_pattern_synergy_alignment",
        _no_alignment,
    )

    scheduler = sched_module.PatternAnalysisScheduler()
    await scheduler.run_pattern_analysis()

    # If AsyncSessionLocal resolved to the live post-init factory, it was
    # called to open the DB session. If it resolved to the stale None
    # snapshot instead, calling it raised TypeError — caught internally by
    # run_pattern_analysis's broad except — and the mock was never reached.
    mock_session_factory.assert_called()
