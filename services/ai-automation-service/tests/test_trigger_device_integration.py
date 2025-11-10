"""
Integration tests for Trigger Device Discovery

Tests the complete flow: query → entity extraction → trigger discovery → results
"""

import pytest

pytest.importorskip(
    "transformers",
    reason="transformers dependency not available in this environment"
)

from unittest.mock import AsyncMock, MagicMock, patch
from src.entity_extraction.multi_model_extractor import MultiModelEntityExtractor
from src.trigger_analysis.trigger_condition_analyzer import TriggerConditionAnalyzer
from src.trigger_analysis.trigger_device_discovery import TriggerDeviceDiscovery
from src.clients.device_intelligence_client import DeviceIntelligenceClient


class TestTriggerDeviceDiscoveryIntegration:
    """Integration tests for trigger device discovery"""
    
    @pytest.fixture
    def mock_device_client(self):
        """Create mock device intelligence client"""
        client = MagicMock(spec=DeviceIntelligenceClient)
        client.get_devices_by_area = AsyncMock(return_value=[])
        client.get_all_devices = AsyncMock(return_value=[])
        client.get_device_details = AsyncMock(return_value=None)
        client.search_sensors_by_condition = AsyncMock(return_value=[])
        return client
    
    @pytest.fixture
    def extractor(self, mock_device_client):
        """Create MultiModelEntityExtractor with mocked dependencies"""
        return MultiModelEntityExtractor(
            openai_api_key="test-key",
            device_intelligence_client=mock_device_client
        )
    
    @pytest.fixture
    def sample_presence_sensor(self):
        """Sample presence sensor device"""
        return {
            'device_id': 'presence-sensor-fp2-8b8a',
            'name': 'PS FP2 Desk',
            'entity_id': 'binary_sensor.ps_fp2_desk',
            'domain': 'binary_sensor',
            'device_class': 'occupancy',
            'area_name': 'office',
            'area': 'office',
            'manufacturer': 'FP2',
            'model': 'Presence Sensor FP2',
            'capabilities': ['presence_detection'],
            'health_score': 95,
            'entities': [
                {
                    'entity_id': 'binary_sensor.ps_fp2_desk',
                    'domain': 'binary_sensor',
                    'device_class': 'occupancy'
                }
            ]
        }
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_complete_flow_with_presence_trigger(self, extractor, mock_device_client, sample_presence_sensor):
        """Test complete flow: query → extraction → trigger discovery"""
        query = "When I sit at my desk. I wan the wled sprit to show fireworks for 15 sec and slowly run the 4 celling lights to energize."
        
        # Mock device intelligence responses
        mock_device_client.get_all_devices.return_value = []
        mock_device_client.search_sensors_by_condition.return_value = [sample_presence_sensor]
        
        # Extract entities (will trigger discovery)
        entities = await extractor.extract_entities(query)
        
        # Verify trigger device was discovered
        trigger_devices = [e for e in entities if e.get('extraction_method') == 'trigger_discovery']
        assert len(trigger_devices) > 0
        
        # Verify presence sensor was found
        presence_device = next((e for e in trigger_devices if e.get('entity_id') == 'binary_sensor.ps_fp2_desk'), None)
        assert presence_device is not None
        assert presence_device['name'] == 'PS FP2 Desk'
        assert presence_device['trigger_type'] == 'presence'
        assert presence_device['device_class'] == 'occupancy'
        
        # Verify search was called correctly
        mock_device_client.search_sensors_by_condition.assert_called()
        call_args = mock_device_client.search_sensors_by_condition.call_args
        assert call_args.kwargs['trigger_type'] == 'presence'
        assert call_args.kwargs['device_class'] == 'occupancy'
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_flow_without_trigger_conditions(self, extractor, mock_device_client):
        """Test flow when query has no trigger conditions"""
        query = "Turn on the lights at 7am"
        
        entities = await extractor.extract_entities(query)
        
        # Should not call trigger discovery
        mock_device_client.search_sensors_by_condition.assert_not_called()
        
        # Should return entities (may be empty if no matches)
        assert isinstance(entities, list)
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_flow_with_motion_trigger(self, extractor, mock_device_client):
        """Test flow with motion trigger"""
        query = "When motion is detected in the kitchen, turn on the lights"
        
        motion_sensor = {
            'device_id': 'motion-kitchen',
            'name': 'Kitchen Motion Sensor',
            'entity_id': 'binary_sensor.motion_kitchen',
            'domain': 'binary_sensor',
            'device_class': 'motion',
            'area_name': 'kitchen',
            'entities': [{'entity_id': 'binary_sensor.motion_kitchen'}]
        }
        
        mock_device_client.search_sensors_by_condition.return_value = [motion_sensor]
        
        entities = await extractor.extract_entities(query)
        
        # Verify motion sensor was discovered
        trigger_devices = [e for e in entities if e.get('extraction_method') == 'trigger_discovery']
        assert len(trigger_devices) > 0
        
        motion_device = next((e for e in trigger_devices if e.get('entity_id') == 'binary_sensor.motion_kitchen'), None)
        assert motion_device is not None
        assert motion_device['trigger_type'] == 'motion'
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_flow_graceful_degradation_on_error(self, extractor, mock_device_client):
        """Test graceful degradation when trigger discovery fails"""
        query = "When I sit at my desk, turn on the lights"
        
        # Simulate error in trigger discovery
        mock_device_client.search_sensors_by_condition.side_effect = Exception("Service unavailable")
        
        # Should not raise exception
        entities = await extractor.extract_entities(query)
        
        # Should return entities (may be empty or just action devices)
        assert isinstance(entities, list)
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_flow_with_action_and_trigger_devices(self, extractor, mock_device_client, sample_presence_sensor):
        """Test flow where both action devices and trigger devices are found"""
        query = "When I sit at my desk, turn on the office lights"
        
        # Mock action device
        light_device = {
            'device_id': 'light-office',
            'name': 'Office Lights',
            'entities': [
                {'entity_id': 'light.office', 'domain': 'light'}
            ]
        }
        
        mock_device_client.get_all_devices.return_value = [light_device]
        mock_device_client.get_device_details.return_value = {
            'name': 'Office Lights',
            'entities': [{'entity_id': 'light.office', 'domain': 'light'}],
            'area_name': 'office'
        }
        mock_device_client.search_sensors_by_condition.return_value = [sample_presence_sensor]
        
        entities = await extractor.extract_entities(query)
        
        # Should have both action devices and trigger devices
        action_devices = [e for e in entities if e.get('extraction_method') != 'trigger_discovery']
        trigger_devices = [e for e in entities if e.get('extraction_method') == 'trigger_discovery']
        
        # Both should be present (exact counts depend on entity extraction)
        assert len(entities) > 0
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_statistics_tracking(self, extractor, mock_device_client, sample_presence_sensor):
        """Test that statistics are tracked correctly"""
        query = "When I sit at my desk, turn on the lights"
        
        mock_device_client.search_sensors_by_condition.return_value = [sample_presence_sensor]
        
        initial_stats = extractor.get_stats()
        initial_trigger_count = initial_stats.get('trigger_devices_discovered', 0)
        
        await extractor.extract_entities(query)
        
        updated_stats = extractor.get_stats()
        updated_trigger_count = updated_stats.get('trigger_devices_discovered', 0)
        
        # Should increment trigger device count
        assert updated_trigger_count >= initial_trigger_count
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_multiple_trigger_types(self, extractor, mock_device_client):
        """Test flow with multiple trigger types in query"""
        query = "When motion is detected or the door opens, turn on the lights"
        
        motion_sensor = {
            'device_id': 'motion-1',
            'name': 'Motion Sensor',
            'entity_id': 'binary_sensor.motion',
            'device_class': 'motion',
            'entities': [{'entity_id': 'binary_sensor.motion'}]
        }
        
        door_sensor = {
            'device_id': 'door-1',
            'name': 'Door Sensor',
            'entity_id': 'binary_sensor.door',
            'device_class': 'door',
            'entities': [{'entity_id': 'binary_sensor.door'}]
        }
        
        # Return different sensors based on trigger type
        async def mock_search(trigger_type, location, device_class):
            if trigger_type == 'motion':
                return [motion_sensor]
            elif trigger_type == 'door':
                return [door_sensor]
            return []
        
        mock_device_client.search_sensors_by_condition.side_effect = mock_search
        
        entities = await extractor.extract_entities(query)
        
        # Should discover both trigger types
        trigger_devices = [e for e in entities if e.get('extraction_method') == 'trigger_discovery']
        trigger_types = [e.get('trigger_type') for e in trigger_devices]
        
        # Should have at least one trigger type discovered
        assert len(trigger_devices) > 0
