"""
Tests for alert_endpoints.py — Epic 80, Story 80.7

Covers 14 scenarios:
1.  AlertEndpoints initialization with default alert_manager
2.  AlertEndpoints initialization with custom alert_manager
3.  GET /alerts — returns empty list when no alerts
4.  GET /alerts — returns all alerts
5.  GET /alerts?severity=critical — filters by severity
6.  GET /alerts?severity=invalid — returns 400
7.  GET /alerts?status=active — filters by status
8.  GET /alerts?status=invalid — returns 400
9.  GET /alerts/active — returns only active alerts
10. GET /alerts/summary — returns summary statistics
11. GET /alerts/{alert_id} — returns specific alert
12. GET /alerts/{alert_id} — 404 for missing alert
13. POST /alerts/{alert_id}/acknowledge — acknowledges alert
14. POST /alerts/{alert_id}/resolve — resolves alert
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.alert_endpoints import AlertEndpoints, AlertResponse, AlertSummaryResponse, create_alert_router

# ---------------------------------------------------------------------------
# Override conftest fresh_db — alert endpoints have no DB dependency
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(autouse=True)
async def fresh_db():
    yield


# ---------------------------------------------------------------------------
# Mock AlertManager for isolated testing
# ---------------------------------------------------------------------------


class FakeAlert:
    """Minimal alert object matching AlertManager's alert interface."""

    def __init__(self, id, name, severity, alert_status, message="test alert",
                 service="data-api", created_at=None):
        from homeiq_observability.alert_manager import AlertSeverity, AlertStatus

        self.id = id
        self.name = name
        self.severity = AlertSeverity(severity) if isinstance(severity, str) else severity
        self.status = AlertStatus(alert_status) if isinstance(alert_status, str) else alert_status
        self.message = message
        self.service = service
        self.metric = None
        self.current_value = None
        self.threshold_value = None
        self.created_at = created_at or datetime.now(UTC).isoformat()
        self.resolved_at = None
        self.acknowledged_at = None
        self.metadata = {}

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "severity": self.severity.value if hasattr(self.severity, 'value') else self.severity,
            "status": self.status.value if hasattr(self.status, 'value') else self.status,
            "message": self.message,
            "service": self.service,
            "metric": self.metric,
            "current_value": self.current_value,
            "threshold_value": self.threshold_value,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
            "acknowledged_at": self.acknowledged_at,
            "metadata": self.metadata,
        }


def _make_mock_alert_manager(alerts=None):
    """Create a mock AlertManager with optional pre-seeded alerts."""
    mgr = MagicMock()
    alert_dict = {}
    if alerts:
        for a in alerts:
            alert_dict[a.id] = a
    mgr.alerts = alert_dict

    def _get_alert(alert_id):
        return alert_dict.get(alert_id)

    def _acknowledge(alert_id):
        alert = alert_dict.get(alert_id)
        if alert:
            from homeiq_observability.alert_manager import AlertStatus
            alert.status = AlertStatus.ACKNOWLEDGED
            return True
        return False

    def _resolve(alert_id):
        alert = alert_dict.get(alert_id)
        if alert:
            from homeiq_observability.alert_manager import AlertStatus
            alert.status = AlertStatus.RESOLVED
            return True
        return False

    def _get_active(severity=None):
        from homeiq_observability.alert_manager import AlertStatus
        active = [a for a in alert_dict.values() if a.status == AlertStatus.ACTIVE]
        if severity:
            active = [a for a in active if a.severity == severity]
        return active

    def _get_summary():
        from homeiq_observability.alert_manager import AlertSeverity, AlertStatus
        active_alerts = [a for a in alert_dict.values() if a.status == AlertStatus.ACTIVE]
        return {
            "total_active": len(active_alerts),
            "critical": sum(1 for a in active_alerts if a.severity == AlertSeverity.CRITICAL),
            "warning": sum(1 for a in active_alerts if a.severity == AlertSeverity.WARNING),
            "info": sum(1 for a in active_alerts if a.severity == AlertSeverity.INFO),
            "total_alerts": len(alert_dict),
            "alert_history_count": len(alert_dict),
        }

    mgr.get_alert = _get_alert
    mgr.acknowledge_alert = _acknowledge
    mgr.resolve_alert = _resolve
    mgr.get_active_alerts = _get_active
    mgr.get_alert_summary = _get_summary
    mgr.clear_resolved_alerts = MagicMock()
    return mgr


def _make_app(alert_manager=None) -> FastAPI:
    """Build a minimal FastAPI app with alert routes."""
    app = FastAPI()
    ep = AlertEndpoints(alert_manager=alert_manager)
    app.include_router(ep.router)
    return app


@pytest_asyncio.fixture
async def empty_client():
    """Client with no alerts."""
    mgr = _make_mock_alert_manager()
    app = _make_app(mgr)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def seeded_client():
    """Client with pre-seeded alerts."""
    alerts = [
        FakeAlert("alert-1", "High CPU", "critical", "active"),
        FakeAlert("alert-2", "Disk Warning", "warning", "active"),
        FakeAlert("alert-3", "Info Notice", "info", "resolved"),
    ]
    mgr = _make_mock_alert_manager(alerts)
    app = _make_app(mgr)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c, mgr


