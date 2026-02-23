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
    deterministic pre-screening and ``metadata_success_signals`` for
    pipeline-metadata-based deterministic scoring.

    When ``metadata_success_signals=True``, the evaluator checks
    ``session.metadata`` for pipeline outcome signals (e.g.
    ``pipeline_success``, ``yaml_valid``, ``execution_mode``) and
    returns a deterministic score before falling back to the LLM judge.
    This eliminates run-to-run variance for unambiguous outcomes.
    """

    name = "goal_success_rate"

    def __init__(
        self,
        llm_judge: LLMJudge | None = None,
        rubric: JudgeRubric | None = None,
        goal_patterns: list[str] | None = None,
        metadata_success_signals: bool = False,
    ):
        self._judge = llm_judge or LLMJudge()
        self._rubric = rubric or self._load_default_rubric()
        self._goal_patterns = goal_patterns or []
        self._use_metadata = metadata_success_signals

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

        # Deterministic pre-screen via pipeline metadata signals
        if self._use_metadata:
            match = self._check_metadata_signals(session)
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

    def _check_metadata_signals(self, session: SessionTrace) -> EvaluationResult | None:
        """
        Deterministic goal success using pipeline metadata.

        Checks session.metadata for concrete outcome signals so that
        unambiguous successes and failures are scored without LLM
        variance.  Returns None for ambiguous cases (falls through to
        LLM judge).
        """
        meta = session.metadata
        if not meta:
            return None

        execution_mode = meta.get("execution_mode", "")

        # Deploy mode: check deployment audit status
        if execution_mode == "deploy":
            audit = meta.get("deployment_audit", {})
            if isinstance(audit, dict) and audit.get("status") == "success":
                return self._result(
                    score=1.0,
                    label="Yes",
                    explanation="Deployment succeeded (deployment_audit.status=success)",
                )
            if isinstance(audit, dict) and audit.get("status"):
                return self._result(
                    score=0.5,
                    label="Partial",
                    explanation=f"Deployment status: {audit['status']}",
                )

        # Preview mode: check pipeline success + YAML validity
        if execution_mode == "preview":
            pipeline_success = meta.get("pipeline_success", False)
            yaml_valid = meta.get("yaml_valid", False)
            pipeline_score = meta.get("pipeline_score", 0)

            if pipeline_success and yaml_valid:
                return self._result(
                    score=1.0,
                    label="Yes",
                    explanation=(
                        f"Pipeline succeeded in preview mode "
                        f"(score={pipeline_score}, yaml_valid=True)"
                    ),
                )
            if pipeline_success and not yaml_valid and pipeline_score >= 50:
                # Pipeline ran but YAML validation didn't pass — partial
                return self._result(
                    score=0.5,
                    label="Partial",
                    explanation=(
                        f"Pipeline succeeded but YAML invalid "
                        f"(score={pipeline_score})"
                    ),
                )

        # Ambiguous — fall through to LLM judge
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
