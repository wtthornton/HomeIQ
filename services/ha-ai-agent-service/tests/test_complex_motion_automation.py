"""
Tests for Complex Motion-Based Automation Validation

Tests 90-minute occupancy detection, group entity handling, and complex automation structures.
"""

import pytest
import yaml
from unittest.mock import AsyncMock, MagicMock

from src.tools.ha_tools import HAToolHandler
from src.clients.ha_client import HomeAssistantClient
from src.clients.data_api_client import DataAPIClient
from src.clients.yaml_validation_client import YAMLValidationClient


@pytest.fixture
def mock_ha_client():
    """Mock Home Assistant client"""
    client = MagicMock(spec=HomeAssistantClient)
    client.get_states = AsyncMock(return_value=[])
    client._get_session = AsyncMock()
    return client


@pytest.fixture
def mock_data_api_client():
    """Mock Data API client"""
    client = MagicMock(spec=DataAPIClient)
    client.fetch_entities = AsyncMock(return_value=[
        {
            "entity_id": "binary_sensor.office_motion_1",
            "friendly_name": "Office Motion Sensor 1",
            "domain": "binary_sensor",
            "area_id": "office"
        },
        {
            "entity_id": "binary_sensor.office_motion_2",
            "friendly_name": "Office Motion Sensor 2",
            "domain": "binary_sensor",
            "area_id": "office"
        },
        {
            "entity_id": "light.office_desk",
            "friendly_name": "Office Desk Light",
            "domain": "light",
            "area_id": "office"
        }
    ])
    return client


@pytest.fixture
def mock_yaml_validation_client():
    """Mock YAML Validation Service client"""
    client = MagicMock(spec=YAMLValidationClient)
    client.validate_yaml = AsyncMock(return_value={
        "valid": True,
        "errors": [],
        "warnings": [],
        "score": 100.0
    })
    return client


@pytest.fixture
def tool_handler(mock_ha_client, mock_data_api_client, mock_yaml_validation_client):
    """Create tool handler with mocked clients (with YAML validation service)"""
    return HAToolHandler(
        mock_ha_client,
        mock_data_api_client,
        yaml_validation_client=mock_yaml_validation_client
    )


@pytest.fixture
def tool_handler_no_yaml_service(mock_ha_client, mock_data_api_client):
    """Create tool handler without YAML validation service (tests basic validation fallback)"""
    return HAToolHandler(
        mock_ha_client,
        mock_data_api_client,
        yaml_validation_client=None
    )


@pytest.mark.asyncio
async def test_validate_90_minute_occupancy_with_condition_state(tool_handler):
    """Test validation of 90-minute occupancy using condition: state with for: option"""
    automation_yaml = """
alias: "Office Motion Focus & Break Lighting"
description: "Office motion-based lighting with 90-minute occupancy check"
initial_state: true
mode: restart
trigger:
  - platform: state
    entity_id: binary_sensor.office_motion_1
    to: "on"
  - platform: state
    entity_id: binary_sensor.office_motion_2
    to: "on"
condition:
  - condition: or
    conditions:
      - condition: state
        entity_id: binary_sensor.office_motion_1
        state: "on"
        for: "01:30:00"
      - condition: state
        entity_id: binary_sensor.office_motion_2
        state: "on"
        for: "01:30:00"
action:
  - service: light.turn_on
    target:
      area_id: office
    data:
      brightness: 255
"""
    result = await tool_handler._validate_yaml(automation_yaml)
    
    assert result["valid"] is True
    # Should not have warnings about group entities or templates
    assert not any("group" in str(w).lower() and "last_changed" in str(w).lower() for w in result.get("warnings", []))


@pytest.mark.asyncio
async def test_validate_group_entity_warning(tool_handler_no_yaml_service):
    """Test that group entities trigger appropriate warnings"""
    automation_yaml = """
alias: "Office Motion Automation"
description: "Uses group entity"
trigger:
  - platform: state
    entity_id: group.office_motion_sensors
    to: "on"
action:
  - service: light.turn_on
    target:
      entity_id: light.office_desk
"""
    result = await tool_handler_no_yaml_service._validate_yaml(automation_yaml)
    
    # Should have warning about group entities
    warnings = result.get("warnings", [])
    assert any("group" in str(w).lower() for w in warnings)
    assert any("last_changed" in str(w).lower() or "condition: state" in str(w).lower() for w in warnings)


