"""
Comprehensive tests for enhanced device intelligence integration
"""

import pytest

pytest.importorskip(
    "transformers",
    reason="transformers dependency not available in this environment"
)

from unittest.mock import AsyncMock, patch
from src.entity_extraction.enhanced_extractor import EnhancedEntityExtractor
from src.prompt_building.enhanced_prompt_builder import EnhancedPromptBuilder
from src.clients.device_intelligence_client import DeviceIntelligenceClient

@pytest.mark.asyncio
async def test_enhanced_entity_extraction():
    """Test enhanced entity extraction with mock device intelligence"""
    
    # Mock device intelligence client
    mock_client = AsyncMock()
    mock_client.get_devices_by_area.return_value = [
        {
            'id': 'device1',
            'name': 'Office Main Light',
            'area_name': 'office',
            'manufacturer': 'Inovelli',
            'model': 'VZM31-SN',
            'health_score': 85
        }
    ]
    mock_client.get_device_details.return_value = {
        'id': 'device1',
        'name': 'Office Main Light',
        'area_name': 'office',
        'manufacturer': 'Inovelli',
        'model': 'VZM31-SN',
        'health_score': 85,
        'capabilities': [
            {'feature': 'led_notifications', 'supported': True, 'configured': False},
            {'feature': 'smart_bulb_mode', 'supported': True, 'configured': True}
        ],
        'entities': [
            {
                'entity_id': 'light.office_main',
                'domain': 'light',
                'state': 'off',
                'attributes': {'brightness': 0}
            }
        ]
    }
    
    extractor = EnhancedEntityExtractor(mock_client)
    entities = await extractor.extract_entities_with_intelligence("Flash office lights when door opens")
    
    assert len(entities) == 1
    assert entities[0]['name'] == 'Office Main Light'
    assert entities[0]['manufacturer'] == 'Inovelli'
    assert entities[0]['model'] == 'VZM31-SN'
    assert 'led_notifications' in [cap['feature'] for cap in entities[0]['capabilities']]

@pytest.mark.asyncio
async def test_enhanced_prompt_building():
    """Test enhanced prompt building with device capabilities"""
    
    entities = [
        {
            'name': 'Office Main Light',
            'manufacturer': 'Inovelli',
            'model': 'VZM31-SN',
            'entity_id': 'light.office_main',
            'area': 'office',
            'state': 'off',
            'health_score': 85,
            'capabilities': [
                {'feature': 'led_notifications', 'supported': True},
                {'feature': 'smart_bulb_mode', 'supported': True}
            ],
            'extraction_method': 'device_intelligence'
        }
    ]
    
    builder = EnhancedPromptBuilder()
    prompt = builder.build_suggestion_prompt("Flash office lights when door opens", entities)
    
    assert "LED notifications" in prompt
    assert "smart bulb mode" in prompt
    assert "health_score" in prompt
    assert "Inovelli VZM31-SN" in prompt
    assert "capabilities_used" in prompt

@pytest.mark.asyncio
async def test_fallback_to_basic_extraction():
    """Test fallback to basic extraction when device intelligence fails"""
    
    # Mock client that fails
    mock_client = AsyncMock()
    mock_client.get_devices_by_area.side_effect = Exception("Service unavailable")
    
    extractor = EnhancedEntityExtractor(mock_client)
    entities = await extractor.extract_entities_with_intelligence("Flash office lights when door opens")
    
    # Should fall back to basic pattern matching
    assert len(entities) >= 1
    assert entities[0]['extraction_method'] == 'pattern_matching'

