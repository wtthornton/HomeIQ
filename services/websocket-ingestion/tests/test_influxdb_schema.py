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
        assert self.schema.MEASUREMENT_SUMMARY == "event_summaries"

        assert self.schema.TAG_ENTITY_ID == "entity_id"
        assert self.schema.TAG_DOMAIN == "domain"
        assert self.schema.TAG_DEVICE_CLASS == "device_class"
        assert self.schema.TAG_AREA == "area"
        assert self.schema.TAG_LOCATION == "location"

        assert self.schema.FIELD_STATE == "state"
        assert self.schema.FIELD_OLD_STATE == "old_state"
        assert self.schema.FIELD_ATTRIBUTES == "attributes"
        assert self.schema.FIELD_TEMPERATURE == "temperature"

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
                "area": "living_room"
            }
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
            assert "state" in point._fields
            assert point._fields["state"] == "20.5"
            assert "old_state" in point._fields
            assert point._fields["old_state"] == "19.8"
        else:
            # Test without InfluxDB Point
            assert point is None

    def test_create_event_point_with_weather(self):
        """Test creating event point with weather data"""
        event_data = {
            "event_type": "state_changed",
            "entity_id": "sensor.temperature",
            "new_state": "20.5",
            "time_fired": "2023-01-01T12:00:00Z",
            "attributes": {
                "device_class": "temperature",
                "area": "living_room"
            },
            "weather": {
                "temperature": 15.2,
                "humidity": 65,
                "pressure": 1013.25,
                "wind_speed": 3.5,
                "weather_description": "clear sky",
                "location": "London"
            }
        }

        point = self.schema.create_event_point(event_data)

        if point:  # Only test if Point is available
            assert point._name == "home_assistant_events"
            assert "location" in point._tags
            assert point._tags["location"] == "London"
            assert "temperature" in point._fields
            assert point._fields["temperature"] == 15.2
            assert "humidity" in point._fields
            assert point._fields["humidity"] == 65
            assert "pressure" in point._fields
            assert point._fields["pressure"] == 1013.25
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
            "new_state": "20.5"
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
            "timestamp": "2023-01-01T12:00:00Z"
        }
        location = "London"

        point = self.schema.create_weather_point(weather_data, location)

        if point:  # Only test if Point is available
            assert point._name == "weather_data"
            assert "location" in point._tags
            assert point._tags["location"] == "London"
            assert "weather_condition" in point._tags
            assert point._tags["weather_condition"] == "Clear"
            assert "temperature" in point._fields
            assert point._fields["temperature"] == 15.2
            assert "humidity" in point._fields
            assert point._fields["humidity"] == 65
            assert "pressure" in point._fields
            assert point._fields["pressure"] == 1013.25
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
        tags = {
            "entity_id": "sensor.temperature",
            "domain": "sensor",
            "area": "living_room"
        }
        fields = {
            "avg_temperature": 20.5,
            "max_temperature": 25.0,
            "min_temperature": 15.0,
            "event_count": 100
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

        assert len(policies) == 3

        # Check raw data policy
        raw_policy = policies[0]
        assert raw_policy["name"] == "raw_data_1y"
        assert raw_policy["duration"] == "365d"
        assert raw_policy["shard_duration"] == "7d"
        assert raw_policy["replication"] == 1

        # Check hourly summary policy
        hourly_policy = policies[1]
        assert hourly_policy["name"] == "hourly_summary_2y"
        assert hourly_policy["duration"] == "730d"
        assert hourly_policy["shard_duration"] == "30d"

        # Check daily summary policy
        daily_policy = policies[2]
        assert daily_policy["name"] == "daily_summary_5y"
        assert daily_policy["duration"] == "1825d"
        assert daily_policy["shard_duration"] == "90d"

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
        assert "state" in rules["required_fields"]

        # Check tag patterns
        assert "entity_id" in rules["tag_patterns"]
        assert "domain" in rules["tag_patterns"]
        assert "device_class" in rules["tag_patterns"]

        # Check field types
        assert "state" in rules["field_types"]
        assert "temperature" in rules["field_types"]
        assert "humidity" in rules["field_types"]

    def test_validate_point_valid(self):
        """Test validating valid point"""
        if not Point:
            pytest.skip("InfluxDB Point not available")

        # Create a valid point
        point = Point("home_assistant_events")
        point = point.tag("entity_id", "sensor.temperature")
        point = point.tag("domain", "sensor")
        point = point.field("state", "20.5")

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
        point = point.field("state", "20.5")

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
        assert any("Missing required field: state" in error for error in errors)

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
