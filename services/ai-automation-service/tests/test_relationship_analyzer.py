"""
Unit tests for Relationship Analyzer

Story AI3.3: Unconnected Relationship Analysis
Epic AI-3: Cross-Device Synergy & Contextual Opportunities
"""

from unittest.mock import AsyncMock

import pytest
from src.synergy_detection.relationship_analyzer import HomeAssistantAutomationChecker

# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_ha_client():
    """Mock Home Assistant client"""
    client = AsyncMock()

    # Mock automation configurations
    client.get_automations = AsyncMock(return_value=[
        {
            'id': 'bedroom_motion_light',
            'alias': 'Bedroom Motion Lighting',
            'trigger': [
                {
                    'platform': 'state',
                    'entity_id': 'binary_sensor.bedroom_motion',
                    'to': 'on'
                }
            ],
            'action': [
                {
                    'service': 'light.turn_on',
                    'target': {
                        'entity_id': 'light.bedroom_ceiling'
                    }
                }
            ]
        },
        {
            'id': 'door_lock',
            'alias': 'Auto Lock Front Door',
            'trigger': [
                {
                    'platform': 'state',
                    'entity_id': 'binary_sensor.front_door',
                    'to': 'off',
                    'for': '00:02:00'
                }
            ],
            'action': [
                {
                    'service': 'lock.lock',
                    'entity_id': 'lock.front_door'
                }
            ]
        }
    ])

    return client


# ============================================================================
# Automation Fetching Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_existing_automations(mock_ha_client):
    """Test fetching automations from HA"""
    checker = HomeAssistantAutomationChecker(mock_ha_client)

    automations = await checker.get_existing_automations()

    assert len(automations) == 2
    assert automations[0]['id'] == 'bedroom_motion_light'
    assert automations[1]['id'] == 'door_lock'


@pytest.mark.asyncio
async def test_automations_caching(mock_ha_client):
    """Test that automations are cached"""
    checker = HomeAssistantAutomationChecker(mock_ha_client)

    # First call
    automations1 = await checker.get_existing_automations()

    # Second call (should use cache)
    automations2 = await checker.get_existing_automations()

    # Should only call HA API once
    assert mock_ha_client.get_automations.call_count == 1
    assert automations1 == automations2


# ============================================================================
# Relationship Parsing Tests
# ============================================================================

@pytest.mark.asyncio
async def test_parse_simple_automation(mock_ha_client):
    """Test parsing simple state trigger → service call automation"""
    checker = HomeAssistantAutomationChecker(mock_ha_client)

    automation = {
        'trigger': {
            'platform': 'state',
            'entity_id': 'binary_sensor.motion'
        },
        'action': {
            'service': 'light.turn_on',
            'target': {
                'entity_id': 'light.bedroom'
            }
        }
    }

    relationships = checker._parse_automation_relationships(automation)

    assert len(relationships) == 1
    assert relationships[0] == ('binary_sensor.motion', 'light.bedroom')


@pytest.mark.asyncio
async def test_parse_multiple_triggers_and_actions():
    """Test parsing automation with multiple triggers and actions"""
    checker = HomeAssistantAutomationChecker(AsyncMock())

    automation = {
        'trigger': [
            {'platform': 'state', 'entity_id': 'binary_sensor.motion_1'},
            {'platform': 'state', 'entity_id': 'binary_sensor.motion_2'}
        ],
        'action': [
            {'service': 'light.turn_on', 'target': {'entity_id': 'light.light_1'}},
            {'service': 'light.turn_on', 'target': {'entity_id': 'light.light_2'}}
        ]
    }

    relationships = checker._parse_automation_relationships(automation)

    # Should create 2x2 = 4 relationships
    assert len(relationships) == 4
    assert ('binary_sensor.motion_1', 'light.light_1') in relationships
    assert ('binary_sensor.motion_2', 'light.light_2') in relationships


