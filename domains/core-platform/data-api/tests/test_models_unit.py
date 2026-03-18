"""Unit tests for data models — Story 85.10

Tests EntityRegistryEntry, Device, Entity, and other model dataclasses.
"""

from unittest.mock import MagicMock

from src.models.entity_registry_entry import EntityRegistryEntry


class TestEntityRegistryEntry:

    def test_defaults(self):
        e = EntityRegistryEntry(entity_id="light.kitchen", unique_id="abc")
        assert e.name is None
        assert e.platform == "unknown"
        assert e.domain == "unknown"
        assert e.related_entities == []
        assert e.capabilities == {}
        assert e.disabled is False

    def test_from_entity_and_device(self):
        entity = MagicMock()
        entity.entity_id = "light.kitchen"
        entity.unique_id = "abc"
        entity.name = "Kitchen Light"
        entity.device_id = "dev-1"
        entity.area_id = "kitchen"
        entity.config_entry_id = "cfg-1"
        entity.platform = "hue"
        entity.domain = "light"
        entity.capabilities = {"brightness": True}
        entity.friendly_name = "Kitchen"
        entity.name_by_user = None
        entity.original_name = "Kitchen Light"
        entity.disabled = False
        entity.supported_features = 1
        entity.available_services = ["turn_on"]
        entity.icon = "mdi:lightbulb"
        entity.device_class = "light"
        entity.unit_of_measurement = None

        device = MagicMock()
        device.manufacturer = "Philips"
        device.model = "Hue Bulb"
        device.sw_version = "1.0"
        device.via_device = "bridge-1"

        entry = EntityRegistryEntry.from_entity_and_device(
            entity=entity,
            device=device,
            related_entities=["switch.kitchen"],
        )
        assert entry.entity_id == "light.kitchen"
        assert entry.manufacturer == "Philips"
        assert entry.via_device == "bridge-1"
        assert entry.related_entities == ["switch.kitchen"]

    def test_from_entity_no_device(self):
        entity = MagicMock()
        entity.entity_id = "sensor.temp"
        entity.unique_id = "xyz"
        entity.name = "Temp"
        entity.device_id = None
        entity.area_id = None
        entity.config_entry_id = None
        entity.platform = None
        entity.domain = None
        entity.capabilities = None
        entity.friendly_name = None
        entity.name_by_user = None
        entity.original_name = None
        entity.disabled = False
        entity.supported_features = None
        entity.available_services = None
        entity.icon = None
        entity.device_class = None
        entity.unit_of_measurement = None

        entry = EntityRegistryEntry.from_entity_and_device(entity=entity)
        assert entry.manufacturer is None
        assert entry.model is None
        assert entry.platform == "unknown"
        assert entry.capabilities == {}

    def test_to_dict(self):
        e = EntityRegistryEntry(
            entity_id="light.kitchen", unique_id="abc",
            name="Kitchen", platform="hue", domain="light",
        )
        d = e.to_dict()
        assert d["entity_id"] == "light.kitchen"
        assert d["name"] == "Kitchen"
        assert d["platform"] == "hue"
        assert isinstance(d, dict)
        assert len(d) >= 20  # All fields present

    def test_to_dict_round_trip(self):
        entity = MagicMock()
        entity.entity_id = "light.x"
        entity.unique_id = "u1"
        entity.name = "X"
        entity.device_id = "d1"
        entity.area_id = "a1"
        entity.config_entry_id = "c1"
        entity.platform = "test"
        entity.domain = "light"
        entity.capabilities = {"color": True}
        entity.friendly_name = "X Light"
        entity.name_by_user = "My Light"
        entity.original_name = "X"
        entity.disabled = True
        entity.supported_features = 131
        entity.available_services = ["turn_on", "turn_off"]
        entity.icon = "mdi:lamp"
        entity.device_class = "light"
        entity.unit_of_measurement = "lx"

        entry = EntityRegistryEntry.from_entity_and_device(entity=entity)
        d = entry.to_dict()
        assert d["disabled"] is True
        assert d["supported_features"] == 131
        assert d["available_services"] == ["turn_on", "turn_off"]
