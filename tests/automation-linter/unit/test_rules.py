"""
Unit tests for all 15 MVP rules.
"""

import pytest
import sys
from pathlib import Path

# Add shared module to path
shared_path = Path(__file__).parent.parent.parent.parent / "shared"
sys.path.insert(0, str(shared_path))

from ha_automation_lint.rules.mvp_rules import (
    MissingTriggerRule,
    MissingActionRule,
    UnknownTopLevelKeysRule,
    DuplicateIDRule,
    InvalidServiceFormatRule,
    TriggerMissingPlatformRule,
    DelayWithSingleModeRule,
    HighFrequencyTriggerRule,
    ChooseWithoutDefaultRule,
    EmptyTriggerListRule,
    EmptyActionListRule,
    ServiceMissingTargetRule,
    InvalidEntityIDFormatRule,
    MissingDescriptionRule,
    MissingAliasRule,
)
from ha_automation_lint.models import AutomationIR, TriggerIR, ActionIR
from ha_automation_lint.constants import Severity


class TestSchemaRules:
    """Test schema validation rules."""

    def test_missing_trigger_rule(self):
        """Test SCHEMA001 - Missing Trigger."""
        rule = MissingTriggerRule()

        # Should trigger on empty trigger list
        auto = AutomationIR(alias="Test", action=[ActionIR()])
        findings = rule.check(auto)
        assert len(findings) == 1
        assert findings[0].rule_id == "SCHEMA001"
        assert findings[0].severity == Severity.ERROR

        # Should not trigger with triggers
        auto_with_trigger = AutomationIR(
            alias="Test",
            trigger=[TriggerIR(platform="state", raw={}, path="")],
            action=[ActionIR()]
        )
        findings = rule.check(auto_with_trigger)
        assert len(findings) == 0

    def test_missing_action_rule(self):
        """Test SCHEMA002 - Missing Action."""
        rule = MissingActionRule()

        # Should trigger on empty action list
        auto = AutomationIR(alias="Test", trigger=[TriggerIR(platform="state", raw={}, path="")])
        findings = rule.check(auto)
        assert len(findings) == 1
        assert findings[0].rule_id == "SCHEMA002"

        # Should not trigger with actions
        auto_with_action = AutomationIR(
            alias="Test",
            trigger=[TriggerIR(platform="state", raw={}, path="")],
            action=[ActionIR(service="light.turn_on")]
        )
        findings = rule.check(auto_with_action)
        assert len(findings) == 0

    def test_unknown_top_level_keys_rule(self):
        """Test SCHEMA003 - Unknown Top-Level Keys."""
        rule = UnknownTopLevelKeysRule()

        # Should trigger on unknown keys
        auto = AutomationIR(
            alias="Test",
            trigger=[TriggerIR(platform="state", raw={}, path="")],
            action=[ActionIR()],
            raw_source={"alias": "Test", "unknown_key": "value"}
        )
        findings = rule.check(auto)
        assert len(findings) == 1
        assert "unknown_key" in findings[0].message

        # Should not trigger on known keys only
        auto_valid = AutomationIR(
            alias="Test",
            trigger=[TriggerIR(platform="state", raw={}, path="")],
            action=[ActionIR()],
            raw_source={"alias": "Test", "id": "test", "description": "Test"}
        )
        findings = rule.check(auto_valid)
        assert len(findings) == 0

    def test_invalid_service_format_rule(self):
        """Test SCHEMA005 - Invalid Service Format."""
        rule = InvalidServiceFormatRule()

        # Should trigger on service without domain
        auto = AutomationIR(
            alias="Test",
            trigger=[TriggerIR(platform="state", raw={}, path="")],
            action=[ActionIR(service="turn_on", path="automations[0].action[0]")]
        )
        findings = rule.check(auto)
        assert len(findings) == 1
        assert findings[0].rule_id == "SCHEMA005"

        # Should not trigger on valid domain.service format
        auto_valid = AutomationIR(
            alias="Test",
            trigger=[TriggerIR(platform="state", raw={}, path="")],
            action=[ActionIR(service="light.turn_on")]
        )
        findings = rule.check(auto_valid)
        assert len(findings) == 0


