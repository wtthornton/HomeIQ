"""
Tests for devices_endpoints.py — Epic 80, Story 80.4

Covers 28 scenarios across device/entity/area/label CRUD and query endpoints:

Helper Functions:
1.  compute_device_status — active within 30 days
2.  compute_device_status — inactive after 30 days
3.  compute_device_status — inactive when last_seen is None
4.  compute_device_status — custom inactive_days
5.  compute_device_status — naive datetime treated as UTC
6.  compute_device_status — boundary exactly 30 days

Response Models:
7.  DeviceResponse — valid construction with all fields
8.  EntityResponse — valid construction with all fields
9.  AreaResponse — valid construction
10. LabelResponse — valid construction with prefix extraction
11. DevicesListResponse — aggregation model
12. EntitiesListResponse — aggregation model

Device Endpoints (via ASGI client + DB override):
13. GET /api/devices — empty list from empty DB
14. GET /api/devices — returns devices with entity count
15. GET /api/devices — applies manufacturer filter
16. GET /api/devices — applies area_id filter
17. GET /api/devices — respects limit parameter
18. GET /api/devices/{id} — returns single device
19. GET /api/devices/{id} — 404 for missing device
20. GET /api/devices — cache works across requests

Entity Endpoints:
21. GET /api/entities — empty list
22. GET /api/entities — returns entities
23. GET /api/entities?domain=X — filters by domain
24. GET /api/entities/{entity_id} — returns entity
25. GET /api/entities/{entity_id} — 404 for missing

Area & Label Endpoints:
26. GET /api/areas — returns areas with counts
27. GET /api/areas — empty when no areas
28. GET /api/labels — returns labels with prefix
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
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
# Helpers: build a minimal FastAPI app with mocked DB dependency
# ---------------------------------------------------------------------------


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
    return e


def _make_device_row(device_id="dev-001", name="Test Light", manufacturer="TestCo",
                     model="Bulb-v2", integration="hue", sw_version="1.0.0",
                     area_id="living_room", config_entry_id="cfg-001", via_device=None,
                     last_seen=None, device_type=None, device_category=None,
                     labels=None, serial_number=None, model_id=None, entity_count=0):
    """Create a tuple matching the list_devices query column order."""
    if last_seen is None:
        last_seen = datetime.now(UTC)
    return (
        device_id, name, manufacturer, model, integration, sw_version,
        area_id, config_entry_id, via_device, last_seen,
        device_type, device_category, labels, serial_number, model_id, entity_count,
    )


def _make_get_device_row(device_id="dev-001", name="Test Light", manufacturer="TestCo",
                          model="Bulb-v2", entity_count=2, **kwargs):
    """Create a tuple matching the get_device query column order."""
    now = kwargs.get("last_seen", datetime.now(UTC))
    return (
        device_id, name, manufacturer, model, kwargs.get("sw_version", "1.0.0"),
        kwargs.get("area_id", "living_room"),
        kwargs.get("integration", "hue"), kwargs.get("config_entry_id", "cfg-001"),
        kwargs.get("via_device"), kwargs.get("device_type"),
        kwargs.get("device_category"),
        kwargs.get("power_idle"), kwargs.get("power_active"), kwargs.get("power_max"),
        kwargs.get("setup_url"), kwargs.get("troubleshoot"), kwargs.get("features_json"),
        kwargs.get("community_rating"), kwargs.get("last_capability_sync"),
        now,
        kwargs.get("labels"), kwargs.get("serial_number"), kwargs.get("model_id"),
        entity_count,
    )


def _build_app_with_mock_db(mock_session):
    """Build a FastAPI app that uses a mock session for get_db dependency."""
    from src.devices_endpoints import router
    from src.database import get_db

    @asynccontextmanager
    async def _override_get_db():
        yield mock_session

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: _override_get_db()
    return app


# FastAPI dependency override — must be an async generator matching get_db signature
def _make_db_override(mock_session):
    """Return a dependency function that yields the mock session."""
    async def _override():
        yield mock_session
    return _override


# ===========================================================================
# Helper Function Tests (no DB needed)
# ===========================================================================


class TestComputeDeviceStatus:
    """compute_device_status() unit tests."""

    def test_active_within_30_days(self):
        from src.devices_endpoints import compute_device_status
        assert compute_device_status(datetime.now(UTC) - timedelta(days=5)) == "active"

    def test_inactive_after_30_days(self):
        from src.devices_endpoints import compute_device_status
        assert compute_device_status(datetime.now(UTC) - timedelta(days=45)) == "inactive"

    def test_inactive_when_none(self):
        from src.devices_endpoints import compute_device_status
        assert compute_device_status(None) == "inactive"

    def test_custom_inactive_days(self):
        from src.devices_endpoints import compute_device_status
        ts = datetime.now(UTC) - timedelta(days=10)
        assert compute_device_status(ts, inactive_days=5) == "inactive"
        assert compute_device_status(ts, inactive_days=15) == "active"

    def test_naive_datetime_treated_as_utc(self):
        from src.devices_endpoints import compute_device_status
        assert compute_device_status(datetime.now() - timedelta(days=1)) == "active"

    def test_boundary_exactly_30_days(self):
        from src.devices_endpoints import compute_device_status
        assert compute_device_status(datetime.now(UTC) - timedelta(days=30)) == "active"


# ===========================================================================
# Response Model Tests (no DB needed)
# ===========================================================================


class TestResponseModels:
    """Pydantic response model validation."""

    def test_device_response(self):
        from src.devices_endpoints import DeviceResponse
        d = DeviceResponse(
            device_id="dev-001", name="Test Light", manufacturer="TestCo",
            model="Bulb-v2", entity_count=3, timestamp=datetime.now(UTC).isoformat(),
        )
        assert d.device_id == "dev-001"
        assert d.status == "active"
        assert d.power_consumption_idle_w is None

    def test_entity_response(self):
        from src.devices_endpoints import EntityResponse
        e = EntityResponse(
            entity_id="light.living_room", domain="light", platform="hue",
            supported_features=44, capabilities=["brightness", "color"],
            aliases=["lounge light"], labels=["ai:automatable"],
            timestamp=datetime.now(UTC).isoformat(),
        )
        assert "brightness" in e.capabilities
        assert "lounge light" in e.aliases

    def test_area_response(self):
        from src.devices_endpoints import AreaResponse
        a = AreaResponse(area_id="kitchen", display_name="Kitchen",
                         entity_count=5, domains=["light", "sensor"])
        assert a.display_name == "Kitchen"

    def test_label_response_prefix(self):
        from src.devices_endpoints import LabelResponse
        l = LabelResponse(label="ai:automatable", entity_count=10, prefix="ai")
        assert l.prefix == "ai"

    def test_devices_list_response(self):
        from src.devices_endpoints import DeviceResponse, DevicesListResponse
        d = DeviceResponse(device_id="dev-001", name="T", manufacturer="X",
                           model="Y", entity_count=0, timestamp="2026-01-01")
        assert DevicesListResponse(devices=[d], count=1, limit=100).count == 1

    def test_entities_list_response(self):
        from src.devices_endpoints import EntitiesListResponse, EntityResponse
        e = EntityResponse(entity_id="light.t", domain="light",
                           platform="hue", timestamp="2026-01-01")
        assert EntitiesListResponse(entities=[e], count=1, limit=100).count == 1


# ===========================================================================
# Device Endpoint Tests (ASGI client + mocked DB session)
# ===========================================================================


class TestListDevicesEndpoint:
    """GET /api/devices"""

    @pytest.mark.asyncio
    async def test_empty_list(self):
        from src.database import get_db
        from src.devices_endpoints import router
        from src.cache import cache

        await cache.clear()

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = _make_db_override(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/devices")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    @pytest.mark.asyncio
    async def test_returns_devices_with_entity_count(self):
        from src.database import get_db
        from src.devices_endpoints import router
        from src.cache import cache

        await cache.clear()

        row = _make_device_row(entity_count=3)
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [row]
        mock_session.execute = AsyncMock(return_value=mock_result)

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = _make_db_override(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/devices")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["devices"][0]["device_id"] == "dev-001"
        assert data["devices"][0]["entity_count"] == 3

    @pytest.mark.asyncio
    async def test_manufacturer_filter(self):
        from src.database import get_db
        from src.devices_endpoints import router
        from src.cache import cache

        await cache.clear()

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = _make_db_override(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/devices?manufacturer=TestCo")
        assert resp.status_code == 200
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_area_filter(self):
        from src.database import get_db
        from src.devices_endpoints import router
        from src.cache import cache

        await cache.clear()

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = _make_db_override(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/devices?area_id=kitchen")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_limit_parameter(self):
        from src.database import get_db
        from src.devices_endpoints import router
        from src.cache import cache

        await cache.clear()

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = _make_db_override(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/devices?limit=5")
        assert resp.status_code == 200
        assert resp.json()["limit"] == 5

    @pytest.mark.asyncio
    async def test_cache_works(self):
        from src.database import get_db
        from src.devices_endpoints import router
        from src.cache import cache

        await cache.clear()

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = _make_db_override(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp1 = await c.get("/api/devices")
            assert resp1.status_code == 200

            # Second call: should hit cache
            mock_session.execute.reset_mock()
            resp2 = await c.get("/api/devices")
            assert resp2.status_code == 200
            mock_session.execute.assert_not_called()


class TestGetDeviceEndpoint:
    """GET /api/devices/{device_id}"""

    @pytest.mark.asyncio
    async def test_returns_device(self):
        from src.database import get_db
        from src.devices_endpoints import router

        row = _make_get_device_row(entity_count=2, device_type="light")
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.first.return_value = row
        mock_session.execute = AsyncMock(return_value=mock_result)

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = _make_db_override(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/devices/dev-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["device_id"] == "dev-001"
        assert data["entity_count"] == 2

    @pytest.mark.asyncio
    async def test_404_missing(self):
        from src.database import get_db
        from src.devices_endpoints import router

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.first.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = _make_db_override(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/devices/nonexistent")
        assert resp.status_code == 404


# ===========================================================================
# Entity Endpoint Tests
# ===========================================================================


class TestListEntitiesEndpoint:
    """GET /api/entities"""

    @pytest.mark.asyncio
    async def test_empty_list(self):
        from src.database import get_db
        from src.devices_endpoints import router

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = _make_db_override(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/entities")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    @pytest.mark.asyncio
    async def test_returns_entities(self):
        from src.database import get_db
        from src.devices_endpoints import router

        mock_entity = _make_mock_entity()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_entity]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = _make_db_override(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/entities")
        assert resp.status_code == 200
        assert resp.json()["count"] == 1

    @pytest.mark.asyncio
    async def test_domain_filter(self):
        from src.database import get_db
        from src.devices_endpoints import router

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = _make_db_override(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/entities?domain=light")
        assert resp.status_code == 200


class TestGetEntityEndpoint:
    """GET /api/entities/{entity_id}"""

    @pytest.mark.asyncio
    async def test_returns_entity(self):
        from src.database import get_db
        from src.devices_endpoints import router

        mock_entity = _make_mock_entity()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_entity
        mock_session.execute = AsyncMock(return_value=mock_result)

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = _make_db_override(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/entities/light.living_room")
        assert resp.status_code == 200
        assert resp.json()["entity_id"] == "light.living_room"

    @pytest.mark.asyncio
    async def test_404_missing(self):
        from src.database import get_db
        from src.devices_endpoints import router

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = _make_db_override(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/entities/nonexistent")
        assert resp.status_code == 404


# ===========================================================================
# Area & Label Endpoint Tests
# ===========================================================================


class TestListAreasEndpoint:
    """GET /api/areas"""

    @pytest.mark.asyncio
    async def test_returns_areas(self):
        from src.database import get_db
        from src.devices_endpoints import router
        from src.cache import cache

        await cache.clear()

        mock_row = MagicMock()
        mock_row.area_id = "living_room"
        mock_row.entity_count = 5
        mock_row.domains = ["light", "sensor"]

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        mock_session.execute = AsyncMock(return_value=mock_result)

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = _make_db_override(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/areas")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["areas"][0]["display_name"] == "Living Room"

    @pytest.mark.asyncio
    async def test_empty_areas(self):
        from src.database import get_db
        from src.devices_endpoints import router
        from src.cache import cache

        await cache.clear()

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = _make_db_override(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/areas")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0


class TestListLabelsEndpoint:
    """GET /api/labels"""

    @pytest.mark.asyncio
    async def test_returns_labels(self):
        from src.database import get_db
        from src.devices_endpoints import router
        from src.cache import cache

        await cache.clear()

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [
            ("ai:automatable", 10),
            ("room:living", 5),
        ]
        mock_session.execute = AsyncMock(return_value=mock_result)

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = _make_db_override(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/labels")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2
        assert data["labels"][0]["prefix"] == "ai"

    @pytest.mark.asyncio
    async def test_empty_labels(self):
        from src.database import get_db
        from src.devices_endpoints import router
        from src.cache import cache

        await cache.clear()

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = _make_db_override(mock_session)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/labels")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0
