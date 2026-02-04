"""
Unit tests for lint engine.
"""

import pytest
import sys
from pathlib import Path

# Add shared module to path
shared_path = Path(__file__).parent.parent.parent.parent / "shared"
sys.path.insert(0, str(shared_path))

from ha_automation_lint.engine import LintEngine
from ha_automation_lint.constants import Severity, ENGINE_VERSION, RULESET_VERSION


class TestLintEngine:
    """Test lint engine functionality."""

    def test_engine_initialization(self, lint_engine):
        """Test engine initializes correctly."""
        assert lint_engine is not None
        assert len(lint_engine.rules) >= 15  # MVP has 15+ rules

    def test_lint_valid_automation(self, lint_engine, valid_automation_yaml):
        """Test linting valid automation."""
        report = lint_engine.lint(valid_automation_yaml)

        assert report.engine_version == ENGINE_VERSION
        assert report.ruleset_version == RULESET_VERSION
        assert report.automations_detected == 1
        assert report.errors_count == 0

    def test_lint_invalid_automation(self, lint_engine, invalid_automation_yaml):
        """Test linting invalid automation (missing trigger)."""
        report = lint_engine.lint(invalid_automation_yaml)

        assert report.automations_detected == 1
        assert report.errors_count > 0
        assert any(f.rule_id == "SCHEMA001" for f in report.findings)

    def test_strict_mode(self, lint_engine):
        """Test strict mode converts warnings to errors."""
        yaml_with_warning = """
alias: "Test"
trigger:
  - platform: state
    entity_id: sensor.power
action:
  - service: notify.mobile_app
    data:
      message: "Test"
"""
        report = lint_engine.lint(yaml_with_warning, strict=True)

        # Warnings should be converted to errors in strict mode
        assert all(f.severity == Severity.ERROR or f.severity == Severity.INFO for f in report.findings)

    def test_duplicate_id_detection(self, lint_engine):
        """Test engine detects duplicate automation IDs."""
        yaml_with_duplicates = """
- alias: "First"
  id: "duplicate_id"
  trigger:
    - platform: state
      entity_id: sensor.test1
  action:
    - service: light.turn_on
      target:
        entity_id: light.test1

- alias: "Second"
  id: "duplicate_id"
  trigger:
    - platform: state
      entity_id: sensor.test2
  action:
    - service: light.turn_off
      target:
        entity_id: light.test2
"""
        report = lint_engine.lint(yaml_with_duplicates)

        assert any(f.rule_id == "SCHEMA004" for f in report.findings)
        duplicate_findings = [f for f in report.findings if f.rule_id == "SCHEMA004"]
        assert len(duplicate_findings) > 0

    def test_get_rules(self, lint_engine):
        """Test get_rules returns rule metadata."""
        rules = lint_engine.get_rules()

        assert len(rules) >= 15
        assert all("rule_id" in r for r in rules)
        assert all("name" in r for r in rules)
        assert all("severity" in r for r in rules)
        assert all("category" in r for r in rules)
        assert all("enabled" in r for r in rules)

    def test_rule_configuration(self):
        """Test engine respects rule configuration."""
        # Disable a specific rule
        engine = LintEngine(rule_config={"MAINTAINABILITY001": False})

        yaml_missing_desc = """
alias: "No Description"
id: "test"
trigger:
  - platform: state
    entity_id: sensor.test
action:
  - service: light.turn_on
    target:
      entity_id: light.test
"""
        report = engine.lint(yaml_missing_desc)

        # MAINTAINABILITY001 should not be in findings
        assert not any(f.rule_id == "MAINTAINABILITY001" for f in report.findings)

    def test_lint_report_properties(self, lint_engine, valid_automation_yaml):
        """Test LintReport property methods."""
        report = lint_engine.lint(valid_automation_yaml)

        assert isinstance(report.errors_count, int)
        assert isinstance(report.warnings_count, int)
        assert isinstance(report.info_count, int)
        assert report.errors_count + report.warnings_count + report.info_count == len(report.findings)