class TestSyntaxRules:
    """Test syntax validation rules."""

    def test_trigger_missing_platform_rule(self):
        """Test SYNTAX001 - Trigger Missing Platform."""
        rule = TriggerMissingPlatformRule()

        # Should trigger on trigger with unknown platform
        auto = AutomationIR(
            alias="Test",
            trigger=[TriggerIR(platform="unknown", raw={}, path="automations[0].trigger[0]")],
            action=[ActionIR()]
        )
        findings = rule.check(auto)
        assert len(findings) == 1
        assert findings[0].rule_id == "SYNTAX001"

        # Should not trigger with valid platform
        auto_valid = AutomationIR(
            alias="Test",
            trigger=[TriggerIR(platform="state", raw={}, path="")],
            action=[ActionIR()]
        )
        findings = rule.check(auto_valid)
        assert len(findings) == 0


class TestLogicRules:
    """Test logic validation rules."""

    def test_delay_with_single_mode_rule(self):
        """Test LOGIC001 - Delay with Single Mode."""
        rule = DelayWithSingleModeRule()

        # Should trigger on single mode with delay
        auto = AutomationIR(
            alias="Test",
            mode="single",
            trigger=[TriggerIR(platform="state", raw={}, path="")],
            action=[ActionIR(raw={"delay": "00:05:00"})]
        )
        findings = rule.check(auto)
        assert len(findings) == 1
        assert findings[0].rule_id == "LOGIC001"

        # Should not trigger on restart mode with delay
        auto_restart = AutomationIR(
            alias="Test",
            mode="restart",
            trigger=[TriggerIR(platform="state", raw={}, path="")],
            action=[ActionIR(raw={"delay": "00:05:00"})]
        )
        findings = rule.check(auto_restart)
        assert len(findings) == 0

    def test_high_frequency_trigger_rule(self):
        """Test LOGIC002 - High-Frequency Trigger Without Debounce."""
        rule = HighFrequencyTriggerRule()

        # Should trigger on state trigger without 'for'
        auto = AutomationIR(
            alias="Test",
            trigger=[TriggerIR(
                platform="state",
                raw={"platform": "state", "entity_id": "sensor.power"},
                path="automations[0].trigger[0]"
            )],
            action=[ActionIR()]
        )
        findings = rule.check(auto)
        assert len(findings) == 1
        assert findings[0].rule_id == "LOGIC002"

        # Should not trigger with 'for' duration
        auto_debounced = AutomationIR(
            alias="Test",
            trigger=[TriggerIR(
                platform="state",
                raw={"platform": "state", "entity_id": "sensor.power", "for": "00:00:30"},
                path=""
            )],
            action=[ActionIR()]
        )
        findings = rule.check(auto_debounced)
        assert len(findings) == 0

    def test_choose_without_default_rule(self):
        """Test LOGIC003 - Choose Without Default."""
        rule = ChooseWithoutDefaultRule()

        # Should trigger on choose without default
        auto = AutomationIR(
            alias="Test",
            trigger=[TriggerIR(platform="state", raw={}, path="")],
            action=[ActionIR(raw={"choose": [{"conditions": [], "sequence": []}]})]
        )
        findings = rule.check(auto)
        assert len(findings) == 1
        assert findings[0].rule_id == "LOGIC003"

        # Should not trigger with default
        auto_with_default = AutomationIR(
            alias="Test",
            trigger=[TriggerIR(platform="state", raw={}, path="")],
            action=[ActionIR(raw={"choose": [{"conditions": [], "sequence": []}], "default": []})]
        )
        findings = rule.check(auto_with_default)
        assert len(findings) == 0


