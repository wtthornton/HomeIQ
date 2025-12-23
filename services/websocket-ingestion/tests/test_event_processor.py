"""
Tests for Event Processor
"""

from unittest.mock import MagicMock

from src.event_processor import EventProcessor


class TestEventProcessor:
    """Test cases for EventProcessor class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.processor = EventProcessor()

    def test_initialization(self):
        """Test processor initialization"""
        assert self.processor.processed_events == 0
        assert self.processor.validation_errors == 0
        assert self.processor.last_processed_time is None

    def test_validate_event_valid_state_changed(self):
        """Test validation of valid state_changed event"""
        event_data = {
            "event_type": "state_changed",
            "old_state": {"state": "off"},
            "new_state": {"state": "on", "entity_id": "light.living_room"}
        }

        is_valid, error_msg = self.processor.validate_event(event_data)

        assert is_valid is True
        assert error_msg == ""

    def test_validate_event_missing_event_type(self):
        """Test validation of event missing event_type"""
        event_data = {
            "old_state": {"state": "off"},
            "new_state": {"state": "on", "entity_id": "light.living_room"}
        }

        is_valid, error_msg = self.processor.validate_event(event_data)

        assert is_valid is False
        assert "event_type" in error_msg

    def test_validate_event_invalid_data_type(self):
        """Test validation of non-dictionary event data"""
        event_data = "invalid_data"

        is_valid, error_msg = self.processor.validate_event(event_data)

        assert is_valid is False
        assert "dictionary" in error_msg

    def test_validate_state_changed_missing_new_state(self):
        """Test validation of state_changed event missing new_state"""
        event_data = {
            "event_type": "state_changed",
            "old_state": {"state": "off"}
        }

        is_valid, error_msg = self.processor.validate_event(event_data)

        assert is_valid is False
        assert "new_state" in error_msg

    def test_validate_state_changed_invalid_entity_id(self):
        """Test validation of state_changed event with invalid entity_id"""
        event_data = {
            "event_type": "state_changed",
            "old_state": {"state": "off"},
            "new_state": {"state": "on", "entity_id": "invalid_entity_id"}
        }

        is_valid, error_msg = self.processor.validate_event(event_data)

        assert is_valid is False
        assert "entity_id" in error_msg

    def test_validate_state_changed_invalid_state(self):
        """Test validation of state_changed event with invalid state"""
        event_data = {
            "event_type": "state_changed",
            "old_state": {"state": "off"},
            "new_state": {"state": 123, "entity_id": "light.living_room"}
        }

        is_valid, error_msg = self.processor.validate_event(event_data)

        assert is_valid is False
        assert "state" in error_msg

    def test_extract_event_data_state_changed(self):
        """Test extracting data from state_changed event"""
        event_data = {
            "event_type": "state_changed",
            "old_state": {"state": "off", "attributes": {"brightness": 0}},
            "new_state": {"state": "on", "entity_id": "light.living_room", "attributes": {"brightness": 255}}
        }

        extracted = self.processor.extract_event_data(event_data)

        assert extracted["event_type"] == "state_changed"
        assert extracted["entity_id"] == "light.living_room"
        assert extracted["domain"] == "light"
        assert extracted["old_state"]["state"] == "off"
        assert extracted["new_state"]["state"] == "on"
        assert extracted["state_change"]["from"] == "off"
        assert extracted["state_change"]["to"] == "on"
        assert extracted["state_change"]["changed"] is True

    def test_extract_event_data_handles_deleted_entity(self):
        """Ensure entity deletions with null new_state don't crash"""
        event_data = {
            "event_type": "state_changed",
            "old_state": {"state": "on", "entity_id": "sensor.kitchen_motion"},
            "new_state": None
        }

        extracted = self.processor.extract_event_data(event_data)

        assert extracted["entity_id"] == "sensor.kitchen_motion"
        assert extracted["state_change"]["from"] == "on"
        assert extracted["state_change"]["to"] is None
        assert extracted["state_change"]["changed"] is True

    def test_extract_event_data_call_service(self):
        """Test extracting data from call_service event"""
        event_data = {
            "event_type": "call_service",
            "domain": "light",
            "service": "turn_on",
            "service_data": {"brightness": 255},
            "entity_id": "light.living_room"
        }

        extracted = self.processor.extract_event_data(event_data)

        assert extracted["event_type"] == "call_service"
        assert extracted["domain"] == "light"
        assert extracted["service"] == "turn_on"
        assert extracted["service_data"]["brightness"] == 255
        assert extracted["entity_id"] == "light.living_room"

    def test_extract_event_data_generic_event(self):
        """Test extracting data from generic event"""
        event_data = {
            "event_type": "custom_event",
            "custom_field": "custom_value"
        }

        extracted = self.processor.extract_event_data(event_data)

        assert extracted["event_type"] == "custom_event"
        assert extracted["generic_data"] == event_data

    def test_process_event_valid(self):
        """Test processing valid event"""
        event_data = {
            "event_type": "state_changed",
            "old_state": {"state": "off"},
            "new_state": {"state": "on", "entity_id": "light.living_room"}
        }

        processed = self.processor.process_event(event_data)

        assert processed is not None
        assert processed["event_type"] == "state_changed"
        assert self.processor.processed_events == 1
        assert self.processor.validation_errors == 0
        assert self.processor.last_processed_time is not None

    def test_process_event_invalid(self):
        """Test processing invalid event"""
        event_data = {
            "event_type": "state_changed",
            "old_state": {"state": "off"}
            # Missing new_state
        }

        processed = self.processor.process_event(event_data)

        assert processed is None
        assert self.processor.processed_events == 0
        assert self.processor.validation_errors == 1

    def test_process_event_exception(self):
        """Test processing event with exception"""
        # Pass None to trigger exception
        processed = self.processor.process_event(None)

        assert processed is None
        assert self.processor.validation_errors == 1

    def test_get_processing_statistics(self):
        """Test getting processing statistics"""
        # Process some events
        self.processor.processed_events = 10
        self.processor.validation_errors = 2

        stats = self.processor.get_processing_statistics()

        assert stats["processed_events"] == 10
        assert stats["validation_errors"] == 2
        assert abs(stats["success_rate"] - 83.33) < 0.01  # 10/(10+2)*100

    def test_get_processing_statistics_no_events(self):
        """Test getting processing statistics with no events"""
        stats = self.processor.get_processing_statistics()

        assert stats["processed_events"] == 0
        assert stats["validation_errors"] == 0
        assert stats["success_rate"] == 0

    def test_reset_statistics(self):
        """Test resetting statistics"""
        # Set up some data
        self.processor.processed_events = 10
        self.processor.validation_errors = 2
        self.processor.last_processed_time = "2024-01-01T00:00:00"

        self.processor.reset_statistics()

        assert self.processor.processed_events == 0
        assert self.processor.validation_errors == 0
        assert self.processor.last_processed_time is None

    def test_validate_call_service_event(self):
        """Test validation of call_service event"""
        event_data = {
            "event_type": "call_service",
            "domain": "light",
            "service": "turn_on",
            "service_data": {"brightness": 255}
        }

        is_valid, error_msg = self.processor.validate_event(event_data)

        assert is_valid is True
        assert error_msg == ""

    def test_validate_call_service_missing_fields(self):
        """Test validation of call_service event missing required fields"""
        event_data = {
            "event_type": "call_service",
            "domain": "light"
            # Missing service and service_data
        }

        is_valid, error_msg = self.processor.validate_event(event_data)

        assert is_valid is False
        assert "service" in error_msg

    def test_extract_event_data_with_error(self):
        """Test extracting event data with error"""
        # Pass invalid data to trigger exception
        extracted = self.processor.extract_event_data("invalid_data")

        assert extracted["event_type"] == "error"
        assert "error" in extracted

    def test_validate_state_changed_with_data_field(self):
        """Test validation of state_changed event with Home Assistant 'data' field structure"""
        event_data = {
            "event_type": "state_changed",
            "time_fired": "2023-01-01T12:00:00.000Z",
            "origin": "LOCAL",
            "context": {"id": "context-123"},
            "data": {
                "entity_id": "light.living_room",
                "old_state": {"state": "off", "last_changed": "2023-01-01T12:00:00.000Z"},
                "new_state": {"state": "on", "entity_id": "light.living_room", "last_changed": "2023-01-01T12:01:00.000Z"}
            }
        }

        is_valid, error_msg = self.processor.validate_event(event_data)

        assert is_valid is True
        assert error_msg == ""

    def test_validate_state_changed_with_data_field_missing_entity_id(self):
        """Test validation of state_changed event with data field but missing entity_id"""
        event_data = {
            "event_type": "state_changed",
            "data": {
                "old_state": {"state": "off"},
                "new_state": {"state": "on"}
            }
        }

        is_valid, error_msg = self.processor.validate_event(event_data)

        assert is_valid is False
        assert "entity_id" in error_msg

    def test_validate_state_changed_with_data_field_null_new_state(self):
        """Test validation of state_changed event with null new_state (entity deletion)"""
        event_data = {
            "event_type": "state_changed",
            "data": {
                "entity_id": "sensor.deleted",
                "old_state": {"state": "on"},
                "new_state": None  # Valid for entity deletion
            }
        }

        is_valid, error_msg = self.processor.validate_event(event_data)

        assert is_valid is True
        assert error_msg == ""

    def test_extract_event_data_with_data_field(self):
        """Test extracting data from state_changed event with Home Assistant 'data' field structure"""
        event_data = {
            "event_type": "state_changed",
            "time_fired": "2023-01-01T12:00:00.000Z",
            "origin": "LOCAL",
            "context": {"id": "context-123", "parent_id": "parent-456", "user_id": "user-789"},
            "data": {
                "entity_id": "light.living_room",
                "old_state": {"state": "off", "last_changed": "2023-01-01T12:00:00.000Z"},
                "new_state": {"state": "on", "entity_id": "light.living_room", "last_changed": "2023-01-01T12:01:00.000Z"}
            }
        }

        extracted = self.processor.extract_event_data(event_data)

        assert extracted["event_type"] == "state_changed"
        assert extracted["entity_id"] == "light.living_room"
        assert extracted["domain"] == "light"
        assert extracted["time_fired"] == "2023-01-01T12:00:00.000Z"
        assert extracted["origin"] == "LOCAL"
        assert extracted["context"]["id"] == "context-123"
        assert extracted["context_id"] == "context-123"
        assert extracted["context_parent_id"] == "parent-456"
        assert extracted["context_user_id"] == "user-789"

    def test_extract_event_data_with_discovery_service_epic_23_2(self):
        """Test Epic 23.2: Device and area lookups with discovery_service"""
        # Mock discovery service
        mock_discovery = MagicMock()
        mock_discovery.get_device_id.return_value = "device-123"
        mock_discovery.get_area_id.return_value = "area-kitchen"
        mock_discovery.get_device_metadata.return_value = {
            "manufacturer": "Philips",
            "model": "Hue Light",
            "sw_version": "1.0.0"
        }

        processor = EventProcessor(discovery_service=mock_discovery)

        event_data = {
            "event_type": "state_changed",
            "data": {
                "entity_id": "light.living_room",
                "old_state": {"state": "off"},
                "new_state": {"state": "on", "entity_id": "light.living_room"}
            }
        }

        extracted = processor.extract_event_data(event_data)

        assert extracted["device_id"] == "device-123"
        assert extracted["area_id"] == "area-kitchen"
        assert extracted["device_metadata"]["manufacturer"] == "Philips"
        assert extracted["device_metadata"]["model"] == "Hue Light"
        mock_discovery.get_device_id.assert_called_once_with("light.living_room")
        mock_discovery.get_area_id.assert_called_once_with("light.living_room", "device-123")
        mock_discovery.get_device_metadata.assert_called_once_with("device-123")

    def test_extract_event_data_with_discovery_service_no_device(self):
        """Test Epic 23.2: Event processing when discovery_service returns None for device"""
        mock_discovery = MagicMock()
        mock_discovery.get_device_id.return_value = None
        mock_discovery.get_area_id.return_value = None

        processor = EventProcessor(discovery_service=mock_discovery)

        event_data = {
            "event_type": "state_changed",
            "data": {
                "entity_id": "light.unknown",
                "old_state": {"state": "off"},
                "new_state": {"state": "on", "entity_id": "light.unknown"}
            }
        }

        extracted = processor.extract_event_data(event_data)

        assert extracted["device_id"] is None
        assert extracted["area_id"] is None
        assert extracted["device_metadata"] is None

    def test_extract_event_data_duration_calculation_epic_23_3(self):
        """Test Epic 23.3: Duration calculation for time-based analytics"""
        event_data = {
            "event_type": "state_changed",
            "data": {
                "entity_id": "light.living_room",
                "old_state": {
                    "state": "off",
                    "last_changed": "2023-01-01T12:00:00.000Z"
                },
                "new_state": {
                    "state": "on",
                    "entity_id": "light.living_room",
                    "last_changed": "2023-01-01T12:00:30.000Z"  # 30 seconds later
                }
            }
        }

        extracted = self.processor.extract_event_data(event_data)

        assert extracted["duration_in_state"] == 30.0
        assert isinstance(extracted["duration_in_state"], float)

    def test_extract_event_data_duration_calculation_without_z_suffix(self):
        """Test Epic 23.3: Duration calculation with timestamps without 'Z' suffix"""
        event_data = {
            "event_type": "state_changed",
            "data": {
                "entity_id": "light.living_room",
                "old_state": {
                    "state": "off",
                    "last_changed": "2023-01-01T12:00:00+00:00"
                },
                "new_state": {
                    "state": "on",
                    "entity_id": "light.living_room",
                    "last_changed": "2023-01-01T12:00:15+00:00"  # 15 seconds later
                }
            }
        }

        extracted = self.processor.extract_event_data(event_data)

        assert extracted["duration_in_state"] == 15.0

    def test_extract_event_data_duration_calculation_negative_duration(self):
        """Test Epic 23.3: Negative duration is clamped to 0"""
        event_data = {
            "event_type": "state_changed",
            "data": {
                "entity_id": "light.living_room",
                "old_state": {
                    "state": "off",
                    "last_changed": "2023-01-01T12:00:30.000Z"  # Later time
                },
                "new_state": {
                    "state": "on",
                    "entity_id": "light.living_room",
                    "last_changed": "2023-01-01T12:00:00.000Z"  # Earlier time (invalid)
                }
            }
        }

        extracted = self.processor.extract_event_data(event_data)

        assert extracted["duration_in_state"] == 0  # Clamped to 0

    def test_extract_event_data_duration_calculation_missing_timestamps(self):
        """Test Epic 23.3: Duration is None when timestamps are missing"""
        event_data = {
            "event_type": "state_changed",
            "data": {
                "entity_id": "light.living_room",
                "old_state": {"state": "off"},  # No last_changed
                "new_state": {"state": "on", "entity_id": "light.living_room"}  # No last_changed
            }
        }

        extracted = self.processor.extract_event_data(event_data)

        assert extracted["duration_in_state"] is None

    def test_extract_event_data_duration_calculation_invalid_timestamp(self):
        """Test Epic 23.3: Duration is None when timestamp parsing fails"""
        event_data = {
            "event_type": "state_changed",
            "data": {
                "entity_id": "light.living_room",
                "old_state": {
                    "state": "off",
                    "last_changed": "invalid-timestamp"
                },
                "new_state": {
                    "state": "on",
                    "entity_id": "light.living_room",
                    "last_changed": "2023-01-01T12:00:00.000Z"
                }
            }
        }

        extracted = self.processor.extract_event_data(event_data)

        assert extracted["duration_in_state"] is None

    def test_extract_event_data_very_long_duration(self):
        """Test Epic 23.3: Very long durations (>7 days) are logged but kept"""
        event_data = {
            "event_type": "state_changed",
            "data": {
                "entity_id": "light.living_room",
                "old_state": {
                    "state": "off",
                    "last_changed": "2023-01-01T12:00:00.000Z"
                },
                "new_state": {
                    "state": "on",
                    "entity_id": "light.living_room",
                    "last_changed": "2023-01-10T12:00:00.000Z"  # 9 days later
                }
            }
        }

        extracted = self.processor.extract_event_data(event_data)

        # Should calculate duration (9 days = 777600 seconds)
        assert extracted["duration_in_state"] == 777600.0

    def test_validate_state_changed_with_data_field_invalid_data_type(self):
        """Test validation when data field is not a dictionary"""
        event_data = {
            "event_type": "state_changed",
            "data": "not_a_dict"
        }

        is_valid, error_msg = self.processor.validate_event(event_data)

        assert is_valid is False
        assert "dictionary" in error_msg

    def test_extract_event_data_legacy_structure_fallback(self):
        """Test extraction with legacy event structure (no 'data' field)"""
        event_data = {
            "event_type": "state_changed",
            "entity_id": "light.living_room",
            "old_state": {"state": "off", "entity_id": "light.living_room"},
            "new_state": {"state": "on", "entity_id": "light.living_room"}
        }

        extracted = self.processor.extract_event_data(event_data)

        assert extracted["entity_id"] == "light.living_room"
        assert extracted["domain"] == "light"
        assert extracted["old_state"]["state"] == "off"
        assert extracted["new_state"]["state"] == "on"

    def test_validate_service_registered_event(self):
        """Test validation of service_registered event"""
        event_data = {
            "event_type": "service_registered",
            "domain": "light",
            "service": "turn_on"
        }

        is_valid, error_msg = self.processor.validate_event(event_data)

        assert is_valid is True
        assert error_msg == ""

    def test_validate_service_removed_event(self):
        """Test validation of service_removed event"""
        event_data = {
            "event_type": "service_removed",
            "domain": "light",
            "service": "turn_on"
        }

        is_valid, error_msg = self.processor.validate_event(event_data)

        assert is_valid is True
        assert error_msg == ""

    def test_validate_unknown_event_type(self):
        """Test validation of unknown event type (should pass basic validation)"""
        event_data = {
            "event_type": "unknown_event",
            "custom_field": "value"
        }

        is_valid, error_msg = self.processor.validate_event(event_data)

        assert is_valid is True
        assert error_msg == ""
