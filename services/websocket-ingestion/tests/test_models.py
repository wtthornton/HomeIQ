"""
Tests for data models
"""


import pytest
from src.models import ConfigEntry, Device, Entity


class TestDevice:
    """Test cases for Device model"""

    def test_device_creation(self):
        """Test creating a Device"""
        device = Device(
            device_id="dev1",
            name="Living Room Light",
            manufacturer="Philips",
            model="Hue Bulb",
            sw_version="1.58.0",
            area_id="living_room",
            entity_count=3
        )

        assert device.device_id == "dev1"
        assert device.name == "Living Room Light"
        assert device.manufacturer == "Philips"
        assert device.model == "Hue Bulb"
        assert device.sw_version == "1.58.0"
        assert device.area_id == "living_room"
        assert device.entity_count == 3

    def test_device_validation_success(self):
        """Test device validation with valid data"""
        device = Device(
            device_id="dev1",
            name="Test Device",
            manufacturer="Test",
            model="Model1"
        )

        assert device.validate() is True

    def test_device_validation_no_id(self):
        """Test device validation fails with no device_id"""
        device = Device(
            device_id="",
            name="Test Device",
            manufacturer="Test",
            model="Model1"
        )

        with pytest.raises(ValueError, match="device_id is required"):
            device.validate()

    def test_device_validation_no_name(self):
        """Test device validation fails with no name"""
        device = Device(
            device_id="dev1",
            name="",
            manufacturer="Test",
            model="Model1"
        )

        with pytest.raises(ValueError, match="name is required"):
            device.validate()

    def test_device_to_influx_point(self):
        """Test converting device to InfluxDB point"""
        device = Device(
            device_id="dev1",
            name="Living Room Light",
            manufacturer="Philips",
            model="Hue Bulb",
            sw_version="1.58.0",
            area_id="living_room",
            entity_count=3,
            timestamp="2025-10-12T10:30:00Z"
        )

        point = device.to_influx_point()

        assert point["measurement"] == "devices"
        assert point["tags"]["device_id"] == "dev1"
        assert point["tags"]["manufacturer"] == "Philips"
        assert point["tags"]["model"] == "Hue Bulb"
        assert point["tags"]["area_id"] == "living_room"
        assert point["fields"]["name"] == "Living Room Light"
        assert point["fields"]["sw_version"] == "1.58.0"
        assert point["fields"]["entity_count"] == 3
        assert point["time"] == "2025-10-12T10:30:00Z"

    def test_device_from_ha_device(self):
        """Test creating Device from HA registry data"""
        ha_device = {
            "id": "abc123",
            "name": "My Device",
            "manufacturer": "Acme Corp",
            "model": "Model X",
            "sw_version": "2.0.0",
            "area_id": "bedroom"
        }

        device = Device.from_ha_device(ha_device)

        assert device.device_id == "abc123"
        assert device.name == "My Device"
        assert device.manufacturer == "Acme Corp"
        assert device.model == "Model X"
        assert device.sw_version == "2.0.0"
        assert device.area_id == "bedroom"

    def test_device_from_ha_device_with_name_by_user(self):
        """Test Device uses name_by_user when name is None"""
        ha_device = {
            "id": "abc123",
            "name": None,
            "name_by_user": "User Custom Name",
            "manufacturer": "Acme",
            "model": "X"
        }

        device = Device.from_ha_device(ha_device)

        assert device.name == "User Custom Name"

    def test_device_from_ha_device_defaults(self):
        """Test Device handles missing fields with defaults"""
        ha_device = {
            "id": "abc123"
        }

        device = Device.from_ha_device(ha_device)

        assert device.device_id == "abc123"
        assert device.name == "Unknown Device"
        assert device.manufacturer == "Unknown"
        assert device.model == "Unknown"
        assert device.sw_version is None
        assert device.area_id is None