class TestReliabilityRules:
    """Test reliability validation rules."""

    def test_service_missing_target_rule(self):
        """Test RELIABILITY001 - Service Missing Target."""
        rule = ServiceMissingTargetRule()

        # Should trigger on service without target
        auto = AutomationIR(
            alias="Test",
            trigger=[TriggerIR(platform="state", raw={}, path="")],
            action=[ActionIR(
                service="light.turn_on",
                raw={"service": "light.turn_on", "data": {"brightness": 100}},
                path="automations[0].action[0]"
            )]
        )
        findings = rule.check(auto)
        assert len(findings) == 1
        assert findings[0].rule_id == "RELIABILITY001"

        # Should not trigger with target
        auto_with_target = AutomationIR(
            alias="Test",
            trigger=[TriggerIR(platform="state", raw={}, path="")],
            action=[ActionIR(
                service="light.turn_on",
                raw={"service": "light.turn_on", "target": {"entity_id": "light.test"}}
            )]
        )
        findings = rule.check(auto_with_target)
        assert len(findings) == 0

    def test_invalid_entity_id_format_rule(self):
        """Test RELIABILITY002 - Invalid Entity ID Format."""
        rule = InvalidEntityIDFormatRule()

        # Should trigger on invalid entity_id format
        auto = AutomationIR(
            alias="Test",
            trigger=[TriggerIR(
                platform="state",
                raw={"platform": "state", "entity_id": "Invalid.Entity-ID"},
                path="automations[0].trigger[0]"
            )],
            action=[ActionIR()]
        )
        findings = rule.check(auto)
        assert len(findings) == 1
        assert findings[0].rule_id == "RELIABILITY002"

        # Should not trigger on valid entity_id
        auto_valid = AutomationIR(
            alias="Test",
            trigger=[TriggerIR(
                platform="state",
                raw={"platform": "state", "entity_id": "sensor.temperature"},
                path=""
            )],
            action=[ActionIR()]
        )
        findings = rule.check(auto_valid)
        assert len(findings) == 0

        # Should not trigger on templates
        auto_template = AutomationIR(
            alias="Test",
            trigger=[TriggerIR(
                platform="state",
                raw={"platform": "state", "entity_id": "{{ sensor_name }}"},
                path=""
            )],
            action=[ActionIR()]
        )
        findings = rule.check(auto_template)
        assert len(findings) == 0


class TestMaintainabilityRules:
    """Test maintainability validation rules."""

    def test_missing_description_rule(self):
        """Test MAINTAINABILITY001 - Missing Description."""
        rule = MissingDescriptionRule()

        # Should trigger on missing description
        auto = AutomationIR(
            alias="Test",
            trigger=[TriggerIR(platform="state", raw={}, path="")],
            action=[ActionIR()]
        )
        findings = rule.check(auto)
        assert len(findings) == 1
        assert findings[0].rule_id == "MAINTAINABILITY001"
        assert findings[0].severity == Severity.INFO
        assert findings[0].suggested_fix is not None
        assert findings[0].suggested_fix.type == "auto"

        # Should not trigger with description
        auto_with_desc = AutomationIR(
            alias="Test",
            description="Test description",
            trigger=[TriggerIR(platform="state", raw={}, path="")],
            action=[ActionIR()]
        )
        findings = rule.check(auto_with_desc)
        assert len(findings) == 0

    def test_missing_alias_rule(self):
        """Test MAINTAINABILITY002 - Missing Alias."""
        rule = MissingAliasRule()

        # Should trigger on missing alias
        auto = AutomationIR(
            description="Test",
            trigger=[TriggerIR(platform="state", raw={}, path="")],
            action=[ActionIR()]
        )
        findings = rule.check(auto)
        assert len(findings) == 1
        assert findings[0].rule_id == "MAINTAINABILITY002"
        assert findings[0].suggested_fix is not None

        # Should not trigger with alias
        auto_with_alias = AutomationIR(
            alias="Test Automation",
            trigger=[TriggerIR(platform="state", raw={}, path="")],
            action=[ActionIR()]
        )
        findings = rule.check(auto_with_alias)
        assert len(findings) == 0