# ===========================================================================
# Initialization
# ===========================================================================


class TestAlertEndpointsInit:
    """AlertEndpoints initialization."""

    def test_default_alert_manager(self):
        with patch("src.alert_endpoints.get_alert_manager") as mock_get:
            mock_get.return_value = MagicMock()
            ep = AlertEndpoints()
            mock_get.assert_called_once_with("admin-api")
            assert ep.router is not None

    def test_custom_alert_manager(self):
        custom_mgr = MagicMock()
        ep = AlertEndpoints(alert_manager=custom_mgr)
        assert ep.alert_manager is custom_mgr

    def test_create_alert_router_factory(self):
        mgr = MagicMock()
        router = create_alert_router(mgr)
        assert router is not None


# ===========================================================================
# GET /alerts
# ===========================================================================


class TestGetAllAlerts:
    """GET /alerts"""

    @pytest.mark.asyncio
    async def test_empty_list(self, empty_client):
        resp = await empty_client.get("/alerts")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_returns_all_alerts(self, seeded_client):
        client, _ = seeded_client
        resp = await client.get("/alerts")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3

    @pytest.mark.asyncio
    async def test_filter_by_severity(self, seeded_client):
        client, _ = seeded_client
        resp = await client.get("/alerts?severity=critical")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["severity"] == "critical"

    @pytest.mark.asyncio
    async def test_invalid_severity_returns_400(self, seeded_client):
        client, _ = seeded_client
        resp = await client.get("/alerts?severity=invalid_sev")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_filter_by_status(self, seeded_client):
        client, _ = seeded_client
        resp = await client.get("/alerts?status=active")
        assert resp.status_code == 200
        data = resp.json()
        assert all(a["status"] == "active" for a in data)

    @pytest.mark.asyncio
    async def test_invalid_status_returns_400(self, seeded_client):
        client, _ = seeded_client
        resp = await client.get("/alerts?status=bogus")
        assert resp.status_code == 400


# ===========================================================================
# GET /alerts/active
# ===========================================================================


class TestGetActiveAlerts:
    """GET /alerts/active"""

    @pytest.mark.asyncio
    async def test_returns_active_only(self, seeded_client):
        client, _ = seeded_client
        resp = await client.get("/alerts/active")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2  # alert-1 and alert-2 are active


# ===========================================================================
# GET /alerts/summary
# ===========================================================================


class TestAlertSummary:
    """GET /alerts/summary"""

    @pytest.mark.asyncio
    async def test_returns_summary(self, seeded_client):
        client, _ = seeded_client
        resp = await client.get("/alerts/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_active"] == 2
        assert data["critical"] == 1
        assert data["warning"] == 1
        assert data["total_alerts"] == 3


# ===========================================================================
# GET /alerts/{alert_id}
# ===========================================================================


class TestGetAlert:
    """GET /alerts/{alert_id}"""

    @pytest.mark.asyncio
    async def test_returns_alert(self, seeded_client):
        client, _ = seeded_client
        resp = await client.get("/alerts/alert-1")
        assert resp.status_code == 200
        assert resp.json()["id"] == "alert-1"

    @pytest.mark.asyncio
    async def test_404_missing_alert(self, seeded_client):
        client, _ = seeded_client
        resp = await client.get("/alerts/nonexistent")
        assert resp.status_code == 404


# ===========================================================================
# POST /alerts/{alert_id}/acknowledge
# ===========================================================================


class TestAcknowledgeAlert:
    """POST /alerts/{alert_id}/acknowledge"""

    @pytest.mark.asyncio
    async def test_acknowledge_success(self, seeded_client):
        client, _ = seeded_client
        resp = await client.post("/alerts/alert-1/acknowledge")
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    @pytest.mark.asyncio
    async def test_acknowledge_404(self, seeded_client):
        client, _ = seeded_client
        resp = await client.post("/alerts/nonexistent/acknowledge")
        assert resp.status_code == 404


# ===========================================================================
# POST /alerts/{alert_id}/resolve
# ===========================================================================


class TestResolveAlert:
    """POST /alerts/{alert_id}/resolve"""

    @pytest.mark.asyncio
    async def test_resolve_success(self, seeded_client):
        client, _ = seeded_client
        resp = await client.post("/alerts/alert-2/resolve")
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    @pytest.mark.asyncio
    async def test_resolve_404(self, seeded_client):
        client, _ = seeded_client
        resp = await client.post("/alerts/nonexistent/resolve")
        assert resp.status_code == 404


# ===========================================================================
# DELETE /alerts/cleanup
# ===========================================================================


class TestCleanupAlerts:
    """DELETE /alerts/cleanup"""

    @pytest.mark.asyncio
    async def test_cleanup_default(self, seeded_client):
        client, mgr = seeded_client
        resp = await client.delete("/alerts/cleanup")
        assert resp.status_code == 200
        mgr.clear_resolved_alerts.assert_called_once_with(24)

    @pytest.mark.asyncio
    async def test_cleanup_custom_hours(self, seeded_client):
        client, mgr = seeded_client
        resp = await client.delete("/alerts/cleanup?older_than_hours=48")
        assert resp.status_code == 200
        mgr.clear_resolved_alerts.assert_called_with(48)
