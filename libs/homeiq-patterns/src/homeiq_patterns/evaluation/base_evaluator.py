"""
Agent Evaluation Framework — Base Evaluator Classes

Abstract base classes for the 5-level Evaluation Pyramid:
  L1 Outcome  — session-level goal achievement
  L2 Path     — session-level tool selection & sequence
  L3 Details  — per-tool-call parameter accuracy
  L4 Quality  — per-response quality (correctness, faithfulness, …)
  L5 Safety   — per-response safety compliance
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .models import (
    EvalLevel,
    EvalScope,
    EvaluationResult,
    SessionTrace,
)


class BaseEvaluator(ABC):
    """
    Abstract base class for all evaluators.

    Subclasses must implement ``evaluate()`` and set ``level``, ``scope``,
    and ``name``.
    """

    level: EvalLevel
    scope: EvalScope
    name: str

    @abstractmethod
    async def evaluate(self, session: SessionTrace) -> EvaluationResult:
        """Run the evaluator on a session trace and return a result."""
        ...

    def _result(
        self,
        score: float,
        label: str = "",
        explanation: str = "",
        passed: bool | None = None,
    ) -> EvaluationResult:
        """Convenience builder for creating an EvaluationResult."""
        if passed is None:
            passed = score >= 0.5
        return EvaluationResult(
            evaluator_name=self.name,
            level=self.level,
            score=score,
            label=label,
            explanation=explanation,
            passed=passed,
        )


# ---------------------------------------------------------------------------
# Level-specific abstract classes
# ---------------------------------------------------------------------------


class OutcomeEvaluator(BaseEvaluator):
    """L1 — evaluates whether the user achieved their goal (session scope)."""

    level = EvalLevel.OUTCOME
    scope = EvalScope.SESSION


class PathEvaluator(BaseEvaluator):
    """L2 — evaluates tool selection and call sequence (session scope)."""

    level = EvalLevel.PATH
    scope = EvalScope.SESSION


class DetailsEvaluator(BaseEvaluator):
    """L3 — evaluates parameter extraction accuracy (per tool call)."""

    level = EvalLevel.DETAILS
    scope = EvalScope.TOOL_CALL


class QualityEvaluator(BaseEvaluator):
    """L4 — evaluates response quality (per response)."""

    level = EvalLevel.QUALITY
    scope = EvalScope.RESPONSE


class SafetyEvaluator(BaseEvaluator):
    """L5 — evaluates safety compliance (per response)."""

    level = EvalLevel.SAFETY
    scope = EvalScope.RESPONSE
