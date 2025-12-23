"""
Unit tests for error handling utilities (Improvement #2)
"""

import pytest

from src.services.automation.error_handling import (
    add_error_handling_to_actions,
    _detect_critical_actions,
    _add_error_handling_to_action,
    _should_use_choose_block,
    _add_choose_block_error_handling
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
        
        # Both should have continue_on_error: True (HA 2025 format)
        action0_dict = enhanced[0].model_dump(exclude_none=True)
        action1_dict = enhanced[1].model_dump(exclude_none=True)
        assert action0_dict.get("continue_on_error") is True
        assert action1_dict.get("continue_on_error") is True

    def test_error_handling_preserves_critical(self):
        """Test that critical actions don't get error handling"""
        actions = [
            Action(service="lock.unlock", entity_id="lock.front_door"),
            Action(service="light.turn_on", entity_id="light.kitchen"),
        ]
        
        enhanced = add_error_handling_to_actions(actions)
        
        # Critical action should not have error handling
        action0_dict = enhanced[0].model_dump(exclude_none=True)
        assert "continue_on_error" not in action0_dict
        # Non-critical should have error handling
        action1_dict = enhanced[1].model_dump(exclude_none=True)
        assert action1_dict.get("continue_on_error") is True

    def test_error_handling_explicit_critical_indices(self):
        """Test error handling with explicit critical indices"""
        actions = [
            Action(service="light.turn_on", entity_id="light.kitchen"),
            Action(service="switch.turn_off", entity_id="switch.fan"),
        ]
        
        enhanced = add_error_handling_to_actions(actions, critical_action_indices={0})
        
        # Index 0 is critical, so no error handling
        action0_dict = enhanced[0].model_dump(exclude_none=True)
        assert "continue_on_error" not in action0_dict
        # Index 1 is not critical, so has error handling
        action1_dict = enhanced[1].model_dump(exclude_none=True)
        assert action1_dict.get("continue_on_error") is True

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
    
    def test_should_use_choose_block_with_entity(self):
        """Test choose block detection for actions with entity_id"""
        action = Action(service="light.turn_on", entity_id="light.kitchen")
        assert _should_use_choose_block(action) is True
    
    def test_should_not_use_choose_block_without_entity(self):
        """Test choose block detection for actions without entity_id"""
        action = Action(service="system_log.write")
        assert _should_use_choose_block(action) is False
    
    def test_choose_block_error_handling(self):
        """Test choose block error handling structure"""
        action = Action(service="light.turn_on", entity_id="light.kitchen")
        choose_block = _add_choose_block_error_handling(action)
        
        # Should be a dict with choose key
        assert isinstance(choose_block, dict)
        assert "choose" in choose_block
        assert isinstance(choose_block["choose"], list)
        assert len(choose_block["choose"]) >= 1
        assert "default" in choose_block
    
    def test_add_error_handling_with_choose_blocks(self):
        """Test error handling with choose blocks enabled"""
        actions = [
            Action(service="light.turn_on", entity_id="light.kitchen"),
            Action(service="switch.turn_off", entity_id="switch.fan"),
        ]
        
        enhanced = add_error_handling_to_actions(actions, use_choose_blocks=True)
        
        # Should use choose blocks for actions with entities
        assert isinstance(enhanced[0], dict)
        assert "choose" in enhanced[0]
        assert isinstance(enhanced[1], dict)
        assert "choose" in enhanced[1]

