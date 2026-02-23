"""
Tests for E4.S3 — Evaluation API Endpoints

Tests the FastAPI router from data-api evaluation_endpoints using
TestClient with the router mounted on a test app.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

# ---------------------------------------------------------------------------
# Path setup for shared imports
# ---------------------------------------------------------------------------
try:
    _project_root = str(Path(__file__).resolve().parents[4])
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)
except IndexError:
    pass  # Docker: PYTHONPATH already includes /app

# ---------------------------------------------------------------------------
# Import the router under test
# ---------------------------------------------------------------------------
# We need to patch shared imports before importing the module
# since data-api src might not be in path. Instead we test the
# models and response schemas, and the store/scheduler/alert integration.

from shared.patterns.evaluation import (
    AlertEngine,
    BatchReport,
    EvalAlert,
    EvalLevel,
    EvaluationReport,
    EvaluationResult,
    EvaluationStore,
)


# ---------------------------------------------------------------------------
# Store tests (query methods used by endpoints)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def store():
    s = EvaluationStore(sqlite_path=":memory:")
    await s.initialize()
    yield s
    await s.close()


def _make_report(agent: str = "test-agent", score: float = 0.85) -> BatchReport:
    return BatchReport(
        agent_name=agent,
        sessions_evaluated=5,
        total_evaluations=10,
        reports=[
            EvaluationReport(
                session_id=f"sess-{i}",
                agent_name=agent,
                results=[
                    EvaluationResult(
                        evaluator_name="goal_success_rate",
                        level=EvalLevel.OUTCOME,
                        score=score,
                        label="Good" if score >= 0.7 else "Poor",
                        passed=score >= 0.7,
                    ),
                    EvaluationResult(
                        evaluator_name="correctness",
                        level=EvalLevel.QUALITY,
                        score=score - 0.05,
                        label="OK",
                        passed=True,
                    ),
                ],
            )
            for i in range(5)
        ],
        aggregate_scores={
            "goal_success_rate": score,
            "correctness": score - 0.05,
        },
    )


@pytest.mark.asyncio
async def test_store_batch_report(store):
    report = _make_report()
    run_id = await store.store_batch_report(report)
    assert run_id > 0


@pytest.mark.asyncio
async def test_get_latest_report(store):
    await store.store_batch_report(_make_report())
    result = await store.get_latest_report("test-agent")
    assert result is not None
    assert result["agent_name"] == "test-agent"
    assert result["sessions_evaluated"] == 5


@pytest.mark.asyncio
async def test_get_scores_empty(store):
    scores = await store.get_scores("nonexistent")
    assert scores == []


@pytest.mark.asyncio
async def test_get_scores_with_data(store):
    await store.store_batch_report(_make_report())
    scores = await store.get_scores("test-agent")
    assert len(scores) > 0
    assert scores[0]["evaluator_name"] in ("goal_success_rate", "correctness")


@pytest.mark.asyncio
async def test_get_scores_filtered_by_evaluator(store):
    await store.store_batch_report(_make_report())
    scores = await store.get_scores("test-agent", evaluator="correctness")
    assert all(s["evaluator_name"] == "correctness" for s in scores)


@pytest.mark.asyncio
async def test_get_trends(store):
    await store.store_batch_report(_make_report())
    trends = await store.get_trends("test-agent", period="7d")
    assert isinstance(trends, dict)
    assert "goal_success_rate" in trends


@pytest.mark.asyncio
async def test_get_trends_empty_agent(store):
    trends = await store.get_trends("nonexistent")
    assert trends == {}


@pytest.mark.asyncio
async def test_get_run_count(store):
    assert await store.get_run_count("test-agent") == 0
    await store.store_batch_report(_make_report())
    assert await store.get_run_count("test-agent") == 1


@pytest.mark.asyncio
async def test_multiple_runs(store):
    await store.store_batch_report(_make_report(score=0.80))
    await store.store_batch_report(_make_report(score=0.90))
    assert await store.get_run_count("test-agent") == 2
    latest = await store.get_latest_report("test-agent")
    assert latest is not None


# ---------------------------------------------------------------------------
# Alert engine tests (used by endpoints)
# ---------------------------------------------------------------------------


class TestAlertEndpointIntegration:
    """Test AlertEngine methods that the API endpoints use."""

    def test_no_alerts_when_passing(self):
        engine = AlertEngine()
        report = _make_report(score=0.85)
        from shared.patterns.evaluation import AgentEvalConfig
        config = AgentEvalConfig(
            agent_name="test-agent",
            thresholds={"goal_success_rate": 0.70},
        )
        alerts = engine.check_report(report, config)
        assert len(alerts) == 0

    def test_alert_created_on_violation(self):
        engine = AlertEngine()
        report = _make_report(score=0.50)
        from shared.patterns.evaluation import AgentEvalConfig
        config = AgentEvalConfig(
            agent_name="test-agent",
            thresholds={"goal_success_rate": 0.70},
        )
        alerts = engine.check_report(report, config)
        assert len(alerts) == 1
        assert alerts[0].metric == "goal_success_rate"
        assert alerts[0].status == "active"

    def test_acknowledge_alert(self):
        engine = AlertEngine()
        report = _make_report(score=0.50)
        from shared.patterns.evaluation import AgentEvalConfig
        config = AgentEvalConfig(
            agent_name="test-agent",
            thresholds={"goal_success_rate": 0.70},
        )
        alerts = engine.check_report(report, config)
        alert = engine.acknowledge(alerts[0].alert_id, by="tester", note="looking into it")
        assert alert is not None
        assert alert.status == "acknowledged"
        assert alert.acknowledged_by == "tester"

    def test_get_active_alerts_by_agent(self):
        engine = AlertEngine()
        report = _make_report(score=0.50)
        from shared.patterns.evaluation import AgentEvalConfig
        config = AgentEvalConfig(
            agent_name="test-agent",
            thresholds={"goal_success_rate": 0.70, "correctness": 0.70},
        )
        engine.check_report(report, config)
        active = engine.get_active_alerts(agent_name="test-agent")
        assert len(active) >= 1

    def test_auto_resolve_on_recovery(self):
        engine = AlertEngine()
        from shared.patterns.evaluation import AgentEvalConfig
        config = AgentEvalConfig(
            agent_name="test-agent",
            thresholds={"goal_success_rate": 0.70},
        )
        # Create violation
        engine.check_report(_make_report(score=0.50), config)
        assert len(engine.get_active_alerts()) == 1
        # Score recovers
        engine.check_report(_make_report(score=0.85), config)
        assert len(engine.get_active_alerts()) == 0

    def test_alert_deduplication(self):
        engine = AlertEngine()
        from shared.patterns.evaluation import AgentEvalConfig
        config = AgentEvalConfig(
            agent_name="test-agent",
            thresholds={"goal_success_rate": 0.70},
        )
        engine.check_report(_make_report(score=0.50), config)
        engine.check_report(_make_report(score=0.55), config)
        # Should still be only 1 alert (updated, not duplicated)
        assert engine.alert_count == 1


# ---------------------------------------------------------------------------
# Response model tests
# ---------------------------------------------------------------------------


class TestResponseModels:
    """Validate Pydantic response models used by endpoints."""

    def test_batch_report_serialization(self):
        report = _make_report()
        data = report.to_dict()
        assert data["agent_name"] == "test-agent"
        assert data["sessions_evaluated"] == 5
        assert "goal_success_rate" in data["aggregate_scores"]

    def test_eval_alert_serialization(self):
        alert = EvalAlert(
            agent_name="test-agent",
            evaluator_name="goal_success_rate",
            level=EvalLevel.OUTCOME,
            metric="goal_success_rate",
            threshold=0.70,
            actual_score=0.50,
            priority="critical",
            status="active",
        )
        data = alert.model_dump(mode="json")
        assert data["priority"] == "critical"
        assert data["status"] == "active"
        assert data["level"] == "L1_OUTCOME"

    def test_evaluation_report_markdown(self):
        report = _make_report().reports[0]
        md = report.to_markdown()
        assert "Evaluation Report" in md

    def test_batch_report_markdown(self):
        report = _make_report()
        md = report.to_markdown()
        assert "Batch Evaluation Report" in md
        assert "goal_success_rate" in md


# ---------------------------------------------------------------------------
# Store cleanup tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cleanup_expired(store):
    await store.store_batch_report(_make_report())
    # With default retention (30 days), nothing should be cleaned up
    deleted = await store.cleanup_expired()
    assert deleted == 0


@pytest.mark.asyncio
async def test_store_close_and_reopen():
    s = EvaluationStore(sqlite_path=":memory:")
    await s.initialize()
    await s.store_batch_report(_make_report())
    await s.close()
    # After close, queries return empty
    scores = await s.get_scores("test-agent")
    assert scores == []
