"""
Tests for InfluxDB Schema
"""

from datetime import datetime

import pytest
from src.influxdb_schema import InfluxDBSchema

try:
    from influxdb_client import Point
except ImportError:
    Point = None


class TestInfluxDBSchema:
    """Test cases for InfluxDBSchema class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.schema = InfluxDBSchema()

    def test_initialization(self):
        """Test schema initialization"""
        assert self.schema.MEASUREMENT_EVENTS == "home_assistant_events"
        assert self.schema.MEASUREMENT_WEATHER == "weather_data"
        assert self.schema.MEASUREMENT_SPORTS == "sports_data"
        assert self.schema.MEASUREMENT_SYSTEM == "system_metrics"

        assert self.schema.TAG_ENTITY_ID == "entity_id"
        assert self.schema.TAG_DOMAIN == "domain"
        assert self.schema.TAG_DEVICE_CLASS == "device_class"
        assert self.schema.TAG_AREA == "area"
        assert self.schema.TAG_LOCATION == "location"

        assert self.schema.FIELD_STATE == "state_value"
        assert self.schema.FIELD_OLD_STATE == "previous_state"
        assert self.schema.FIELD_ATTRIBUTES == "attributes"
        assert self.schema.FIELD_TEMPERATURE == "weather_temp"

    def test_create_event_point_basic(self):
        """Test creating basic event point"""
        event_data = {
            "event_type": "state_changed",
            "entity_id": "sensor.temperature",
            "new_state": "20.5",
            "old_state": "19.8",
            "time_fired": "2023-01-01T12:00:00Z",
            "attributes": {
                "device_class": "temperature",
                "unit_of_measurement": "°C",
                "area": "living_room",
            },
        }

        point = self.schema.create_event_point(event_data)

        if point:  # Only test if Point is available
            assert point._name == "home_assistant_events"
            assert "entity_id" in point._tags
            assert point._tags["entity_id"] == "sensor.temperature"
            assert "domain" in point._tags
            assert point._tags["domain"] == "sensor"
            assert "device_class" in point._tags
            assert point._tags["device_class"] == "temperature"
            assert "area" in point._tags
            assert point._tags["area"] == "living_room"
            assert "state_value" in point._fields
            assert point._fields["state_value"] == "20.5"
            assert "previous_state" in point._fields
            assert point._fields["previous_state"] == "19.8"
        else:
            # Test without InfluxDB Point
            assert point is None

    def test_state_fields_hold_bare_state_not_state_object_repr(self):
        """HA delivers new_state/old_state as full state dicts; only `.state` is stored."""
        event_data = {
            "event_type": "state_changed",
            "entity_id": "light.garage",
            "new_state": {
                "entity_id": "light.garage",
                "state": "on",
                "attributes": {"brightness": 200, "friendly_name": "Garage"},
                "last_changed": "2026-08-17T10:00:00+00:00",
            },
            "old_state": {"entity_id": "light.garage", "state": "off", "attributes": {}},
            "time_fired": "2026-08-17T10:00:00Z",
        }
        point = self.schema.create_event_point(event_data)
        assert point is not None
        assert point._fields["state_value"] == "on"
        assert point._fields["previous_state"] == "off"

    def test_missing_old_state_writes_no_previous_state_field(self):
        event_data = {
            "event_type": "state_changed",
            "entity_id": "sensor.t",
            "new_state": {"entity_id": "sensor.t", "state": "21.5", "attributes": {}},
            "old_state": None,
            "time_fired": "2026-08-17T10:00:00Z",
        }
        point = self.schema.create_event_point(event_data)
        assert point is not None
        assert point._fields["state_value"] == "21.5"
        assert "previous_state" not in point._fields

    def test_create_event_point_with_weather(self):
        """Test creating event point with weather data"""
        event_data = {
            "event_type": "state_changed",
            "entity_id": "sensor.temperature",
            "new_state": "20.5",
            "time_fired": "2023-01-01T12:00:00Z",
            "attributes": {"device_class": "temperature", "area": "living_room"},
            "weather": {
                "temperature": 15.2,
                "humidity": 65,
                "pressure": 1013.25,
                "wind_speed": 3.5,
                "weather_description": "clear sky",
                "location": "London",
            },
        }

        point = self.schema.create_event_point(event_data)

        if point:  # Only test if Point is available
            assert point._name == "home_assistant_events"
            assert "location" in point._tags
            assert point._tags["location"] == "London"
            assert "weather_temp" in point._fields
            assert point._fields["weather_temp"] == 15.2
            assert "weather_humidity" in point._fields
            assert point._fields["weather_humidity"] == 65
            assert "weather_pressure" in point._fields
            assert point._fields["weather_pressure"] == 1013.25
            assert "wind_speed" in point._fields
            assert point._fields["wind_speed"] == 3.5
            assert "weather_description" in point._fields
            assert point._fields["weather_description"] == "clear sky"
        else:
            # Test without InfluxDB Point
            assert point is None

    def test_create_event_point_missing_required(self):
        """Test creating event point with missing required data"""
        event_data = {
            "event_type": "state_changed",
            # Missing entity_id
            "new_state": "20.5",
        }

        point = self.schema.create_event_point(event_data)
        assert point is None

    def test_create_weather_point(self):
        """Test creating weather point"""
        weather_data = {
            "temperature": 15.2,
            "humidity": 65,
            "pressure": 1013.25,
            "wind_speed": 3.5,
            "weather_description": "clear sky",
            "weather_condition": "Clear",
            "timestamp": "2023-01-01T12:00:00Z",
        }
        location = "London"

        point = self.schema.create_weather_point(weather_data, location)

        if point:  # Only test if Point is available
            assert point._name == "weather_data"
            assert "location" in point._tags
            assert point._tags["location"] == "London"
            assert "weather_condition" in point._tags
            assert point._tags["weather_condition"] == "Clear"
            assert "weather_temp" in point._fields
            assert point._fields["weather_temp"] == 15.2
            assert "weather_humidity" in point._fields
            assert point._fields["weather_humidity"] == 65
            assert "weather_pressure" in point._fields
            assert point._fields["weather_pressure"] == 1013.25
            assert "wind_speed" in point._fields
            assert point._fields["wind_speed"] == 3.5
            assert "weather_description" in point._fields
            assert point._fields["weather_description"] == "clear sky"
        else:
            # Test without InfluxDB Point
            assert point is None

    def test_create_summary_point(self):
        """Test creating summary point"""
        measurement = "event_summaries"
        tags = {"entity_id": "sensor.temperature", "domain": "sensor", "area": "living_room"}
        fields = {
            "avg_temperature": 20.5,
            "max_temperature": 25.0,
            "min_temperature": 15.0,
            "event_count": 100,
        }
        timestamp = datetime(2023, 1, 1, 12, 0, 0)

        point = self.schema.create_summary_point(measurement, tags, fields, timestamp)

        if point:  # Only test if Point is available
            assert point._name == "event_summaries"
            assert "entity_id" in point._tags
            assert point._tags["entity_id"] == "sensor.temperature"
            assert "domain" in point._tags
            assert point._tags["domain"] == "sensor"
            assert "area" in point._tags
            assert point._tags["area"] == "living_room"
            assert "avg_temperature" in point._fields
            assert point._fields["avg_temperature"] == 20.5
            assert "max_temperature" in point._fields
            assert point._fields["max_temperature"] == 25.0
            assert "min_temperature" in point._fields
            assert point._fields["min_temperature"] == 15.0
            assert "event_count" in point._fields
            assert point._fields["event_count"] == 100
        else:
            # Test without InfluxDB Point
            assert point is None

    def test_get_retention_policies(self):
        """Test getting retention policies"""
        policies = self.schema.get_retention_policies()

        # One policy per measurement bucket
        assert len(policies) == 4
        assert [p["name"] for p in policies] == [
            "home_assistant_events",
            "weather_data",
            "sports_data",
            "system_metrics",
        ]

        by_name = {p["name"]: p for p in policies}

        events_policy = by_name["home_assistant_events"]
        assert events_policy["duration"] == "365d"
        assert events_policy["shard_duration"] == "7d"
        assert events_policy["replication"] == 1

        assert by_name["weather_data"]["duration"] == "180d"
        assert by_name["weather_data"]["shard_duration"] == "30d"

        assert by_name["sports_data"]["duration"] == "90d"
        assert by_name["sports_data"]["shard_duration"] == "30d"

        assert by_name["system_metrics"]["duration"] == "30d"
        assert by_name["system_metrics"]["shard_duration"] == "7d"

    def test_get_schema_validation_rules(self):
        """Test getting schema validation rules"""
        rules = self.schema.get_schema_validation_rules()

        assert "required_tags" in rules
        assert "required_fields" in rules
        assert "tag_patterns" in rules
        assert "field_types" in rules

        # Check required tags
        assert "entity_id" in rules["required_tags"]
        assert "domain" in rules["required_tags"]

        # Check required fields
        assert "state_value" in rules["required_fields"]

        # Check tag patterns
        assert "entity_id" in rules["tag_patterns"]
        assert "domain" in rules["tag_patterns"]
        assert "device_class" in rules["tag_patterns"]

        # Check field types
        assert "state_value" in rules["field_types"]
        assert "weather_temp" in rules["field_types"]
        assert "weather_humidity" in rules["field_types"]

    def test_validate_point_valid(self):
        """Test validating valid point"""
        if not Point:
            pytest.skip("InfluxDB Point not available")

        # Create a valid point
        point = Point("home_assistant_events")
        point = point.tag("entity_id", "sensor.temperature")
        point = point.tag("domain", "sensor")
        point = point.field("state_value", "20.5")

        is_valid, errors = self.schema.validate_point(point)

        assert is_valid
        assert len(errors) == 0

    def test_validate_point_missing_required_tag(self):
        """Test validating point with missing required tag"""
        if not Point:
            pytest.skip("InfluxDB Point not available")

        # Create point missing required tag
        point = Point("home_assistant_events")
        point = point.tag("domain", "sensor")  # Missing entity_id
        point = point.field("state_value", "20.5")

        is_valid, errors = self.schema.validate_point(point)

        assert not is_valid
        assert any("Missing required tag: entity_id" in error for error in errors)

    def test_validate_point_missing_required_field(self):
        """Test validating point with missing required field"""
        if not Point:
            pytest.skip("InfluxDB Point not available")

        # Create point missing required field
        point = Point("home_assistant_events")
        point = point.tag("entity_id", "sensor.temperature")
        point = point.tag("domain", "sensor")
        # Missing state field

        is_valid, errors = self.schema.validate_point(point)

        assert not is_valid
        assert "Missing required field: state_value" in errors

    def test_validate_point_invalid_tag_pattern(self):
        """Test validating point with invalid tag pattern"""
        if not Point:
            pytest.skip("InfluxDB Point not available")

        # Create point with invalid tag pattern
        point = Point("home_assistant_events")
        point = point.tag("entity_id", "invalid-entity-id")  # Invalid pattern
        point = point.tag("domain", "sensor")
        point = point.field("state", "20.5")

        is_valid, errors = self.schema.validate_point(point)

        assert not is_valid
        assert any("Invalid tag pattern for entity_id" in error for error in errors)


class TestContextParentIdField:
    """The point builder writes context_parent_id (TAP-6107).

    The processor extracted context.parent_id all along and the schema
    declared the field name, but no builder ever wrote it — the live bucket
    had context_id and context_user_id and nothing else, so the automation
    trace endpoint and the MCP trace_automation tool always walked an empty
    chain while looking merely quiet.
    """

    def setup_method(self):
        self.schema = InfluxDBSchema()

    def test_parent_id_is_written_when_present(self):
        point = self.schema.create_event_point(
            {
                "event_type": "state_changed",
                "entity_id": "light.office",
                "new_state": "on",
                "time_fired": "2026-08-20T04:00:00Z",
                "context_id": "01CTX_CHILD",
                "context_parent_id": "01CTX_PARENT",
            }
        )

        if point:
            assert point._fields["context_id"] == "01CTX_CHILD"
            assert point._fields["context_parent_id"] == "01CTX_PARENT"
        else:
            assert point is None

    def test_no_parent_id_writes_no_field(self):
        point = self.schema.create_event_point(
            {
                "event_type": "state_changed",
                "entity_id": "light.office",
                "new_state": "on",
                "time_fired": "2026-08-20T04:00:00Z",
                "context_id": "01CTX_MANUAL",
            }
        )

        if point:
            assert "context_parent_id" not in point._fields
        else:
            assert point is None
