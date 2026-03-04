"""
Tests for E1.S3: BaseEvaluator + Level Classes (shared/patterns/evaluation/base_evaluator.py)
"""

import pytest
from homeiq_patterns.evaluation.base_evaluator import (
    BaseEvaluator,
    DetailsEvaluator,
    OutcomeEvaluator,
    PathEvaluator,
    QualityEvaluator,
    SafetyEvaluator,
)
from homeiq_patterns.evaluation.models import (
    EvalLevel,
    EvalScope,
    EvaluationResult,
    SessionTrace,
    UserMessage,
)

# ---------------------------------------------------------------------------
# Concrete test implementations
# ---------------------------------------------------------------------------


class AlwaysPassOutcomeEvaluator(OutcomeEvaluator):
    name = "always_pass_outcome"

    async def evaluate(self, _session: SessionTrace) -> EvaluationResult:
        return self._result(score=1.0, label="Yes", explanation="Always passes")


class AlwaysFailPathEvaluator(PathEvaluator):
    name = "always_fail_path"

    async def evaluate(self, _session: SessionTrace) -> EvaluationResult:
        return self._result(score=0.0, label="Wrong", explanation="Always fails")


class SimpleDetailsEvaluator(DetailsEvaluator):
    name = "simple_details"

    async def evaluate(self, session: SessionTrace) -> EvaluationResult:
        has_tools = len(session.tool_calls) > 0
        return self._result(
            score=1.0 if has_tools else 0.0,
            label="Has tools" if has_tools else "No tools",
        )


class SimpleQualityEvaluator(QualityEvaluator):
    name = "simple_quality"

    async def evaluate(self, _session: SessionTrace) -> EvaluationResult:
        return self._result(score=0.75, label="Good")


class SimpleSafetyEvaluator(SafetyEvaluator):
    name = "simple_safety"

    async def evaluate(self, _session: SessionTrace) -> EvaluationResult:
        return self._result(score=1.0, label="Safe", passed=True)


# ---------------------------------------------------------------------------
# Tests: Level + Scope assignments
# ---------------------------------------------------------------------------


class TestLevelAssignment:
    def test_outcome_evaluator_level(self):
        e = AlwaysPassOutcomeEvaluator()
        assert e.level == EvalLevel.OUTCOME

    def test_path_evaluator_level(self):
        e = AlwaysFailPathEvaluator()
        assert e.level == EvalLevel.PATH

    def test_details_evaluator_level(self):
        e = SimpleDetailsEvaluator()
        assert e.level == EvalLevel.DETAILS

    def test_quality_evaluator_level(self):
        e = SimpleQualityEvaluator()
        assert e.level == EvalLevel.QUALITY

    def test_safety_evaluator_level(self):
        e = SimpleSafetyEvaluator()
        assert e.level == EvalLevel.SAFETY


class TestScopeAssignment:
    def test_outcome_scope_session(self):
        assert AlwaysPassOutcomeEvaluator().scope == EvalScope.SESSION

    def test_path_scope_session(self):
        assert AlwaysFailPathEvaluator().scope == EvalScope.SESSION

    def test_details_scope_tool_call(self):
        assert SimpleDetailsEvaluator().scope == EvalScope.TOOL_CALL

    def test_quality_scope_response(self):
        assert SimpleQualityEvaluator().scope == EvalScope.RESPONSE

    def test_safety_scope_response(self):
        assert SimpleSafetyEvaluator().scope == EvalScope.RESPONSE


# ---------------------------------------------------------------------------
# Tests: evaluate() method
# ---------------------------------------------------------------------------


class TestEvaluate:
    @pytest.fixture
    def session(self):
        return SessionTrace(
            agent_name="test-agent",
            user_messages=[UserMessage(content="test message")],
        )

    @pytest.mark.asyncio
    async def test_outcome_pass(self, session):
        evaluator = AlwaysPassOutcomeEvaluator()
        result = await evaluator.evaluate(session)
        assert result.score == 1.0
        assert result.passed is True
        assert result.evaluator_name == "always_pass_outcome"
        assert result.level == EvalLevel.OUTCOME

    @pytest.mark.asyncio
    async def test_path_fail(self, session):
        evaluator = AlwaysFailPathEvaluator()
        result = await evaluator.evaluate(session)
        assert result.score == 0.0
        assert result.passed is False
        assert result.label == "Wrong"

    @pytest.mark.asyncio
    async def test_quality_partial(self, session):
        evaluator = SimpleQualityEvaluator()
        result = await evaluator.evaluate(session)
        assert result.score == 0.75
        assert result.passed is True  # 0.75 >= 0.5

    @pytest.mark.asyncio
    async def test_safety_explicit_passed(self, session):
        evaluator = SimpleSafetyEvaluator()
        result = await evaluator.evaluate(session)
        assert result.passed is True


# ---------------------------------------------------------------------------
# Tests: _result() helper
# ---------------------------------------------------------------------------


class TestResultHelper:
    def test_auto_passed_true(self):
        e = AlwaysPassOutcomeEvaluator()
        r = e._result(score=0.6)
        assert r.passed is True  # 0.6 >= 0.5

    def test_auto_passed_false(self):
        e = AlwaysPassOutcomeEvaluator()
        r = e._result(score=0.3)
        assert r.passed is False  # 0.3 < 0.5

    def test_explicit_passed_override(self):
        e = AlwaysPassOutcomeEvaluator()
        r = e._result(score=0.0, passed=True)
        assert r.passed is True  # explicit override

    def test_result_includes_evaluator_name(self):
        e = SimpleQualityEvaluator()
        r = e._result(score=0.5)
        assert r.evaluator_name == "simple_quality"

    def test_result_includes_level(self):
        e = SimpleSafetyEvaluator()
        r = e._result(score=1.0)
        assert r.level == EvalLevel.SAFETY


# ---------------------------------------------------------------------------
# Tests: abstract class enforcement
# ---------------------------------------------------------------------------


class TestAbstractEnforcement:
    def test_cannot_instantiate_base_evaluator(self):
        with pytest.raises(TypeError):
            BaseEvaluator()  # type: ignore

    def test_cannot_instantiate_outcome_without_evaluate(self):
        # OutcomeEvaluator itself is still abstract (no evaluate)
        with pytest.raises(TypeError):
            OutcomeEvaluator()  # type: ignore
