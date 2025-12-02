"""
Unit tests for AutomationPlan improvements (Improvements #1 and #4)
"""

import pytest
import yaml

from src.contracts.models import (
    AutomationPlan,
    AutomationMode,
    Trigger,
    Action
)


class TestInitialState:
    """Test Improvement #1: initial_state field"""

    def test_initial_state_default_true(self):
        """Test that initial_state defaults to True"""
        plan = AutomationPlan(
            name="Test Automation",
            triggers=[Trigger(platform="time", at="07:00:00")],
            actions=[Action(service="light.turn_on", entity_id="light.kitchen")]
        )
        
        assert plan.initial_state is True

    def test_initial_state_in_yaml_output(self):
        """Test that initial_state appears in YAML output"""
        plan = AutomationPlan(
            name="Test Automation",
            triggers=[Trigger(platform="time", at="07:00:00")],
            actions=[Action(service="light.turn_on", entity_id="light.kitchen")]
        )
        
        yaml_output = plan.to_yaml()
        yaml_data = yaml.safe_load(yaml_output)
        
        assert "initial_state" in yaml_data
        assert yaml_data["initial_state"] is True

    def test_initial_state_can_be_false(self):
        """Test that initial_state can be set to False"""
        plan = AutomationPlan(
            name="Test Automation",
            triggers=[Trigger(platform="time", at="07:00:00")],
            actions=[Action(service="light.turn_on", entity_id="light.kitchen")],
            initial_state=False
        )
        
        assert plan.initial_state is False
        yaml_output = plan.to_yaml()
        yaml_data = yaml.safe_load(yaml_output)
        assert yaml_data["initial_state"] is False


