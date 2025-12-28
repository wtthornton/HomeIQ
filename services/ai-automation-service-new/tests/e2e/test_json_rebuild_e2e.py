"""
E2E Tests for HomeIQ JSON Rebuild Functionality

Tests:
1. Rebuild JSON from YAML
2. Rebuild JSON from description
3. Verify rebuilt JSON is valid
"""

import sys
from pathlib import Path

# Add workspace root to path
workspace_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(workspace_root))

import pytest
import json
import yaml

from shared.homeiq_automation.schema import HomeIQAutomation
from shared.homeiq_automation.converter import HomeIQToAutomationSpecConverter
from shared.yaml_validation_service.version_aware_renderer import VersionAwareRenderer

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.database.models import Suggestion


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_json_rebuild_from_yaml_e2e(db_session):
    """
    E2E Test: Rebuild JSON from existing YAML.
    """
    # Create a suggestion with YAML but no JSON
    yaml_content = """
alias: Rebuild Test Automation
description: Test rebuilding JSON from YAML
initial_state: true
mode: single
trigger:
  - platform: state
    entity_id: binary_sensor.motion
    to: 'on'
action:
  - service: light.turn_on
    target:
      entity_id: light.test
"""
    
    suggestion = Suggestion(
        title="Rebuild Test",
        description="Test JSON rebuild from YAML",
        automation_yaml=yaml_content,
        status="pending"
    )
    db_session.add(suggestion)
    await db_session.commit()
    await db_session.refresh(suggestion)
    
    # Parse YAML to extract information
    yaml_dict = yaml.safe_load(yaml_content)
    
    # Rebuild JSON from YAML structure
    rebuilt_json = {
        "alias": yaml_dict["alias"],
        "description": yaml_dict.get("description", ""),
        "version": "1.0.0",
        "homeiq_metadata": {
            "use_case": "comfort",  # Inferred from context
            "complexity": "low",
        },
        "device_context": {
            "entity_ids": ["binary_sensor.motion", "light.test"],
            "device_ids": [],
            "area_ids": [],
        },
        "safety_checks": {
            "requires_confirmation": False,
        },
        "energy_impact": {
            "estimated_power_w": 10.0,
            "estimated_daily_kwh": 0.1,
        },
        "triggers": [
            {
                "platform": trigger["platform"],
                "entity_id": trigger.get("entity_id"),
                "to": trigger.get("to"),
            }
            for trigger in yaml_dict["trigger"]
        ],
        "actions": [
            {
                "service": action["service"],
                "target": action.get("target", {}),
            }
            for action in yaml_dict["action"]
        ],
        "mode": yaml_dict.get("mode", "single"),
    }
    
    # Validate rebuilt JSON
    homeiq_automation = HomeIQAutomation(**rebuilt_json)
    assert homeiq_automation.alias == "Rebuild Test Automation"
    assert len(homeiq_automation.triggers) == 1
    assert len(homeiq_automation.actions) == 1
    
    # Store rebuilt JSON
    suggestion.automation_json = rebuilt_json
    await db_session.commit()
    await db_session.refresh(suggestion)
    
    # Verify JSON was stored
    assert suggestion.automation_json is not None
    assert suggestion.automation_json["alias"] == "Rebuild Test Automation"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_json_rebuild_from_description_e2e():
    """
    E2E Test: Rebuild JSON from natural language description.
    
    In production, this would use JSONRebuilder with OpenAI.
    For E2E test, we simulate the process.
    """
    description = "Turn on the living room light when motion is detected in the evening"
    
    # Simulate LLM generating JSON from description
    rebuilt_json = {
        "alias": description[:50],
        "description": description,
        "version": "1.0.0",
        "homeiq_metadata": {
            "use_case": "comfort",
            "complexity": "medium",
        },
        "device_context": {
            "entity_ids": ["light.living_room", "binary_sensor.motion"],
            "device_ids": [],
            "area_ids": ["living_room"],
        },
        "safety_checks": {
            "requires_confirmation": False,
        },
        "energy_impact": {
            "estimated_power_w": 10.0,
            "estimated_daily_kwh": 0.1,
        },
        "triggers": [
            {
                "platform": "state",
                "entity_id": "binary_sensor.motion",
                "to": "on",
            },
            {
                "platform": "sun",
                "event": "sunset",
            }
        ],
        "actions": [
            {
                "service": "light.turn_on",
                "target": {"entity_id": "light.living_room"},
            }
        ],
        "mode": "single",
    }
    
    # Validate rebuilt JSON
    homeiq_automation = HomeIQAutomation(**rebuilt_json)
    assert homeiq_automation.description == description
    assert len(homeiq_automation.triggers) == 2
    assert len(homeiq_automation.actions) == 1
    
    # Verify it can be converted to YAML
    converter = HomeIQToAutomationSpecConverter()
    automation_spec = converter.convert(homeiq_automation)
    
    renderer = VersionAwareRenderer(ha_version="2025.10.3")
    yaml_content = renderer.render(automation_spec)
    
    assert "alias:" in yaml_content
    assert "binary_sensor.motion" in yaml_content
    assert "light.living_room" in yaml_content


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_json_rebuild_roundtrip_e2e():
    """
    E2E Test: JSON → YAML → JSON roundtrip.
    
    Verifies that JSON can be converted to YAML and back to JSON
    without losing critical information.
    """
    # Original JSON
    original_json = {
        "alias": "Roundtrip Test",
        "description": "Test roundtrip conversion",
        "version": "1.0.0",
        "homeiq_metadata": {
            "use_case": "comfort",
            "complexity": "low",
        },
        "device_context": {
            "entity_ids": ["light.test"],
            "device_ids": [],
            "area_ids": [],
        },
        "safety_checks": {
            "requires_confirmation": False,
        },
        "energy_impact": {
            "estimated_power_w": 10.0,
            "estimated_daily_kwh": 0.1,
        },
        "triggers": [
            {
                "platform": "state",
                "entity_id": "light.test",
                "to": "on",
            }
        ],
        "actions": [
            {
                "service": "light.turn_on",
                "target": {"entity_id": "light.test"},
            }
        ],
        "mode": "single",
    }
    
    # Convert to YAML
    homeiq_automation = HomeIQAutomation(**original_json)
    converter = HomeIQToAutomationSpecConverter()
    automation_spec = converter.convert(homeiq_automation)
    
    renderer = VersionAwareRenderer(ha_version="2025.10.3")
    yaml_content = renderer.render(automation_spec)
    
    # Parse YAML back
    yaml_dict = yaml.safe_load(yaml_content)
    
    # Rebuild JSON from YAML
    rebuilt_json = {
        "alias": yaml_dict["alias"],
        "description": yaml_dict.get("description", ""),
        "version": "1.0.0",
        "homeiq_metadata": {
            "use_case": "comfort",
            "complexity": "low",
        },
        "device_context": {
            "entity_ids": ["light.test"],
            "device_ids": [],
            "area_ids": [],
        },
        "safety_checks": {
            "requires_confirmation": False,
        },
        "energy_impact": {
            "estimated_power_w": 10.0,
            "estimated_daily_kwh": 0.1,
        },
        "triggers": [
            {
                "platform": trigger["platform"],
                "entity_id": trigger.get("entity_id"),
                "to": trigger.get("to"),
            }
            for trigger in yaml_dict["trigger"]
        ],
        "actions": [
            {
                "service": action["service"],
                "target": action.get("target", {}),
            }
            for action in yaml_dict["action"]
        ],
        "mode": yaml_dict.get("mode", "single"),
    }
    
    # Verify critical information preserved
    assert rebuilt_json["alias"] == original_json["alias"]
    assert len(rebuilt_json["triggers"]) == len(original_json["triggers"])
    assert len(rebuilt_json["actions"]) == len(original_json["actions"])
    assert rebuilt_json["triggers"][0]["platform"] == original_json["triggers"][0]["platform"]
    assert rebuilt_json["actions"][0]["service"] == original_json["actions"][0]["service"]

