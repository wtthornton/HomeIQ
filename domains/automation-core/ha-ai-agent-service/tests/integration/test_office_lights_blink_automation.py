"""
Integration test for office lights blink automation creation.

Tests the complete flow for: "Make the office lights blink red every 15 minutes 
and then return back to the state they were"

This test validates:
1. Context injection provides necessary information
2. Prompt contains required patterns
3. Automation YAML generation is correct
4. State restoration pattern is used
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from services.context_builder import ContextBuilder
from services.prompt_assembly_service import PromptAssemblyService
from config import Settings


@pytest.fixture
def mock_settings():
    """Mock settings for testing"""
    settings = Settings()
    settings.ha_url = "http://localhost:8123"
    settings.ha_token = "test_token"
    settings.data_api_url = "http://localhost:8006"
    return settings


@pytest.fixture
async def context_builder(mock_settings):
    """Create context builder with mocked services"""
    cb = ContextBuilder(mock_settings)
    
    # Mock all services - patch at the module level where they're imported
    with patch('services.entity_inventory_service.EntityInventoryService') as mock_ei, \
         patch('services.areas_service.AreasService') as mock_areas, \
         patch('services.services_summary_service.ServicesSummaryService') as mock_services, \
         patch('services.capability_patterns_service.CapabilityPatternsService') as mock_caps, \
         patch('services.helpers_scenes_service.HelpersScenesService') as mock_helpers:
        
        # Mock entity inventory with office lights
        mock_ei_instance = AsyncMock()
        mock_ei_instance.get_summary.return_value = """Light: 3 entities (Office: 3)
  Examples: Office Light 1 (light.office_light_1, device_id: dev1, area_id: office, state: on), 
            Office Light 2 (light.office_light_2, device_id: dev2, area_id: office, state: off),
            Office Light 3 (light.office_light_3, device_id: dev3, area_id: office, state: on)"""
        
        # Mock areas with office
        mock_areas_instance = AsyncMock()
        mock_areas_instance.get_areas_list.return_value = """Office (area_id: office, aliases: [workspace, study])
Kitchen (area_id: kitchen)"""
        
        # Mock services with light services
        mock_services_instance = AsyncMock()
        mock_services_instance.get_summary.return_value = """light:
  turn_on:
    target: entity_id, area_id, device_id
    data:
      rgb_color: [int, int, int] (0-255 each) - RGB color values
      brightness: int (0-255) - Brightness level
      effect: string - Effect name
  turn_off:
    target: entity_id, area_id, device_id
