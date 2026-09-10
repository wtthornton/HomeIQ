"""Tests for the merged application's /health endpoint, proactive slice.

TAP-7275: the proactive slice's own ``GET /health`` is no longer mounted --
``src/api/health.py`` answers for all three slices at that path and reports a
per-slice breakdown. These tests were re-pointed from the retired per-service
payload (``service: proactive-agent-service``, top-level ``scheduler``) to the
merged one (``service: automation-domain``, ``slices.proactive.scheduler``).

The merged endpoint returns 503 whenever any slice is degraded, and a bare
TestClient has no database and no started chat dependencies, so the status code
is not what these tests assert on -- the scheduler reporting is.
"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.proactive.api.health import set_scheduler_service_for_health


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


def _proactive_slice(client) -> dict:
    """GET /health and return the proactive slice's section of the payload."""
    response = client.get("/health")
    assert response.status_code in (200, 503), response.text
    data = response.json()
    assert data["service"] == "automation-domain"
    assert data["version"] == "1.0.0"
    assert "proactive" in data["slices"]
    return data["slices"]["proactive"]


def test_health_check(client):
    """The merged endpoint reports the proactive slice with a database probe."""
    proactive = _proactive_slice(client)
    assert "database" in proactive
    assert proactive["database"]["status"] in ("healthy", "unhealthy")


def test_health_check_includes_scheduler_status(client):
    """Scheduler state is reported when a scheduler service is registered."""
    mock_scheduler = MagicMock()
    mock_scheduler.is_running = MagicMock(return_value=True)
    mock_scheduler.get_next_run_time = MagicMock(return_value=datetime(2025, 1, 8, 3, 0, 0))

    set_scheduler_service_for_health(mock_scheduler)
    try:
        scheduler = _proactive_slice(client)["scheduler"]
        assert scheduler["enabled"] is True
        assert scheduler["running"] is True
        assert scheduler["next_run"] is not None
    finally:
        set_scheduler_service_for_health(None)


def test_health_check_scheduler_disabled_when_not_set(client):
    """Scheduler reports disabled when no scheduler service is registered."""
    set_scheduler_service_for_health(None)

    scheduler = _proactive_slice(client)["scheduler"]
    assert scheduler["enabled"] is False
    assert scheduler["running"] is False
    assert scheduler["next_run"] is None
