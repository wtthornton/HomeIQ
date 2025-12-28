"""
Tests for HomeIQ JSON Automation Schema
"""

import pytest
from datetime import datetime

from shared.homeiq_automation.schema import (
    HomeIQAutomation,
    HomeIQMetadata,
    HomeIQTrigger,
    HomeIQAction,
    DeviceContext,
)


def test_homeiq_automation_creation():
    """Test creating a basic HomeIQ automation."""
    automation = HomeIQAutomation(
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
    
    assert automation.alias == "Test Automation"
    assert automation.version == "1.0.0"
    assert len(automation.triggers) == 1
    assert len(automation.actions) == 1


def test_homeiq_automation_validation():
    """Test HomeIQ automation validation."""
    # Valid automation
    automation = HomeIQAutomation(
        alias="Valid Automation",
        homeiq_metadata=HomeIQMetadata(
            use_case="energy",
            complexity="medium"
        ),
        device_context=DeviceContext(
            entity_ids=["sensor.temperature"]
        ),
        triggers=[
            HomeIQTrigger(platform="time", at="08:00:00")
        ],
        actions=[
            HomeIQAction(service="climate.set_temperature", data={"temperature": 72})
        ]
    )
    
    assert automation.homeiq_metadata.use_case == "energy"
    
    # Invalid: missing required fields
    with pytest.raises(Exception):
        HomeIQAutomation(
            alias="Invalid",
            homeiq_metadata=HomeIQMetadata(use_case="comfort", complexity="low"),
            device_context=DeviceContext(entity_ids=[]),
            triggers=[],
            actions=[]
        )

