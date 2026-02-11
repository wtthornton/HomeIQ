"""
L3 Details Evaluators — Parameter extraction accuracy.

Evaluators:
  - ToolParameterAccuracyEvaluator: Were correct parameter values extracted?
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..base_evaluator import DetailsEvaluator
from ..config import AgentEvalConfig, ParamRule, ToolDef
from ..llm_judge import JudgeRubric, LLMJudge
from ..models import EvaluationResult, SessionTrace, ToolCall

_RUBRICS_DIR = Path(__file__).resolve().parent.parent / "rubrics"


class ToolParameterAccuracyEvaluator(DetailsEvaluator):
    """
    L3 — Evaluates whether the agent extracted correct parameter values
    from user input.

    Rule-based checks:
      - Type validation (expected int got string, etc.)
      - Format validation (date YYYY-MM-DD, time HH:MM)
      - Enum validation (value in allowed set)
      - Range validation (min/max bounds)

    LLM-judged checks (via fallback):
      - Natural language extraction accuracy
      - Entity resolution quality

    Score: fraction of parameters that pass validation.
    """

    name = "tool_parameter_accuracy"

    def __init__(
        self,
        config: AgentEvalConfig | None = None,
        llm_judge: LLMJudge | None = None,
        rubric: JudgeRubric | None = None,
    ):
        self._config = config or AgentEvalConfig()
        self._judge = llm_judge or LLMJudge()
        self._rubric = rubric or self._load_default_rubric()

    async def evaluate(self, session: SessionTrace) -> EvaluationResult:
        if not session.tool_calls:
            return self._result(
                score=1.0,
                label="Yes",
                explanation="No tool calls to evaluate",
            )

        total_params = 0
        correct_params = 0
        issues: list[str] = []

        for tc in session.tool_calls:
            tool_def = self._config.get_tool(tc.tool_name)
            param_rules = self._config.get_param_rules_for_tool(tc.tool_name)

            if tool_def is None and not param_rules:
                # No config for this tool — skip
                continue

            # Check required parameters are present
            if tool_def and tool_def.required_params:
                for req in tool_def.required_params:
                    total_params += 1
                    if req in tc.parameters:
                        correct_params += 1
                    else:
                        issues.append(
                            f"{tc.tool_name}: missing required param '{req}'"
                        )

            # Validate parameters against rules
            for rule in param_rules:
                if rule.param not in tc.parameters:
                    continue  # Already counted in required check
                total_params += 1
                value = tc.parameters[rule.param]
                valid, reason = self._validate_param(value, rule, tool_def)
                if valid:
                    correct_params += 1
                else:
                    issues.append(
                        f"{tc.tool_name}.{rule.param}: {reason}"
                    )

            # Check params defined in tool_def but not covered by rules
            if tool_def:
                rule_params = {r.param for r in param_rules}
                for param_def in tool_def.parameters:
                    pname = param_def.name
                    if pname in rule_params:
                        continue  # Already checked by rule
                    if pname in tc.parameters:
                        total_params += 1
                        value = tc.parameters[pname]
                        valid, reason = self._validate_param_def(
                            value, param_def
                        )
                        if valid:
                            correct_params += 1
                        else:
                            issues.append(
                                f"{tc.tool_name}.{pname}: {reason}"
                            )

        # If no parameters to validate, fall through to LLM judge
        if total_params == 0:
            if session.tool_calls:
                result = await self._judge.judge(session, self._rubric)
                return self._result(
                    score=result.score,
                    label=result.label,
                    explanation=result.explanation,
                )
            return self._result(
                score=1.0,
                label="Yes",
                explanation="No parameters to validate",
            )

        score = correct_params / total_params
        label = "Yes" if score == 1.0 else "No"
        explanation = (
            f"{correct_params}/{total_params} parameters valid."
            + (f" Issues: {'; '.join(issues)}" if issues else "")
        )

        return self._result(score=score, label=label, explanation=explanation)

    def _validate_param(
        self,
        value: Any,
        rule: ParamRule,
        tool_def: ToolDef | None,
    ) -> tuple[bool, str]:
        """Validate a parameter value against its rule."""

        # Enum validation from rule
        if rule.valid_values:
            if value not in rule.valid_values:
                return False, (
                    f"value {value!r} not in allowed: {rule.valid_values}"
                )

        # Format validation from rule
        if rule.format:
            ok, reason = self._check_format(value, rule.format)
            if not ok:
                return False, reason

        # Also check the param definition if tool_def exists
        if tool_def:
            param_def = next(
                (p for p in tool_def.parameters if p.name == rule.param),
                None,
            )
            if param_def:
                ok, reason = self._validate_param_def(value, param_def)
                if not ok:
                    return False, reason

        return True, ""

    @staticmethod
    def _validate_param_def(value: Any, param_def: Any) -> tuple[bool, str]:
        """Validate value against a ParamDef (type, format, range, enum)."""

        # Type validation
        expected_type = param_def.type
        if expected_type == "integer":
            if not isinstance(value, int):
                try:
                    int(value)
                except (ValueError, TypeError):
                    return False, (
                        f"expected integer, got {type(value).__name__}"
                    )
        elif expected_type == "number" or expected_type == "float":
            if not isinstance(value, (int, float)):
                try:
                    float(value)
                except (ValueError, TypeError):
                    return False, (
                        f"expected number, got {type(value).__name__}"
                    )

        # Format validation
        if param_def.format:
            ok, reason = ToolParameterAccuracyEvaluator._check_format(
                value, param_def.format
            )
            if not ok:
                return False, reason

        # Range validation
        if param_def.min_value is not None:
            try:
                if float(value) < param_def.min_value:
                    return False, (
                        f"value {value} below min {param_def.min_value}"
                    )
            except (ValueError, TypeError):
                pass

        if param_def.max_value is not None:
            try:
                if float(value) > param_def.max_value:
                    return False, (
                        f"value {value} above max {param_def.max_value}"
                    )
            except (ValueError, TypeError):
                pass

        # Enum validation from param_def
        if param_def.valid_values:
            if value not in param_def.valid_values:
                return False, (
                    f"value {value!r} not in {param_def.valid_values}"
                )

        return True, ""

    @staticmethod
    def _check_format(value: Any, fmt: str) -> tuple[bool, str]:
        """Validate value against a format string."""
        s = str(value)

        if fmt == "YYYY-MM-DD":
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", s):
                return False, f"expected YYYY-MM-DD format, got '{s}'"
        elif fmt == "HH:MM":
            if not re.match(r"^\d{2}:\d{2}$", s):
                return False, f"expected HH:MM format, got '{s}'"
            # Validate hour/minute ranges
            parts = s.split(":")
            hour, minute = int(parts[0]), int(parts[1])
            if hour > 23 or minute > 59:
                return False, f"invalid time '{s}' (hour 0-23, minute 0-59)"
        elif fmt == "HH:MM:SS":
            if not re.match(r"^\d{2}:\d{2}:\d{2}$", s):
                return False, f"expected HH:MM:SS format, got '{s}'"

        return True, ""

    @staticmethod
    def _load_default_rubric() -> JudgeRubric:
        rubric_path = _RUBRICS_DIR / "tool_parameter_accuracy.yaml"
        if rubric_path.exists():
            return JudgeRubric.from_yaml(rubric_path)
        return JudgeRubric(
            name="tool_parameter_accuracy",
            prompt_template=(
                "Evaluate whether the agent extracted correct parameter "
                "values from the user's input.\n\n"
                "User input: {{ user_input }}\n"
                "Agent response: {{ agent_response }}\n"
                "Tool calls: {{ tool_calls }}\n\n"
                "Were the parameters extracted correctly?"
            ),
            output_labels=["Yes", "No"],
            score_mapping={"Yes": 1.0, "No": 0.0},
        )
