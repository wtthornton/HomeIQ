"""
L1 Outcome Evaluators — Goal achievement at session level.

Evaluators:
  - GoalSuccessRateEvaluator: Did the user achieve their goal?
"""

from __future__ import annotations

from pathlib import Path

from ..base_evaluator import OutcomeEvaluator
from ..llm_judge import JudgeRubric, LLMJudge
from ..models import EvaluationResult, SessionTrace

_RUBRICS_DIR = Path(__file__).resolve().parent.parent / "rubrics"


class GoalSuccessRateEvaluator(OutcomeEvaluator):
    """
    L1 — Evaluates whether the user achieved their goal in the session.

    Uses LLM-as-Judge with a rubric that considers user intent, agent
    actions, and final state.  Supports optional ``goal_patterns`` for
    deterministic pre-screening.
    """

    name = "goal_success_rate"

    def __init__(
        self,
        llm_judge: LLMJudge | None = None,
        rubric: JudgeRubric | None = None,
        goal_patterns: list[str] | None = None,
    ):
        self._judge = llm_judge or LLMJudge()
        self._rubric = rubric or self._load_default_rubric()
        self._goal_patterns = goal_patterns or []

    async def evaluate(self, session: SessionTrace) -> EvaluationResult:
        # Check for error sessions — score as failure
        if self._is_error_session(session):
            return self._result(
                score=0.0,
                label="No",
                explanation="Session ended in error",
            )

        # Deterministic pre-screen via goal patterns
        if self._goal_patterns:
            match = self._check_goal_patterns(session)
            if match is not None:
                return match

        # LLM judge evaluation
        result = await self._judge.judge(session, self._rubric)
        return self._result(
            score=result.score,
            label=result.label,
            explanation=result.explanation,
        )

    def _is_error_session(self, session: SessionTrace) -> bool:
        """Check if session ended in an error state."""
        if session.metadata.get("error"):
            return True
        # Check for error tool results
        for tc in session.tool_calls:
            if isinstance(tc.result, dict) and tc.result.get("error"):
                return True
        return False

    def _check_goal_patterns(self, session: SessionTrace) -> EvaluationResult | None:
        """Try to match goal patterns deterministically before using LLM."""
        if not session.agent_responses:
            return None

        last_response = session.agent_responses[-1].content.lower()
        for pattern in self._goal_patterns:
            if pattern.lower() in last_response:
                return self._result(
                    score=1.0,
                    label="Yes",
                    explanation=f"Goal pattern matched: {pattern}",
                )
        return None

    @staticmethod
    def _load_default_rubric() -> JudgeRubric:
        rubric_path = _RUBRICS_DIR / "goal_success_rate.yaml"
        if rubric_path.exists():
            return JudgeRubric.from_yaml(rubric_path)
        # Fallback inline rubric
        return JudgeRubric(
            name="goal_success_rate",
            prompt_template=(
                "Evaluate whether the user achieved their goal in this conversation.\n\n"
                "User input: {{ user_input }}\n"
                "Agent response: {{ agent_response }}\n"
                "Tool calls: {{ tool_calls }}\n\n"
                "Did the user achieve their goal?"
            ),
            output_labels=["Yes", "Partial", "No"],
            score_mapping={"Yes": 1.0, "Partial": 0.5, "No": 0.0},
        )