@pytest.mark.asyncio
async def test_validate_template_with_group_last_changed_error(tool_handler):
    """Test that templates accessing group.last_changed are detected by YAML validation service"""
    # Note: Template validation happens in YAML validation service, not basic validation
    # This test uses tool_handler with yaml_validation_client to test the full validation path
    automation_yaml = """
alias: "Office Motion Automation"
description: "Uses template with group.last_changed"
trigger:
  - platform: state
    entity_id: binary_sensor.office_motion_1
    to: "on"
condition:
  - condition: template
    value_template: >
      {{ (now() - states.group.office_motion_sensors.last_changed).total_seconds() > 5400 }}
action:
  - service: light.turn_on
    target:
      entity_id: light.office_desk
"""
    # Mock the YAML validation service to return warnings about group.last_changed
    tool_handler.yaml_validation_client.validate_yaml = AsyncMock(return_value={
        "valid": True,
        "errors": [],
        "warnings": [
            "Template accesses group.last_changed: 'group.office_motion_sensors.last_changed'. "
            "Groups don't have 'last_changed' attribute. Use individual entities with condition: state and for: option instead."
        ],
        "score": 85.0
    })
    
    result = await tool_handler._validate_yaml(automation_yaml)
    
    # Should have warnings about group.last_changed from YAML validation service
    warnings = result.get("warnings", [])
    assert any("group" in str(w).lower() and "last_changed" in str(w).lower() for w in warnings)


@pytest.mark.asyncio
async def test_validate_2025_10_format_initial_state(tool_handler_no_yaml_service):
    """Test that missing initial_state triggers warning"""
    automation_yaml = """
alias: "Test Automation"
trigger:
  - platform: time
    at: "07:00:00"
action:
  - service: light.turn_on
    target:
      entity_id: light.office_desk
"""
    result = await tool_handler_no_yaml_service._validate_yaml(automation_yaml)
    
    # Should have warning about missing initial_state
    warnings = result.get("warnings", [])
    assert any("initial_state" in str(w).lower() and "2025.10" in str(w).lower() for w in warnings)


@pytest.mark.asyncio
async def test_validate_complex_motion_automation_with_multiple_triggers(tool_handler):
    """Test validation of complex automation with multiple triggers and conditions"""
    automation_yaml = """
alias: "Office Motion Focus & Break Lighting"
description: "Complex motion-based lighting automation"
initial_state: true
mode: restart
trigger:
  - platform: state
    entity_id: binary_sensor.office_motion_1
    to: "on"
  - platform: state
    entity_id: binary_sensor.office_motion_2
    to: "on"
condition:
  - condition: or
    conditions:
      - condition: state
        entity_id: binary_sensor.office_motion_1
        state: "on"
        for: "01:30:00"
      - condition: state
        entity_id: binary_sensor.office_motion_2
        state: "on"
        for: "01:30:00"
action:
  - service: light.turn_on
    target:
      area_id: office
    data:
      brightness: 255
      color_temp: 370
  - delay: "00:05:00"
  - service: light.turn_on
    target:
      area_id: office
    data:
      effect: "colorloop"
"""
    result = await tool_handler._validate_yaml(automation_yaml)
    
    assert result["valid"] is True
    # Verify entities are extracted correctly
    entities = tool_handler._extract_entities_from_yaml(yaml.safe_load(automation_yaml))
    assert "binary_sensor.office_motion_1" in entities
    assert "binary_sensor.office_motion_2" in entities


def test_is_group_entity(tool_handler):
    """Test group entity detection"""
    assert tool_handler._is_group_entity("group.office_motion_sensors") is True
    assert tool_handler._is_group_entity("binary_sensor.office_motion_1") is False
    assert tool_handler._is_group_entity("light.office_desk") is False


@pytest.mark.asyncio
async def test_validate_error_messages_context(tool_handler_no_yaml_service):
    """Test that error messages include helpful context"""
    automation_yaml = """
alias: "Test Automation"
triggers:
  - platform: time
    at: "07:00:00"
actions:
  - service: light.turn_on
"""
    result = await tool_handler_no_yaml_service._validate_yaml(automation_yaml)
    
    errors = result.get("errors", [])
    # Should mention 2025.10+ format in error messages
    assert any("2025.10" in str(e) or "singular" in str(e).lower() for e in errors)