@pytest.mark.asyncio
async def test_health_score_filtering():
    """Test that devices with low health scores are filtered out"""
    
    mock_client = AsyncMock()
    mock_client.get_devices_by_area.return_value = [
        {
            'id': 'device1',
            'name': 'Healthy Light',
            'area_name': 'office',
            'health_score': 85
        },
        {
            'id': 'device2', 
            'name': 'Unhealthy Light',
            'area_name': 'office',
            'health_score': 30
        }
    ]
    
    # Mock device details
    def mock_get_device_details(device_id):
        if device_id == 'device1':
            return {
                'id': 'device1',
                'name': 'Healthy Light',
                'area_name': 'office',
                'health_score': 85,
                'capabilities': [],
                'entities': [{'entity_id': 'light.healthy', 'domain': 'light', 'state': 'off'}]
            }
        elif device_id == 'device2':
            return {
                'id': 'device2',
                'name': 'Unhealthy Light',
                'area_name': 'office',
                'health_score': 30,
                'capabilities': [],
                'entities': [{'entity_id': 'light.unhealthy', 'domain': 'light', 'state': 'off'}]
            }
        return None
    
    mock_client.get_device_details.side_effect = mock_get_device_details
    
    extractor = EnhancedEntityExtractor(mock_client)
    entities = await extractor.extract_entities_with_intelligence("Flash office lights when door opens")
    
    # Should only include healthy device
    assert len(entities) == 1
    assert entities[0]['name'] == 'Healthy Light'
    assert entities[0]['health_score'] == 85

@pytest.mark.asyncio
async def test_capability_extraction():
    """Test extraction of device capabilities"""
    
    mock_client = AsyncMock()
    mock_client.get_devices_by_area.return_value = [
        {
            'id': 'device1',
            'name': 'Smart Light',
            'area_name': 'office',
            'health_score': 90
        }
    ]
    mock_client.get_device_details.return_value = {
        'id': 'device1',
        'name': 'Smart Light',
        'area_name': 'office',
        'health_score': 90,
        'capabilities': [
            {'feature': 'led_notifications', 'supported': True, 'configured': False},
            {'feature': 'smart_bulb_mode', 'supported': True, 'configured': True},
            {'feature': 'auto_off_timer', 'supported': True, 'configured': False},
            {'feature': 'unsupported_feature', 'supported': False, 'configured': False}
        ],
        'entities': [
            {
                'entity_id': 'light.smart',
                'domain': 'light',
                'state': 'off',
                'attributes': {'brightness': 0}
            }
        ]
    }
    
    extractor = EnhancedEntityExtractor(mock_client)
    entities = await extractor.extract_entities_with_intelligence("Use smart light features")
    
    assert len(entities) == 1
    capabilities = entities[0]['capabilities']
    
    # Should include supported capabilities
    supported_features = [cap['feature'] for cap in capabilities if cap.get('supported')]
    assert 'led_notifications' in supported_features
    assert 'smart_bulb_mode' in supported_features
    assert 'auto_off_timer' in supported_features
    
    # Should not include unsupported features
    assert 'unsupported_feature' not in supported_features

@pytest.mark.asyncio
async def test_area_devices_summary():
    """Test area devices summary functionality"""
    
    mock_client = AsyncMock()
    mock_client.get_devices_by_area.return_value = [
        {
            'id': 'device1',
            'name': 'Office Light',
            'area_name': 'office',
            'health_score': 85
        },
        {
            'id': 'device2',
            'name': 'Office Sensor',
            'area_name': 'office',
            'health_score': 90
        }
    ]
    
    def mock_get_device_details(device_id):
        if device_id == 'device1':
            return {
                'id': 'device1',
                'name': 'Office Light',
                'area_name': 'office',
                'integration': 'zigbee2mqtt',
                'health_score': 85,
                'capabilities': [
                    {'feature': 'led_notifications', 'supported': True}
                ]
            }
        elif device_id == 'device2':
            return {
                'id': 'device2',
                'name': 'Office Sensor',
                'area_name': 'office',
                'integration': 'zigbee2mqtt',
                'health_score': 90,
                'capabilities': [
                    {'feature': 'motion_detection', 'supported': True}
                ]
            }
        return None
    
    mock_client.get_device_details.side_effect = mock_get_device_details
    
    extractor = EnhancedEntityExtractor(mock_client)
    summary = await extractor.get_area_devices_summary('office')
    
    assert summary['area_name'] == 'office'
    assert summary['total_devices'] == 2
    assert summary['device_types']['zigbee2mqtt'] == 2
    assert 'led_notifications' in summary['capabilities_available']
    assert 'motion_detection' in summary['capabilities_available']
    assert len(summary['health_scores']) == 2
    assert 85 in summary['health_scores']
    assert 90 in summary['health_scores']
