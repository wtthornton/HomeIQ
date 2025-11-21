"""
Tests for Event Processor
"""

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
            "new_state": {"state": "on", "entity_id": "light.living_room"},
        }

        is_valid, error_msg = self.processor.validate_event(event_data)

        assert is_valid is True
        assert error_msg == ""

    def test_validate_event_missing_event_type(self):
        """Test validation of event missing event_type"""
        event_data = {
            "old_state": {"state": "off"},
            "new_state": {"state": "on", "entity_id": "light.living_room"},
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
            "old_state": {"state": "off"},
        }

        is_valid, error_msg = self.processor.validate_event(event_data)

        assert is_valid is False
        assert "new_state" in error_msg

    def test_validate_state_changed_invalid_entity_id(self):
        """Test validation of state_changed event with invalid entity_id"""
        event_data = {
            "event_type": "state_changed",
            "old_state": {"state": "off"},
            "new_state": {"state": "on", "entity_id": "invalid_entity_id"},
        }

        is_valid, error_msg = self.processor.validate_event(event_data)

        assert is_valid is False
        assert "entity_id" in error_msg

    def test_validate_state_changed_invalid_state(self):
        """Test validation of state_changed event with invalid state"""
        event_data = {
            "event_type": "state_changed",
            "old_state": {"state": "off"},
            "new_state": {"state": 123, "entity_id": "light.living_room"},
        }

        is_valid, error_msg = self.processor.validate_event(event_data)

        assert is_valid is False
        assert "state" in error_msg

    def test_extract_event_data_state_changed(self):
        """Test extracting data from state_changed event"""
        event_data = {
            "event_type": "state_changed",
            "old_state": {"state": "off", "attributes": {"brightness": 0}},
            "new_state": {"state": "on", "entity_id": "light.living_room", "attributes": {"brightness": 255}},
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
            "new_state": None,
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
            "entity_id": "light.living_room",
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
            "custom_field": "custom_value",
        }

        extracted = self.processor.extract_event_data(event_data)

        assert extracted["event_type"] == "custom_event"
        assert extracted["generic_data"] == event_data

    def test_process_event_valid(self):
        """Test processing valid event"""
        event_data = {
            "event_type": "state_changed",
            "old_state": {"state": "off"},
            "new_state": {"state": "on", "entity_id": "light.living_room"},
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
            "old_state": {"state": "off"},
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
            "service_data": {"brightness": 255},
        }

        is_valid, error_msg = self.processor.validate_event(event_data)

        assert is_valid is True
        assert error_msg == ""

    def test_validate_call_service_missing_fields(self):
        """Test validation of call_service event missing required fields"""
        event_data = {
            "event_type": "call_service",
            "domain": "light",
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
