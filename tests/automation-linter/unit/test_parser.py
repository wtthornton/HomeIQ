"""
Unit tests for YAML parser.
"""

import pytest
import sys
from pathlib import Path

# Add shared module to path
shared_path = Path(__file__).parent.parent.parent.parent / "shared"
sys.path.insert(0, str(shared_path))

from ha_automation_lint.parsers.yaml_parser import AutomationParser
from ha_automation_lint.constants import Severity


class TestYAMLParser:
    """Test YAML parser functionality."""

    def test_parse_single_automation(self, parser):
        """Test parsing a single automation."""
        yaml_content = """
alias: "Test automation"
id: "test_001"
trigger:
  - platform: state
    entity_id: sensor.test
action:
  - service: light.turn_on
    target:
      entity_id: light.test
"""
        automations, findings = parser.parse(yaml_content)

        assert len(automations) == 1
        assert automations[0].alias == "Test automation"
        assert automations[0].id == "test_001"
        assert len(automations[0].trigger) == 1
        assert len(automations[0].action) == 1
        assert len([f for f in findings if f.severity == Severity.ERROR]) == 0

    def test_parse_automation_list(self, parser):
        """Test parsing a list of automations."""
        yaml_content = """
- alias: "First"
  id: "first"
  trigger:
    - platform: state
      entity_id: sensor.test1
  action:
    - service: light.turn_on
      target:
        entity_id: light.test1

- alias: "Second"
  id: "second"
  trigger:
    - platform: state
      entity_id: sensor.test2
  action:
    - service: light.turn_off
      target:
        entity_id: light.test2
"""
        automations, findings = parser.parse(yaml_content)

        assert len(automations) == 2
        assert automations[0].alias == "First"
        assert automations[1].alias == "Second"

    def test_parse_invalid_yaml(self, parser):
        """Test parsing invalid YAML syntax."""
        yaml_content = """
alias: "Test"
trigger:
  - platform: state
    entity_id: sensor.test
  invalid indent here
"""
        automations, findings = parser.parse(yaml_content)

        assert len(automations) == 0
        assert any(f.rule_id == "PARSE001" for f in findings)
        assert any(f.severity == Severity.ERROR for f in findings)

    def test_parse_empty_yaml(self, parser):
        """Test parsing empty YAML."""
        yaml_content = ""
        automations, findings = parser.parse(yaml_content)

        assert len(automations) == 0
        assert any(f.rule_id == "PARSE002" for f in findings)

    def test_parse_with_conditions(self, parser):
        """Test parsing automation with conditions."""
        yaml_content = """
alias: "With conditions"
trigger:
  - platform: state
    entity_id: sensor.test
condition:
  - condition: state
    entity_id: sun.sun
    state: "below_horizon"
action:
  - service: light.turn_on
    target:
      entity_id: light.test
"""
        automations, findings = parser.parse(yaml_content)

        assert len(automations) == 1
        assert len(automations[0].condition) == 1
        assert automations[0].condition[0].condition == "state"

    def test_parse_with_variables(self, parser):
        """Test parsing automation with variables."""
        yaml_content = """
alias: "With variables"
variables:
  brightness: 75
  entity: light.test
trigger:
  - platform: state
    entity_id: sensor.test
action:
  - service: light.turn_on
    target:
      entity_id: "{{ entity }}"
    data:
      brightness_pct: "{{ brightness }}"
"""
        automations, findings = parser.parse(yaml_content)

        assert len(automations) == 1
        assert "brightness" in automations[0].variables
        assert automations[0].variables["brightness"] == 75

    def test_parse_different_modes(self, parser):
        """Test parsing automations with different modes."""
        for mode in ["single", "restart", "queued", "parallel"]:
            yaml_content = f"""
alias: "Test mode"
mode: {mode}
trigger:
  - platform: state
    entity_id: sensor.test
action:
  - service: light.turn_on
    target:
      entity_id: light.test
"""
            automations, findings = parser.parse(yaml_content)
            assert len(automations) == 1
            assert automations[0].mode == mode

    def test_parse_multi_trigger(self, parser):
        """Test parsing automation with multiple triggers."""
        yaml_content = """
alias: "Multi trigger"
trigger:
  - platform: state
    entity_id: sensor.test1
  - platform: time
    at: "09:00:00"
  - platform: sun
    event: sunset
action:
  - service: light.turn_on
    target:
      entity_id: light.test
"""
        automations, findings = parser.parse(yaml_content)

        assert len(automations) == 1
        assert len(automations[0].trigger) == 3
        assert automations[0].trigger[0].platform == "state"
        assert automations[0].trigger[1].platform == "time"
        assert automations[0].trigger[2].platform == "sun"

    def test_parse_multi_action(self, parser):
        """Test parsing automation with multiple actions."""
        yaml_content = """
alias: "Multi action"
trigger:
  - platform: state
    entity_id: sensor.test
action:
  - service: light.turn_on
    target:
      entity_id: light.test1
  - service: light.turn_on
    target:
      entity_id: light.test2
  - service: notify.mobile_app
    data:
      message: "Lights on"
"""
        automations, findings = parser.parse(yaml_content)

        assert len(automations) == 1
        assert len(automations[0].action) == 3

    def test_parse_preserves_raw_source(self, parser):
        """Test that parsing preserves raw source data."""
        yaml_content = """
alias: "Test"
id: "test_123"
description: "Test description"
trigger:
  - platform: state
    entity_id: sensor.test
action:
  - service: light.turn_on
    target:
      entity_id: light.test
"""
        automations, findings = parser.parse(yaml_content)

        assert len(automations) == 1
        assert automations[0].raw_source is not None
        assert "alias" in automations[0].raw_source
        assert automations[0].raw_source["alias"] == "Test"
