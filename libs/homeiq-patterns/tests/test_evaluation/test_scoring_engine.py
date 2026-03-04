"""
Tests for E1.S5: ScoringEngine + Summary Matrix
"""

import pytest
from homeiq_patterns.evaluation.base_evaluator import (
    OutcomeEvaluator,
    QualityEvaluator,
    SafetyEvaluator,
)
from homeiq_patterns.evaluation.models import (
    EvalLevel,
    EvaluationResult,
    SessionTrace,
    UserMessage,
)
from homeiq_patterns.evaluation.scoring_engine import ScoringEngine

# ---------------------------------------------------------------------------
# Test evaluators
# ---------------------------------------------------------------------------


class PassEvaluator(OutcomeEvaluator):
    name = "goal_success"

    async def evaluate(self, _session: SessionTrace) -> EvaluationResult:
        return self._result(score=1.0, label="Yes", explanation="Goal met")


class FailEvaluator(QualityEvaluator):
    name = "correctness"

    async def evaluate(self, _session: SessionTrace) -> EvaluationResult:
        return self._result(score=0.3, label="Incorrect", explanation="Fabricated data")


class SafeEvaluator(SafetyEvaluator):
    name = "harmfulness"

    async def evaluate(self, _session: SessionTrace) -> EvaluationResult:
        return self._result(score=1.0, label="Not Harmful", passed=True)


class ErrorEvaluator(QualityEvaluator):
    name = "broken_eval"

    async def evaluate(self, _session: SessionTrace) -> EvaluationResult:
        raise RuntimeError("Evaluator crashed")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def session():
    return SessionTrace(
        agent_name="test-agent",
        user_messages=[UserMessage(content="test")],
    )


@pytest.fixture
def evaluators():
    return [PassEvaluator(), FailEvaluator(), SafeEvaluator()]


# ---------------------------------------------------------------------------
# Tests: Single session scoring
# ---------------------------------------------------------------------------


class TestScoreSingle:
    @pytest.mark.asyncio
    async def test_produces_report(self, session, evaluators):
        engine = ScoringEngine()
        report = await engine.score(session, evaluators)
        assert report.session_id == session.session_id
        assert report.agent_name == "test-agent"
        assert len(report.results) == 3

    @pytest.mark.asyncio
    async def test_builds_summary_matrix(self, session, evaluators):
        engine = ScoringEngine()
        report = await engine.score(session, evaluators)
        matrix = report.summary_matrix

        assert EvalLevel.OUTCOME in matrix.levels
        assert EvalLevel.QUALITY in matrix.levels
        assert EvalLevel.SAFETY in matrix.levels

        outcome = matrix.levels[EvalLevel.OUTCOME]
        assert outcome.metrics["goal_success"].score == 1.0
        assert outcome.metrics["goal_success"].passed is True

        quality = matrix.levels[EvalLevel.QUALITY]
        assert quality.metrics["correctness"].score == 0.3
        assert quality.metrics["correctness"].passed is False

    @pytest.mark.asyncio
    async def test_handles_evaluator_exception(self, session):
        engine = ScoringEngine()
        report = await engine.score(session, [ErrorEvaluator()])
        assert len(report.results) == 1
        assert report.results[0].score == 0.0
        assert report.results[0].label == "ERROR"
        assert report.results[0].passed is False

    @pytest.mark.asyncio
    async def test_report_to_markdown(self, session, evaluators):
        engine = ScoringEngine()
        report = await engine.score(session, evaluators)
        md = report.to_markdown()
        assert "test-agent" in md
        assert "goal_success" in md

    @pytest.mark.asyncio
    async def test_report_to_dict(self, session, evaluators):
        engine = ScoringEngine()
        report = await engine.score(session, evaluators)
        d = report.to_dict()
        assert d["agent_name"] == "test-agent"
        assert len(d["results"]) == 3


# ---------------------------------------------------------------------------
# Tests: Batch scoring
# ---------------------------------------------------------------------------


class TestScoreBatch:
    @pytest.mark.asyncio
    async def test_batch_report(self):
        sessions = [
            SessionTrace(agent_name="test-agent", user_messages=[UserMessage(content="s1")]),
            SessionTrace(agent_name="test-agent", user_messages=[UserMessage(content="s2")]),
        ]
        engine = ScoringEngine()
        batch = await engine.score_batch(sessions, [PassEvaluator(), SafeEvaluator()])
        assert batch.sessions_evaluated == 2
        assert batch.total_evaluations == 4
        assert len(batch.reports) == 2

    @pytest.mark.asyncio
    async def test_aggregate_scores(self):
        sessions = [
            SessionTrace(agent_name="test"),
            SessionTrace(agent_name="test"),
        ]
        engine = ScoringEngine()
        batch = await engine.score_batch(sessions, [PassEvaluator()])
        assert batch.aggregate_scores["goal_success"] == 1.0

    @pytest.mark.asyncio
    async def test_threshold_alert_triggered(self):
        sessions = [SessionTrace(agent_name="test")]
        engine = ScoringEngine(thresholds={"correctness": 0.8})
        batch = await engine.score_batch(sessions, [FailEvaluator()])
        assert len(batch.alerts) == 1
        alert = batch.alerts[0]
        assert alert.metric == "correctness"
        assert alert.threshold == 0.8
        assert alert.actual == 0.3

    @pytest.mark.asyncio
    async def test_no_alert_when_above_threshold(self):
        sessions = [SessionTrace(agent_name="test")]
        engine = ScoringEngine(thresholds={"goal_success": 0.5})
        batch = await engine.score_batch(sessions, [PassEvaluator()])
        assert len(batch.alerts) == 0

    @pytest.mark.asyncio
    async def test_critical_priority_when_far_below(self):
        sessions = [SessionTrace(agent_name="test")]
        engine = ScoringEngine(thresholds={"correctness": 0.8})
        batch = await engine.score_batch(sessions, [FailEvaluator()])
        # 0.3 < 0.8 * 0.5 = 0.4, so it should be critical
        assert batch.alerts[0].priority == "critical"

    @pytest.mark.asyncio
    async def test_batch_to_markdown(self):
        sessions = [SessionTrace(agent_name="test")]
        engine = ScoringEngine(thresholds={"correctness": 0.8})
        batch = await engine.score_batch(sessions, [FailEvaluator()])
        md = batch.to_markdown()
        assert "correctness" in md
