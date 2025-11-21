"""
Unit Tests for MQTTCapabilityListener (Epic AI-2, Story AI2.1)

Tests MQTT bridge subscription and device capability discovery.
"""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from src.device_intelligence.capability_parser import CapabilityParser
from src.device_intelligence.mqtt_capability_listener import MQTTCapabilityListener


class TestMQTTCapabilityListener:
    """Test MQTTCapabilityListener MQTT bridge subscription and processing"""

    def setup_method(self):
        """Initialize mocks for each test"""
        self.mock_mqtt_client = Mock()
        self.mock_mqtt_client.subscribe = Mock(return_value=(0, 1))  # (result, mid)
        self.mock_db_session = AsyncMock()
        self.mock_parser = Mock(spec=CapabilityParser)

        self.listener = MQTTCapabilityListener(
            mqtt_client=self.mock_mqtt_client,
            db_session=self.mock_db_session,
            parser=self.mock_parser,
        )

    # =========================================================================
    # Listener Startup Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_listener_starts_successfully(self):
        """Test listener starts and subscribes to bridge topic"""
        await self.listener.start()

        # Should subscribe to bridge devices topic
        self.mock_mqtt_client.subscribe.assert_called_once_with(
            "zigbee2mqtt/bridge/devices",
        )

        # Should set message callback
        assert self.mock_mqtt_client.on_message is not None

        # Should be marked as started
        assert self.listener.is_started() is True

    @pytest.mark.asyncio
    async def test_listener_start_called_twice(self):
        """Test listener handles being started twice"""
        await self.listener.start()
        await self.listener.start()  # Second call

        # Should only subscribe once
        assert self.mock_mqtt_client.subscribe.call_count == 1

    @pytest.mark.asyncio
    async def test_listener_start_failure(self):
        """Test listener handles subscription failure"""
        self.mock_mqtt_client.subscribe.side_effect = Exception("Connection failed")

        with pytest.raises(Exception):
            await self.listener.start()

        # Should not be marked as started
        assert self.listener.is_started() is False

    # =========================================================================
    # Bridge Message Processing Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_process_bridge_message_success(self):
        """Test processing valid bridge message with devices"""
        # Mock parser to return capabilities
        self.mock_parser.parse_exposes.return_value = {
            "light_control": {"type": "composite"},
            "smart_bulb_mode": {"type": "enum"},
        }

        devices = [
            {
                "friendly_name": "kitchen_switch",
                "definition": {
                    "vendor": "Inovelli",
                    "model": "VZM31-SN",
                    "description": "Red Series Dimmer Switch",
                    "exposes": [
                        {"type": "light", "features": [{"name": "state"}]},
                        {"type": "enum", "name": "smartBulbMode", "values": ["Disabled", "Enabled"]},
                    ],
                },
            },
        ]

        await self.listener._process_devices(devices)

        # Should have processed device
        assert self.listener.devices_processed == 1
        assert self.listener.devices_discovered == 1
        assert self.listener.errors == 0

        # Parser should have been called
        self.mock_parser.parse_exposes.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_device_without_definition(self):
        """Test skipping device without definition (coordinator/router)"""
        devices = [
            {
                "friendly_name": "coordinator",
                "definition": None,  # No definition = coordinator
            },
        ]

        await self.listener._process_devices(devices)

        # Should have skipped device
        assert self.listener.devices_processed == 0
        assert self.listener.devices_skipped == 1
        assert self.listener.devices_discovered == 1

    @pytest.mark.asyncio
    async def test_process_device_without_exposes(self):
        """Test skipping device without exposes array"""
        devices = [
            {
                "friendly_name": "router",
                "definition": {
                    "vendor": "Unknown",
                    "model": "Router",
                    "exposes": [],  # No exposes
                },
            },
        ]

        await self.listener._process_devices(devices)

        # Should have skipped device
        assert self.listener.devices_processed == 0
        assert self.listener.devices_skipped == 1

    @pytest.mark.asyncio
    async def test_process_multiple_devices(self):
        """Test processing multiple devices from bridge"""
        self.mock_parser.parse_exposes.return_value = {"light_control": {}}

        devices = [
            {
                "friendly_name": f"device_{i}",
                "definition": {
                    "vendor": "Manufacturer",
                    "model": f"Model{i}",
                    "exposes": [{"type": "light"}],
                },
            }
            for i in range(5)
        ]

        await self.listener._process_devices(devices)

        # Should have processed all devices
        assert self.listener.devices_processed == 5
        assert self.listener.devices_discovered == 5

        # Parser should have been called 5 times
        assert self.mock_parser.parse_exposes.call_count == 5

    # =========================================================================
    # MQTT Message Callback Tests
    # =========================================================================

    def test_on_message_valid_json(self):
        """Test MQTT callback with valid JSON payload"""
        mock_message = Mock()
        mock_message.topic = "zigbee2mqtt/bridge/devices"
        mock_message.payload = json.dumps([
            {
                "friendly_name": "test_device",
                "definition": {
                    "vendor": "Test",
                    "model": "Test-1",
                    "exposes": [{"type": "switch"}],
                },
            },
        ])

        # Call message handler
        self.listener._on_message(None, None, mock_message)

        # Should have queued devices for processing (Story 2.3 batch pattern)
        assert len(self.listener._pending_devices) == 1
        assert self.listener._pending_devices[0]["friendly_name"] == "test_device"

    def test_on_message_invalid_json(self):
        """Test MQTT callback with malformed JSON"""
        mock_message = Mock()
        mock_message.topic = "zigbee2mqtt/bridge/devices"
        mock_message.payload = b"invalid json{"

        # Should not crash
        self.listener._on_message(None, None, mock_message)

        # Error count should increase
        assert self.listener.errors == 1

    def test_on_message_not_array(self):
        """Test MQTT callback with non-array payload"""
        mock_message = Mock()
        mock_message.topic = "zigbee2mqtt/bridge/devices"
        mock_message.payload = json.dumps({"not": "an array"})

        # Should not crash
        self.listener._on_message(None, None, mock_message)

    def test_on_message_wrong_topic(self):
        """Test MQTT callback ignores messages from other topics"""
        mock_message = Mock()
        mock_message.topic = "other/topic"
        mock_message.payload = b"data"

        with patch("asyncio.create_task") as mock_task:
            self.listener._on_message(None, None, mock_message)

            # Should NOT create task for other topics
            mock_task.assert_not_called()

    # =========================================================================
    # Parser Integration Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_parser_returns_empty_capabilities(self):
        """Test handling when parser returns no capabilities"""
        self.mock_parser.parse_exposes.return_value = {}  # Empty

        devices = [
            {
                "friendly_name": "test_device",
                "definition": {
                    "vendor": "Test",
                    "model": "Test-1",
                    "exposes": [{"type": "unknown"}],
                },
            },
        ]

        await self.listener._process_devices(devices)

        # Should skip device with no capabilities
        assert self.listener.devices_processed == 0
        assert self.listener.devices_skipped == 1

    @pytest.mark.asyncio
    async def test_parser_raises_exception(self):
        """Test handling when parser raises exception"""
        self.mock_parser.parse_exposes.side_effect = Exception("Parser error")

        devices = [
            {
                "friendly_name": "test_device",
                "definition": {
                    "vendor": "Test",
                    "model": "Test-1",
                    "exposes": [{"type": "light"}],
                },
            },
        ]

        await self.listener._process_devices(devices)

        # Should count as error
        assert self.listener.errors == 1

    # =========================================================================
    # Statistics Tests
    # =========================================================================

    def test_get_stats_initial(self):
        """Test get_stats returns initial values"""
        stats = self.listener.get_stats()

        assert stats["devices_discovered"] == 0
        assert stats["devices_processed"] == 0
        assert stats["devices_skipped"] == 0
        assert stats["errors"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_after_processing(self):
        """Test get_stats returns correct values after processing"""
        self.mock_parser.parse_exposes.return_value = {"light": {}}

        devices = [
            {"friendly_name": "d1", "definition": {"vendor": "A", "model": "M1", "exposes": [{}]}},
            {"friendly_name": "d2", "definition": None},  # Skipped
            {"friendly_name": "d3", "definition": {"vendor": "B", "model": "M2", "exposes": [{}]}},
        ]

        await self.listener._process_devices(devices)

        stats = self.listener.get_stats()

        assert stats["devices_discovered"] == 3
        assert stats["devices_processed"] == 2
        assert stats["devices_skipped"] == 1
        assert stats["errors"] == 0

    # =========================================================================
    # Performance Tests (NFR12: <3 minutes for 100 devices)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_performance_100_devices(self):
        """Test processing 100 devices completes quickly"""
        import time

        self.mock_parser.parse_exposes.return_value = {"light": {}}

        # Create 100 devices
        devices = [
            {
                "friendly_name": f"device_{i}",
                "definition": {
                    "vendor": "Manufacturer",
                    "model": f"Model{i}",
                    "exposes": [{"type": "light"}],
                },
            }
            for i in range(100)
        ]

        start_time = time.time()
        await self.listener._process_devices(devices)
        duration = time.time() - start_time

        # Should complete in reasonable time (well under 3 minutes)
        assert duration < 5  # 5 seconds for 100 devices
        assert self.listener.devices_processed == 100

    # =========================================================================
    # Real-World Scenario Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_mixed_device_types(self):
        """Test processing mix of valid devices, coordinators, and routers"""
        self.mock_parser.parse_exposes.return_value = {"light": {}}

        devices = [
            # Valid device with capabilities
            {
                "friendly_name": "kitchen_switch",
                "definition": {
                    "vendor": "Inovelli",
                    "model": "VZM31-SN",
                    "exposes": [{"type": "light"}],
                },
            },
            # Coordinator (no definition)
            {
                "friendly_name": "coordinator",
                "definition": None,
            },
            # Router (no exposes)
            {
                "friendly_name": "router",
                "definition": {
                    "vendor": "Router",
                    "model": "Router-1",
                    "exposes": [],
                },
            },
            # Another valid device
            {
                "friendly_name": "bedroom_sensor",
                "definition": {
                    "vendor": "Aqara",
                    "model": "MCCGQ11LM",
                    "exposes": [{"type": "binary"}],
                },
            },
        ]

        await self.listener._process_devices(devices)

        # Should process 2 valid devices, skip 2
        assert self.listener.devices_processed == 2
        assert self.listener.devices_skipped == 2
        assert self.listener.devices_discovered == 4

    @pytest.mark.asyncio
    async def test_is_started_flag(self):
        """Test is_started() returns correct state"""
        assert self.listener.is_started() is False

        await self.listener.start()

        assert self.listener.is_started() is True

    # =========================================================================
    # Error Recovery Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_continues_after_error(self):
        """Test listener continues processing after encountering errors"""
        # First call succeeds, second fails, third succeeds
        self.mock_parser.parse_exposes.side_effect = [
            {"light": {}},  # Success
            Exception("Parse error"),  # Error
            {"switch": {}},  # Success
        ]

        devices = [
            {"friendly_name": "d1", "definition": {"vendor": "A", "model": "M1", "exposes": [{}]}},
            {"friendly_name": "d2", "definition": {"vendor": "B", "model": "M2", "exposes": [{}]}},
            {"friendly_name": "d3", "definition": {"vendor": "C", "model": "M3", "exposes": [{}]}},
        ]

        await self.listener._process_devices(devices)

        # Should have processed 2 successfully, 1 error
        assert self.listener.devices_processed == 2
        assert self.listener.errors == 1

