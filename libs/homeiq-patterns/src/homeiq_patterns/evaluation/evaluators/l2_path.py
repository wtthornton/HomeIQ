"""
L2 Path Evaluators — Tool selection and sequence validation.

Evaluators:
  - ToolSelectionAccuracyEvaluator: Did the agent pick the correct tool?
  - ToolSequenceValidatorEvaluator: Did the agent call tools in the right order?
"""

from __future__ import annotations

from pathlib import Path

from ..base_evaluator import PathEvaluator
from ..config import AgentEvalConfig, PathRule
from ..llm_judge import JudgeRubric, LLMJudge
from ..models import EvaluationResult, SessionTrace

_RUBRICS_DIR = Path(__file__).resolve().parent.parent / "rubrics"


class ToolSelectionAccuracyEvaluator(PathEvaluator):
    """
    L2 — Evaluates whether the agent selected the correct tool for each
    user intent.

    Rule-based mode: uses ``tools`` and ``paths`` from ``AgentEvalConfig``
    to match intent → expected tool.  LLM-fallback mode: when intent-to-tool
    mapping is ambiguous, uses ``LLMJudge`` to assess.

    Score: fraction of tool calls that selected a valid/known tool.
    """

    name = "tool_selection_accuracy"

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

        known_tools = {t.name for t in self._config.tools}

        # If no tools defined in config, fall through to LLM judge
        if not known_tools:
            result = await self._judge.judge(session, self._rubric)
            return self._result(
                score=result.score,
                label=result.label,
                explanation=result.explanation,
            )

        correct = 0
        total = len(session.tool_calls)
        details: list[str] = []

        for tc in session.tool_calls:
            if tc.tool_name in known_tools:
                correct += 1
            else:
                details.append(
                    f"Unknown tool '{tc.tool_name}' "
                    f"(expected one of: {sorted(known_tools)})"
                )

        score = correct / total if total > 0 else 1.0
        label = "Yes" if score == 1.0 else "No"
        explanation = (
            f"{correct}/{total} tool calls used known tools."
            + (f" Issues: {'; '.join(details)}" if details else "")
        )

        return self._result(score=score, label=label, explanation=explanation)

    @staticmethod
    def _load_default_rubric() -> JudgeRubric:
        rubric_path = _RUBRICS_DIR / "tool_selection_accuracy.yaml"
        if rubric_path.exists():
            return JudgeRubric.from_yaml(rubric_path)
        return JudgeRubric(
            name="tool_selection_accuracy",
            prompt_template=(
                "Evaluate whether the agent selected the correct tool for "
                "the user's request.\n\n"
                "User input: {{ user_input }}\n"
                "Agent response: {{ agent_response }}\n"
                "Tool calls: {{ tool_calls }}\n\n"
                "Did the agent use the correct tool?"
            ),
            output_labels=["Yes", "No"],
            score_mapping={"Yes": 1.0, "No": 0.0},
        )


class ToolSequenceValidatorEvaluator(PathEvaluator):
    """
    L2 — Validates that tools were called in the mandatory sequence
    defined in the agent's config.

    Purely rule-based for sequence checking.  LLM-judged only when
    natural-language exception conditions need evaluation.

    For each configured path rule, outputs whether the sequence was
    followed or violated.
    """

    name = "tool_sequence_validator"

    def __init__(
        self,
        config: AgentEvalConfig | None = None,
        llm_judge: LLMJudge | None = None,
    ):
        self._config = config or AgentEvalConfig()
        self._judge = llm_judge or LLMJudge()

    async def evaluate(self, session: SessionTrace) -> EvaluationResult:
        path_rules = self._config.paths
        if not path_rules:
            return self._result(
                score=1.0,
                label="Correct Sequence",
                explanation="No path rules configured",
            )

        if not session.tool_calls:
            # No tool calls but path rules exist — check if any paths
            # require mandatory tools
            required_tools = set()
            for rule in path_rules:
                required_tools.update(rule.sequence)
            if required_tools:
                return self._result(
                    score=0.0,
                    label="Wrong Sequence",
                    explanation=(
                        "No tool calls made but path rules require: "
                        f"{sorted(required_tools)}"
                    ),
                )
            return self._result(
                score=1.0,
                label="Correct Sequence",
                explanation="No tool calls and no mandatory sequences",
            )

        actual_sequence = [tc.tool_name for tc in session.tool_calls]
        passed_rules = 0
        total_rules = len(path_rules)
        details: list[str] = []

        for rule in path_rules:
            rule_passed = await self._check_path_rule(
                rule, actual_sequence, session
            )
            if rule_passed:
                passed_rules += 1
            else:
                details.append(f"Rule '{rule.name}' violated")

        score = passed_rules / total_rules if total_rules > 0 else 1.0
        label = "Correct Sequence" if score == 1.0 else "Wrong Sequence"
        explanation = (
            f"{passed_rules}/{total_rules} path rules satisfied."
            + (f" Issues: {'; '.join(details)}" if details else "")
        )

        return self._result(score=score, label=label, explanation=explanation)

    async def _check_path_rule(
        self,
        rule: PathRule,
        actual_sequence: list[str],
        session: SessionTrace,
    ) -> bool:
        """Check whether the actual tool call sequence satisfies a path rule.

        A rule passes when all tools in ``rule.sequence`` appear in the
        actual sequence in order (not necessarily contiguous).  Missing
        or out-of-order tools cause a failure unless an exception applies.
        """
        expected = rule.sequence
        if not expected:
            return True

        # Check subsequence: expected tools appear in order in actual
        exp_idx = 0
        for tool_name in actual_sequence:
            if exp_idx < len(expected) and tool_name == expected[exp_idx]:
                exp_idx += 1
        sequence_valid = exp_idx == len(expected)

        if sequence_valid:
            return True

        # Sequence violated — check if any exception applies
        if rule.exceptions:
            exception_applies = await self._check_exceptions(
                rule.exceptions, session
            )
            return exception_applies

        return False

    async def _check_exceptions(
        self,
        exceptions: list[str],
        session: SessionTrace,
    ) -> bool:
        """Evaluate whether any natural-language exception condition
        applies to the current session.

        Story 4.3: Checks structured metadata first for deterministic
        results.  Falls back to LLM judge only for unrecognized
        exception descriptions.
        """
        if not exceptions:
            return False

        mode = session.metadata.get("execution_mode", "deploy")

        # Deterministic exception checks based on metadata
        for exc_text in exceptions:
            exc_lower = exc_text.lower()
            if (
                ("dry-run" in exc_lower or "preview" in exc_lower)
                and mode in ("preview", "dry_run")
            ):
                return True
            if "external source" in exc_lower and mode == "external":
                return True
            if "manual" in exc_lower and session.metadata.get(
                "user_requested"
            ):
                return True

        # Fall back to LLM judge for unrecognized exceptions
        user_input = " ".join(m.content for m in session.user_messages)
        exception_list = "\n".join(f"- {exc}" for exc in exceptions)

        rubric = JudgeRubric(
            name="exception_check",
            prompt_template=(
                "A tool sequence rule was violated. Check if any of the "
                "following exceptions apply to justify the violation.\n\n"
                "User input: {{ user_input }}\n"
                "Agent response: {{ agent_response }}\n"
                "Tool calls: {{ tool_calls }}\n\n"
                f"Exceptions:\n{exception_list}\n\n"
                "Does any exception apply?"
            ),
            output_labels=["Yes", "No"],
            score_mapping={"Yes": 1.0, "No": 0.0},
        )

        result = await self._judge.judge(session, rubric)
        return result.score >= 0.5