class TestModeSelection:
    """Test Improvement #4: Intelligent mode selection"""

    def test_mode_single_for_time_trigger(self):
        """Test that time-based triggers get single mode"""
        triggers = [Trigger(platform="time", at="07:00:00")]
        actions = [Action(service="light.turn_on", entity_id="light.kitchen")]
        
        mode = AutomationPlan.determine_automation_mode(
            triggers=triggers,
            actions=actions,
            description="Turn on light at 7 AM"
        )
        
        assert mode == AutomationMode.SINGLE

    def test_mode_restart_for_motion_with_delay(self):
        """Test that motion sensors with delays get restart mode"""
        triggers = [Trigger(
            platform="state",
            entity_id="binary_sensor.motion_sensor",
            to="on"
        )]
        actions = [
            Action(
                service="light.turn_on",
                entity_id="light.kitchen",
                delay="00:05:00"
            )
        ]
        
        mode = AutomationPlan.determine_automation_mode(
            triggers=triggers,
            actions=actions,
            description="Motion sensor turns on light"
        )
        
        assert mode == AutomationMode.RESTART

    def test_mode_single_for_motion_without_delay(self):
        """Test that motion sensors without delays get single mode"""
        triggers = [Trigger(
            platform="state",
            entity_id="binary_sensor.motion_sensor",
            to="on"
        )]
        actions = [Action(service="light.turn_on", entity_id="light.kitchen")]
        
        mode = AutomationPlan.determine_automation_mode(
            triggers=triggers,
            actions=actions
        )
        
        assert mode == AutomationMode.SINGLE

    def test_mode_restart_for_multiple_actions_with_delay(self):
        """Test that multiple actions with delays get restart mode"""
        triggers = [Trigger(platform="time", at="07:00:00")]
        actions = [
            Action(service="light.turn_on", entity_id="light.kitchen", delay="00:01:00"),
            Action(service="switch.turn_on", entity_id="switch.fan", delay="00:02:00")
        ]
        
        mode = AutomationPlan.determine_automation_mode(
            triggers=triggers,
            actions=actions
        )
        
        assert mode == AutomationMode.RESTART

    def test_mode_single_default(self):
        """Test that single is default mode"""
        triggers = [Trigger(platform="state", entity_id="sensor.temperature", to="30")]
        actions = [Action(service="fan.turn_on", entity_id="fan.living_room")]
        
        mode = AutomationPlan.determine_automation_mode(
            triggers=triggers,
            actions=actions
        )
        
        assert mode == AutomationMode.SINGLE

    def test_mode_selection_with_description_keywords(self):
        """Test mode selection considers description keywords"""
        triggers = [Trigger(platform="state", entity_id="binary_sensor.motion", to="on")]
        actions = [Action(service="light.turn_on", entity_id="light.office", delay="00:03:00")]
        
        mode_with_motion = AutomationPlan.determine_automation_mode(
            triggers=triggers,
            actions=actions,
            description="Motion sensor activates office light"
        )
        
        assert mode_with_motion == AutomationMode.RESTART
    
    def test_mode_restart_for_presence_sensor_with_delay(self):
        """Test that presence sensors with delays get restart mode"""
        triggers = [Trigger(
            platform="state",
            entity_id="binary_sensor.presence_sensor",
            to="on"
        )]
        actions = [
            Action(
                service="light.turn_on",
                entity_id="light.kitchen",
                delay="00:05:00"
            )
        ]
        
        mode = AutomationPlan.determine_automation_mode(
            triggers=triggers,
            actions=actions,
            description="Presence sensor turns on light"
        )
        
        assert mode == AutomationMode.RESTART
    
    def test_mode_restart_for_door_sensor_with_delay(self):
        """Test that door sensors with delays get restart mode"""
        triggers = [Trigger(
            platform="state",
            entity_id="binary_sensor.front_door",
            to="on"
        )]
        actions = [
            Action(
                service="light.turn_on",
                entity_id="light.entryway",
                delay="00:02:00"
            )
        ]
        
        mode = AutomationPlan.determine_automation_mode(
            triggers=triggers,
            actions=actions,
            description="Door sensor activates entryway light"
        )
        
        assert mode == AutomationMode.RESTART
    
    def test_mode_single_for_event_trigger(self):
        """Test that event triggers get single mode"""
        triggers = [Trigger(platform="event", event_type="button_pressed")]
        actions = [Action(service="light.turn_on", entity_id="light.kitchen")]
        
        mode = AutomationPlan.determine_automation_mode(
            triggers=triggers,
            actions=actions,
            description="Button press turns on light"
        )
        
        assert mode == AutomationMode.SINGLE
    
    def test_mode_single_for_webhook_trigger(self):
        """Test that webhook triggers get single mode"""
        triggers = [Trigger(platform="webhook", topic="automation/webhook")]
        actions = [Action(service="light.turn_on", entity_id="light.kitchen")]
        
        mode = AutomationPlan.determine_automation_mode(
            triggers=triggers,
            actions=actions,
            description="Webhook triggers light"
        )
        
        assert mode == AutomationMode.SINGLE
    
    def test_mode_parallel_for_independent_actions(self):
        """Test that independent actions without delays get parallel mode"""
        triggers = [Trigger(platform="time", at="07:00:00")]
        actions = [
            Action(service="light.turn_on", entity_id="light.kitchen"),
            Action(service="switch.turn_on", entity_id="switch.fan")
        ]
        
        mode = AutomationPlan.determine_automation_mode(
            triggers=triggers,
            actions=actions,
            description="Turn on kitchen light and fan simultaneously"
        )
        
        # Should be parallel for independent actions
        assert mode == AutomationMode.PARALLEL
    
    def test_mode_queued_for_sequential_description(self):
        """Test that sequential descriptions suggest queued mode"""
        triggers = [Trigger(platform="time", at="07:00:00")]
        actions = [
            Action(service="light.turn_on", entity_id="light.kitchen"),
            Action(service="switch.turn_on", entity_id="switch.fan")
        ]
        
        mode = AutomationPlan.determine_automation_mode(
            triggers=triggers,
            actions=actions,
            description="Sequential actions: first light, then fan"
        )
        
        assert mode == AutomationMode.QUEUED
    
    def test_mode_parallel_for_parallel_description(self):
        """Test that parallel descriptions suggest parallel mode"""
        triggers = [Trigger(platform="time", at="07:00:00")]
        actions = [
            Action(service="light.turn_on", entity_id="light.kitchen"),
            Action(service="switch.turn_on", entity_id="switch.fan")
        ]
        
        mode = AutomationPlan.determine_automation_mode(
            triggers=triggers,
            actions=actions,
            description="Parallel independent actions"
        )
        
        assert mode == AutomationMode.PARALLEL
    
    def test_mode_restart_for_window_sensor_with_delay(self):
        """Test that window sensors with delays get restart mode"""
        triggers = [Trigger(
            platform="state",
            entity_id="binary_sensor.window_sensor",
            to="on"
        )]
        actions = [
            Action(
                service="climate.set_temperature",
                entity_id="climate.thermostat",
                delay="00:01:00"
            )
        ]
        
        mode = AutomationPlan.determine_automation_mode(
            triggers=triggers,
            actions=actions,
            description="Window sensor adjusts temperature"
        )
        
        assert mode == AutomationMode.RESTART