@pytest.mark.asyncio
async def test_parse_action_with_list_entities():
    """Test parsing action with list of entity IDs"""
    checker = HomeAssistantAutomationChecker(AsyncMock())

    automation = {
        'trigger': {
            'platform': 'state',
            'entity_id': 'binary_sensor.motion'
        },
        'action': {
            'service': 'light.turn_on',
            'target': {
                'entity_id': ['light.light_1', 'light.light_2', 'light.light_3']
            }
        }
    }

    relationships = checker._parse_automation_relationships(automation)

    # Should create relationship with each light
    assert len(relationships) == 3
    assert ('binary_sensor.motion', 'light.light_1') in relationships
    assert ('binary_sensor.motion', 'light.light_2') in relationships


# ============================================================================
# Connection Checking Tests
# ============================================================================

@pytest.mark.asyncio
async def test_is_connected_true(mock_ha_client):
    """Test detecting existing automation connection"""
    checker = HomeAssistantAutomationChecker(mock_ha_client)

    # This pair has automation (from mock data)
    is_connected = await checker.is_connected(
        'binary_sensor.bedroom_motion',
        'light.bedroom_ceiling'
    )

    assert is_connected is True


@pytest.mark.asyncio
async def test_is_connected_false(mock_ha_client):
    """Test detecting no connection"""
    checker = HomeAssistantAutomationChecker(mock_ha_client)

    # This pair has NO automation
    is_connected = await checker.is_connected(
        'binary_sensor.kitchen_motion',
        'light.kitchen_ceiling'
    )

    assert is_connected is False


@pytest.mark.asyncio
async def test_is_connected_bidirectional(mock_ha_client):
    """Test that connection check works in both directions"""
    checker = HomeAssistantAutomationChecker(mock_ha_client)

    # Check both directions
    forward = await checker.is_connected(
        'binary_sensor.bedroom_motion',
        'light.bedroom_ceiling'
    )
    reverse = await checker.is_connected(
        'light.bedroom_ceiling',
        'binary_sensor.bedroom_motion'
    )

    # Both should be True (bidirectional check)
    assert forward is True
    assert reverse is True


# ============================================================================
# Error Handling Tests
# ============================================================================

@pytest.mark.asyncio
async def test_ha_api_failure_graceful_handling():
    """Test graceful handling when HA API fails"""
    mock_client = AsyncMock()
    mock_client.get_automations = AsyncMock(side_effect=Exception("HA API unavailable"))

    checker = HomeAssistantAutomationChecker(mock_client)

    # Should return empty list, not crash
    automations = await checker.get_existing_automations()
    assert automations == []


@pytest.mark.asyncio
async def test_malformed_automation_handling():
    """Test handling of malformed automation config"""
    checker = HomeAssistantAutomationChecker(AsyncMock())

    # Malformed automation (missing trigger/action)
    automation = {
        'id': 'broken_automation'
        # No trigger or action
    }

    # Should return empty list, not crash
    relationships = checker._parse_automation_relationships(automation)
    assert relationships == []


# ============================================================================
# Cache Tests
# ============================================================================

@pytest.mark.asyncio
async def test_cache_clear(mock_ha_client):
    """Test cache clearing"""
    checker = HomeAssistantAutomationChecker(mock_ha_client)

    # Populate cache
    await checker.get_existing_automations()
    await checker.get_connected_entity_pairs()

    assert checker._automation_cache is not None
    assert checker._relationship_cache is not None

    # Clear cache
    checker.clear_cache()

    assert checker._automation_cache is None
    assert checker._relationship_cache is None


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_connected_entity_pairs(mock_ha_client):
    """Test extracting all connected pairs from automations"""
    checker = HomeAssistantAutomationChecker(mock_ha_client)

    pairs = await checker.get_connected_entity_pairs()

    # Should have 2 pairs from mock automations
    assert len(pairs) >= 2
    assert ('binary_sensor.bedroom_motion', 'light.bedroom_ceiling') in pairs
    assert ('binary_sensor.front_door', 'lock.front_door') in pairs


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

