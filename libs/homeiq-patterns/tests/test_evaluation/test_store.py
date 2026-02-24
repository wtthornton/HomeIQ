"""
Tests for E4.S2: Evaluation History Storage

Tests the EvaluationStore with in-memory SQLite and mock InfluxDB writer.
"""

from datetime import datetime, timezone, timedelta
from typing import Any

import pytest
import pytest_asyncio

from homeiq_patterns.evaluation.models import (
    BatchReport,
    EvalLevel,
    EvaluationReport,
    EvaluationResult,
    SummaryMatrix,
)
from homeiq_patterns.evaluation.store import (
    EvaluationStore,
    NullInfluxDBWriter,
    _parse_period,
)


class MockInfluxDBWriter:
    """Captures points written to InfluxDB for assertion."""

    def __init__(self):
        self.points: list[dict[str, Any]] = []
        self.write_count = 0

    def write_points(self, points: list[dict[str, Any]]) -> None:
        self.points.extend(points)
        self.write_count += 1


class FailingInfluxDBWriter:
    """Simulates InfluxDB write failures."""

    def write_points(self, points: list[dict[str, Any]]) -> None:
        raise ConnectionError("InfluxDB unavailable")


def _make_batch_report(
    agent_name: str = "test-agent",
    num_sessions: int = 2,
    timestamp: datetime | None = None,
) -> BatchReport:
    """Create a minimal BatchReport for testing."""
    ts = timestamp or datetime.now(timezone.utc)
    reports = []
    for i in range(num_sessions):
        reports.append(
            EvaluationReport(
                session_id=f"session-{i}",
                agent_name=agent_name,
                timestamp=ts,
                results=[
                    EvaluationResult(
                        evaluator_name="goal_success_rate",
                        level=EvalLevel.OUTCOME,
                        score=0.85,
                        label="Yes",
                        explanation="Goal achieved",
                        passed=True,
                    ),
                    EvaluationResult(
                        evaluator_name="correctness",
                        level=EvalLevel.QUALITY,
                        score=0.90,
                        label="Correct",
                        explanation="Accurate response",
                        passed=True,
                    ),
                ],
            )
        )

    return BatchReport(
        agent_name=agent_name,
        timestamp=ts,
        sessions_evaluated=num_sessions,
        total_evaluations=num_sessions * 2,
        reports=reports,
        aggregate_scores={"goal_success_rate": 0.85, "correctness": 0.90},
    )


# ---------------------------------------------------------------------------
# Period parsing tests
# ---------------------------------------------------------------------------


class TestParsePeriod:
    def test_7d(self):
        assert _parse_period("7d") == 7

    def test_30d(self):
        assert _parse_period("30d") == 30

    def test_90d(self):
        assert _parse_period("90d") == 90

    def test_default(self):
        assert _parse_period("unknown") == 7


# ---------------------------------------------------------------------------
# NullInfluxDBWriter tests
# ---------------------------------------------------------------------------


class TestNullInfluxDBWriter:
    def test_write_does_not_raise(self):
        writer = NullInfluxDBWriter()
        writer.write_points([{"measurement": "test"}])


# ---------------------------------------------------------------------------
# EvaluationStore tests
# ---------------------------------------------------------------------------


