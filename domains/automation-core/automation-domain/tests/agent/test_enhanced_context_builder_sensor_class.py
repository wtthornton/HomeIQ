"""build_binary_sensor_context must classify by device metadata, not by a
keyword scan over entity_id (TAP-7590).

The renamed-FP1E case here is the exact bug the old code had: an mmWave
presence-capable module with no HA-assigned device_class was only found
because its entity_id happened to contain the product-name substring "fp2".
Renaming the entity dropped it from context silently. The fix reads the
device's manufacturer/model through the shared taxonomy instead.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agent.config.entity_blacklist import EntityBlacklist
from src.agent.services.enhanced_context_builder import EnhancedContextBuilder


@pytest.fixture()
def blacklist():
    from pathlib import Path

    cfg = Path(__file__).resolve().parents[2] / "src" / "agent" / "config" / "entity_blacklist.yaml"
    return EntityBlacklist(cfg)


@pytest.fixture()
def builder(blacklist):
    settings = MagicMock()
    settings.ha_url = "http://localhost:8123"
    settings.ha_token = MagicMock()
    settings.ha_token.get_secret_value.return_value = "fake-token"
    settings.data_api_url = "http://localhost:8006"
    settings.data_api_key = None
    return EnhancedContextBuilder(settings=settings, blacklist=blacklist)


class TestRenamedFp1eSurvivesClassification:
    @pytest.mark.asyncio
    async def test_renamed_fp1e_with_no_device_class_is_still_included(self, builder):
        """An mmWave presence-capable device with no device_class, whose
        entity_id carries no motion/presence/occupancy/fp2/fp300 keyword,
        must still appear — because it is identified by manufacturer/model,
        not by name."""
        entity = {
            "entity_id": "binary_sensor.zone_beta_3",
            "domain": "binary_sensor",
            "device_id": "dev-fp1e-1",
            "area_id": "bar",
            "friendly_name": "Zone Beta 3",
            "state": "off",
            "attributes": {},
        }
        device = {
            "id": "dev-fp1e-1",
            "area_id": "bar",
            "manufacturer": "Aqara",
            "model": "lumi.sensor_occupy.agl8",
        }
        builder.data_api_client.fetch_entities = AsyncMock(return_value=[entity])
        builder.ha_client.get_device_registry = AsyncMock(return_value=[device])
        builder.ha_client.get_area_registry = AsyncMock(return_value=[])
        builder.ha_client.get_states = AsyncMock(
            return_value=[{"entity_id": "binary_sensor.zone_beta_3", "state": "off"}]
        )

        result = await builder.build_binary_sensor_context()

        assert "binary_sensor.zone_beta_3" in result

    @pytest.mark.asyncio
    async def test_an_unrelated_sensor_with_a_stray_product_keyword_is_not_included(
        self, builder
    ):
        """A non-presence device whose entity_id happens to contain a
        product-name substring must not be swept in — classification reads
        manufacturer/model, not the name."""
        entity = {
            "entity_id": "binary_sensor.fp300_unrelated_thing",
            "domain": "binary_sensor",
            "device_id": "dev-other-1",
            "area_id": "bar",
            "friendly_name": "Unrelated",
            "state": "off",
            "attributes": {},
        }
        device = {
            "id": "dev-other-1",
            "area_id": "bar",
            "manufacturer": "Generic Corp",
            "model": "Contact Sensor V2",
        }
        builder.data_api_client.fetch_entities = AsyncMock(return_value=[entity])
        builder.ha_client.get_device_registry = AsyncMock(return_value=[device])
        builder.ha_client.get_area_registry = AsyncMock(return_value=[])
        builder.ha_client.get_states = AsyncMock(
            return_value=[{"entity_id": "binary_sensor.fp300_unrelated_thing", "state": "off"}]
        )

        result = await builder.build_binary_sensor_context()

        assert "binary_sensor.fp300_unrelated_thing" not in result


class TestNoKeywordSubstringSurvives:
    def test_fp2_and_fp300_do_not_appear_anywhere_in_the_source(self):
        import inspect

        import src.agent.services.enhanced_context_builder as module

        source = inspect.getsource(module)
        assert "fp2" not in source.lower()
        assert "fp300" not in source.lower()
