"""Shared fixtures for the homeiq-ha tests."""

from __future__ import annotations

import pytest
from homeiq_ha.agent import backup as backup_helpers

from tests.simulators import SimHA


@pytest.fixture(autouse=True)
def _no_poll_delay(monkeypatch):
    """Poll the simulated backup job without the real three-second gap.

    The waits themselves are still exercised — only the sleep between polls is
    removed, so a regression in the polling logic still fails the suite.
    """
    monkeypatch.setattr(backup_helpers, "POLL_INTERVAL", 0)


@pytest.fixture
def sim() -> SimHA:
    return SimHA()