class TestEntity:
    """Test cases for Entity model"""

    def test_entity_creation(self):
        """Test creating an Entity"""
        entity = Entity(
            entity_id="light.living_room",
            device_id="dev1",
            domain="light",
            platform="hue",
            unique_id="hue123",
            area_id="living_room",
            disabled=False
        )

        assert entity.entity_id == "light.living_room"
        assert entity.device_id == "dev1"
        assert entity.domain == "light"
        assert entity.platform == "hue"
        assert entity.unique_id == "hue123"
        assert entity.area_id == "living_room"
        assert entity.disabled is False

    def test_entity_validation_success(self):
        """Test entity validation with valid data"""
        entity = Entity(entity_id="light.test")
        assert entity.validate() is True

    def test_entity_validation_no_id(self):
        """Test entity validation fails with no entity_id"""
        entity = Entity(entity_id="")

        with pytest.raises(ValueError, match="entity_id is required"):
            entity.validate()

    def test_entity_to_influx_point(self):
        """Test converting entity to InfluxDB point"""
        entity = Entity(
            entity_id="light.living_room",
            device_id="dev1",
            domain="light",
            platform="hue",
            unique_id="hue123",
            area_id="living_room",
            disabled=False,
            timestamp="2025-10-12T10:30:00Z"
        )

        point = entity.to_influx_point()

        assert point["measurement"] == "entities"
        assert point["tags"]["entity_id"] == "light.living_room"
        assert point["tags"]["device_id"] == "dev1"
        assert point["tags"]["domain"] == "light"
        assert point["tags"]["platform"] == "hue"
        assert point["tags"]["area_id"] == "living_room"
        assert point["fields"]["unique_id"] == "hue123"
        assert point["fields"]["disabled"] is False
        assert point["time"] == "2025-10-12T10:30:00Z"

    def test_entity_from_ha_entity(self):
        """Test creating Entity from HA registry data"""
        ha_entity = {
            "entity_id": "sensor.temperature",
            "device_id": "dev1",
            "platform": "mqtt",
            "unique_id": "mqtt_temp_123",
            "area_id": "kitchen",
            "disabled_by": None
        }

        entity = Entity.from_ha_entity(ha_entity)

        assert entity.entity_id == "sensor.temperature"
        assert entity.device_id == "dev1"
        assert entity.domain == "sensor"
        assert entity.platform == "mqtt"
        assert entity.unique_id == "mqtt_temp_123"
        assert entity.area_id == "kitchen"
        assert entity.disabled is False

    def test_entity_from_ha_entity_disabled(self):
        """Test Entity detects disabled status"""
        ha_entity = {
            "entity_id": "light.test",
            "disabled_by": "user"
        }

        entity = Entity.from_ha_entity(ha_entity)

        assert entity.disabled is True

    def test_entity_from_ha_entity_domain_extraction(self):
        """Test Entity extracts domain from entity_id"""
        ha_entity = {
            "entity_id": "switch.bedroom_fan"
        }

        entity = Entity.from_ha_entity(ha_entity)

        assert entity.domain == "switch"


class TestConfigEntry:
    """Test cases for ConfigEntry model"""

    def test_config_entry_creation(self):
        """Test creating a ConfigEntry"""
        entry = ConfigEntry(
            entry_id="entry1",
            domain="hue",
            title="Philips Hue",
            state="loaded",
            version=2
        )

        assert entry.entry_id == "entry1"
        assert entry.domain == "hue"
        assert entry.title == "Philips Hue"
        assert entry.state == "loaded"
        assert entry.version == 2

    def test_config_entry_validation_success(self):
        """Test config entry validation with valid data"""
        entry = ConfigEntry(
            entry_id="entry1",
            domain="test",
            title="Test"
        )

        assert entry.validate() is True

    def test_config_entry_validation_no_id(self):
        """Test config entry validation fails with no entry_id"""
        entry = ConfigEntry(
            entry_id="",
            domain="test",
            title="Test"
        )

        with pytest.raises(ValueError, match="entry_id is required"):
            entry.validate()

    def test_config_entry_validation_no_domain(self):
        """Test config entry validation fails with no domain"""
        entry = ConfigEntry(
            entry_id="entry1",
            domain="",
            title="Test"
        )

        with pytest.raises(ValueError, match="domain is required"):
            entry.validate()

    def test_config_entry_to_influx_point(self):
        """Test converting config entry to InfluxDB point"""
        entry = ConfigEntry(
            entry_id="entry1",
            domain="hue",
            title="Philips Hue",
            state="loaded",
            version=2,
            timestamp="2025-10-12T10:30:00Z"
        )

        point = entry.to_influx_point()

        assert point["measurement"] == "config_entries"
        assert point["tags"]["entry_id"] == "entry1"
        assert point["tags"]["domain"] == "hue"
        assert point["tags"]["state"] == "loaded"
        assert point["fields"]["title"] == "Philips Hue"
        assert point["fields"]["version"] == 2
        assert point["time"] == "2025-10-12T10:30:00Z"

    def test_config_entry_from_ha_config_entry(self):
        """Test creating ConfigEntry from HA data"""
        ha_entry = {
            "entry_id": "entry123",
            "domain": "nest",
            "title": "Google Nest",
            "state": "loaded",
            "version": 3
        }

        entry = ConfigEntry.from_ha_config_entry(ha_entry)

        assert entry.entry_id == "entry123"
        assert entry.domain == "nest"
        assert entry.title == "Google Nest"
        assert entry.state == "loaded"
        assert entry.version == 3

    def test_config_entry_from_ha_config_entry_defaults(self):
        """Test ConfigEntry handles missing fields"""
        ha_entry = {
            "entry_id": "entry123"
        }

        entry = ConfigEntry.from_ha_config_entry(ha_entry)

        assert entry.entry_id == "entry123"
        assert entry.domain == "unknown"
        assert entry.title == "Unknown Integration"
        assert entry.state == "unknown"
        assert entry.version == 1

