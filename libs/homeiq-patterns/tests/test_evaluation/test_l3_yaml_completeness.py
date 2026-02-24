"""
Tests for Story 3.2: YAMLCompletenessEvaluator (L3 Details)

Verifies deterministic HA automation YAML structure validation:
required keys, list formats, and unresolved placeholder detection.
"""

import pytest

from homeiq_patterns.evaluation.evaluators.l3_yaml_completeness import (
    YAMLCompletenessEvaluator,
)
from homeiq_patterns.evaluation.models import (
    EvalLevel,
    EvalScope,
    SessionTrace,
)

_COMPLETE_YAML = """\
alias: Office Lights On
trigger:
  - platform: state
    entity_id: binary_sensor.office_motion
    to: "on"
action:
  - service: light.turn_on
    target:
      entity_id: light.office
"""

_NO_TRIGGER_YAML = """\
alias: Office Lights On
action:
  - service: light.turn_on
    target:
      entity_id: light.office
"""

_NO_ACTION_YAML = """\
alias: Office Lights On
trigger:
  - platform: state
    entity_id: binary_sensor.office_motion
"""

_NO_ALIAS_YAML = """\
trigger:
  - platform: state
    entity_id: binary_sensor.office_motion
action:
  - service: light.turn_on
    target:
      entity_id: light.office
"""

_TRIGGER_NOT_LIST_YAML = """\
alias: Office Lights On
trigger:
  platform: state
  entity_id: binary_sensor.office_motion
action:
  - service: light.turn_on
"""

_ACTION_NOT_LIST_YAML = """\
alias: Office Lights On
trigger:
  - platform: state
    entity_id: binary_sensor.office_motion
action:
  service: light.turn_on
"""

_MINIMAL_YAML = """\
alias: Test
trigger:
  - platform: time
action:
  - service: light.turn_on
"""


def _make_session(
    yaml_str: str = "",
    placeholders: list[str] | None = None,
    execution_mode: str = "",
) -> SessionTrace:
    metadata: dict = {}
    if yaml_str:
        metadata["generated_yaml"] = yaml_str
    if placeholders is not None:
        metadata["unresolved_placeholders"] = placeholders
    if execution_mode:
        metadata["execution_mode"] = execution_mode
    return SessionTrace(agent_name="test", metadata=metadata)


# =====================================================================
# Complete YAML
# =====================================================================


class TestCompleteYAML:
    @pytest.mark.asyncio
    async def test_complete_yaml_scores_1(self):
        evaluator = YAMLCompletenessEvaluator()
        session = _make_session(_COMPLETE_YAML, placeholders=[])
        result = await evaluator.evaluate(session)
        assert result.score == 1.0
        assert result.label == "Complete"

    @pytest.mark.asyncio
    async def test_minimal_complete_yaml(self):
        evaluator = YAMLCompletenessEvaluator()
        session = _make_session(_MINIMAL_YAML, placeholders=[])
        result = await evaluator.evaluate(session)
        assert result.score == 1.0


# =====================================================================
# Missing keys
# =====================================================================


class TestMissingKeys:
    @pytest.mark.asyncio
    async def test_missing_trigger(self):
        evaluator = YAMLCompletenessEvaluator()
        session = _make_session(_NO_TRIGGER_YAML, placeholders=[])
        result = await evaluator.evaluate(session)
        # Missing: trigger (0.2) + trigger-is-list (0.1) = 0.3 lost
        assert abs(result.score - 0.7) < 0.01
        assert "trigger: MISSING" in result.explanation

    @pytest.mark.asyncio
    async def test_missing_action(self):
        evaluator = YAMLCompletenessEvaluator()
        session = _make_session(_NO_ACTION_YAML, placeholders=[])
        result = await evaluator.evaluate(session)
        # Missing: action (0.2) + action-is-list (0.1) = 0.3 lost
        assert abs(result.score - 0.7) < 0.01
        assert "action: MISSING" in result.explanation

    @pytest.mark.asyncio
    async def test_missing_alias(self):
        evaluator = YAMLCompletenessEvaluator()
        session = _make_session(_NO_ALIAS_YAML, placeholders=[])
        result = await evaluator.evaluate(session)
        # Missing: alias (0.2) = 0.2 lost
        assert abs(result.score - 0.8) < 0.01
        assert "alias: MISSING" in result.explanation


# =====================================================================
# List format compliance
# =====================================================================


