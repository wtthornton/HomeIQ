"""
Unit tests for error handling utilities (Improvement #2)
"""

import pytest

from src.services.automation.error_handling import (
    add_error_handling_to_actions,
    _detect_critical_actions,
    _add_error_handling_to_action
)
from src.contracts.models import Action


class TestErrorHandling:
    """Test error handling utilities"""

    def test_detect_critical_actions_security(self):
        """Test detection of security-critical actions"""
        actions = [
            Action(service="lock.unlock", entity_id="lock.front_door"),
            Action(service="light.turn_on", entity_id="light.kitchen"),
        ]
        
        critical = _detect_critical_actions(actions)
        assert 0 in critical  # lock.unlock is critical
        assert 1 not in critical  # light.turn_on is not critical

    def test_detect_critical_actions_alarm(self):
        """Test detection of alarm actions"""
        actions = [
            Action(service="alarm_control_panel.disarm", entity_id="alarm.home"),
            Action(service="switch.turn_on", entity_id="switch.fan"),
        ]
        
        critical = _detect_critical_actions(actions)
        assert 0 in critical  # alarm.disarm is critical
        assert 1 not in critical  # switch.turn_on is not critical

    def test_add_error_handling_to_non_critical(self):
        """Test adding error handling to non-critical actions"""
        actions = [
            Action(service="light.turn_on", entity_id="light.kitchen"),
            Action(service="switch.turn_off", entity_id="switch.fan"),
        ]
        
        enhanced = add_error_handling_to_actions(actions)
        
        # Both should have error: "continue"
        assert enhanced[0].error == "continue"
        assert enhanced[1].error == "continue"

    def test_error_handling_preserves_critical(self):
        """Test that critical actions don't get error handling"""
        actions = [
            Action(service="lock.unlock", entity_id="lock.front_door"),
            Action(service="light.turn_on", entity_id="light.kitchen"),
        ]
        
        enhanced = add_error_handling_to_actions(actions)
        
        # Critical action should not have error handling
        assert enhanced[0].error is None
        # Non-critical should have error handling
        assert enhanced[1].error == "continue"

    def test_error_handling_explicit_critical_indices(self):
        """Test error handling with explicit critical indices"""
        actions = [
            Action(service="light.turn_on", entity_id="light.kitchen"),
            Action(service="switch.turn_off", entity_id="switch.fan"),
        ]
        
        enhanced = add_error_handling_to_actions(actions, critical_action_indices={0})
        
        # Index 0 is critical, so no error handling
        assert enhanced[0].error is None
        # Index 1 is not critical, so has error handling
        assert enhanced[1].error == "continue"

    def test_add_error_handling_to_action_already_has_error(self):
        """Test that actions with existing error field are not overridden"""
        action = Action(
            service="light.turn_on",
            entity_id="light.kitchen",
            error="stop"
        )
        
        enhanced = _add_error_handling_to_action(action)
        # Should preserve existing error value
        assert enhanced.error == "stop"

