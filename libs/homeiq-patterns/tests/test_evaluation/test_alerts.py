"""
Tests for E4.S6: Alert System for Threshold Violations

Tests the AlertEngine lifecycle: creation, deduplication, acknowledgement,
auto-resolve, and priority calculation.
"""

import pytest

from homeiq_patterns.evaluation.alerts import AlertEngine
from homeiq_patterns.evaluation.config import AgentEvalConfig
from homeiq_patterns.evaluation.models import (
    BatchReport,
    EvalAlert,
    EvalLevel,
    EvaluationReport,
    EvaluationResult,
)


def _make_config(
    agent_name: str = "test-agent",
    thresholds: dict | None = None,
) -> AgentEvalConfig:
    """Create a minimal config with thresholds."""
    return AgentEvalConfig(
        agent_name=agent_name,
        thresholds=thresholds or {"goal_success_rate": 0.85, "correctness": 0.90},
    )


def _make_report(
    agent_name: str = "test-agent",
    aggregate_scores: dict | None = None,
) -> BatchReport:
    """Create a minimal BatchReport with aggregate scores."""
    scores = aggregate_scores or {"goal_success_rate": 0.80, "correctness": 0.95}
    reports = [
        EvaluationReport(
            session_id="s1",
            agent_name=agent_name,
            results=[
                EvaluationResult(
                    evaluator_name="goal_success_rate",
                    level=EvalLevel.OUTCOME,
                    score=scores.get("goal_success_rate", 0.8),
                    passed=True,
                ),
                EvaluationResult(
                    evaluator_name="correctness",
                    level=EvalLevel.QUALITY,
                    score=scores.get("correctness", 0.95),
                    passed=True,
                ),
            ],
        )
    ]
    return BatchReport(
        agent_name=agent_name,
        sessions_evaluated=1,
        total_evaluations=2,
        reports=reports,
        aggregate_scores=scores,
    )


# ---------------------------------------------------------------------------
# Alert creation tests
# ---------------------------------------------------------------------------


class TestAlertCreation:
    """Test alert creation from threshold violations."""

    def test_creates_alert_for_violation(self):
        engine = AlertEngine()
        config = _make_config()
        report = _make_report(aggregate_scores={"goal_success_rate": 0.70, "correctness": 0.95})
        alerts = engine.check_report(report, config)
        assert len(alerts) == 1
        assert alerts[0].metric == "goal_success_rate"
        assert alerts[0].status == "active"

    def test_no_alerts_when_all_pass(self):
        engine = AlertEngine()
        config = _make_config()
        report = _make_report(aggregate_scores={"goal_success_rate": 0.90, "correctness": 0.95})
        alerts = engine.check_report(report, config)
        assert len(alerts) == 0

    def test_multiple_violations(self):
        engine = AlertEngine()
        config = _make_config()
        report = _make_report(aggregate_scores={"goal_success_rate": 0.70, "correctness": 0.80})
        alerts = engine.check_report(report, config)
        assert len(alerts) == 2
        metrics = {a.metric for a in alerts}
        assert "goal_success_rate" in metrics
        assert "correctness" in metrics

    def test_alert_has_correct_fields(self):
        engine = AlertEngine()
        config = _make_config()
        report = _make_report(aggregate_scores={"goal_success_rate": 0.70, "correctness": 0.95})
        alerts = engine.check_report(report, config)
        alert = alerts[0]
        assert alert.agent_name == "test-agent"
        assert alert.threshold == 0.85
        assert alert.actual_score == 0.70
        assert alert.alert_id  # UUID is set
        assert alert.created_at is not None


# ---------------------------------------------------------------------------
# Priority calculation tests
# ---------------------------------------------------------------------------


class TestPriorityCalculation:
    """Test alert priority (critical vs warning)."""

    def test_warning_priority(self):
        engine = AlertEngine()
        config = _make_config(thresholds={"correctness": 0.90})
        report = _make_report(aggregate_scores={"correctness": 0.60})
        alerts = engine.check_report(report, config)
        assert alerts[0].priority == "warning"

    def test_critical_priority_below_half(self):
        engine = AlertEngine()
        config = _make_config(thresholds={"correctness": 0.90})
        report = _make_report(aggregate_scores={"correctness": 0.40})
        alerts = engine.check_report(report, config)
        assert alerts[0].priority == "critical"

    def test_critical_at_zero(self):
        engine = AlertEngine()
        config = _make_config(thresholds={"correctness": 0.90})
        report = _make_report(aggregate_scores={"correctness": 0.0})
        alerts = engine.check_report(report, config)
        assert alerts[0].priority == "critical"


# ---------------------------------------------------------------------------
# Deduplication tests
# ---------------------------------------------------------------------------


class TestDeduplication:
    """Test that repeated violations don't create duplicate alerts."""

    def test_same_violation_not_duplicated(self):
        engine = AlertEngine()
        config = _make_config()
        report = _make_report(aggregate_scores={"goal_success_rate": 0.70, "correctness": 0.95})

        # First check creates alert
        alerts1 = engine.check_report(report, config)
        assert len(alerts1) == 1
        alert_id = alerts1[0].alert_id

        # Second check returns same alert (updated, not duplicated)
        alerts2 = engine.check_report(report, config)
        assert len(alerts2) == 1
        assert alerts2[0].alert_id == alert_id
        assert engine.alert_count == 1

    def test_different_metrics_get_different_alerts(self):
        engine = AlertEngine()
        config = _make_config()
        report = _make_report(aggregate_scores={"goal_success_rate": 0.70, "correctness": 0.80})
        engine.check_report(report, config)
        assert engine.alert_count == 2

    def test_different_agents_get_different_alerts(self):
        engine = AlertEngine()
        config_a = _make_config(agent_name="agent-a")
        config_b = _make_config(agent_name="agent-b")
        report_a = _make_report(agent_name="agent-a", aggregate_scores={"goal_success_rate": 0.70, "correctness": 0.95})
        report_b = _make_report(agent_name="agent-b", aggregate_scores={"goal_success_rate": 0.70, "correctness": 0.95})

        engine.check_report(report_a, config_a)
        engine.check_report(report_b, config_b)
        assert engine.alert_count == 2


