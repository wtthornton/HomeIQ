"""
Unit tests for PolicyValidator
"""

import sys
from datetime import datetime, time
from pathlib import Path
from unittest.mock import patch

import pytest

# Fix import path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.validation.policy_validator import PolicyValidator


class TestPolicyValidator:
    """Test PolicyValidator class"""
    
    @pytest.fixture
    def validator(self):
        """Create PolicyValidator instance"""
        return PolicyValidator()
    
    def test_validate_risk_level_low(self, validator):
        """Test low risk level validation"""
        policy = {"risk": "low"}
        is_allowed, reason = validator.validate_risk_level(policy)
        assert is_allowed is True
        assert reason is None
    
    def test_validate_risk_level_high_ha_unstable(self, validator):
        """Test high risk with HA unstable"""
        policy = {"risk": "high", "allow_when_ha_unstable": False}
        risk_state = {"ha_unstable": True}
        is_allowed, reason = validator.validate_risk_level(policy, risk_state)
        assert is_allowed is False
        assert "HA unstable" in reason
    
    def test_validate_risk_level_high_allow_unstable(self, validator):
        """Test high risk allowing unstable HA"""
        policy = {"risk": "high", "allow_when_ha_unstable": True}
        risk_state = {"ha_unstable": True}
        is_allowed, reason = validator.validate_risk_level(policy, risk_state)
        assert is_allowed is True
    
    def test_validate_quiet_hours_no_conditions(self, validator):
        """Test quiet hours with no conditions"""
        is_allowed, reason = validator.validate_quiet_hours(None)
        assert is_allowed is True
        assert reason is None
    
    @patch('services.api-automation-edge.src.validation.policy_validator.datetime')
    def test_validate_quiet_hours_in_range(self, mock_datetime, validator):
        """Test quiet hours when current time is in quiet hours"""
        mock_datetime.now.return_value.time.return_value = time(23, 0, 0)  # 11 PM
        conditions = [
            {
                "type": "not_in_time_range",
                "start": "22:00:00",
                "end": "06:00:00"
            }
        ]
        is_allowed, reason = validator.validate_quiet_hours(conditions)
        assert is_allowed is False
        assert "Quiet hours" in reason
    
    @patch('services.api-automation-edge.src.validation.policy_validator.datetime')
    def test_validate_quiet_hours_outside_range(self, mock_datetime, validator):
        """Test quiet hours when current time is outside quiet hours"""
        mock_datetime.now.return_value.time.return_value = time(14, 0, 0)  # 2 PM
        conditions = [
            {
                "type": "not_in_time_range",
                "start": "22:00:00",
                "end": "06:00:00"
            }
        ]
        is_allowed, reason = validator.validate_quiet_hours(conditions)
        assert is_allowed is True
    
    @patch('services.api-automation-edge.src.validation.policy_validator.datetime')
    def test_validate_in_time_range(self, mock_datetime, validator):
        """Test in_time_range condition"""
        mock_datetime.now.return_value.time.return_value = time(10, 0, 0)  # 10 AM
        conditions = [
            {
                "type": "in_time_range",
                "start": "09:00:00",
                "end": "17:00:00"
            }
        ]
        is_allowed, reason = validator.validate_quiet_hours(conditions)
        assert is_allowed is True
    
    @patch('services.api-automation-edge.src.validation.policy_validator.datetime')
    def test_validate_in_time_range_outside(self, mock_datetime, validator):
        """Test in_time_range when outside allowed time"""
        mock_datetime.now.return_value.time.return_value = time(20, 0, 0)  # 8 PM
        conditions = [
            {
                "type": "in_time_range",
                "start": "09:00:00",
                "end": "17:00:00"
            }
        ]
        is_allowed, reason = validator.validate_quiet_hours(conditions)
        assert is_allowed is False
        assert "Outside allowed time range" in reason
    
    def test_validate_manual_override_no_conditions(self, validator):
        """Test manual override with no conditions"""
        is_allowed, reason = validator.validate_manual_override(None, ["light.test"])
        assert is_allowed is True
    
    def test_validate_manual_override_active(self, validator):
        """Test manual override when override is active"""
        validator.set_manual_override("light.test", 300)  # 5 minutes
        conditions = [{"type": "not_manual_override", "scope": "all"}]
        is_allowed, reason = validator.validate_manual_override(conditions, ["light.test"])
        assert is_allowed is False
        assert "Manual override active" in reason
    
    def test_validate_manual_override_expired(self, validator):
        """Test manual override when override has expired"""
        # Set override in the past (would need time mocking for real test)
        validator.manual_overrides["light.test"] = 0  # Expired
        conditions = [{"type": "not_manual_override", "scope": "all"}]
        is_allowed, reason = validator.validate_manual_override(conditions, ["light.test"])
        assert is_allowed is True
    
    def test_set_clear_manual_override(self, validator):
        """Test setting and clearing manual override"""
        validator.set_manual_override("light.test", 300)
        assert "light.test" in validator.manual_overrides
        
        validator.clear_manual_override("light.test")
        assert "light.test" not in validator.manual_overrides
    
    def test_validate_policy_all_passes(self, validator):
        """Test full policy validation when all checks pass"""
        spec = {
            "policy": {"risk": "low"},
            "conditions": [],
            "actions": [{"resolved_entity_ids": ["light.test"]}]
        }
        is_valid, errors = validator.validate_policy(spec)
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_policy_fails_risk(self, validator):
        """Test policy validation fails on risk check"""
        spec = {
            "policy": {"risk": "high", "allow_when_ha_unstable": False},
            "conditions": [],
            "actions": [{"resolved_entity_ids": ["light.test"]}]
        }
        risk_state = {"ha_unstable": True}
        is_valid, errors = validator.validate_policy(spec, risk_state)
        assert is_valid is False
        assert len(errors) > 0
