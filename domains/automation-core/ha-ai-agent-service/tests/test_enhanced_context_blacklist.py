"""Tests for entity blacklist filtering in EnhancedContextBuilder — Epic 93 Story 93.2."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.config.entity_blacklist import EntityBlacklist
from src.services.enhanced_context_builder import EnhancedContextBuilder


def _make_entity(entity_id: str, domain: str, area_id: str = "living_room", state: str = "on"):
    return {
        "entity_id": entity_id,
        "domain": domain,
        "area_id": area_id,
        "friendly_name": entity_id.split(".")[-1].replace("_", " ").title(),
        "state": state,
        "attributes": {},
    }


SAMPLE_ENTITIES = [
    _make_entity("light.office_lamp", "light", "office"),
    _make_entity("light.kitchen_ceiling", "light", "kitchen"),
    _make_entity("lock.front_door", "lock", "hallway"),
    _make_entity("lock.back_door", "lock", "hallway"),
    _make_entity("alarm_control_panel.home", "alarm_control_panel", "hallway"),
    _make_entity("cover.garage_door", "cover", "garage"),
    _make_entity("siren.alarm", "siren", "hallway"),
    _make_entity("switch.kitchen_outlet", "switch", "kitchen"),
    _make_entity("binary_sensor.hallway_motion", "binary_sensor", "hallway"),
]


@pytest.fixture()
def blacklist():
    """Use real blacklist config."""
    from pathlib import Path
    cfg = Path(__file__).resolve().parent.parent / "src" / "config" / "entity_blacklist.yaml"
    return EntityBlacklist(cfg)


@pytest.fixture()
def builder(blacklist):
    settings = MagicMock()
    settings.ha_url = "http://localhost:8123"
    settings.ha_token = MagicMock()
    settings.ha_token.get_secret_value.return_value = "fake-token"
    settings.data_api_url = "http://localhost:8006"
    settings.data_api_key = None
    ecb = EnhancedContextBuilder(settings=settings, blacklist=blacklist)
    return ecb


class TestBuildAreaEntityContextFiltering:
    """93.2 AC: build_area_entity_context filters blocked entities."""

    @pytest.mark.asyncio
    async def test_lock_entities_excluded(self, builder):
        builder.data_api_client.fetch_entities = AsyncMock(return_value=SAMPLE_ENTITIES)
        builder.ha_client.get_device_registry = AsyncMock(return_value=[])
        builder.ha_client.get_area_registry = AsyncMock(return_value=[])

        result = await builder.build_area_entity_context()

        assert "lock.front_door" not in result
        assert "lock.back_door" not in result

    @pytest.mark.asyncio
    async def test_alarm_entities_excluded(self, builder):
        builder.data_api_client.fetch_entities = AsyncMock(return_value=SAMPLE_ENTITIES)
        builder.ha_client.get_device_registry = AsyncMock(return_value=[])
        builder.ha_client.get_area_registry = AsyncMock(return_value=[])

        result = await builder.build_area_entity_context()

        assert "alarm_control_panel.home" not in result

    @pytest.mark.asyncio
    async def test_light_entities_included(self, builder):
        builder.data_api_client.fetch_entities = AsyncMock(return_value=SAMPLE_ENTITIES)
        builder.ha_client.get_device_registry = AsyncMock(return_value=[])
        builder.ha_client.get_area_registry = AsyncMock(return_value=[])

        result = await builder.build_area_entity_context()

        assert "light.office_lamp" in result
        assert "light.kitchen_ceiling" in result

    @pytest.mark.asyncio
    async def test_filtered_count_notice(self, builder):
        builder.data_api_client.fetch_entities = AsyncMock(return_value=SAMPLE_ENTITIES)
        builder.ha_client.get_device_registry = AsyncMock(return_value=[])
        builder.ha_client.get_area_registry = AsyncMock(return_value=[])

        result = await builder.build_area_entity_context()

        # 2 locks + 1 alarm = 3 filtered
        assert "[FILTERED]" in result
        assert "3 security-sensitive entities filtered" in result

    @pytest.mark.asyncio
    async def test_warn_domain_annotated(self, builder):
        builder.data_api_client.fetch_entities = AsyncMock(return_value=SAMPLE_ENTITIES)
        builder.ha_client.get_device_registry = AsyncMock(return_value=[])
        builder.ha_client.get_area_registry = AsyncMock(return_value=[])

        result = await builder.build_area_entity_context()

        # cover.garage_door should be present but with warning
        assert "cover.garage_door" in result
        assert "SAFETY WARNING" in result


class TestBuildExistingAutomationsNotFiltered:
    """93.2 AC: Existing automations context still shows lock/alarm automations."""

    @pytest.mark.asyncio
    async def test_existing_automations_include_lock(self, builder):
        lock_automation = {
            "entity_id": "automation.lock_at_night",
            "domain": "automation",
            "friendly_name": "Lock doors at night",
            "state": "on",
        }
        builder.data_api_client.fetch_entities = AsyncMock(return_value=[lock_automation])
        builder.ha_client.get_states = AsyncMock(
            return_value=[{"entity_id": "automation.lock_at_night", "state": "on"}]
        )

        result = await builder.build_existing_automations_context()

        assert "automation.lock_at_night" in result
        assert "Lock doors at night" in result


class TestBuildBinarySensorFiltering:
    """93.2: Binary sensors from blocked domains are filtered."""

    @pytest.mark.asyncio
    async def test_normal_binary_sensors_included(self, builder):
        entities = [
            {
                "entity_id": "binary_sensor.office_motion",
                "domain": "binary_sensor",
                "area_id": "office",
                "friendly_name": "Office Motion",
                "state": "off",
                "attributes": {"device_class": "motion"},
            },
        ]
        builder.data_api_client.fetch_entities = AsyncMock(return_value=entities)
        builder.ha_client.get_device_registry = AsyncMock(return_value=[])
        builder.ha_client.get_area_registry = AsyncMock(return_value=[])
        builder.ha_client.get_states = AsyncMock(return_value=[
            {"entity_id": "binary_sensor.office_motion", "state": "off"},
        ])

        result = await builder.build_binary_sensor_context()

        assert "binary_sensor.office_motion" in result
