"""
End-to-end integration tests for JSON workflow
"""

import pytest

from shared.homeiq_automation.schema import (
    HomeIQAutomation,
    HomeIQMetadata,
    HomeIQTrigger,
    HomeIQAction,
    DeviceContext,
)
from shared.homeiq_automation.converter import HomeIQToAutomationSpecConverter
from shared.yaml_validation_service.version_aware_renderer import VersionAwareRenderer


def test_json_workflow_end_to_end():
    """Test complete workflow: JSON → AutomationSpec → YAML."""
    # Step 1: Create HomeIQ JSON
    homeiq_automation = HomeIQAutomation(
        alias="End-to-End Test",
        homeiq_metadata=HomeIQMetadata(
            use_case="comfort",
            complexity="medium"
        ),
        device_context=DeviceContext(
            entity_ids=["light.test", "sensor.motion"]
        ),
        triggers=[
            HomeIQTrigger(platform="state", entity_id="sensor.motion", to="on")
        ],
        actions=[
            HomeIQAction(service="light.turn_on", target={"entity_id": "light.test"})
        ]
    )
    
    # Step 2: Convert to AutomationSpec
    converter = HomeIQToAutomationSpecConverter()
    spec = converter.convert(homeiq_automation)
    
    assert spec.alias == "End-to-End Test"
    assert len(spec.trigger) == 1
    assert len(spec.action) == 1
    
    # Step 3: Render to YAML
    renderer = VersionAwareRenderer(ha_version="2025.10.3")
    yaml_content = renderer.render(spec)
    
    assert "alias:" in yaml_content
    assert "End-to-End Test" in yaml_content
    assert "trigger:" in yaml_content
    assert "action:" in yaml_content
    
    # Verify metadata preserved
    assert "homeiq_metadata" in spec.extra

