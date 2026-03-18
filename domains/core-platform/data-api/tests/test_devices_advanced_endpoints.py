"""
Tests for devices_endpoints.py — Advanced routes (not covered by test_devices_endpoints.py)

Covers 55 scenarios across integration analytics, bulk upsert, device health, power analysis,
classification, setup assistant, capability discovery, entity enrichment, recommendations,
entity relationships, reliability, and device clear.

Routes tested:
  - GET  /api/integrations/{platform}/performance
  - GET  /api/integrations/{platform}/analytics
  - GET  /api/integrations
  - POST /internal/devices/bulk_upsert
  - POST /internal/entities/bulk_upsert
  - POST /internal/services/bulk_upsert
  - GET  /api/devices/{device_id}/health
  - GET  /api/devices/health-summary
  - GET  /api/devices/maintenance-alerts
  - GET  /api/devices/{device_id}/power-analysis
  - GET  /api/devices/{device_id}/efficiency
  - GET  /api/devices/power-anomalies
  - POST /api/devices/{device_id}/classify
  - POST /api/devices/link-entities
  - POST /api/devices/classify-all
  - GET  /api/devices/{device_id}/setup-guide
  - GET  /api/devices/{device_id}/setup-issues
  - POST /api/devices/{device_id}/setup-complete
  - POST /api/devices/{device_id}/discover-capabilities
  - POST /api/entities/enrich
  - GET  /api/devices/recommendations
  - GET  /api/devices/compare
  - GET  /api/devices/similar/{device_id}
  - GET  /api/entities/by-device/{device_id}
  - GET  /api/entities/{entity_id}/siblings
  - GET  /api/entities/{entity_id}/device
  - GET  /api/entities/by-area/{area_id}
  - GET  /api/entities/by-config-entry/{config_entry_id}
  - GET  /api/devices/{device_id}/hierarchy
  - GET  /api/devices/reliability
  - DELETE /internal/devices/clear
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


# ---------------------------------------------------------------------------
# Override conftest fresh_db — no real DB needed for unit tests
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(autouse=True)
async def fresh_db():
    yield


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_device(device_id="dev-001", name="Test Light", manufacturer="TestCo",
                      model="Bulb-v2", **kwargs):
    """Create a MagicMock that looks like a Device ORM instance."""
    d = MagicMock()
    d.device_id = device_id
    d.name = name
    d.manufacturer = manufacturer
    d.model = model
    d.sw_version = kwargs.get("sw_version", "1.0.0")
    d.area_id = kwargs.get("area_id", "living_room")
    d.integration = kwargs.get("integration", "hue")
    d.config_entry_id = kwargs.get("config_entry_id", "cfg-001")
    d.via_device = kwargs.get("via_device")
    d.device_type = kwargs.get("device_type")
    d.device_category = kwargs.get("device_category")
    d.power_consumption_idle_w = kwargs.get("power_consumption_idle_w")
    d.power_consumption_active_w = kwargs.get("power_consumption_active_w")
    d.power_consumption_max_w = kwargs.get("power_consumption_max_w")
    d.setup_instructions_url = kwargs.get("setup_instructions_url")
    d.troubleshooting_notes = kwargs.get("troubleshooting_notes")
    d.device_features_json = kwargs.get("device_features_json")
    d.community_rating = kwargs.get("community_rating")
    d.last_capability_sync = kwargs.get("last_capability_sync")
    d.last_seen = kwargs.get("last_seen", datetime.now(UTC))
    d.labels = kwargs.get("labels")
    d.serial_number = kwargs.get("serial_number")
    d.model_id = kwargs.get("model_id")
    return d


def _make_mock_entity(entity_id="light.living_room", device_id="dev-001",
                      domain="light", platform="hue", **kwargs):
    """Create a MagicMock that looks like an Entity ORM instance."""
    now = datetime.now(UTC)
    e = MagicMock()
    e.entity_id = entity_id
    e.device_id = device_id
    e.domain = domain
    e.platform = platform
    e.unique_id = kwargs.get("unique_id")
    e.area_id = kwargs.get("area_id")
    e.disabled = kwargs.get("disabled", False)
    e.config_entry_id = kwargs.get("config_entry_id")
    e.name = kwargs.get("name", entity_id.split(".")[-1].replace("_", " ").title())
    e.name_by_user = kwargs.get("name_by_user")
    e.original_name = kwargs.get("original_name")
    e.friendly_name = kwargs.get("friendly_name", e.name)
    e.supported_features = kwargs.get("supported_features")
    e.capabilities = kwargs.get("capabilities")
    e.available_services = kwargs.get("available_services")
    e.icon = kwargs.get("icon")
    e.original_icon = kwargs.get("original_icon")
    e.device_class = kwargs.get("device_class")
    e.unit_of_measurement = kwargs.get("unit_of_measurement")
    e.aliases = kwargs.get("aliases")
    e.labels = kwargs.get("labels")
    e.options = kwargs.get("options")
    e.updated_at = kwargs.get("updated_at", now)
    e.created_at = kwargs.get("created_at", now)
    # Support device relationship loading
    e.device = kwargs.get("device")
    return e


def _make_db_override(mock_session):
    """Return a dependency function that yields the mock session."""
    async def _override():
        yield mock_session
    return _override


def _build_app(mock_session):
    """Build a FastAPI app with mocked DB dependency."""
    from src.database import get_db
    from src.devices_endpoints import router

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = _make_db_override(mock_session)
    return app


def _build_unshadowed_app(mock_session, endpoint_fn, path, method="get"):
    """Build a FastAPI app with a single endpoint to avoid route-shadowing.

    Routes like /api/devices/health-summary are shadowed by /api/devices/{device_id}
    (registered first in devices_endpoints.py). This helper mounts the endpoint
    function directly so its logic can be tested in isolation.
    """
    from src.database import get_db

    app = FastAPI()
    getattr(app, method)(path)(endpoint_fn)
    app.dependency_overrides[get_db] = _make_db_override(mock_session)
    return app


def _mock_scalars_all(mock_session, items):
    """Configure mock_session.execute to return items via scalars().all()."""
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = items
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute = AsyncMock(return_value=mock_result)


def _mock_scalar(mock_session, value):
    """Configure mock_session.execute to return a scalar value."""
    mock_result = MagicMock()
    mock_result.scalar.return_value = value
    mock_session.execute = AsyncMock(return_value=mock_result)


# ===========================================================================
# Integration Analytics
# ===========================================================================


class TestIntegrationPerformance:
    """GET /api/integrations/{platform}/performance"""

    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_session = AsyncMock()
        app = _build_app(mock_session)

        # Mock InfluxDB
        mock_query_api = MagicMock()
        mock_query_api.query.return_value = []  # No records

        mock_client = MagicMock()
        mock_client.query_api.return_value = mock_query_api

        with patch("src.devices_endpoints._get_shared_influxdb_client", return_value=mock_client):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get("/api/integrations/hue/performance")

        assert resp.status_code == 200
        data = resp.json()
        assert data["platform"] == "hue"
        assert "events_per_minute" in data
        assert "error_rate" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_influxdb_error_returns_defaults(self):
        mock_session = AsyncMock()
        app = _build_app(mock_session)

        with patch("src.devices_endpoints._get_shared_influxdb_client", side_effect=Exception("InfluxDB down")):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get("/api/integrations/hue/performance")

        assert resp.status_code == 200
        data = resp.json()
        assert data["events_per_minute"] == 0
        assert "error" in data


class TestIntegrationAnalytics:
    """GET /api/integrations/{platform}/analytics"""

    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_session = AsyncMock()

        # We need execute to return different results for different queries
        call_count = 0

        async def _multi_execute(query, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                # device count
                result.scalar.return_value = 5
            elif call_count == 2:
                # entity count
                result.scalar.return_value = 12
            else:
                # domain breakdown
                row1 = MagicMock()
                row1.domain = "light"
                row1.count = 8
                row2 = MagicMock()
                row2.domain = "sensor"
                row2.count = 4
                result.__iter__ = MagicMock(return_value=iter([row1, row2]))
            return result

        mock_session.execute = AsyncMock(side_effect=_multi_execute)
        app = _build_app(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/integrations/hue/analytics")

        assert resp.status_code == 200
        data = resp.json()
        assert data["platform"] == "hue"
        assert data["device_count"] == 5
        assert data["entity_count"] == 12

    @pytest.mark.asyncio
    async def test_unknown_platform_returns_zero_counts(self):
        mock_session = AsyncMock()

        async def _zero_execute(query, *args, **kwargs):
            result = MagicMock()
            result.scalar.return_value = 0
            result.__iter__ = MagicMock(return_value=iter([]))
            return result

        mock_session.execute = AsyncMock(side_effect=_zero_execute)
        app = _build_app(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/integrations/nonexistent/analytics")

        assert resp.status_code == 200
        assert resp.json()["device_count"] == 0


class TestListIntegrations:
    """GET /api/integrations"""

    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_session = AsyncMock()
        app = _build_app(mock_session)

        mock_influx = MagicMock()
        mock_influx.is_connected = True
        mock_influx._execute_query = AsyncMock(return_value=[
            {"entry_id": "e1", "domain": "hue", "title": "Philips Hue",
             "state": "loaded", "version": 1, "_time": "2026-01-01T00:00:00Z"}
        ])

        with patch("src.devices_endpoints.influxdb_client", mock_influx):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get("/api/integrations")

        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["integrations"][0]["domain"] == "hue"

    @pytest.mark.asyncio
    async def test_influxdb_failure_500(self):
        mock_session = AsyncMock()
        app = _build_app(mock_session)

        mock_influx = MagicMock()
        mock_influx.is_connected = False
        mock_influx.connect = AsyncMock(side_effect=Exception("connection refused"))

        with patch("src.devices_endpoints.influxdb_client", mock_influx):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get("/api/integrations")

        assert resp.status_code == 500


# ===========================================================================
# Bulk Upsert Endpoints
# ===========================================================================


class TestBulkUpsertDevices:
    """POST /internal/devices/bulk_upsert"""

    @pytest.mark.asyncio
    async def test_empty_list(self):
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.flush = AsyncMock()
        app = _build_app(mock_session)

        with patch("src.devices_endpoints.get_device_database_service"):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post("/internal/devices/bulk_upsert", json=[])

        assert resp.status_code == 200
        assert resp.json()["upserted"] == 0

    @pytest.mark.asyncio
    async def test_single_device_insert(self):
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.flush = AsyncMock()
        mock_session.add = MagicMock()

        # First execute returns existing device check (None = new)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        app = _build_app(mock_session)

        mock_db_service = MagicMock()
        mock_db_service.update_device_from_database = AsyncMock(return_value={})

        with patch("src.devices_endpoints.get_device_database_service", return_value=mock_db_service):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post("/internal/devices/bulk_upsert", json=[
                    {"id": "dev-new", "name": "New Device", "manufacturer": "Test", "model": "X"}
                ])

        assert resp.status_code == 200
        assert resp.json()["upserted"] == 1
        assert resp.json()["success"] is True

    @pytest.mark.asyncio
    async def test_device_without_id_skipped(self):
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.flush = AsyncMock()
        app = _build_app(mock_session)

        with patch("src.devices_endpoints.get_device_database_service"):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post("/internal/devices/bulk_upsert", json=[
                    {"name": "No ID Device"}
                ])

        assert resp.status_code == 200
        assert resp.json()["upserted"] == 0

    @pytest.mark.asyncio
    async def test_update_existing_device(self):
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.flush = AsyncMock()

        existing_device = _make_mock_device(device_id="dev-exist")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_device
        mock_session.execute = AsyncMock(return_value=mock_result)

        app = _build_app(mock_session)

        mock_db_service = MagicMock()
        mock_db_service.update_device_from_database = AsyncMock(return_value={})

        with patch("src.devices_endpoints.get_device_database_service", return_value=mock_db_service):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post("/internal/devices/bulk_upsert", json=[
                    {"id": "dev-exist", "name": "Updated Name"}
                ])

        assert resp.status_code == 200
        assert resp.json()["upserted"] == 1


class TestBulkUpsertEntities:
    """POST /internal/entities/bulk_upsert"""

    @pytest.mark.asyncio
    async def test_empty_list(self):
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.merge = AsyncMock()

        # Pre-fetch device_ids
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        app = _build_app(mock_session)

        with patch("src.devices_endpoints.get_entity_enrichment_service") as mock_enrich:
            mock_enrich.return_value.get_available_services_for_domain = AsyncMock(return_value=None)
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post("/internal/entities/bulk_upsert", json=[])

        assert resp.status_code == 200
        assert resp.json()["upserted"] == 0

    @pytest.mark.asyncio
    async def test_single_entity_upsert(self):
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.merge = AsyncMock()

        call_count = 0

        async def _multi_execute(query, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                # Pre-fetch device_ids
                result.fetchall.return_value = [("dev-001",)]
            else:
                # Other queries (classifier, enrichment)
                mock_scalars = MagicMock()
                mock_scalars.all.return_value = []
                result.scalars.return_value = mock_scalars
            return result

        mock_session.execute = AsyncMock(side_effect=_multi_execute)
        app = _build_app(mock_session)

        mock_enrichment = MagicMock()
        mock_enrichment.get_available_services_for_domain = AsyncMock(return_value=["turn_on"])
        mock_enrichment.enrich_entity_capabilities = AsyncMock(return_value={})

        mock_classifier = MagicMock()
        mock_classifier.classify_device_from_domains = AsyncMock(return_value={})

        with (
            patch("src.devices_endpoints.get_entity_enrichment_service", return_value=mock_enrichment),
            patch("src.devices_endpoints.get_classifier_service", return_value=mock_classifier),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post("/internal/entities/bulk_upsert", json=[
                    {"entity_id": "light.kitchen", "device_id": "dev-001", "platform": "hue"}
                ])

        assert resp.status_code == 200
        assert resp.json()["upserted"] == 1

    @pytest.mark.asyncio
    async def test_entity_without_id_skipped(self):
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.merge = AsyncMock()

        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        app = _build_app(mock_session)

        mock_enrichment = MagicMock()
        mock_enrichment.get_available_services_for_domain = AsyncMock(return_value=None)

        mock_classifier = MagicMock()

        with (
            patch("src.devices_endpoints.get_entity_enrichment_service", return_value=mock_enrichment),
            patch("src.devices_endpoints.get_classifier_service", return_value=mock_classifier),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post("/internal/entities/bulk_upsert", json=[
                    {"platform": "hue"}  # missing entity_id
                ])

        assert resp.status_code == 200
        assert resp.json()["upserted"] == 0


class TestBulkUpsertServices:
    """POST /internal/services/bulk_upsert"""

    @pytest.mark.asyncio
    async def test_empty_dict(self):
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        app = _build_app(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/internal/services/bulk_upsert", json={})

        assert resp.status_code == 200
        assert resp.json()["upserted"] == 0

    @pytest.mark.asyncio
    async def test_single_service_insert(self):
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.add = MagicMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # new service
        mock_session.execute = AsyncMock(return_value=mock_result)

        app = _build_app(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/internal/services/bulk_upsert", json={
                "light": {
                    "turn_on": {"name": "Turn On", "description": "Turn on a light"}
                }
            })

        assert resp.status_code == 200
        assert resp.json()["upserted"] == 1

    @pytest.mark.asyncio
    async def test_update_existing_service(self):
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        existing = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_session.execute = AsyncMock(return_value=mock_result)

        app = _build_app(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/internal/services/bulk_upsert", json={
                "light": {
                    "turn_on": {"name": "Turn On Updated", "description": "Updated desc"}
                }
            })

        assert resp.status_code == 200
        assert resp.json()["upserted"] == 1

    @pytest.mark.asyncio
    async def test_empty_domain_services_zero_upserts(self):
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        app = _build_app(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/internal/services/bulk_upsert", json={
                "light": {}  # valid format, no services to upsert
            })

        assert resp.status_code == 200
        assert resp.json()["upserted"] == 0


# ===========================================================================
# Device Health
# ===========================================================================


class TestDeviceHealth:
    """GET /api/devices/{device_id}/health"""

    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_session = AsyncMock()
        device = _make_mock_device()
        mock_session.get = AsyncMock(return_value=device)

        entities = [_make_mock_entity()]
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = entities
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        app = _build_app(mock_session)

        mock_health = MagicMock()
        mock_health.get_device_health = AsyncMock(return_value={
            "device_id": "dev-001",
            "overall_status": "healthy",
            "issues": []
        })

        with patch("src.devices_endpoints.get_health_service", return_value=mock_health):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get("/api/devices/dev-001/health")

        assert resp.status_code == 200
        assert resp.json()["overall_status"] == "healthy"

    @pytest.mark.asyncio
    async def test_404_missing_device(self):
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=None)
        app = _build_app(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/devices/nonexistent/health")

        assert resp.status_code == 404


class TestHealthSummary:
    """GET /api/devices/health-summary

    Note: This route is shadowed by /api/devices/{device_id} in production
    (registered first in devices_endpoints.py). Tests use _build_unshadowed_app
    to test the endpoint logic in isolation.
    """

    @pytest.mark.asyncio
    async def test_happy_path(self):
        from src.devices_endpoints import get_health_summary

        mock_session = AsyncMock()

        device1 = _make_mock_device(device_id="d1")
        device2 = _make_mock_device(device_id="d2")

        call_count = 0

        async def _multi_execute(query, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            mock_scalars = MagicMock()
            if call_count == 1:
                mock_scalars.all.return_value = [device1, device2]
            else:
                mock_scalars.all.return_value = []
            result.scalars.return_value = mock_scalars
            return result

        mock_session.execute = AsyncMock(side_effect=_multi_execute)
        app = _build_unshadowed_app(mock_session, get_health_summary, "/api/devices/health-summary")

        mock_health = MagicMock()
        mock_health.get_device_health = AsyncMock(return_value={
            "overall_status": "healthy", "issues": []
        })

        with patch("src.devices_endpoints.get_health_service", return_value=mock_health):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get("/api/devices/health-summary")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_devices"] == 2
        assert data["healthy_devices"] == 2


class TestMaintenanceAlerts:
    """GET /api/devices/maintenance-alerts

    Note: Route shadowed by /api/devices/{device_id} in production.
    Tests use _build_unshadowed_app.
    """

    @pytest.mark.asyncio
    async def test_returns_alerts(self):
        from src.devices_endpoints import get_maintenance_alerts

        mock_session = AsyncMock()

        device1 = _make_mock_device(device_id="d1")

        call_count = 0

        async def _multi_execute(query, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            mock_scalars = MagicMock()
            if call_count == 1:
                mock_scalars.all.return_value = [device1]
            else:
                mock_scalars.all.return_value = []
            result.scalars.return_value = mock_scalars
            return result

        mock_session.execute = AsyncMock(side_effect=_multi_execute)
        app = _build_unshadowed_app(mock_session, get_maintenance_alerts, "/api/devices/maintenance-alerts")

        mock_health = MagicMock()
        mock_health.get_device_health = AsyncMock(return_value={
            "overall_status": "warning",
            "issues": [{"type": "battery_low", "severity": "warning", "message": "Battery at 5%"}]
        })

        with patch("src.devices_endpoints.get_health_service", return_value=mock_health):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get("/api/devices/maintenance-alerts")

        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 1
        assert data["alerts"][0]["issue_type"] == "battery_low"


# ===========================================================================
# Power Analysis
# ===========================================================================


class TestPowerAnalysis:
    """GET /api/devices/{device_id}/power-analysis"""

    @pytest.mark.asyncio
    async def test_happy_path_with_spec(self):
        mock_session = AsyncMock()
        device = _make_mock_device(power_consumption_active_w=60.0)
        mock_session.get = AsyncMock(return_value=device)

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [_make_mock_entity()]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        app = _build_app(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/devices/dev-001/power-analysis")

        assert resp.status_code == 200
        data = resp.json()
        assert data["device_id"] == "dev-001"
        assert data["spec_power_w"] == 60.0

    @pytest.mark.asyncio
    async def test_no_entities_returns_message(self):
        mock_session = AsyncMock()
        device = _make_mock_device()
        mock_session.get = AsyncMock(return_value=device)

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        app = _build_app(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/devices/dev-001/power-analysis")

        assert resp.status_code == 200
        assert "No entities found" in resp.json()["message"]

    @pytest.mark.asyncio
    async def test_404_missing_device(self):
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=None)
        app = _build_app(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/devices/nonexistent/power-analysis")

        assert resp.status_code == 404


class TestDeviceEfficiency:
    """GET /api/devices/{device_id}/efficiency"""

    @pytest.mark.asyncio
    async def test_no_power_spec(self):
        mock_session = AsyncMock()
        device = _make_mock_device(power_consumption_active_w=None)
        mock_session.get = AsyncMock(return_value=device)
        app = _build_app(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/devices/dev-001/efficiency")

        assert resp.status_code == 200
        data = resp.json()
        assert data["efficiency_score"] is None
        assert "No power specification" in data["message"]

    @pytest.mark.asyncio
    async def test_with_power_spec(self):
        mock_session = AsyncMock()
        device = _make_mock_device(power_consumption_active_w=60.0)
        mock_session.get = AsyncMock(return_value=device)
        app = _build_app(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/devices/dev-001/efficiency")

        assert resp.status_code == 200
        data = resp.json()
        assert data["spec_power_w"] == 60.0

    @pytest.mark.asyncio
    async def test_404_missing(self):
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=None)
        app = _build_app(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/devices/missing/efficiency")

        assert resp.status_code == 404


class TestPowerAnomalies:
    """GET /api/devices/power-anomalies

    Note: Route shadowed by /api/devices/{device_id} in production.
    Tests use _build_unshadowed_app.
    """

    @pytest.mark.asyncio
    async def test_no_anomalies(self):
        from src.devices_endpoints import get_power_anomalies

        mock_session = AsyncMock()
        _mock_scalars_all(mock_session, [])
        app = _build_unshadowed_app(mock_session, get_power_anomalies, "/api/devices/power-anomalies")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/devices/power-anomalies")

        assert resp.status_code == 200
        assert resp.json()["count"] == 0


# ===========================================================================
# Classification
# ===========================================================================


class TestClassifyDevice:
    """POST /api/devices/{device_id}/classify"""

    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_session = AsyncMock()
        device = _make_mock_device()
        mock_session.get = AsyncMock(return_value=device)
        mock_session.commit = AsyncMock()

        entities = [_make_mock_entity(domain="light")]
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = entities
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        app = _build_app(mock_session)

        mock_classifier = MagicMock()
        mock_classifier.classify_device_from_domains = AsyncMock(return_value={
            "device_type": "smart_bulb",
            "device_category": "lighting"
        })

        with patch("src.devices_endpoints.get_classifier_service", return_value=mock_classifier):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post("/api/devices/dev-001/classify")

        assert resp.status_code == 200
        data = resp.json()
        assert data["device_id"] == "dev-001"

    @pytest.mark.asyncio
    async def test_404_missing_device(self):
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=None)
        app = _build_app(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/devices/missing/classify")

        assert resp.status_code == 404


class TestClassifyAll:
    """POST /api/devices/classify-all"""

    @pytest.mark.asyncio
    async def test_all_already_classified(self):
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        _mock_scalars_all(mock_session, [])  # no unclassified devices
        app = _build_app(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/devices/classify-all")

        assert resp.status_code == 200
        assert resp.json()["classified"] == 0


class TestLinkEntities:
    """POST /api/devices/link-entities"""

    @pytest.mark.asyncio
    async def test_no_ha_config(self):
        mock_session = AsyncMock()
        _mock_scalars_all(mock_session, [])
        app = _build_app(mock_session)

        with (
            patch.dict("os.environ", {"HA_URL": "", "HA_TOKEN": ""}, clear=False),
            patch("src.devices_endpoints.os.getenv", return_value=None),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post("/api/devices/link-entities")

        assert resp.status_code == 503


# ===========================================================================
# Setup Assistant
# ===========================================================================


class TestSetupGuide:
    """GET /api/devices/{device_id}/setup-guide"""

    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_session = AsyncMock()
        device = _make_mock_device(device_type="smart_bulb", integration="hue")
        mock_session.get = AsyncMock(return_value=device)
        app = _build_app(mock_session)

        mock_assistant = MagicMock()
        mock_assistant.generate_setup_guide.return_value = {
            "device_id": "dev-001",
            "steps": ["Step 1: Plug in", "Step 2: Pair"]
        }

        with patch("src.devices_endpoints.get_setup_assistant", return_value=mock_assistant):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get("/api/devices/dev-001/setup-guide")

        assert resp.status_code == 200
        assert "steps" in resp.json()

    @pytest.mark.asyncio
    async def test_404_missing(self):
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=None)
        app = _build_app(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/devices/missing/setup-guide")

        assert resp.status_code == 404


class TestSetupIssues:
    """GET /api/devices/{device_id}/setup-issues"""

    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_session = AsyncMock()
        device = _make_mock_device()
        mock_session.get = AsyncMock(return_value=device)

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [_make_mock_entity()]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        app = _build_app(mock_session)

        mock_assistant = MagicMock()
        mock_assistant.detect_setup_issues = AsyncMock(return_value=[
            {"type": "missing_area", "message": "No area assigned"}
        ])

        with patch("src.devices_endpoints.get_setup_assistant", return_value=mock_assistant):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get("/api/devices/dev-001/setup-issues")

        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["issues"][0]["type"] == "missing_area"

    @pytest.mark.asyncio
    async def test_404_missing(self):
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=None)
        app = _build_app(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/devices/missing/setup-issues")

        assert resp.status_code == 404


class TestSetupComplete:
    """POST /api/devices/{device_id}/setup-complete"""

    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_session = AsyncMock()
        device = _make_mock_device()
        mock_session.get = AsyncMock(return_value=device)
        app = _build_app(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/devices/dev-001/setup-complete")

        assert resp.status_code == 200
        data = resp.json()
        assert data["setup_complete"] is True
        assert data["device_id"] == "dev-001"

    @pytest.mark.asyncio
    async def test_404_missing(self):
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=None)
        app = _build_app(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/devices/missing/setup-complete")

        assert resp.status_code == 404


# ===========================================================================
# Capability Discovery
# ===========================================================================


class TestDiscoverCapabilities:
    """POST /api/devices/{device_id}/discover-capabilities"""

    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_session = AsyncMock()
        device = _make_mock_device()
        mock_session.get = AsyncMock(return_value=device)
        mock_session.commit = AsyncMock()

        entities = [_make_mock_entity()]
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = entities
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        app = _build_app(mock_session)

        mock_cap_service = MagicMock()
        mock_cap_service.discover_device_capabilities = AsyncMock(return_value={
            "capabilities": ["brightness", "color_temp"],
            "features": {"brightness": True},
            "device_classes": ["light"],
            "state_classes": []
        })
        mock_cap_service.format_capabilities_for_storage.return_value = '{"brightness": true}'

        with patch("src.devices_endpoints.get_capability_service", return_value=mock_cap_service):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post("/api/devices/dev-001/discover-capabilities")

        assert resp.status_code == 200
        data = resp.json()
        assert "brightness" in data["capabilities"]

    @pytest.mark.asyncio
    async def test_no_entities(self):
        mock_session = AsyncMock()
        device = _make_mock_device()
        mock_session.get = AsyncMock(return_value=device)

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        app = _build_app(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/devices/dev-001/discover-capabilities")

        assert resp.status_code == 200
        assert resp.json()["capabilities"] == []

    @pytest.mark.asyncio
    async def test_404_missing(self):
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=None)
        app = _build_app(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/api/devices/missing/discover-capabilities")

        assert resp.status_code == 404


# ===========================================================================
# Entity Enrichment
# ===========================================================================


class TestEnrichEntities:
    """POST /api/entities/enrich"""

    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        entity = _make_mock_entity(capabilities=None, available_services=None)

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [entity]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        app = _build_app(mock_session)

        mock_enrichment = MagicMock()
        mock_enrichment.enrich_entity_capabilities = AsyncMock(return_value={
            "supported_features": 44,
            "capabilities": ["brightness"]
        })
        mock_enrichment.get_available_services_for_domain = AsyncMock(return_value=["turn_on"])

        with patch("src.devices_endpoints.get_entity_enrichment_service", return_value=mock_enrichment):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.post("/api/entities/enrich")

        assert resp.status_code == 200
        assert resp.json()["enriched"] >= 0


# ===========================================================================
# Recommendations
# ===========================================================================


class TestDeviceRecommendations:
    """GET /api/devices/recommendations

    Note: Route shadowed by /api/devices/{device_id} in production.
    Tests use _build_unshadowed_app.
    """

    @pytest.mark.asyncio
    async def test_happy_path(self):
        from src.devices_endpoints import get_device_recommendations

        mock_session = AsyncMock()
        _mock_scalars_all(mock_session, [_make_mock_device()])
        app = _build_unshadowed_app(mock_session, get_device_recommendations, "/api/devices/recommendations")

        mock_recommender = MagicMock()
        mock_recommender.recommend_devices = AsyncMock(return_value=[
            {"name": "Smart Bulb Pro", "score": 0.95}
        ])

        with patch("src.devices_endpoints.get_recommender_service", return_value=mock_recommender):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get("/api/devices/recommendations?device_type=light")

        assert resp.status_code == 200
        data = resp.json()
        assert data["device_type"] == "light"
        assert data["count"] == 1

    @pytest.mark.asyncio
    async def test_missing_device_type_422(self):
        from src.devices_endpoints import get_device_recommendations

        mock_session = AsyncMock()
        app = _build_unshadowed_app(mock_session, get_device_recommendations, "/api/devices/recommendations")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/devices/recommendations")

        assert resp.status_code == 422  # missing required query param


class TestCompareDevices:
    """GET /api/devices/compare

    Note: Route shadowed by /api/devices/{device_id} in production.
    Tests use _build_unshadowed_app.
    """

    @pytest.mark.asyncio
    async def test_happy_path(self):
        from src.devices_endpoints import compare_devices

        mock_session = AsyncMock()

        d1 = _make_mock_device(device_id="d1", name="Light A")
        d2 = _make_mock_device(device_id="d2", name="Light B")
        _mock_scalars_all(mock_session, [d1, d2])
        app = _build_unshadowed_app(mock_session, compare_devices, "/api/devices/compare")

        mock_recommender = MagicMock()
        mock_recommender.compare_devices.return_value = {
            "comparison": [{"device_id": "d1"}, {"device_id": "d2"}]
        }

        with patch("src.devices_endpoints.get_recommender_service", return_value=mock_recommender):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get("/api/devices/compare?device_ids=d1,d2")

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_less_than_2_ids(self):
        from src.devices_endpoints import compare_devices

        mock_session = AsyncMock()
        app = _build_unshadowed_app(mock_session, compare_devices, "/api/devices/compare")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/devices/compare?device_ids=d1")

        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_not_all_found(self):
        from src.devices_endpoints import compare_devices

        mock_session = AsyncMock()
        _mock_scalars_all(mock_session, [_make_mock_device(device_id="d1")])  # only 1 found
        app = _build_unshadowed_app(mock_session, compare_devices, "/api/devices/compare")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/devices/compare?device_ids=d1,d2")

        assert resp.status_code == 404


class TestSimilarDevices:
    """GET /api/devices/similar/{device_id}"""

    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_session = AsyncMock()
        device = _make_mock_device()
        mock_session.get = AsyncMock(return_value=device)
        _mock_scalars_all(mock_session, [device, _make_mock_device(device_id="d2")])
        app = _build_app(mock_session)

        mock_recommender = MagicMock()
        mock_recommender.find_similar_devices.return_value = [
            {"device_id": "d2", "similarity": 0.8}
        ]

        with patch("src.devices_endpoints.get_recommender_service", return_value=mock_recommender):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get("/api/devices/similar/dev-001")

        assert resp.status_code == 200
        data = resp.json()
        assert data["reference_device_id"] == "dev-001"
        assert data["count"] == 1

    @pytest.mark.asyncio
    async def test_404_missing(self):
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=None)
        app = _build_app(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/devices/similar/missing")

        assert resp.status_code == 404


# ===========================================================================
# Entity Relationship Routes
# ===========================================================================


class TestEntitiesByDevice:
    """GET /api/entities/by-device/{device_id}"""

    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_session = AsyncMock()
        app = _build_app(mock_session)

        mock_entry = MagicMock()
        mock_entry.entity_id = "light.living_room"
        mock_entry.to_dict.return_value = {"entity_id": "light.living_room", "device_id": "dev-001"}

        with patch("src.devices_endpoints.EntityRegistry") as MockRegistry:
            instance = MockRegistry.return_value
            instance.get_entities_by_device = AsyncMock(return_value=[mock_entry])

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get("/api/entities/by-device/dev-001")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["count"] == 1

    @pytest.mark.asyncio
    async def test_empty_result(self):
        mock_session = AsyncMock()
        app = _build_app(mock_session)

        with patch("src.devices_endpoints.EntityRegistry") as MockRegistry:
            instance = MockRegistry.return_value
            instance.get_entities_by_device = AsyncMock(return_value=[])

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get("/api/entities/by-device/dev-999")

        assert resp.status_code == 200
        assert resp.json()["count"] == 0


class TestSiblingEntities:
    """GET /api/entities/{entity_id}/siblings"""

    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_session = AsyncMock()
        app = _build_app(mock_session)

        sibling = MagicMock()
        sibling.entity_id = "sensor.living_room_temp"
        sibling.to_dict.return_value = {"entity_id": "sensor.living_room_temp"}

        with patch("src.devices_endpoints.EntityRegistry") as MockRegistry:
            instance = MockRegistry.return_value
            instance.get_sibling_entities = AsyncMock(return_value=[sibling])

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get("/api/entities/light.living_room/siblings")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True


class TestDeviceForEntity:
    """GET /api/entities/{entity_id}/device"""

    @pytest.mark.asyncio
    async def test_found(self):
        mock_session = AsyncMock()
        app = _build_app(mock_session)

        device = _make_mock_device()

        with patch("src.devices_endpoints.EntityRegistry") as MockRegistry:
            instance = MockRegistry.return_value
            instance.get_device_for_entity = AsyncMock(return_value=device)

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get("/api/entities/light.living_room/device")

        assert resp.status_code == 200
        data = resp.json()
        assert data["device"]["device_id"] == "dev-001"

    @pytest.mark.asyncio
    async def test_404_no_device(self):
        mock_session = AsyncMock()
        app = _build_app(mock_session)

        with patch("src.devices_endpoints.EntityRegistry") as MockRegistry:
            instance = MockRegistry.return_value
            instance.get_device_for_entity = AsyncMock(return_value=None)

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get("/api/entities/orphan.entity/device")

        assert resp.status_code == 404


class TestEntitiesByArea:
    """GET /api/entities/by-area/{area_id}"""

    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_session = AsyncMock()
        app = _build_app(mock_session)

        entry = MagicMock()
        entry.to_dict.return_value = {"entity_id": "light.kitchen", "area_id": "kitchen"}

        with patch("src.devices_endpoints.EntityRegistry") as MockRegistry:
            instance = MockRegistry.return_value
            instance.get_entities_in_area = AsyncMock(return_value=[entry])

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get("/api/entities/by-area/kitchen")

        assert resp.status_code == 200
        assert resp.json()["count"] == 1


class TestEntitiesByConfigEntry:
    """GET /api/entities/by-config-entry/{config_entry_id}"""

    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_session = AsyncMock()
        app = _build_app(mock_session)

        entry = MagicMock()
        entry.to_dict.return_value = {"entity_id": "light.kitchen", "config_entry_id": "cfg-001"}

        with patch("src.devices_endpoints.EntityRegistry") as MockRegistry:
            instance = MockRegistry.return_value
            instance.get_entities_by_config_entry = AsyncMock(return_value=[entry])

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get("/api/entities/by-config-entry/cfg-001")

        assert resp.status_code == 200
        assert resp.json()["count"] == 1


class TestDeviceHierarchy:
    """GET /api/devices/{device_id}/hierarchy"""

    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_session = AsyncMock()
        app = _build_app(mock_session)

        with patch("src.devices_endpoints.EntityRegistry") as MockRegistry:
            instance = MockRegistry.return_value
            instance.get_device_hierarchy = AsyncMock(return_value={
                "device_id": "dev-001",
                "parent": None,
                "children": ["dev-002"]
            })

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get("/api/devices/dev-001/hierarchy")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["device_id"] == "dev-001"


# ===========================================================================
# Reliability
# ===========================================================================


class TestDeviceReliability:
    """GET /api/devices/reliability

    Note: Route shadowed by /api/devices/{device_id} in production.
    Tests use _build_unshadowed_app.
    """

    @pytest.mark.asyncio
    async def test_happy_path(self):
        from src.devices_endpoints import get_device_reliability

        mock_session = AsyncMock()
        app = _build_unshadowed_app(mock_session, get_device_reliability, "/api/devices/reliability")

        mock_query_api = MagicMock()
        mock_query_api.query.return_value = []

        mock_client = MagicMock()
        mock_client.query_api.return_value = mock_query_api

        with patch("src.devices_endpoints._get_shared_influxdb_client", return_value=mock_client):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get("/api/devices/reliability")

        assert resp.status_code == 200
        data = resp.json()
        assert data["period"] == "7d"
        assert data["group_by"] == "manufacturer"
        assert "reliability_data" in data

    @pytest.mark.asyncio
    async def test_custom_params(self):
        from src.devices_endpoints import get_device_reliability

        mock_session = AsyncMock()
        app = _build_unshadowed_app(mock_session, get_device_reliability, "/api/devices/reliability")

        mock_query_api = MagicMock()
        mock_query_api.query.return_value = []

        mock_client = MagicMock()
        mock_client.query_api.return_value = mock_query_api

        with patch("src.devices_endpoints._get_shared_influxdb_client", return_value=mock_client):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                resp = await c.get("/api/devices/reliability?period=30d&group_by=model")

        assert resp.status_code == 200
        data = resp.json()
        assert data["period"] == "30d"
        assert data["group_by"] == "model"


# ===========================================================================
# Clear Devices
# ===========================================================================


class TestClearDevices:
    """DELETE /internal/devices/clear"""

    @pytest.mark.asyncio
    async def test_happy_path(self):
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        entities_result = MagicMock()
        entities_result.rowcount = 10
        devices_result = MagicMock()
        devices_result.rowcount = 5

        call_count = 0

        async def _multi_execute(query, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return entities_result
            return devices_result

        mock_session.execute = AsyncMock(side_effect=_multi_execute)
        app = _build_app(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.delete("/internal/devices/clear")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["devices_deleted"] == 5
        assert data["entities_deleted"] == 10

    @pytest.mark.asyncio
    async def test_empty_db(self):
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        empty_result = MagicMock()
        empty_result.rowcount = 0
        mock_session.execute = AsyncMock(return_value=empty_result)

        app = _build_app(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.delete("/internal/devices/clear")

        assert resp.status_code == 200
        assert resp.json()["devices_deleted"] == 0
        assert resp.json()["entities_deleted"] == 0