class TestListFormat:
    @pytest.mark.asyncio
    async def test_trigger_not_list(self):
        evaluator = YAMLCompletenessEvaluator()
        session = _make_session(_TRIGGER_NOT_LIST_YAML, placeholders=[])
        result = await evaluator.evaluate(session)
        # Has trigger (0.2), alias (0.2), action (0.2), action-is-list (0.1),
        # no-placeholders (0.2) = 0.9. Missing trigger-is-list (0.1).
        assert abs(result.score - 0.9) < 0.01
        assert "NOT a list" in result.explanation

    @pytest.mark.asyncio
    async def test_action_not_list(self):
        evaluator = YAMLCompletenessEvaluator()
        session = _make_session(_ACTION_NOT_LIST_YAML, placeholders=[])
        result = await evaluator.evaluate(session)
        # Missing action-is-list (0.1) = 0.9
        assert abs(result.score - 0.9) < 0.01


# =====================================================================
# Placeholder detection
# =====================================================================


class TestPlaceholders:
    @pytest.mark.asyncio
    async def test_unresolved_placeholders(self):
        evaluator = YAMLCompletenessEvaluator()
        session = _make_session(
            _COMPLETE_YAML, placeholders=["{{entity_id}}"]
        )
        result = await evaluator.evaluate(session)
        # Missing no-placeholders (0.2) = 0.8
        assert abs(result.score - 0.8) < 0.01
        assert "Unresolved" in result.explanation

    @pytest.mark.asyncio
    async def test_no_placeholders_metadata_absent(self):
        """When unresolved_placeholders key is absent, default to empty = pass."""
        evaluator = YAMLCompletenessEvaluator()
        session = _make_session(_COMPLETE_YAML)  # no placeholders key
        result = await evaluator.evaluate(session)
        assert result.score == 1.0


# =====================================================================
# Invalid / missing YAML
# =====================================================================


class TestInvalidYAML:
    @pytest.mark.asyncio
    async def test_malformed_yaml(self):
        evaluator = YAMLCompletenessEvaluator()
        session = _make_session("{{invalid: yaml: [", placeholders=[])
        result = await evaluator.evaluate(session)
        assert result.score == 0.0
        assert result.label == "Invalid"

    @pytest.mark.asyncio
    async def test_yaml_root_is_list(self):
        evaluator = YAMLCompletenessEvaluator()
        session = _make_session("- item1\n- item2\n", placeholders=[])
        result = await evaluator.evaluate(session)
        assert result.score == 0.0
        assert result.label == "Invalid"
        assert "list" in result.explanation

    @pytest.mark.asyncio
    async def test_no_yaml_preview_mode(self):
        evaluator = YAMLCompletenessEvaluator()
        session = _make_session("", execution_mode="preview")
        result = await evaluator.evaluate(session)
        assert result.score == 0.5
        assert result.label == "N/A"

    @pytest.mark.asyncio
    async def test_no_yaml_non_preview(self):
        evaluator = YAMLCompletenessEvaluator()
        session = _make_session("")
        result = await evaluator.evaluate(session)
        assert result.score == 0.0
        assert result.label == "Missing"


# =====================================================================
# Cumulative deductions
# =====================================================================


class TestCumulativeDeductions:
    @pytest.mark.asyncio
    async def test_multiple_missing(self):
        """Missing trigger + missing alias + unresolved placeholders."""
        yaml_str = "action:\n  - service: light.turn_on\n"
        evaluator = YAMLCompletenessEvaluator()
        session = _make_session(yaml_str, placeholders=["{{area}}"])
        result = await evaluator.evaluate(session)
        # Has: action (0.2) + action-is-list (0.1) = 0.3
        # Missing: trigger (0.2) + trigger-list (0.1) + alias (0.2) + placeholders (0.2)
        assert abs(result.score - 0.3) < 0.01
        assert result.label == "Incomplete"


# =====================================================================
# Evaluator properties
# =====================================================================


class TestEvaluatorProperties:
    def test_name(self):
        evaluator = YAMLCompletenessEvaluator()
        assert evaluator.name == "yaml_completeness"

    def test_level(self):
        evaluator = YAMLCompletenessEvaluator()
        assert evaluator.level == EvalLevel.DETAILS

    def test_scope(self):
        evaluator = YAMLCompletenessEvaluator()
        assert evaluator.scope == EvalScope.TOOL_CALL
