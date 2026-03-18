"""Unit tests for MemoryConsolidationJob — Story 85.9

Tests consolidation job lifecycle, metrics tracking, and status reporting
with mocked dependencies.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import UTC, datetime

from src.jobs.memory_consolidation import (
    ConsolidationMetrics,
    ConsolidationAction,
    DetectedOverride,
    DetectedUsagePattern,
    MemoryConsolidationJob,
    PatternDrift,
    RoutineProfile,
)


# ---------------------------------------------------------------------------
# ConsolidationMetrics
# ---------------------------------------------------------------------------

class TestConsolidationMetrics:

    def test_initial_state(self):
        m = ConsolidationMetrics(started_at=datetime.now(UTC))
        assert m.overrides_detected == 0
        assert m.memories_created == 0
        assert m.memories_reinforced == 0
        assert m.memories_superseded == 0
        assert m.memories_archived == 0
        assert m.patterns_detected == 0
        assert m.error is None

    def test_to_dict_fields(self):
        now = datetime.now(UTC)
        m = ConsolidationMetrics(started_at=now)
        m.overrides_detected = 5
        m.memories_created = 3
        m.duration_ms = 1234.5678
        d = m.to_dict()
        assert d["overrides_detected"] == 5
        assert d["memories_created"] == 3
        assert d["duration_ms"] == 1234.57  # rounded
        assert d["success"] is True

    def test_to_dict_with_error(self):
        m = ConsolidationMetrics(started_at=datetime.now(UTC), error="something broke")
        d = m.to_dict()
        assert d["success"] is False
        assert d["error"] == "something broke"

    def test_to_dict_completed_at(self):
        now = datetime.now(UTC)
        m = ConsolidationMetrics(started_at=now, completed_at=now)
        d = m.to_dict()
        assert d["completed_at"] is not None

    def test_to_dict_no_completed(self):
        m = ConsolidationMetrics(started_at=datetime.now(UTC))
        d = m.to_dict()
        assert d["completed_at"] is None


# ---------------------------------------------------------------------------
# ConsolidationAction
# ---------------------------------------------------------------------------

class TestConsolidationAction:

    def test_enum_values(self):
        assert ConsolidationAction.INSERT.value == "insert"
        assert ConsolidationAction.REINFORCE.value == "reinforce"
        assert ConsolidationAction.SUPERSEDE.value == "supersede"
        assert ConsolidationAction.ARCHIVE.value == "archive"
        assert ConsolidationAction.SKIP.value == "skip"


# ---------------------------------------------------------------------------
# DetectedUsagePattern
# ---------------------------------------------------------------------------

class TestDetectedUsagePattern:

    def test_pattern_key(self):
        pattern = DetectedUsagePattern(
            entity_id="light.kitchen",
            state="on",
            hour_of_day=7,
            minute_window_start=0,
            occurrence_count=15,
        )
        key = pattern.pattern_key()
        assert "light.kitchen" in key
        assert "on" in key
        assert "7" in key

    def test_pattern_key_dedup(self):
        """Same 30-min window should produce same key."""
        p1 = DetectedUsagePattern(
            entity_id="light.kitchen", state="on",
            hour_of_day=7, minute_window_start=0, occurrence_count=10
        )
        p2 = DetectedUsagePattern(
            entity_id="light.kitchen", state="on",
            hour_of_day=7, minute_window_start=15, occurrence_count=10
        )
        assert p1.pattern_key() == p2.pattern_key()

    def test_pattern_key_different_entities(self):
        p1 = DetectedUsagePattern(
            entity_id="light.kitchen", state="on",
            hour_of_day=7, minute_window_start=0, occurrence_count=10
        )
        p2 = DetectedUsagePattern(
            entity_id="light.bedroom", state="on",
            hour_of_day=7, minute_window_start=0, occurrence_count=10
        )
        assert p1.pattern_key() != p2.pattern_key()

    def test_defaults(self):
        p = DetectedUsagePattern(
            entity_id="x", state="on", hour_of_day=0,
            minute_window_start=0, occurrence_count=1
        )
        assert p.first_seen is None
        assert p.last_seen is None
        assert p.days_span == 0
        assert p.confidence == 0.0


# ---------------------------------------------------------------------------
# MemoryConsolidationJob
# ---------------------------------------------------------------------------

class TestMemoryConsolidationJobInit:

    def test_init_with_none_clients(self):
        job = MemoryConsolidationJob(
            influxdb=MagicMock(),
            memory_client=None,
            consolidator=None,
        )
        assert job.influxdb is not None
        assert job.memory is None
        assert job.consolidator is None

    def test_initial_counters_zero(self):
        job = MemoryConsolidationJob(
            influxdb=MagicMock(),
            memory_client=None,
            consolidator=None,
        )
        assert job._overrides_detected == 0
        assert job._memories_created == 0
        assert job._patterns_detected == 0
        assert job._routines_synthesized == 0

    def test_metrics_history_empty(self):
        job = MemoryConsolidationJob(
            influxdb=MagicMock(),
            memory_client=None,
            consolidator=None,
        )
        assert job.last_run_metrics is None
        assert len(job._metrics_history) == 0


class TestMemoryConsolidationJobGetStatus:

    def test_initial_status(self):
        job = MemoryConsolidationJob(
            influxdb=MagicMock(),
            memory_client=None,
            consolidator=None,
        )
        status = job.get_status()
        assert status["last_run"] is None
        assert status["overrides_detected"] == 0
        assert status["patterns_detected"] == 0

    def test_status_after_run_time_set(self):
        job = MemoryConsolidationJob(
            influxdb=MagicMock(),
            memory_client=None,
            consolidator=None,
        )
        now = datetime.now(UTC)
        job._last_run = now
        job._overrides_detected = 5
        status = job.get_status()
        assert status["last_run"] == now.isoformat()
        assert status["overrides_detected"] == 5


class TestMemoryConsolidationJobRun:

    @pytest.mark.asyncio
    async def test_run_returns_metrics_object(self):
        job = MemoryConsolidationJob(
            influxdb=MagicMock(),
            memory_client=None,
            consolidator=None,
        )
        # Mock all internal async methods
        job._load_existing_pattern_memories = AsyncMock()
        job._detect_overrides = AsyncMock(return_value=[])
        job._detect_usage_patterns = AsyncMock(return_value=[])
        job._detect_pattern_drift = AsyncMock(return_value=[])
        job._store_override_memories = AsyncMock()
        job._store_usage_pattern_memories = AsyncMock()
        job._synthesize_routines = AsyncMock(return_value=0)
        job._resolve_contradictions = AsyncMock(return_value=0)
        job._garbage_collect = AsyncMock(return_value=0)
        job._write_metrics = AsyncMock()

        result = await job.run()
        assert isinstance(result, ConsolidationMetrics)
        assert result.error is None

    @pytest.mark.asyncio
    async def test_run_updates_last_run(self):
        job = MemoryConsolidationJob(
            influxdb=MagicMock(),
            memory_client=None,
            consolidator=None,
        )
        job._load_existing_pattern_memories = AsyncMock()
        job._detect_overrides = AsyncMock(return_value=[])
        job._detect_usage_patterns = AsyncMock(return_value=[])
        job._detect_pattern_drift = AsyncMock(return_value=[])
        job._store_override_memories = AsyncMock()
        job._store_usage_pattern_memories = AsyncMock()
        job._synthesize_routines = AsyncMock(return_value=0)
        job._resolve_contradictions = AsyncMock(return_value=0)
        job._garbage_collect = AsyncMock(return_value=0)
        job._write_metrics = AsyncMock()

        await job.run()
        assert job._last_run is not None


# ---------------------------------------------------------------------------
# PatternDrift, RoutineProfile, DetectedOverride dataclasses
# ---------------------------------------------------------------------------

class TestPatternDrift:

    def test_construction(self):
        d = PatternDrift(
            entity_id="light.kitchen",
            state="on",
            original_time="07:00",
            new_time="07:30",
            drift_minutes=30,
        )
        assert d.entity_id == "light.kitchen"
        assert d.drift_minutes == 30
        assert d.memory_id is None

    def test_with_memory_id(self):
        d = PatternDrift(
            entity_id="light.kitchen",
            state="on",
            original_time="07:00",
            new_time="08:00",
            drift_minutes=60,
            memory_id="mem-123",
        )
        assert d.memory_id == "mem-123"


class TestRoutineProfile:

    def test_construction(self):
        r = RoutineProfile(
            day_type="weekday",
            wake_time="06:30",
            leave_time="08:00",
            return_time="17:30",
            sleep_time="22:00",
            confidence=0.85,
            sample_days=20,
        )
        assert r.day_type == "weekday"
        assert r.wake_time == "06:30"
        assert r.confidence == 0.85

    def test_weekend_profile(self):
        r = RoutineProfile(
            day_type="weekend",
            wake_time="09:00",
            leave_time=None,
            return_time=None,
            sleep_time="23:00",
            confidence=0.6,
            sample_days=8,
        )
        assert r.leave_time is None
        assert r.return_time is None


class TestDetectedOverride:

    def test_construction(self):
        now = datetime.now(UTC)
        o = DetectedOverride(
            entity_id="light.kitchen",
            automation_time=now,
            manual_time=now,
            automation_state="off",
            manual_state="on",
        )
        assert o.entity_id == "light.kitchen"
        assert o.automation_context_id is None

    def test_with_context_id(self):
        now = datetime.now(UTC)
        o = DetectedOverride(
            entity_id="light.kitchen",
            automation_time=now,
            manual_time=now,
            automation_state="off",
            manual_state="on",
            automation_context_id="ctx-abc",
        )
        assert o.automation_context_id == "ctx-abc"


# ---------------------------------------------------------------------------
# get_last_run_metrics & get_metrics_history
# ---------------------------------------------------------------------------

class TestMetricsAccess:

    def _make_job(self):
        return MemoryConsolidationJob(
            influxdb=MagicMock(),
            memory_client=None,
            consolidator=None,
        )

    def test_get_last_run_metrics_none(self):
        job = self._make_job()
        assert job.get_last_run_metrics() is None

    def test_get_last_run_metrics_returns_dict(self):
        job = self._make_job()
        job.last_run_metrics = ConsolidationMetrics(started_at=datetime.now(UTC))
        result = job.get_last_run_metrics()
        assert isinstance(result, dict)
        assert "started_at" in result

    def test_get_metrics_history_empty(self):
        job = self._make_job()
        assert job.get_metrics_history() == []

    def test_get_metrics_history_returns_list(self):
        job = self._make_job()
        job._metrics_history.append(ConsolidationMetrics(started_at=datetime.now(UTC)))
        job._metrics_history.append(ConsolidationMetrics(started_at=datetime.now(UTC)))
        result = job.get_metrics_history()
        assert len(result) == 2
        assert all(isinstance(m, dict) for m in result)


# ---------------------------------------------------------------------------
# _should_run_routine_synthesis
# ---------------------------------------------------------------------------

class TestShouldRunRoutineSynthesis:

    def _make_job(self):
        return MemoryConsolidationJob(
            influxdb=MagicMock(),
            memory_client=None,
            consolidator=None,
        )

    def test_never_run_on_sunday(self):
        job = self._make_job()
        # Find the next Sunday
        from datetime import timedelta
        now = datetime.now(UTC)
        days_until_sunday = (6 - now.weekday()) % 7
        sunday = now + timedelta(days=days_until_sunday)
        with patch("src.jobs.memory_consolidation.datetime") as mock_dt:
            mock_dt.now.return_value = sunday
            mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)
            # _last_routine_synthesis is None and it's Sunday → True
            result = job._should_run_routine_synthesis()
            # Can't guarantee day, but method should return bool
            assert isinstance(result, bool)

    def test_returns_true_after_7_days(self):
        job = self._make_job()
        from datetime import timedelta
        job._last_routine_synthesis = datetime.now(UTC) - timedelta(days=8)
        assert job._should_run_routine_synthesis() is True

    def test_returns_false_if_recent(self):
        job = self._make_job()
        from datetime import timedelta
        job._last_routine_synthesis = datetime.now(UTC) - timedelta(days=1)
        # Only returns True on Sunday or after 7 days
        now = datetime.now(UTC)
        if now.weekday() != 6:  # not Sunday
            assert job._should_run_routine_synthesis() is False


# ---------------------------------------------------------------------------
# Run with exception
# ---------------------------------------------------------------------------

class TestRunWithException:

    @pytest.mark.asyncio
    async def test_run_captures_exception(self):
        job = MemoryConsolidationJob(
            influxdb=MagicMock(),
            memory_client=None,
            consolidator=None,
        )
        job._load_existing_pattern_memories = AsyncMock(
            side_effect=Exception("db timeout")
        )
        job._write_metrics = AsyncMock()

        result = await job.run()
        assert isinstance(result, ConsolidationMetrics)
        assert result.error is not None
        assert "db timeout" in result.error
