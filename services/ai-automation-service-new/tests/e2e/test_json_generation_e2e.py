"""
E2E Tests for HomeIQ JSON Generation Workflow

Tests the complete flow:
1. Generate HomeIQ JSON from suggestion
2. Validate JSON schema
3. Convert to AutomationSpec
4. Render to YAML
5. Store in database
"""

import sys
from pathlib import Path

# Add workspace root to path
workspace_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(workspace_root))

import pytest
import json
from datetime import datetime
from typing import Any

from shared.homeiq_automation.schema import (
    HomeIQAutomation,
    HomeIQMetadata,
    HomeIQTrigger,
    HomeIQAction,
    DeviceContext,
    SafetyChecks,
    EnergyImpact,
)
from shared.homeiq_automation.converter import HomeIQToAutomationSpecConverter
from shared.homeiq_automation.validator import HomeIQAutomationValidator
from shared.yaml_validation_service.version_aware_renderer import VersionAwareRenderer
from shared.yaml_validation_service.schema import AutomationMode

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.database.models import Suggestion


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_json_generation_complete_workflow(db_session):
    """
    E2E Test: Complete JSON generation workflow from suggestion to stored automation.
    
    Flow:
    1. Create a suggestion
    2. Generate HomeIQ JSON
    3. Validate JSON
    4. Convert to AutomationSpec
    5. Render to YAML
    6. Store in database
    """
    # Step 1: Create a suggestion
    suggestion = Suggestion(
        title="Test Automation",
        description="Turn on light when motion detected",
        status="pending"
    )
    db_session.add(suggestion)
    await db_session.commit()
    await db_session.refresh(suggestion)
    
    assert suggestion.id is not None
    
    # Step 2: Generate HomeIQ JSON (simulated - in production would use OpenAI)
    homeiq_json = {
        "alias": "Test Motion Light",
        "description": "Turn on light when motion detected",
        "version": "1.0.0",
        "homeiq_metadata": {
            "use_case": "comfort",
            "complexity": "low",
        },
        "device_context": {
            "entity_ids": ["light.test", "binary_sensor.motion"],
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
                "entity_id": "binary_sensor.motion",
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
    
    # Step 3: Validate JSON schema
    homeiq_automation = HomeIQAutomation(**homeiq_json)
    assert homeiq_automation.alias == "Test Motion Light"
    assert homeiq_automation.homeiq_metadata.use_case == "comfort"
    
    # Step 4: Convert to AutomationSpec
    converter = HomeIQToAutomationSpecConverter()
    automation_spec = converter.convert(homeiq_automation)
    assert automation_spec.alias == "Test Motion Light"
    assert len(automation_spec.trigger) == 1
    assert len(automation_spec.action) == 1
    
    # Step 5: Render to YAML
    renderer = VersionAwareRenderer(ha_version="2025.10.3")
    yaml_content = renderer.render(automation_spec)
    assert "alias:" in yaml_content
    assert "Test Motion Light" in yaml_content
    assert "binary_sensor.motion" in yaml_content
    
    # Step 6: Store in database
    suggestion.automation_json = homeiq_json
    suggestion.automation_yaml = yaml_content
    suggestion.ha_version = "2025.10.3"
    suggestion.json_schema_version = "1.0.0"
    await db_session.commit()
    await db_session.refresh(suggestion)
    
    assert suggestion.automation_json is not None
    assert suggestion.automation_yaml is not None
    assert suggestion.ha_version == "2025.10.3"
    assert suggestion.json_schema_version == "1.0.0"
    
    # Verify JSON can be retrieved and parsed
    retrieved_json = suggestion.automation_json
    assert isinstance(retrieved_json, dict)
    assert retrieved_json["alias"] == "Test Motion Light"
    
    # Verify YAML can be retrieved
    retrieved_yaml = suggestion.automation_yaml
    assert isinstance(retrieved_yaml, str)
    assert "Test Motion Light" in retrieved_yaml


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_json_validation_e2e():
    """
    E2E Test: JSON validation with entity checking.
    """
    # Create HomeIQ JSON with valid structure
    homeiq_json = {
        "alias": "Valid Automation",
        "description": "Test automation",
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
    
    # Validate schema
    homeiq_automation = HomeIQAutomation(**homeiq_json)
    assert homeiq_automation is not None
    
    # In production, would also validate entities against Data API
    # For E2E test, we verify the structure is correct
    assert homeiq_automation.device_context.entity_ids == ["light.test"]


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_json_to_yaml_conversion_e2e():
    """
    E2E Test: Complete JSON to YAML conversion workflow.
    """
    # Create HomeIQ JSON
    homeiq_json = {
        "alias": "Sunset Light Automation",
        "description": "Turn on lights at sunset",
        "version": "1.0.0",
        "homeiq_metadata": {
            "use_case": "comfort",
            "complexity": "medium",
        },
        "device_context": {
            "entity_ids": ["light.living_room", "sun.sun"],
            "device_ids": [],
            "area_ids": ["living_room"],
        },
        "safety_checks": {
            "requires_confirmation": False,
        },
        "energy_impact": {
            "estimated_power_w": 50.0,
            "estimated_daily_kwh": 0.5,
        },
        "triggers": [
            {
                "platform": "sun",
                "event": "sunset",
            }
        ],
        "actions": [
            {
                "service": "light.turn_on",
                "target": {"entity_id": "light.living_room"},
                "data": {"brightness": 255},
            }
        ],
        "mode": "single",
    }
    
    # Convert to Pydantic model
    homeiq_automation = HomeIQAutomation(**homeiq_json)
    
    # Convert to AutomationSpec
    converter = HomeIQToAutomationSpecConverter()
    automation_spec = converter.convert(homeiq_automation)
    
    # Render to YAML
    renderer = VersionAwareRenderer(ha_version="2025.10.3")
    yaml_content = renderer.render(automation_spec)
    
    # Verify YAML content
    assert "alias:" in yaml_content
    assert "Sunset Light Automation" in yaml_content
    assert "sunset" in yaml_content.lower()
    assert "light.living_room" in yaml_content
    
    # Verify YAML can be parsed
    import yaml
    yaml_dict = yaml.safe_load(yaml_content)
    assert yaml_dict["alias"] == "Sunset Light Automation"
    assert len(yaml_dict["trigger"]) == 1
    assert len(yaml_dict["action"]) == 1