class TestEvaluationStore:
    """Test EvaluationStore with in-memory SQLite."""

    @pytest_asyncio.fixture
    async def store(self):
        s = EvaluationStore(sqlite_path=":memory:")
        await s.initialize()
        yield s
        await s.close()

    @pytest.mark.asyncio
    async def test_initialize_creates_tables(self, store):
        # Should not raise
        assert store._db is not None

    @pytest.mark.asyncio
    async def test_store_batch_report(self, store):
        report = _make_batch_report()
        run_id = await store.store_batch_report(report)
        assert run_id >= 1

    @pytest.mark.asyncio
    async def test_get_run_count(self, store):
        assert await store.get_run_count("test-agent") == 0
        await store.store_batch_report(_make_batch_report())
        assert await store.get_run_count("test-agent") == 1
        await store.store_batch_report(_make_batch_report())
        assert await store.get_run_count("test-agent") == 2

    @pytest.mark.asyncio
    async def test_get_latest_report(self, store):
        await store.store_batch_report(_make_batch_report())
        latest = await store.get_latest_report("test-agent")
        assert latest is not None
        assert latest["agent_name"] == "test-agent"
        assert latest["sessions_evaluated"] == 2
        assert latest["total_evaluations"] == 4

    @pytest.mark.asyncio
    async def test_get_latest_report_no_data(self, store):
        assert await store.get_latest_report("nonexistent") is None

    @pytest.mark.asyncio
    async def test_get_scores(self, store):
        await store.store_batch_report(_make_batch_report())
        scores = await store.get_scores("test-agent")
        assert len(scores) == 4  # 2 sessions * 2 evaluators
        assert all("evaluator_name" in s for s in scores)
        assert all("score" in s for s in scores)

    @pytest.mark.asyncio
    async def test_get_scores_filter_by_evaluator(self, store):
        await store.store_batch_report(_make_batch_report())
        scores = await store.get_scores("test-agent", evaluator="correctness")
        assert len(scores) == 2  # 2 sessions, 1 evaluator each
        assert all(s["evaluator_name"] == "correctness" for s in scores)

    @pytest.mark.asyncio
    async def test_get_scores_filter_by_date_range(self, store):
        old = datetime.now(timezone.utc) - timedelta(days=10)
        new = datetime.now(timezone.utc)
        await store.store_batch_report(_make_batch_report(timestamp=old))
        await store.store_batch_report(_make_batch_report(timestamp=new))

        cutoff = datetime.now(timezone.utc) - timedelta(days=5)
        scores = await store.get_scores("test-agent", start=cutoff)
        # Only scores from the newer report
        assert len(scores) == 4

    @pytest.mark.asyncio
    async def test_get_trends(self, store):
        await store.store_batch_report(_make_batch_report())
        trends = await store.get_trends("test-agent", period="7d")
        assert "goal_success_rate" in trends
        assert "correctness" in trends
        assert len(trends["goal_success_rate"]) >= 1

    @pytest.mark.asyncio
    async def test_get_trends_empty(self, store):
        trends = await store.get_trends("nonexistent", period="7d")
        assert trends == {}

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, store):
        # Store an old report
        old = datetime.now(timezone.utc) - timedelta(days=60)
        await store.store_batch_report(_make_batch_report(timestamp=old))
        assert await store.get_run_count("test-agent") == 1

        # Cleanup with default 30-day retention
        deleted = await store.cleanup_expired()
        assert deleted == 1
        assert await store.get_run_count("test-agent") == 0

    @pytest.mark.asyncio
    async def test_cleanup_keeps_recent(self, store):
        await store.store_batch_report(_make_batch_report())
        deleted = await store.cleanup_expired()
        assert deleted == 0
        assert await store.get_run_count("test-agent") == 1


# ---------------------------------------------------------------------------
# InfluxDB integration tests
# ---------------------------------------------------------------------------


class TestInfluxDBIntegration:
    """Test InfluxDB writing via mock writer."""

    @pytest_asyncio.fixture
    async def store_with_influx(self):
        writer = MockInfluxDBWriter()
        s = EvaluationStore(
            influxdb_writer=writer,
            sqlite_path=":memory:",
        )
        await s.initialize()
        yield s, writer
        await s.close()

    @pytest.mark.asyncio
    async def test_writes_influxdb_points(self, store_with_influx):
        store, writer = store_with_influx
        await store.store_batch_report(_make_batch_report())
        assert writer.write_count == 1
        assert len(writer.points) == 4  # 2 sessions * 2 evaluators
        point = writer.points[0]
        assert point["measurement"] == "agent_evaluation"
        assert "agent_name" in point["tags"]
        assert "score" in point["fields"]

    @pytest.mark.asyncio
    async def test_influxdb_failure_degrades_gracefully(self):
        store = EvaluationStore(
            influxdb_writer=FailingInfluxDBWriter(),
            sqlite_path=":memory:",
        )
        await store.initialize()

        # Should not raise — degrades to SQLite only
        run_id = await store.store_batch_report(_make_batch_report())
        assert run_id >= 1

        # SQLite data should still be written
        assert await store.get_run_count("test-agent") == 1
        await store.close()
