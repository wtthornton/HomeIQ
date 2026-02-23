"""
Tests for AutomationSpec schema (Epic 51, Story 51.1)
"""

import pytest
from yaml_validation_service.schema import (
    ActionSpec,
    AutomationMode,
    AutomationSpec,
    ConditionSpec,
    MaxExceeded,
    TriggerSpec,
)


class TestAutomationSpec:
    """Test AutomationSpec schema validation and rendering."""
    
    def test_basic_automation_spec(self):
        """Test creating a basic automation spec."""
        spec = AutomationSpec(
            alias="Test Automation",
            description="Test description",
            trigger=[
                TriggerSpec(platform="time", at="07:00:00")
            ],
            action=[
                ActionSpec(service="light.turn_on", target={"area_id": "office"})
            ]
        )
        
        assert spec.alias == "Test Automation"
        assert len(spec.trigger) == 1
        assert len(spec.action) == 1
    
    def test_automation_mode_enum(self):
        """Test automation mode enum values."""
        assert AutomationMode.SINGLE == "single"
        assert AutomationMode.RESTART == "restart"
        assert AutomationMode.QUEUED == "queued"
        assert AutomationMode.PARALLEL == "parallel"
    
    def test_max_exceeded_enum(self):
        """Test max_exceeded enum values."""
        assert MaxExceeded.SILENT == "silent"
        assert MaxExceeded.WARNING == "warning"
        assert MaxExceeded.ERROR == "error"
    
    def test_trigger_spec_validation(self):
        """Test trigger spec validation."""
        # Valid trigger
        trigger = TriggerSpec(platform="state", entity_id="light.living_room")
        assert trigger.platform == "state"
        assert trigger.entity_id == "light.living_room"
    
    def test_action_spec_validation(self):
        """Test action spec validation."""
        # Valid action
        action = ActionSpec(service="light.turn_on", target={"entity_id": "light.living_room"})
        assert action.service == "light.turn_on"
        assert action.target == {"entity_id": "light.living_room"}
    
    def test_condition_spec(self):
        """Test condition spec."""
        condition = ConditionSpec(
            condition="state",
            entity_id="light.living_room",
            state="on"
        )
        assert condition.condition == "state"
        assert condition.entity_id == "light.living_room"
        assert condition.state == "on"
