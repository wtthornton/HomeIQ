"""
Tests for JSON to YAML conversion
"""

import pytest

from shared.homeiq_automation.converter import HomeIQToAutomationSpecConverter
from shared.homeiq_automation.schema import (
    HomeIQAutomation,
    HomeIQMetadata,
    HomeIQTrigger,
    HomeIQAction,
    DeviceContext,
)


def test_json_to_automation_spec_conversion():
    """Test converting HomeIQ JSON to AutomationSpec."""
    homeiq_automation = HomeIQAutomation(
        alias="Test Automation",
        homeiq_metadata=HomeIQMetadata(
            use_case="comfort",
            complexity="low"
        ),
        device_context=DeviceContext(
            entity_ids=["light.test"]
        ),
        triggers=[
            HomeIQTrigger(platform="state", entity_id="light.test", to="on")
        ],
        actions=[
            HomeIQAction(service="light.turn_on", target={"entity_id": "light.test"})
        ]
    )
    
    converter = HomeIQToAutomationSpecConverter()
    spec = converter.convert(homeiq_automation)
    
    assert spec.alias == "Test Automation"
    assert len(spec.trigger) == 1
    assert len(spec.action) == 1
    assert "homeiq_metadata" in spec.extra


def test_json_to_yaml_preserves_metadata():
    """Test that HomeIQ metadata is preserved in AutomationSpec.extra."""
    homeiq_automation = HomeIQAutomation(
        alias="Metadata Test",
        homeiq_metadata=HomeIQMetadata(
            use_case="security",
            complexity="high",
            confidence_score=0.95
        ),
        device_context=DeviceContext(
            entity_ids=["lock.front_door"]
        ),
        triggers=[
            HomeIQTrigger(platform="state", entity_id="lock.front_door", to="unlocked")
        ],
        actions=[
            HomeIQAction(service="lock.lock", target={"entity_id": "lock.front_door"})
        ]
    )
    
    converter = HomeIQToAutomationSpecConverter()
    spec = converter.convert(homeiq_automation)
    
    assert "homeiq_metadata" in spec.extra
    assert spec.extra["homeiq_metadata"]["use_case"] == "security"
    assert spec.extra["homeiq_metadata"]["confidence_score"] == 0.95

