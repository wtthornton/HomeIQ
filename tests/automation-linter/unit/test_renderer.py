"""
Unit tests for YAML renderer.
"""

import pytest
import sys
from pathlib import Path
import yaml

shared_path = Path(__file__).parent.parent.parent.parent / "shared"
sys.path.insert(0, str(shared_path))

from ha_automation_lint.renderers.yaml_renderer import YAMLRenderer
from ha_automation_lint.models import AutomationIR, TriggerIR, ActionIR


class TestYAMLRenderer:
    """Test YAML renderer functionality."""

    def test_render_single_automation(self, renderer, sample_automation_ir):
        """Test rendering single automation."""
        yaml_output = renderer.render([sample_automation_ir])

        assert yaml_output is not None
        assert "alias" in yaml_output
        assert "trigger" in yaml_output
        assert "action" in yaml_output

        # Verify it's valid YAML
        parsed = yaml.safe_load(yaml_output)
        assert parsed is not None

    def test_render_multiple_automations(self, renderer):
        """Test rendering multiple automations."""
        auto1 = AutomationIR(
            alias="First",
            trigger=[TriggerIR(platform="state", raw={"platform": "state"}, path="")],
            action=[ActionIR(service="light.turn_on", raw={"service": "light.turn_on"})],
            raw_source={}
        )
        auto2 = AutomationIR(
            alias="Second",
            trigger=[TriggerIR(platform="time", raw={"platform": "time"}, path="")],
            action=[ActionIR(service="light.turn_off", raw={"service": "light.turn_off"})],
            raw_source={}
        )

        yaml_output = renderer.render([auto1, auto2])

        assert yaml_output is not None
        parsed = yaml.safe_load(yaml_output)
        assert isinstance(parsed, list)
        assert len(parsed) == 2

    def test_render_preserves_order(self, renderer):
        """Test that rendered YAML preserves field order."""
        auto = AutomationIR(
            id="test_id",
            alias="Test",
            description="Description",
            trigger=[TriggerIR(platform="state", raw={"platform": "state"}, path="")],
            action=[ActionIR(service="light.turn_on", raw={"service": "light.turn_on"})],
            raw_source={}
        )

        yaml_output = renderer.render([auto])

        # Check that id comes before alias
        lines = yaml_output.split('\n')
        id_line = next((i for i, line in enumerate(lines) if 'id:' in line), None)
        alias_line = next((i for i, line in enumerate(lines) if 'alias:' in line), None)

        assert id_line is not None
        assert alias_line is not None
        assert id_line < alias_line

    def test_render_with_conditions(self, renderer):
        """Test rendering automation with conditions."""
        from ha_automation_lint.models import ConditionIR

        auto = AutomationIR(
            alias="With Conditions",
            trigger=[TriggerIR(platform="state", raw={"platform": "state"}, path="")],
            condition=[ConditionIR(condition="state", raw={"condition": "state"}, path="")],
            action=[ActionIR(service="light.turn_on", raw={"service": "light.turn_on"})],
            raw_source={}
        )

        yaml_output = renderer.render([auto])

        assert "condition" in yaml_output
        parsed = yaml.safe_load(yaml_output)
        assert "condition" in parsed

    def test_render_deterministic(self, renderer, sample_automation_ir):
        """Test that rendering is deterministic."""
        output1 = renderer.render([sample_automation_ir])
        output2 = renderer.render([sample_automation_ir])

        assert output1 == output2

    def test_create_diff_summary(self, renderer):
        """Test diff summary creation."""
        original = "line1\nline2\nline3"
        fixed = "line1\nline2\nline3\nline4\nline5"

        diff = renderer.create_diff_summary(original, fixed)

        assert diff is not None
        assert "2" in diff or "Modified" in diff
