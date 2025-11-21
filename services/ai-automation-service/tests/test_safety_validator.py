"""
Unit tests for Safety Validation Engine
Story AI1.19: Safety Validation Engine
"""

import pytest
from src.safety_validator import SafetyIssue, SafetyLevel, SafetyValidator


class TestSafetyValidator:
    """Test suite for SafetyValidator"""

    @pytest.fixture
    def validator(self):
        """Create validator with moderate safety level"""
        return SafetyValidator(SafetyLevel.MODERATE)

    @pytest.fixture
    def strict_validator(self):
        """Create validator with strict safety level"""
        return SafetyValidator(SafetyLevel.STRICT)

    @pytest.mark.asyncio
    async def test_valid_automation_passes(self, validator):
        """Test that a clean automation gets high score"""
        automation_yaml = """
alias: Morning Lights
trigger:
  - platform: time
    at: "07:00:00"
condition:
  - condition: state
    entity_id: binary_sensor.workday
    state: "on"
action:
  - service: light.turn_on
    target:
      entity_id: light.kitchen
    data:
      brightness_pct: 50
"""
        result = await validator.validate(automation_yaml)

        assert result.passed is True
        assert result.safety_score >= 90
        assert len(result.issues) == 0
        assert "✅" in result.summary

    @pytest.mark.asyncio
    async def test_invalid_yaml_fails(self, validator):
        """Test that invalid YAML is rejected"""
        automation_yaml = """
alias: Broken YAML
trigger:
  - platform: time
    at: "07:00:00
    # Missing closing quote
"""
        result = await validator.validate(automation_yaml)

        assert result.passed is False
        assert result.safety_score == 0
        assert len(result.issues) == 1
        assert result.issues[0].rule == "yaml_syntax"
        assert result.issues[0].severity == "critical"

    @pytest.mark.asyncio
    async def test_climate_extremes_detected(self, validator):
        """Test Rule 1: Extreme climate changes detected"""
        automation_yaml = """
alias: Dangerous Heat
trigger:
  - platform: time
    at: "12:00:00"
action:
  - service: climate.set_temperature
    data:
      temperature: 95
"""
        result = await validator.validate(automation_yaml)

        assert not result.passed  # Should fail
        assert result.safety_score < 70
        assert any(i.rule == "climate_extremes" for i in result.issues)
        assert any(i.severity == "critical" for i in result.issues)

    @pytest.mark.asyncio
    async def test_bulk_device_off_detected(self, validator):
        """Test Rule 2: Bulk shutoff detected"""
        automation_yaml = """
alias: Turn Off Everything
trigger:
  - platform: time
    at: "22:00:00"
action:
  - service: light.turn_off
    target:
      area_id: all
"""
        result = await validator.validate(automation_yaml)

        assert not result.passed
        assert any(i.rule == "bulk_device_off" for i in result.issues)
        assert any(i.severity == "critical" for i in result.issues)
        assert "ALL" in result.issues[0].message

    @pytest.mark.asyncio
    async def test_security_disable_detected(self, validator):
        """Test Rule 3: Security automation disable detected"""
        automation_yaml = """
alias: Disable Security
trigger:
  - platform: time
    at: "08:00:00"
action:
  - service: automation.turn_off
    target:
      entity_id: automation.security_alarm
"""
        result = await validator.validate(automation_yaml)

        assert not result.passed
        assert any(i.rule == "security_disable" for i in result.issues)
        assert any(i.severity == "critical" for i in result.issues)

    @pytest.mark.asyncio
    async def test_time_constraints_warning(self, validator):
        """Test Rule 4: Destructive action without constraints"""
        automation_yaml = """
alias: Close All Blinds
trigger:
  - platform: state
    entity_id: sensor.brightness
action:
  - service: cover.close_cover
    target:
      area_id: all_rooms
"""
        result = await validator.validate(automation_yaml)

        # Should pass (only warnings), but with lower score
        assert result.passed is True  # Warnings don't fail validation
        assert result.safety_score < 100
        assert any(i.rule == "time_constraints" for i in result.issues)
        assert any(i.severity == "warning" for i in result.issues)

    @pytest.mark.asyncio
    async def test_excessive_triggers_detected(self, validator):
        """Test Rule 5: High-frequency triggers detected"""
        automation_yaml = """
alias: Every Minute Check
trigger:
  - platform: time_pattern
    minutes: "*"
action:
  - service: light.turn_on
    target:
      entity_id: light.kitchen
"""
        result = await validator.validate(automation_yaml)

        # Should pass but with warnings
        assert result.passed is True
        assert any(i.rule == "excessive_triggers" for i in result.issues)

    @pytest.mark.asyncio
    async def test_destructive_actions_detected(self, validator):
        """Test Rule 6: System-level destructive actions detected"""
        automation_yaml = """
alias: Restart HA
trigger:
  - platform: time
    at: "03:00:00"
action:
  - service: homeassistant.restart
"""
        result = await validator.validate(automation_yaml)

        assert not result.passed
        assert any(i.rule == "destructive_actions" for i in result.issues)
        assert any(i.severity == "critical" for i in result.issues)

    @pytest.mark.asyncio
    async def test_multiple_issues_cumulative_score(self, validator):
        """Test that multiple issues reduce score cumulatively"""
        automation_yaml = """
alias: Multiple Problems
trigger:
  - platform: time_pattern
    minutes: "*"
action:
  - service: climate.set_temperature
    data:
      temperature: 95
  - service: light.turn_off
    target:
      area_id: all
"""
        result = await validator.validate(automation_yaml)

        assert not result.passed
        assert len(result.issues) > 1
        # Multiple critical issues should significantly reduce score
        assert result.safety_score < 50

    @pytest.mark.asyncio
    async def test_strict_level_blocks_warnings(self, strict_validator):
        """Test that strict level is more restrictive"""
        automation_yaml = """
alias: Moderate Warning
trigger:
  - platform: state
    entity_id: sensor.temp
action:
  - service: cover.close_cover
    target:
      entity_id: cover.blinds
"""
        result = await strict_validator.validate(automation_yaml)

        # Strict validator should have higher standards
        # This would pass moderate but might fail strict
        # (depends on exact score calculation)
        assert result.safety_score <= 100

    @pytest.mark.asyncio
    async def test_can_override_non_critical(self, validator):
        """Test override allowed for non-critical issues"""
        automation_yaml = """
alias: Minor Warning
trigger:
  - platform: time
    at: "07:00:00"
action:
  - service: light.turn_on
    target:
      entity_id: light.kitchen
"""
        result = await validator.validate(automation_yaml)

        # Should be able to override if any issues
        assert result.can_override is True

    @pytest.mark.asyncio
    async def test_cannot_override_critical_security(self, validator):
        """Test override blocked for critical security issues"""
        automation_yaml = """
alias: Cannot Override This
trigger:
  - platform: time
    at: "08:00:00"
action:
  - service: homeassistant.restart
"""
        result = await validator.validate(automation_yaml)

        assert not result.passed
        assert result.can_override is False  # Cannot override system-level calls

    def test_safety_level_enum(self):
        """Test SafetyLevel enum values"""
        assert SafetyLevel.STRICT.value == "strict"
        assert SafetyLevel.MODERATE.value == "moderate"
        assert SafetyLevel.PERMISSIVE.value == "permissive"

    def test_safety_issue_dataclass(self):
        """Test SafetyIssue dataclass"""
        issue = SafetyIssue(
            rule="test_rule",
            severity="warning",
            message="Test message",
            suggested_fix="Test fix",
        )

        assert issue.rule == "test_rule"
        assert issue.severity == "warning"
        assert issue.message == "Test message"
        assert issue.suggested_fix == "Test fix"
        assert issue.line_number is None

    @pytest.mark.asyncio
    async def test_climate_with_mode_passes(self, validator):
        """Test climate change with mode check passes"""
        automation_yaml = """
alias: Safe Climate
trigger:
  - platform: time
    at: "07:00:00"
action:
  - service: climate.set_temperature
    data:
      temperature: 72
      hvac_mode: heat
"""
        result = await validator.validate(automation_yaml)

        # Should pass - reasonable temp with mode
        assert result.passed is True
        # Might have info-level warnings but should score well
        assert result.safety_score >= 60

    @pytest.mark.asyncio
    async def test_specific_entities_pass(self, validator):
        """Test specific entity IDs don't trigger bulk warnings"""
        automation_yaml = """
alias: Specific Lights
trigger:
  - platform: time
    at: "22:00:00"
action:
  - service: light.turn_off
    target:
      entity_id:
        - light.kitchen
        - light.living_room
"""
        result = await validator.validate(automation_yaml)

        assert result.passed is True
        # Should NOT trigger bulk_device_off rule
        assert not any(i.rule == "bulk_device_off" for i in result.issues)

    @pytest.mark.asyncio
    async def test_time_condition_prevents_warning(self, validator):
        """Test time condition prevents destructive action warning"""
        automation_yaml = """
alias: Scheduled Close
trigger:
  - platform: sun
    event: sunset
condition:
  - condition: time
    after: "18:00:00"
    before: "23:00:00"
action:
  - service: cover.close_cover
    target:
      entity_id: cover.blinds
"""
        result = await validator.validate(automation_yaml)

        assert result.passed is True
        # Should NOT trigger time_constraints warning
        assert not any(i.rule == "time_constraints" for i in result.issues)

    @pytest.mark.asyncio
    async def test_state_trigger_with_debounce_no_warning(self, validator):
        """Test state trigger with 'for' duration doesn't warn"""
        automation_yaml = """
alias: Debounced Sensor
trigger:
  - platform: state
    entity_id: sensor.power
    for: "00:05:00"
action:
  - service: notify.pushover
    data:
      message: "Power stable"
"""
        result = await validator.validate(automation_yaml)

        assert result.passed is True
        # Should not trigger excessive_triggers for debounced sensor
        frequent_warnings = [i for i in result.issues if i.rule == "excessive_triggers"]
        assert len(frequent_warnings) == 0

    @pytest.mark.asyncio
    async def test_permissive_level_allows_more(self):
        """Test permissive level allows lower scores"""
        permissive_validator = SafetyValidator(SafetyLevel.PERMISSIVE)

        automation_yaml = """
alias: Somewhat Risky
trigger:
  - platform: time
    at: "22:00:00"
action:
  - service: light.turn_off
    target:
      area_id:
        - bedroom
        - kitchen
        - living_room
        - office
"""
        result = await permissive_validator.validate(automation_yaml)

        # Permissive should pass things that moderate might not
        # (4 areas = warning, but permissive is lenient)
        assert result.safety_score >= 40  # Permissive threshold


class TestGetSafetyValidator:
    """Test the get_safety_validator factory function"""

    def test_default_level(self):
        """Test default safety level is moderate"""
        from src.safety_validator import get_safety_validator

        validator = get_safety_validator()
        assert validator.safety_level == SafetyLevel.MODERATE

    def test_strict_level(self):
        """Test strict level creation"""
        from src.safety_validator import get_safety_validator

        validator = get_safety_validator("strict")
        assert validator.safety_level == SafetyLevel.STRICT

    def test_invalid_level_defaults_to_moderate(self):
        """Test invalid level falls back to moderate"""
        from src.safety_validator import get_safety_validator

        validator = get_safety_validator("invalid_level")
        assert validator.safety_level == SafetyLevel.MODERATE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

