"""
Unit tests for auto-fixer.
"""

import pytest
import sys
from pathlib import Path

shared_path = Path(__file__).parent.parent.parent.parent / "shared"
sys.path.insert(0, str(shared_path))

from ha_automation_lint.fixers.auto_fixer import AutoFixer
from ha_automation_lint.models import AutomationIR, TriggerIR, ActionIR, Finding, SuggestedFix
from ha_automation_lint.constants import FixMode, Severity


class TestAutoFixer:
    """Test auto-fixer functionality."""

    def test_fix_mode_none(self, auto_fixer):
        """Test fix mode NONE returns unchanged automations."""
        auto_fixer.fix_mode = FixMode.NONE
        automations = [AutomationIR(alias="Test", trigger=[TriggerIR(platform="state", raw={}, path="")], action=[ActionIR()])]
        findings = [Finding(rule_id="TEST", severity=Severity.INFO, message="Test", why_it_matters="Test", path="automations[0]")]

        fixed, applied = auto_fixer.apply_fixes(automations, findings)

        assert len(applied) == 0
        assert fixed == automations

    def test_fix_missing_description(self):
        """Test fixing missing description."""
        fixer = AutoFixer(fix_mode=FixMode.SAFE)

        auto = AutomationIR(
            alias="Test",
            trigger=[TriggerIR(platform="state", raw={}, path="")],
            action=[ActionIR()],
            path="automations[0]",
            raw_source={"alias": "Test"}
        )

        finding = Finding(
            rule_id="MAINTAINABILITY001",
            severity=Severity.INFO,
            message="Missing description",
            why_it_matters="Test",
            path="automations[0]",
            suggested_fix=SuggestedFix(type="auto", summary="Add description")
        )

        fixed, applied = fixer.apply_fixes([auto], [finding])

        assert "MAINTAINABILITY001" in applied
        assert fixed[0].description == ""

    def test_fix_missing_alias(self):
        """Test fixing missing alias."""
        fixer = AutoFixer(fix_mode=FixMode.SAFE)

        auto = AutomationIR(
            description="Test",
            trigger=[TriggerIR(platform="state", raw={}, path="")],
            action=[ActionIR()],
            path="automations[0]",
            raw_source={"description": "Test"}
        )

        finding = Finding(
            rule_id="MAINTAINABILITY002",
            severity=Severity.INFO,
            message="Missing alias",
            why_it_matters="Test",
            path="automations[0]",
            suggested_fix=SuggestedFix(type="auto", summary="Add alias")
        )

        fixed, applied = fixer.apply_fixes([auto], [finding])

        assert "MAINTAINABILITY002" in applied
        assert fixed[0].alias == ""

    def test_manual_fix_not_applied(self, auto_fixer):
        """Test manual fixes are not auto-applied."""
        auto = AutomationIR(alias="Test", trigger=[TriggerIR(platform="state", raw={}, path="")], action=[ActionIR()])
        finding = Finding(
            rule_id="TEST",
            severity=Severity.WARN,
            message="Test",
            why_it_matters="Test",
            path="automations[0]",
            suggested_fix=SuggestedFix(type="manual", summary="Fix manually")
        )

        fixed, applied = auto_fixer.apply_fixes([auto], [finding])

        assert len(applied) == 0
