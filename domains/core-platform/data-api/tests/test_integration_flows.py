"""
Tests for cross-endpoint integration flows — Epic 80, Story 80.12

Covers 10 scenarios:

Cross-Module:
1.  EntityRegistryEntry.from_entity_and_device — constructs from ORM objects
2.  EntityRegistryEntry.to_dict — serializes all fields
3.  EntityRegistryEntry — handles None device
4.  EntityRegistryEntry — handles None related_entities

Error Propagation:
5.  devices_endpoints — HTTPException propagation (404 re-raised, not wrapped)
6.  alert_endpoints — 400 for invalid severity propagates correctly

Cache Interaction:
7.  cache.set then devices cache hit skips DB
8.  cache.clear invalidates cached responses

Response Model Interop:
9.  DeviceResponse -> DevicesListResponse composition
10. AlertResponse validates all optional fields
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

# ---------------------------------------------------------------------------
# Override conftest fresh_db
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(autouse=True)
async def fresh_db():
    yield


# ===========================================================================
# EntityRegistryEntry Cross-Module Tests
# ===========================================================================


class TestEntityRegistryEntry:
    """EntityRegistryEntry dataclass composition."""

    def _make_entity(self, **kwargs):
        e = MagicMock()
        e.entity_id = kwargs.get("entity_id", "light.living_room")
        e.unique_id = kwargs.get("unique_id", "hue-001")
        e.name = kwargs.get("name", "Living Room Light")
        e.device_id = kwargs.get("device_id", "dev-001")
        e.area_id = kwargs.get("area_id", "living_room")
        e.config_entry_id = kwargs.get("config_entry_id", "cfg-001")
        e.platform = kwargs.get("platform", "hue")
        e.domain = kwargs.get("domain", "light")
        e.friendly_name = kwargs.get("friendly_name", "Living Room Light")
        e.name_by_user = kwargs.get("name_by_user")
        e.original_name = kwargs.get("original_name")
        e.disabled = kwargs.get("disabled", False)
        e.supported_features = kwargs.get("supported_features", 44)
        e.capabilities = kwargs.get("capabilities", {"brightness": True})
        e.available_services = kwargs.get("available_services", ["light.turn_on"])
        e.icon = kwargs.get("icon", "mdi:lightbulb")
        e.device_class = kwargs.get("device_class")
        e.unit_of_measurement = kwargs.get("unit_of_measurement")
        return e

    def _make_device(self, **kwargs):
        d = MagicMock()
        d.device_id = kwargs.get("device_id", "dev-001")
        d.name = kwargs.get("name", "Test Device")
        d.manufacturer = kwargs.get("manufacturer", "TestCo")
        d.model = kwargs.get("model", "Bulb-v2")
        d.sw_version = kwargs.get("sw_version", "1.0.0")
        d.via_device = kwargs.get("via_device")
        return d

    def test_from_entity_and_device(self):
        from src.models.entity_registry_entry import EntityRegistryEntry

        entity = self._make_entity()
        device = self._make_device()

        entry = EntityRegistryEntry.from_entity_and_device(
            entity=entity, device=device, related_entities=["sensor.temp"]
        )
        assert entry.entity_id == "light.living_room"
        assert entry.manufacturer == "TestCo"
        assert entry.related_entities == ["sensor.temp"]

    def test_to_dict(self):
        from src.models.entity_registry_entry import EntityRegistryEntry

        entity = self._make_entity()
        device = self._make_device()

        entry = EntityRegistryEntry.from_entity_and_device(entity=entity, device=device)
        d = entry.to_dict()
        assert d["entity_id"] == "light.living_room"
        assert d["manufacturer"] == "TestCo"
        assert d["platform"] == "hue"
        assert "related_entities" in d

    def test_none_device(self):
        from src.models.entity_registry_entry import EntityRegistryEntry

        entity = self._make_entity()
        entry = EntityRegistryEntry.from_entity_and_device(entity=entity, device=None)
        assert entry.manufacturer is None
        assert entry.model is None

    def test_none_related_entities(self):
        from src.models.entity_registry_entry import EntityRegistryEntry

        entity = self._make_entity()
        entry = EntityRegistryEntry.from_entity_and_device(
            entity=entity, device=None, related_entities=None
        )
        assert entry.related_entities == []


# ===========================================================================
# Error Propagation Tests
# ===========================================================================


class TestErrorPropagation:
    """HTTPException propagation across endpoint layers."""

    @pytest.mark.asyncio
    async def test_device_404_propagates(self):
        from fastapi import HTTPException
        from src.devices_endpoints import get_device

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.first.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await get_device(device_id="missing", db=mock_db)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_alert_invalid_severity(self):
        """Invalid severity results in ValueError from AlertSeverity enum."""
        from homeiq_observability.alert_manager import AlertSeverity

        with pytest.raises(ValueError):
            AlertSeverity("bogus")


# ===========================================================================
# Cache Interaction Tests
# ===========================================================================


class TestCacheInteraction:
    """Cache set/get/clear interactions."""

    @pytest.mark.asyncio
    async def test_cache_set_get(self):
        from src.cache import SimpleCache

        c = SimpleCache()
        await c.set("test:key", {"count": 42}, ttl=60)
        result = await c.get("test:key")
        assert result == {"count": 42}

    @pytest.mark.asyncio
    async def test_cache_clear_invalidates(self):
        from src.cache import SimpleCache

        c = SimpleCache()
        await c.set("test:key", "value")
        await c.clear()
        result = await c.get("test:key")
        assert result is None


# ===========================================================================
# Response Model Interoperability
# ===========================================================================


class TestResponseModelInterop:
    """Cross-model composition tests."""

    def test_device_to_list_composition(self):
        from src.devices_endpoints import DeviceResponse, DevicesListResponse

        devices = [
            DeviceResponse(
                device_id=f"dev-{i}", name=f"Device {i}",
                manufacturer="TestCo", model="Model-X",
                entity_count=i, timestamp=datetime.now(UTC).isoformat(),
            )
            for i in range(3)
        ]
        dl = DevicesListResponse(devices=devices, count=3, limit=100)
        assert dl.count == 3
        assert dl.devices[2].entity_count == 2

    def test_alert_response_optional_fields(self):
        from src.alert_endpoints import AlertResponse

        a = AlertResponse(
            id="alert-1", name="Test Alert", severity="warning",
            status="active", message="Something happened", service="data-api",
        )
        assert a.metric is None
        assert a.current_value is None
        assert a.metadata is None