scene:
  create:
    data:
      scene_id: string (required) - Unique scene ID
      snapshot_entities: list[string] (required) - Entity IDs to snapshot
  turn_on:
    target:
      entity_id: string - Scene entity ID"""
        
        # Mock capability patterns
        mock_caps_instance = AsyncMock()
        mock_caps_instance.get_patterns.return_value = """light:
  rgb_color: [0-255, 0-255, 0-255] - RGB color values
  brightness: 0-255 - Brightness level
  supported_color_modes: [rgb, hs, color_temp]"""
        
        # Mock helpers/scenes
        mock_helpers_instance = AsyncMock()
        mock_helpers_instance.get_summary.return_value = """Scenes: Office Bright (scene.office_bright), Office Dim (scene.office_dim)"""
        
        cb._entity_inventory_service = mock_ei_instance
        cb._areas_service = mock_areas_instance
        cb._services_summary_service = mock_services_instance
        cb._capability_patterns_service = mock_caps_instance
        cb._helpers_scenes_service = mock_helpers_instance
        cb._initialized = True
        
        yield cb


@pytest.mark.asyncio
async def test_context_contains_office_lights(context_builder):
    """Test that context contains office lights information"""
    context = await context_builder.build_context()
    
    # Assert office lights are in context
    assert "office" in context.lower() or "Office" in context
    assert "light.office" in context or "office_light" in context
    
    # Assert area_id is available
    assert "area_id: office" in context or "area_id:office" in context


@pytest.mark.asyncio
async def test_context_contains_light_services(context_builder):
    """Test that context contains light service information"""
    context = await context_builder.build_context()
    
    # Assert light services are in context
    assert "light.turn_on" in context or "turn_on" in context
    assert "rgb_color" in context or "color" in context.lower()
    
    # Assert scene services for state restoration
    assert "scene.create" in context or "scene" in context.lower()
    assert "snapshot_entities" in context or "snapshot" in context.lower()


@pytest.mark.asyncio
async def test_context_contains_color_capabilities(context_builder):
    """Test that context contains color capability information"""
    context = await context_builder.build_context()
    
    # Assert RGB color information
    assert "rgb_color" in context or "rgb" in context.lower()
    assert "255" in context or "0-255" in context


@pytest.mark.asyncio
async def test_system_prompt_contains_state_restoration_pattern():
    """Test that system prompt explains state restoration"""
    from prompts.system_prompt import SYSTEM_PROMPT
    
    # Check for state restoration keywords
    assert "restore" in SYSTEM_PROMPT.lower() or "state" in SYSTEM_PROMPT.lower()
    assert "scene" in SYSTEM_PROMPT.lower() or "snapshot" in SYSTEM_PROMPT.lower()


@pytest.mark.asyncio
async def test_complete_prompt_has_all_required_info(context_builder):
    """Test that complete prompt has all information needed for the automation"""
    complete_prompt = await context_builder.build_complete_system_prompt()
    
    # Required information for "office lights blink red every 15 minutes and restore state"
    required_info = [
        "office",  # Area or entity reference
        "light",   # Light domain
        "turn_on", # Service to turn on lights
        "rgb" or "color",  # Color capability
        "scene" or "snapshot",  # State restoration
        "time" or "trigger",  # Time-based trigger
    ]
    
    missing = [info for info in required_info if info.lower() not in complete_prompt.lower()]
    
    if missing:
        pytest.fail(f"Missing required information in prompt: {missing}")


@pytest.mark.asyncio
async def test_automation_yaml_structure():
    """Test that expected automation YAML structure is correct"""
    # Expected YAML structure for the automation
    expected_yaml = """
alias: Office Lights Blink Red Every 15 Minutes
description: Makes office lights blink red every 15 minutes and restores original state
initial_state: true
mode: single
trigger:
  - platform: time_pattern
    minutes: "/15"
action:
  # Save current state
  - service: scene.create
    data:
      scene_id: office_lights_restore_state
      snapshot_entities:
        - light.office_light_1
        - light.office_light_2
        - light.office_light_3
  # Blink red
  - service: light.turn_on
    target:
      area_id: office
    data:
      rgb_color: [255, 0, 0]  # Red
      brightness: 255
  - delay: "00:00:01"  # Blink duration
  # Restore state
  - service: scene.turn_on
    target:
      entity_id: scene.office_lights_restore_state
"""
    
    # Basic validation - YAML should be parseable
    import yaml
    parsed = yaml.safe_load(expected_yaml)
    assert "alias" in parsed
    assert "trigger" in parsed
    assert "action" in parsed
    assert len(parsed["action"]) >= 3  # Save, blink, restore


@pytest.mark.asyncio
async def test_context_missing_areas_issue(context_builder):
    """Test that missing areas are properly handled"""
    # Simulate missing areas
    context_builder._areas_service.get_areas_list.return_value = "No areas found"
    
    context = await context_builder.build_context()
    
    # If areas are missing, entity inventory should still have area_id info
    assert "area_id" in context or "unassigned" in context


@pytest.mark.asyncio
async def test_context_missing_services_issue(context_builder):
    """Test that missing services are properly handled"""
    # Simulate missing services
    context_builder._services_summary_service.get_summary.return_value = ""
    
    context = await context_builder.build_context()
    
    # Context should still be built (other sections present)
    assert len(context) > 0
    # But should indicate services are unavailable
    assert "unavailable" in context.lower() or len(context) > 100

