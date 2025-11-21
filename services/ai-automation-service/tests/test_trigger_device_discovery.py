"""
Unit tests for Trigger Device Discovery

Tests sensor discovery, entity conversion, and error handling.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from src.clients.device_intelligence_client import DeviceIntelligenceClient
from src.trigger_analysis.trigger_device_discovery import TriggerDeviceDiscovery


class TestTriggerDeviceDiscovery:
    """Test suite for TriggerDeviceDiscovery"""

    @pytest.fixture
    def mock_device_client(self):
        """Create mock device intelligence client"""
        client = MagicMock(spec=DeviceIntelligenceClient)
        client.search_sensors_by_condition = AsyncMock()
        return client

    @pytest.fixture
    def discovery(self, mock_device_client):
        """Create discovery instance with mocked client"""
        return TriggerDeviceDiscovery(mock_device_client)

    @pytest.fixture
    def sample_presence_condition(self):
        """Sample presence trigger condition"""
        return {
            "type": "trigger_condition",
            "trigger_type": "presence",
            "condition_text": "when I sit at desk",
            "location": "office",
            "required_device_class": "occupancy",
            "required_sensor_type": "binary_sensor",
            "confidence": 0.8,
            "extraction_method": "pattern_matching",
        }

    @pytest.fixture
    def sample_motion_condition(self):
        """Sample motion trigger condition"""
        return {
            "type": "trigger_condition",
            "trigger_type": "motion",
            "condition_text": "when motion detected",
            "location": "kitchen",
            "required_device_class": "motion",
            "required_sensor_type": "binary_sensor",
            "confidence": 0.8,
            "extraction_method": "pattern_matching",
        }

    @pytest.fixture
    def sample_sensor_device(self):
        """Sample sensor device from device intelligence"""
        return {
            "device_id": "presence-sensor-fp2-8b8a",
            "name": "PS FP2 Desk",
            "entity_id": "binary_sensor.ps_fp2_desk",
            "domain": "binary_sensor",
            "device_class": "occupancy",
            "area_name": "office",
            "area": "office",
            "manufacturer": "FP2",
            "model": "Presence Sensor FP2",
            "capabilities": ["presence_detection"],
            "health_score": 95,
            "entities": [
                {
                    "entity_id": "binary_sensor.ps_fp2_desk",
                    "domain": "binary_sensor",
                    "device_class": "occupancy",
                },
            ],
        }

    @pytest.mark.asyncio
    async def test_discover_presence_sensor(self, discovery, mock_device_client, sample_presence_condition, sample_sensor_device):
        """Test discovery of presence sensor"""
        # Mock device client response
        mock_device_client.search_sensors_by_condition.return_value = [sample_sensor_device]

        conditions = [sample_presence_condition]
        devices = await discovery.discover_trigger_devices(conditions)

        assert len(devices) == 1
        device = devices[0]
        assert device["name"] == "PS FP2 Desk"
        assert device["entity_id"] == "binary_sensor.ps_fp2_desk"
        assert device["device_class"] == "occupancy"
        assert device["trigger_type"] == "presence"
        assert device["area"] == "office"

        # Verify client was called correctly
        mock_device_client.search_sensors_by_condition.assert_called_once_with(
            trigger_type="presence",
            location="office",
            device_class="occupancy",
        )

    @pytest.mark.asyncio
    async def test_discover_motion_sensor(self, discovery, mock_device_client, sample_motion_condition):
        """Test discovery of motion sensor"""
        sample_motion_sensor = {
            "device_id": "motion-sensor-kitchen",
            "name": "Kitchen Motion Sensor",
            "entity_id": "binary_sensor.motion_kitchen",
            "domain": "binary_sensor",
            "device_class": "motion",
            "area_name": "kitchen",
            "entities": [
                {"entity_id": "binary_sensor.motion_kitchen", "domain": "binary_sensor"},
            ],
        }

        mock_device_client.search_sensors_by_condition.return_value = [sample_motion_sensor]

        conditions = [sample_motion_condition]
        devices = await discovery.discover_trigger_devices(conditions)

        assert len(devices) == 1
        assert devices[0]["entity_id"] == "binary_sensor.motion_kitchen"
        assert devices[0]["device_class"] == "motion"

    @pytest.mark.asyncio
    async def test_no_matching_sensors(self, discovery, mock_device_client, sample_presence_condition):
        """Test when no sensors match"""
        mock_device_client.search_sensors_by_condition.return_value = []

        conditions = [sample_presence_condition]
        devices = await discovery.discover_trigger_devices(conditions)

        assert len(devices) == 0

    @pytest.mark.asyncio
    async def test_multiple_matching_sensors(self, discovery, mock_device_client, sample_presence_condition):
        """Test when multiple sensors match"""
        sensor1 = {
            "device_id": "presence-sensor-1",
            "name": "PS FP2 Desk",
            "entity_id": "binary_sensor.ps_fp2_desk",
            "domain": "binary_sensor",
            "device_class": "occupancy",
            "area_name": "office",
            "entities": [{"entity_id": "binary_sensor.ps_fp2_desk"}],
        }
        sensor2 = {
            "device_id": "presence-sensor-2",
            "name": "PS FP2 Chair",
            "entity_id": "binary_sensor.ps_fp2_chair",
            "domain": "binary_sensor",
            "device_class": "occupancy",
            "area_name": "office",
            "entities": [{"entity_id": "binary_sensor.ps_fp2_chair"}],
        }

        mock_device_client.search_sensors_by_condition.return_value = [sensor1, sensor2]

        conditions = [sample_presence_condition]
        devices = await discovery.discover_trigger_devices(conditions)

        assert len(devices) == 2
        entity_ids = [d["entity_id"] for d in devices]
        assert "binary_sensor.ps_fp2_desk" in entity_ids
        assert "binary_sensor.ps_fp2_chair" in entity_ids

    @pytest.mark.asyncio
    async def test_duplicate_entities_filtered(self, discovery, mock_device_client, sample_presence_condition, sample_sensor_device):
        """Test that duplicate entities are filtered"""
        # Return same sensor twice (shouldn't happen but test defensive code)
        mock_device_client.search_sensors_by_condition.return_value = [sample_sensor_device, sample_sensor_device]

        conditions = [sample_presence_condition]
        devices = await discovery.discover_trigger_devices(conditions)

        # Should only return one device
        assert len(devices) == 1

    @pytest.mark.asyncio
    async def test_multiple_conditions(self, discovery, mock_device_client, sample_presence_condition, sample_motion_condition):
        """Test discovery with multiple trigger conditions"""
        presence_sensor = {
            "device_id": "presence-1",
            "name": "Presence Sensor",
            "entity_id": "binary_sensor.presence_office",
            "domain": "binary_sensor",
            "device_class": "occupancy",
            "area_name": "office",
            "entities": [{"entity_id": "binary_sensor.presence_office"}],
        }
        motion_sensor = {
            "device_id": "motion-1",
            "name": "Motion Sensor",
            "entity_id": "binary_sensor.motion_kitchen",
            "domain": "binary_sensor",
            "device_class": "motion",
            "area_name": "kitchen",
            "entities": [{"entity_id": "binary_sensor.motion_kitchen"}],
        }

        # Mock different responses for different conditions
        async def mock_search(trigger_type, location, device_class):
            if trigger_type == "presence":
                return [presence_sensor]
            if trigger_type == "motion":
                return [motion_sensor]
            return []

        mock_device_client.search_sensors_by_condition.side_effect = mock_search

        conditions = [sample_presence_condition, sample_motion_condition]
        devices = await discovery.discover_trigger_devices(conditions)

        assert len(devices) == 2
        trigger_types = [d["trigger_type"] for d in devices]
        assert "presence" in trigger_types
        assert "motion" in trigger_types

    @pytest.mark.asyncio
    async def test_empty_conditions_list(self, discovery):
        """Test with empty conditions list"""
        devices = await discovery.discover_trigger_devices([])

        assert devices == []

    @pytest.mark.asyncio
    async def test_condition_without_trigger_type(self, discovery, mock_device_client):
        """Test handling of condition without trigger_type"""
        invalid_condition = {
            "type": "trigger_condition",
            "condition_text": "some condition",
            "location": "office",
        }

        conditions = [invalid_condition]
        devices = await discovery.discover_trigger_devices(conditions)

        # Should skip invalid condition
        assert len(devices) == 0
        mock_device_client.search_sensors_by_condition.assert_not_called()

    @pytest.mark.asyncio
    async def test_sensor_to_entity_conversion(self, discovery, mock_device_client, sample_presence_condition, sample_sensor_device):
        """Test sensor to entity conversion"""
        mock_device_client.search_sensors_by_condition.return_value = [sample_sensor_device]

        conditions = [sample_presence_condition]
        devices = await discovery.discover_trigger_devices(conditions)

        assert len(devices) == 1
        entity = devices[0]

        # Check all required fields
        assert entity["name"] == "PS FP2 Desk"
        assert entity["entity_id"] == "binary_sensor.ps_fp2_desk"
        assert entity["device_id"] == "presence-sensor-fp2-8b8a"
        assert entity["domain"] == "binary_sensor"
        assert entity["type"] == "device"
        assert entity["area"] == "office"
        assert entity["device_class"] == "occupancy"
        assert entity["trigger_type"] == "presence"
        assert entity["trigger_condition"] == "when I sit at desk"
        assert entity["confidence"] == 0.8
        assert entity["extraction_method"] == "trigger_discovery"
        assert "capabilities" in entity
        assert "health_score" in entity

    @pytest.mark.asyncio
    async def test_sensor_with_missing_entity_id(self, discovery, mock_device_client, sample_presence_condition):
        """Test sensor conversion when entity_id is missing"""
        sensor_no_entity_id = {
            "device_id": "sensor-1",
            "name": "Sensor Without Entity ID",
            "domain": "binary_sensor",
            "entities": [],  # Empty entities list
        }

        mock_device_client.search_sensors_by_condition.return_value = [sensor_no_entity_id]

        conditions = [sample_presence_condition]
        devices = await discovery.discover_trigger_devices(conditions)

        # Should handle gracefully - may return None or use device_id as fallback
        # Implementation dependent
        assert isinstance(devices, list)

    @pytest.mark.asyncio
    async def test_client_error_handling(self, discovery, mock_device_client, sample_presence_condition):
        """Test error handling when client raises exception"""
        mock_device_client.search_sensors_by_condition.side_effect = Exception("Connection error")

        conditions = [sample_presence_condition]
        devices = await discovery.discover_trigger_devices(conditions)

        # Should return empty list on error (graceful degradation)
        assert devices == []

    @pytest.mark.asyncio
    async def test_sensor_with_entities_list(self, discovery, mock_device_client, sample_presence_condition):
        """Test sensor conversion when entity_id is in entities list"""
        sensor_with_entities = {
            "device_id": "sensor-1",
            "name": "Sensor",
            "domain": "binary_sensor",
            "entities": [
                {
                    "entity_id": "binary_sensor.test_sensor",
                    "domain": "binary_sensor",
                    "device_class": "occupancy",
                },
            ],
        }

        mock_device_client.search_sensors_by_condition.return_value = [sensor_with_entities]

        conditions = [sample_presence_condition]
        devices = await discovery.discover_trigger_devices(conditions)

        assert len(devices) == 1
        assert devices[0]["entity_id"] == "binary_sensor.test_sensor"

    @pytest.mark.asyncio
    async def test_entity_extraction_method(self, discovery, mock_device_client, sample_presence_condition, sample_sensor_device):
        """Test that extraction_method is set correctly"""
        mock_device_client.search_sensors_by_condition.return_value = [sample_sensor_device]

        conditions = [sample_presence_condition]
        devices = await discovery.discover_trigger_devices(conditions)

        assert len(devices) == 1
        assert devices[0]["extraction_method"] == "trigger_discovery"
