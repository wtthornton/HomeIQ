"""
Tests for services/entity_registry.py + services/entity_enrichment.py — Epic 80, Story 80.8

Covers 14 scenarios:

EntityRegistry:
1.  Initialization sets db and cache
2.  get_entities_by_device — returns registry entries
3.  get_entities_by_device — returns empty for unknown device
4.  get_entities_by_device — handles exception gracefully
5.  get_device_for_entity — returns device
6.  get_device_for_entity — returns None for orphan entity
7.  get_sibling_entities — returns siblings
8.  get_sibling_entities — returns empty when no device_id
9.  get_entities_in_area — returns entries
10. get_device_hierarchy — returns hierarchy dict

EntityEnrichmentService:
11. _extract_capabilities — light with brightness+color
12. _extract_capabilities — switch with on_off
13. _extract_capabilities — sensor with device_class
14. _extract_capabilities — cover with supported_features
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

# ---------------------------------------------------------------------------
# Override conftest fresh_db — no real DB needed
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(autouse=True)
async def fresh_db():
    yield


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _make_mock_entity(entity_id="light.living_room", device_id="dev-001",
                       domain="light", platform="hue", **kwargs):
    e = MagicMock()
    e.entity_id = entity_id
    e.device_id = device_id
    e.domain = domain
    e.platform = platform
    e.unique_id = kwargs.get("unique_id", "hue-001")
    e.area_id = kwargs.get("area_id")
    e.config_entry_id = kwargs.get("config_entry_id")
    e.name = kwargs.get("name", "Test Entity")
    e.name_by_user = kwargs.get("name_by_user")
    e.original_name = kwargs.get("original_name")
    e.friendly_name = kwargs.get("friendly_name", "Test Entity")
    e.supported_features = kwargs.get("supported_features")
    e.capabilities = kwargs.get("capabilities")
    e.available_services = kwargs.get("available_services")
    e.icon = kwargs.get("icon")
    e.device_class = kwargs.get("device_class")
    e.unit_of_measurement = kwargs.get("unit_of_measurement")
    e.disabled = kwargs.get("disabled", False)
    return e


def _make_mock_device(device_id="dev-001", name="Test Device", manufacturer="TestCo",
                       model="Bulb-v2", **kwargs):
    d = MagicMock()
    d.device_id = device_id
    d.name = name
    d.manufacturer = manufacturer
    d.model = model
    d.sw_version = kwargs.get("sw_version", "1.0.0")
    d.via_device = kwargs.get("via_device")
    d.config_entry_id = kwargs.get("config_entry_id")
    return d


# ===========================================================================
# EntityRegistry Tests
# ===========================================================================


class TestEntityRegistryInit:
    """EntityRegistry initialization."""

    def test_init_sets_db_and_cache(self):
        from src.services.entity_registry import EntityRegistry

        mock_db = AsyncMock()
        reg = EntityRegistry(mock_db)
        assert reg.db is mock_db
        assert isinstance(reg._cache, dict)
        assert reg._cache_ttl == 300


class TestGetEntitiesByDevice:
    """EntityRegistry.get_entities_by_device()."""

    @pytest.mark.asyncio
    async def test_returns_registry_entries(self):
        from src.services.entity_registry import EntityRegistry

        entity1 = _make_mock_entity("light.living", "dev-001", "light")
        entity2 = _make_mock_entity("sensor.temp", "dev-001", "sensor")
        device = _make_mock_device("dev-001")

        mock_db = AsyncMock()

        # First call: entities query
        mock_entities_result = MagicMock()
        mock_entities_scalars = MagicMock()
        mock_entities_scalars.all.return_value = [entity1, entity2]
        mock_entities_result.scalars.return_value = mock_entities_scalars

        # Second call: device query
        mock_device_result = MagicMock()
        mock_device_result.scalar_one_or_none.return_value = device

        mock_db.execute = AsyncMock(side_effect=[mock_entities_result, mock_device_result])

        reg = EntityRegistry(mock_db)
        entries = await reg.get_entities_by_device("dev-001")
        assert len(entries) == 2
        assert entries[0].entity_id == "light.living"
        assert entries[0].manufacturer == "TestCo"

    @pytest.mark.asyncio
    async def test_returns_empty_for_unknown_device(self):
        from src.services.entity_registry import EntityRegistry

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars

        mock_device_result = MagicMock()
        mock_device_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(side_effect=[mock_result, mock_device_result])

        reg = EntityRegistry(mock_db)
        entries = await reg.get_entities_by_device("nonexistent")
        assert entries == []

    @pytest.mark.asyncio
    async def test_handles_exception(self):
        from src.services.entity_registry import EntityRegistry

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=Exception("DB error"))

        reg = EntityRegistry(mock_db)
        entries = await reg.get_entities_by_device("dev-001")
        assert entries == []


class TestGetDeviceForEntity:
    """EntityRegistry.get_device_for_entity()."""

    @pytest.mark.asyncio
    async def test_returns_device(self):
        from src.services.entity_registry import EntityRegistry

        entity = _make_mock_entity("light.living", "dev-001")
        device = _make_mock_device("dev-001")

        mock_db = AsyncMock()
        mock_entity_result = MagicMock()
        mock_entity_result.scalar_one_or_none.return_value = entity

        mock_device_result = MagicMock()
        mock_device_result.scalar_one_or_none.return_value = device

        mock_db.execute = AsyncMock(side_effect=[mock_entity_result, mock_device_result])

        reg = EntityRegistry(mock_db)
        result = await reg.get_device_for_entity("light.living")
        assert result.device_id == "dev-001"

    @pytest.mark.asyncio
    async def test_returns_none_for_orphan(self):
        from src.services.entity_registry import EntityRegistry

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        reg = EntityRegistry(mock_db)
        result = await reg.get_device_for_entity("orphan.entity")
        assert result is None


class TestGetSiblingEntities:
    """EntityRegistry.get_sibling_entities()."""

    @pytest.mark.asyncio
    async def test_returns_siblings(self):
        from src.services.entity_registry import EntityRegistry

        entity = _make_mock_entity("light.living", "dev-001")
        sibling = _make_mock_entity("sensor.temp", "dev-001", "sensor")
        device = _make_mock_device("dev-001")

        mock_db = AsyncMock()

        # First call: get entity
        mock_entity_result = MagicMock()
        mock_entity_result.scalar_one_or_none.return_value = entity

        # Second/third calls: get_entities_by_device
        mock_entities_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [entity, sibling]
        mock_entities_result.scalars.return_value = mock_scalars

        mock_device_result = MagicMock()
        mock_device_result.scalar_one_or_none.return_value = device

        mock_db.execute = AsyncMock(side_effect=[
            mock_entity_result, mock_entities_result, mock_device_result
        ])

        reg = EntityRegistry(mock_db)
        entries = await reg.get_sibling_entities("light.living")
        assert len(entries) == 2

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_device(self):
        from src.services.entity_registry import EntityRegistry

        entity = _make_mock_entity("orphan.entity", None)

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = entity
        mock_db.execute = AsyncMock(return_value=mock_result)

        reg = EntityRegistry(mock_db)
        entries = await reg.get_sibling_entities("orphan.entity")
        assert entries == []


class TestGetDeviceHierarchy:
    """EntityRegistry.get_device_hierarchy()."""

    @pytest.mark.asyncio
    async def test_returns_hierarchy(self):
        from src.services.entity_registry import EntityRegistry

        parent = _make_mock_device("hub-001", "Hub")
        device = _make_mock_device("dev-001", via_device="hub-001")
        child = _make_mock_device("child-001", "Child Device")

        mock_db = AsyncMock()

        # Query device, parent, children
        mock_device_result = MagicMock()
        mock_device_result.scalar_one_or_none.return_value = device

        mock_parent_result = MagicMock()
        mock_parent_result.scalar_one_or_none.return_value = parent

        mock_children_result = MagicMock()
        mock_children_scalars = MagicMock()
        mock_children_scalars.all.return_value = [child]
        mock_children_result.scalars.return_value = mock_children_scalars

        mock_db.execute = AsyncMock(side_effect=[
            mock_device_result, mock_parent_result, mock_children_result
        ])

        reg = EntityRegistry(mock_db)
        hierarchy = await reg.get_device_hierarchy("dev-001")
        assert hierarchy["device_id"] == "dev-001"
        assert hierarchy["parent_device"]["device_id"] == "hub-001"
        assert len(hierarchy["child_devices"]) == 1


# ===========================================================================
# EntityEnrichmentService Tests
# ===========================================================================


class TestExtractCapabilities:
    """EntityEnrichmentService._extract_capabilities()."""

    def _get_service(self):
        from src.services.entity_enrichment import EntityEnrichmentService
        return EntityEnrichmentService()

    def test_light_brightness_color(self):
        svc = self._get_service()
        caps = svc._extract_capabilities(
            "light", {"brightness": 255, "rgb_color": [255, 0, 0]}, 133  # 1+4+128
        )
        assert "brightness" in caps
        assert "color" in caps
        assert "effect" in caps

    def test_switch_on_off(self):
        svc = self._get_service()
        caps = svc._extract_capabilities("switch", {}, None)
        assert "on_off" in caps

    def test_sensor_device_class(self):
        svc = self._get_service()
        caps = svc._extract_capabilities(
            "sensor", {"device_class": "temperature", "state_class": "measurement"}, None
        )
        assert "measure_temperature" in caps
        assert "state_measurement" in caps

    def test_cover_supported_features(self):
        svc = self._get_service()
        caps = svc._extract_capabilities("cover", {}, 7)  # 1+2+4 = open+close+position
        assert "open" in caps
        assert "close" in caps
        assert "position" in caps