# ---------------------------------------------------------------------------
# Lifecycle tests
# ---------------------------------------------------------------------------


class TestAlertLifecycle:
    """Test alert lifecycle transitions."""

    def test_acknowledge_alert(self):
        engine = AlertEngine()
        config = _make_config()
        report = _make_report(aggregate_scores={"goal_success_rate": 0.70, "correctness": 0.95})
        alerts = engine.check_report(report, config)
        alert_id = alerts[0].alert_id

        result = engine.acknowledge(alert_id, by="operator", note="Looking into it")
        assert result is not None
        assert result.status == "acknowledged"
        assert result.acknowledged_by == "operator"
        assert result.note == "Looking into it"

    def test_acknowledge_nonexistent_returns_none(self):
        engine = AlertEngine()
        assert engine.acknowledge("nonexistent-id", by="op") is None

    def test_auto_resolve_on_recovery(self):
        engine = AlertEngine()
        config = _make_config()

        # First run: violation
        bad_report = _make_report(aggregate_scores={"goal_success_rate": 0.70, "correctness": 0.95})
        engine.check_report(bad_report, config)
        assert len(engine.get_active_alerts()) == 1

        # Second run: score recovered
        good_report = _make_report(aggregate_scores={"goal_success_rate": 0.90, "correctness": 0.95})
        engine.check_report(good_report, config)
        assert len(engine.get_active_alerts()) == 0

    def test_manual_resolve(self):
        engine = AlertEngine()
        config = _make_config()
        report = _make_report(aggregate_scores={"goal_success_rate": 0.70, "correctness": 0.95})
        alerts = engine.check_report(report, config)

        result = engine.resolve(alerts[0].alert_id)
        assert result is not None
        assert result.status == "resolved"

    def test_cannot_acknowledge_resolved(self):
        engine = AlertEngine()
        config = _make_config()
        report = _make_report(aggregate_scores={"goal_success_rate": 0.70, "correctness": 0.95})
        alerts = engine.check_report(report, config)
        alert_id = alerts[0].alert_id

        engine.resolve(alert_id)
        result = engine.acknowledge(alert_id, by="op")
        assert result is not None
        assert result.status == "resolved"  # Still resolved

    def test_resolved_violation_creates_new_alert(self):
        engine = AlertEngine()
        config = _make_config()

        # Violation → resolve
        bad_report = _make_report(aggregate_scores={"goal_success_rate": 0.70, "correctness": 0.95})
        alerts1 = engine.check_report(bad_report, config)
        engine.resolve(alerts1[0].alert_id)

        # Same violation again → new alert
        alerts2 = engine.check_report(bad_report, config)
        assert len(alerts2) == 1
        assert alerts2[0].alert_id != alerts1[0].alert_id


# ---------------------------------------------------------------------------
# Query tests
# ---------------------------------------------------------------------------


class TestAlertQueries:
    """Test alert query methods."""

    def test_get_active_alerts_filters_resolved(self):
        engine = AlertEngine()
        config = _make_config()
        report = _make_report(aggregate_scores={"goal_success_rate": 0.70, "correctness": 0.80})
        alerts = engine.check_report(report, config)

        engine.resolve(alerts[0].alert_id)
        active = engine.get_active_alerts()
        assert len(active) == 1

    def test_get_active_alerts_by_agent(self):
        engine = AlertEngine()
        config_a = _make_config(agent_name="agent-a")
        config_b = _make_config(agent_name="agent-b")
        engine.check_report(
            _make_report(agent_name="agent-a", aggregate_scores={"goal_success_rate": 0.70, "correctness": 0.95}),
            config_a,
        )
        engine.check_report(
            _make_report(agent_name="agent-b", aggregate_scores={"goal_success_rate": 0.70, "correctness": 0.95}),
            config_b,
        )

        assert len(engine.get_active_alerts("agent-a")) == 1
        assert len(engine.get_active_alerts("agent-b")) == 1
        assert len(engine.get_active_alerts()) == 2

    def test_get_all_alerts_includes_resolved(self):
        engine = AlertEngine()
        config = _make_config()
        report = _make_report(aggregate_scores={"goal_success_rate": 0.70, "correctness": 0.80})
        alerts = engine.check_report(report, config)
        engine.resolve(alerts[0].alert_id)

        all_alerts = engine.get_all_alerts()
        assert len(all_alerts) == 2
        statuses = {a.status for a in all_alerts}
        assert "resolved" in statuses
        assert "active" in statuses

    def test_clear_resolved(self):
        engine = AlertEngine()
        config = _make_config()
        report = _make_report(aggregate_scores={"goal_success_rate": 0.70, "correctness": 0.80})
        alerts = engine.check_report(report, config)
        engine.resolve(alerts[0].alert_id)

        removed = engine.clear_resolved()
        assert removed == 1
        assert engine.alert_count == 1
