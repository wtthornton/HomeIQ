"""Unit tests for memory_consolidation.py

Comprehensive tests for all dataclasses, enums, and MemoryConsolidationJob
methods with mocked InfluxDB and memory clients. No external services required.

Story 85.9 + expanded coverage for override detection, pattern aggregation,
confidence calculation, drift detection, routine synthesis, and metrics.
"""

import pytest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.jobs.memory_consolidation import (
    ANALYSIS_WINDOW_DAYS,
    CONSOLIDATION_CYCLE_HOURS,
    ConsolidationAction,
    ConsolidationMetrics,
    DetectedOverride,
    DetectedUsagePattern,
    METRICS_MEASUREMENT,
    MemoryConsolidationJob,
    OVERRIDE_THRESHOLD,
    OVERRIDE_WINDOW_MINUTES,
    PATTERN_DRIFT_THRESHOLD_MINUTES,
    PATTERN_MIN_DAYS,
    PATTERN_MIN_OCCURRENCES,
    PATTERN_WINDOW_MINUTES,
    PatternDrift,
    ROUTINE_LABELS,
    ROUTINE_MIN_SAMPLES,
    ROUTINE_SYNTHESIS_DAYS,
    ROUTINE_TIME_SHIFT_THRESHOLD_MINUTES,
    RoutineProfile,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_influxdb(connected: bool = True, bucket: str = "homeiq") -> MagicMock:
    """Create a mock InfluxDB query client."""
    mock = MagicMock()
    mock.is_connected = connected
    mock.bucket = bucket
    mock._execute_query = AsyncMock(return_value=[])
    return mock


def _mock_consolidator() -> AsyncMock:
    """Create a mock memory consolidator."""
    consolidator = AsyncMock()
    consolidator.consolidate = AsyncMock()
    consolidator.update = AsyncMock()
    consolidator.supersede = AsyncMock()
    consolidator.reinforce = AsyncMock()
    consolidator.run_garbage_collection = AsyncMock(return_value=0)
    consolidator.detect_contradictions = AsyncMock(return_value=[])
    return consolidator


def _mock_memory_client() -> AsyncMock:
    """Create a mock memory client."""
    client = AsyncMock()
    client.query = AsyncMock(return_value=[])
    return client


def _make_job(
    connected: bool = True,
    with_consolidator: bool = False,
    with_memory: bool = False,
) -> tuple[MemoryConsolidationJob, MagicMock]:
    """Create a MemoryConsolidationJob with mocked dependencies."""
    influx = _mock_influxdb(connected=connected)
    consolidator = _mock_consolidator() if with_consolidator else None
    memory = _mock_memory_client() if with_memory else None
    job = MemoryConsolidationJob(influx, memory_client=memory, consolidator=consolidator)
    return job, influx


def _make_auto_event(entity_id: str, state: str, time: datetime, context_id: str = "ctx-1") -> dict:
    return {
        "entity_id": entity_id,
        "new_state": state,
        "_time": time.isoformat(),
        "context_id": context_id,
    }


def _make_manual_event(entity_id: str, state: str, time: datetime) -> dict:
    return {
        "entity_id": entity_id,
        "new_state": state,
        "_time": time.isoformat(),
        "context_user_id": "user-1",
    }


def _make_pattern_event(entity_id: str, state: str, time: datetime) -> dict:
    return {
        "entity_id": entity_id,
        "_value": state,
        "_time": time.isoformat(),
    }


# ---------------------------------------------------------------------------
# ConsolidationAction enum
# ---------------------------------------------------------------------------

class TestConsolidationAction:

    @pytest.mark.unit
    def test_insert_value(self):
        assert ConsolidationAction.INSERT.value == "insert"

    @pytest.mark.unit
    def test_reinforce_value(self):
        assert ConsolidationAction.REINFORCE.value == "reinforce"

    @pytest.mark.unit
    def test_supersede_value(self):
        assert ConsolidationAction.SUPERSEDE.value == "supersede"

    @pytest.mark.unit
    def test_archive_value(self):
        assert ConsolidationAction.ARCHIVE.value == "archive"

    @pytest.mark.unit
    def test_skip_value(self):
        assert ConsolidationAction.SKIP.value == "skip"

    @pytest.mark.unit
    def test_all_members(self):
        names = {m.name for m in ConsolidationAction}
        assert names == {"INSERT", "REINFORCE", "SUPERSEDE", "ARCHIVE", "SKIP"}


# ---------------------------------------------------------------------------
# ConsolidationMetrics dataclass
# ---------------------------------------------------------------------------

class TestConsolidationMetrics:

    @pytest.mark.unit
    def test_creation_defaults(self):
        now = datetime.now(UTC)
        m = ConsolidationMetrics(started_at=now)
        assert m.started_at == now
        assert m.completed_at is None
        assert m.memories_created == 0
        assert m.memories_reinforced == 0
        assert m.memories_superseded == 0
        assert m.memories_archived == 0
        assert m.overrides_detected == 0
        assert m.patterns_detected == 0
        assert m.pattern_drifts_detected == 0
        assert m.contradictions_found == 0
        assert m.garbage_collected == 0
        assert m.routines_synthesized == 0
        assert m.error is None
        assert m.duration_ms == 0.0

    @pytest.mark.unit
    def test_to_dict_success(self):
        now = datetime.now(UTC)
        later = now + timedelta(seconds=2)
        m = ConsolidationMetrics(
            started_at=now,
            completed_at=later,
            memories_created=5,
            overrides_detected=3,
            duration_ms=2000.123,
        )
        d = m.to_dict()
        assert d["started_at"] == now.isoformat()
        assert d["completed_at"] == later.isoformat()
        assert d["memories_created"] == 5
        assert d["overrides_detected"] == 3
        assert d["duration_ms"] == 2000.12
        assert d["success"] is True

    @pytest.mark.unit
    def test_to_dict_with_error(self):
        m = ConsolidationMetrics(
            started_at=datetime.now(UTC),
            error="InfluxDB down",
        )
        d = m.to_dict()
        assert d["error"] == "InfluxDB down"
        assert d["success"] is False

    @pytest.mark.unit
    def test_to_dict_no_completed_at(self):
        m = ConsolidationMetrics(started_at=datetime.now(UTC))
        d = m.to_dict()
        assert d["completed_at"] is None

    @pytest.mark.unit
    def test_to_dict_all_fields_present(self):
        m = ConsolidationMetrics(started_at=datetime.now(UTC))
        d = m.to_dict()
        expected_keys = {
            "started_at", "completed_at", "memories_created",
            "memories_reinforced", "memories_superseded", "memories_archived",
            "overrides_detected", "patterns_detected", "pattern_drifts_detected",
            "contradictions_found", "garbage_collected", "routines_synthesized",
            "error", "duration_ms", "success",
        }
        assert set(d.keys()) == expected_keys


# ---------------------------------------------------------------------------
# DetectedUsagePattern dataclass
# ---------------------------------------------------------------------------

class TestDetectedUsagePattern:

    @pytest.mark.unit
    def test_creation(self):
        p = DetectedUsagePattern(
            entity_id="light.kitchen",
            state="on",
            hour_of_day=7,
            minute_window_start=0,
            occurrence_count=15,
        )
        assert p.entity_id == "light.kitchen"
        assert p.state == "on"
        assert p.hour_of_day == 7
        assert p.occurrence_count == 15
        assert p.first_seen is None
        assert p.confidence == 0.0

    @pytest.mark.unit
    def test_pattern_key_generation(self):
        p = DetectedUsagePattern(
            entity_id="light.kitchen",
            state="on",
            hour_of_day=7,
            minute_window_start=0,
            occurrence_count=10,
        )
        assert p.pattern_key() == "light.kitchen:on:7:0"

    @pytest.mark.unit
    def test_pattern_key_second_window(self):
        p = DetectedUsagePattern(
            entity_id="light.bedroom",
            state="off",
            hour_of_day=22,
            minute_window_start=30,
            occurrence_count=10,
        )
        assert p.pattern_key() == "light.bedroom:off:22:1"

    @pytest.mark.unit
    def test_pattern_key_same_window_dedup(self):
        """Same 30-min window produces same key."""
        p1 = DetectedUsagePattern(
            entity_id="light.kitchen", state="on",
            hour_of_day=7, minute_window_start=0, occurrence_count=10,
        )
        p2 = DetectedUsagePattern(
            entity_id="light.kitchen", state="on",
            hour_of_day=7, minute_window_start=15, occurrence_count=10,
        )
        assert p1.pattern_key() == p2.pattern_key()

    @pytest.mark.unit
    def test_pattern_key_different_entities(self):
        p1 = DetectedUsagePattern(
            entity_id="light.kitchen", state="on",
            hour_of_day=7, minute_window_start=0, occurrence_count=10,
        )
        p2 = DetectedUsagePattern(
            entity_id="light.bedroom", state="on",
            hour_of_day=7, minute_window_start=0, occurrence_count=10,
        )
        assert p1.pattern_key() != p2.pattern_key()


# ---------------------------------------------------------------------------
# PatternDrift dataclass
# ---------------------------------------------------------------------------

class TestPatternDrift:

    @pytest.mark.unit
    def test_creation(self):
        d = PatternDrift(
            entity_id="light.kitchen",
            state="on",
            original_time="07:00",
            new_time="08:30",
            drift_minutes=90,
            memory_id="mem-123",
        )
        assert d.entity_id == "light.kitchen"
        assert d.original_time == "07:00"
        assert d.new_time == "08:30"
        assert d.drift_minutes == 90
        assert d.memory_id == "mem-123"

    @pytest.mark.unit
    def test_creation_no_memory_id(self):
        d = PatternDrift(
            entity_id="light.kitchen",
            state="on",
            original_time="07:00",
            new_time="08:30",
            drift_minutes=90,
        )
        assert d.memory_id is None


# ---------------------------------------------------------------------------
# RoutineProfile dataclass
# ---------------------------------------------------------------------------

class TestRoutineProfile:

    @pytest.mark.unit
    def test_creation(self):
        r = RoutineProfile(
            day_type="weekday",
            wake_time="06:30",
            leave_time="08:00",
            return_time="17:30",
            sleep_time="22:00",
            confidence=0.85,
            sample_days=12,
        )
        assert r.day_type == "weekday"
        assert r.wake_time == "06:30"
        assert r.leave_time == "08:00"
        assert r.return_time == "17:30"
        assert r.sleep_time == "22:00"
        assert r.confidence == 0.85
        assert r.sample_days == 12

    @pytest.mark.unit
    def test_creation_with_none_times(self):
        r = RoutineProfile(
            day_type="weekend",
            wake_time="09:00",
            leave_time=None,
            return_time=None,
            sleep_time="23:30",
            confidence=0.5,
            sample_days=6,
        )
        assert r.leave_time is None
        assert r.return_time is None


# ---------------------------------------------------------------------------
# DetectedOverride dataclass
# ---------------------------------------------------------------------------

class TestDetectedOverride:

    @pytest.mark.unit
    def test_creation(self):
        now = datetime.now(UTC)
        o = DetectedOverride(
            entity_id="light.living_room",
            automation_time=now,
            manual_time=now + timedelta(minutes=5),
            automation_state="off",
            manual_state="on",
            automation_context_id="ctx-abc",
        )
        assert o.entity_id == "light.living_room"
        assert o.automation_state == "off"
        assert o.manual_state == "on"
        assert o.automation_context_id == "ctx-abc"

    @pytest.mark.unit
    def test_creation_no_context_id(self):
        now = datetime.now(UTC)
        o = DetectedOverride(
            entity_id="light.living_room",
            automation_time=now,
            manual_time=now + timedelta(minutes=5),
            automation_state="off",
            manual_state="on",
        )
        assert o.automation_context_id is None


# ---------------------------------------------------------------------------
# Constants validation
# ---------------------------------------------------------------------------

class TestConstants:

    @pytest.mark.unit
    def test_override_window(self):
        assert OVERRIDE_WINDOW_MINUTES == 15

    @pytest.mark.unit
    def test_override_threshold(self):
        assert OVERRIDE_THRESHOLD == 3

    @pytest.mark.unit
    def test_analysis_window_days(self):
        assert ANALYSIS_WINDOW_DAYS == 7

    @pytest.mark.unit
    def test_pattern_window_minutes(self):
        assert PATTERN_WINDOW_MINUTES == 30

    @pytest.mark.unit
    def test_pattern_min_occurrences(self):
        assert PATTERN_MIN_OCCURRENCES == 10

    @pytest.mark.unit
    def test_pattern_min_days(self):
        assert PATTERN_MIN_DAYS == 14

    @pytest.mark.unit
    def test_pattern_drift_threshold(self):
        assert PATTERN_DRIFT_THRESHOLD_MINUTES == 60

    @pytest.mark.unit
    def test_routine_synthesis_days(self):
        assert ROUTINE_SYNTHESIS_DAYS == 28

    @pytest.mark.unit
    def test_routine_min_samples(self):
        assert ROUTINE_MIN_SAMPLES == 5

    @pytest.mark.unit
    def test_routine_time_shift_threshold(self):
        assert ROUTINE_TIME_SHIFT_THRESHOLD_MINUTES == 30

    @pytest.mark.unit
    def test_routine_labels(self):
        assert ROUTINE_LABELS == ("waking", "leaving", "arriving", "sleeping")

    @pytest.mark.unit
    def test_consolidation_cycle_hours(self):
        assert CONSOLIDATION_CYCLE_HOURS == 6

    @pytest.mark.unit
    def test_metrics_measurement(self):
        assert METRICS_MEASUREMENT == "memory_consolidation_metrics"


# ---------------------------------------------------------------------------
# MemoryConsolidationJob initialization
# ---------------------------------------------------------------------------

class TestJobInit:

    @pytest.mark.unit
    def test_init_with_influx_only(self):
        influx = _mock_influxdb()
        job = MemoryConsolidationJob(influx)
        assert job.influxdb is influx
        assert job.memory is None
        assert job.consolidator is None
        assert job._last_run is None
        assert job._last_routine_synthesis is None
        assert job.last_run_metrics is None
        assert job._metrics_history == []
        assert job._max_history_size == 24

    @pytest.mark.unit
    def test_init_with_all_clients(self):
        influx = _mock_influxdb()
        memory = _mock_memory_client()
        consolidator = _mock_consolidator()
        job = MemoryConsolidationJob(influx, memory_client=memory, consolidator=consolidator)
        assert job.memory is memory
        assert job.consolidator is consolidator

    @pytest.mark.unit
    def test_init_counters_zero(self):
        influx = _mock_influxdb()
        job = MemoryConsolidationJob(influx)
        assert job._overrides_detected == 0
        assert job._memories_created == 0
        assert job._patterns_detected == 0
        assert job._pattern_drifts_detected == 0
        assert job._routines_synthesized == 0


# ---------------------------------------------------------------------------
# run() method
# ---------------------------------------------------------------------------

class TestJobRun:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_run_success_no_consolidator(self):
        """run() completes and returns metrics even without consolidator."""
        job, influx = _make_job(connected=True)
        metrics = await job.run()
        assert metrics.error is None
        assert metrics.completed_at is not None
        assert metrics.duration_ms >= 0
        assert job.last_run_metrics is metrics
        assert job._last_run is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_run_success_with_consolidator(self):
        """run() with consolidator calls consolidation steps."""
        job, influx = _make_job(connected=True, with_consolidator=True)
        metrics = await job.run()
        assert metrics.error is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_run_influxdb_disconnected(self):
        """run() completes gracefully when InfluxDB is disconnected."""
        job, influx = _make_job(connected=False)
        metrics = await job.run()
        assert metrics.error is None
        assert metrics.overrides_detected == 0
        assert metrics.patterns_detected == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_run_error_handling(self):
        """run() catches exceptions and records them in metrics."""
        job, influx = _make_job(connected=True)
        job._load_existing_pattern_memories = AsyncMock(
            side_effect=RuntimeError("boom")
        )
        metrics = await job.run()
        assert metrics.error == "boom"
        assert metrics.completed_at is not None
        assert job.last_run_metrics is metrics

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_run_updates_instance_counters(self):
        """run() updates _overrides_detected, _patterns_detected, etc."""
        job, influx = _make_job(connected=True)
        metrics = await job.run()
        assert job._overrides_detected == metrics.overrides_detected
        assert job._patterns_detected == metrics.patterns_detected
        assert job._memories_created == metrics.memories_created

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_run_adds_to_history(self):
        """run() appends metrics to history."""
        job, influx = _make_job(connected=True)
        await job.run()
        assert len(job._metrics_history) == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_run_with_garbage_collection(self):
        """run() calls garbage collection on consolidator."""
        job, influx = _make_job(connected=True, with_consolidator=True)
        job.consolidator.run_garbage_collection = AsyncMock(return_value=3)
        metrics = await job.run()
        assert metrics.garbage_collected == 3
        assert metrics.memories_archived == 3

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_run_with_contradictions(self):
        """run() detects contradictions from consolidator."""
        job, influx = _make_job(connected=True, with_consolidator=True)
        job.consolidator.detect_contradictions = AsyncMock(
            return_value=[{"id": "c1"}, {"id": "c2"}]
        )
        metrics = await job.run()
        assert metrics.contradictions_found == 2


# ---------------------------------------------------------------------------
# Override detection
# ---------------------------------------------------------------------------

class TestOverrideDetection:

    @pytest.mark.unit
    def test_match_overrides_within_window(self):
        """Manual change within 15 min of automation = override."""
        job, _ = _make_job()
        base = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        auto_events = [_make_auto_event("light.lr", "off", base)]
        manual_events = [_make_manual_event("light.lr", "on", base + timedelta(minutes=5))]

        overrides = job._match_overrides(auto_events, manual_events)
        assert len(overrides) == 1
        assert overrides[0].entity_id == "light.lr"
        assert overrides[0].automation_state == "off"
        assert overrides[0].manual_state == "on"

    @pytest.mark.unit
    def test_match_overrides_at_exact_boundary(self):
        """Manual change at exactly 15 min = override."""
        job, _ = _make_job()
        base = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        auto_events = [_make_auto_event("light.lr", "off", base)]
        manual_events = [_make_manual_event("light.lr", "on", base + timedelta(minutes=15))]

        overrides = job._match_overrides(auto_events, manual_events)
        assert len(overrides) == 1

    @pytest.mark.unit
    def test_match_overrides_outside_window(self):
        """Manual change after 15 min window = no override."""
        job, _ = _make_job()
        base = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        auto_events = [_make_auto_event("light.lr", "off", base)]
        manual_events = [_make_manual_event("light.lr", "on", base + timedelta(minutes=16))]

        overrides = job._match_overrides(auto_events, manual_events)
        assert len(overrides) == 0

    @pytest.mark.unit
    def test_match_overrides_same_state_ignored(self):
        """Manual change to same state as automation = not an override."""
        job, _ = _make_job()
        base = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        auto_events = [_make_auto_event("light.lr", "off", base)]
        manual_events = [_make_manual_event("light.lr", "off", base + timedelta(minutes=5))]

        overrides = job._match_overrides(auto_events, manual_events)
        assert len(overrides) == 0

    @pytest.mark.unit
    def test_match_overrides_manual_before_automation(self):
        """Manual change before automation = not an override."""
        job, _ = _make_job()
        base = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        auto_events = [_make_auto_event("light.lr", "off", base)]
        manual_events = [_make_manual_event("light.lr", "on", base - timedelta(minutes=5))]

        overrides = job._match_overrides(auto_events, manual_events)
        assert len(overrides) == 0

    @pytest.mark.unit
    def test_match_overrides_different_entities(self):
        """Override must be same entity."""
        job, _ = _make_job()
        base = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        auto_events = [_make_auto_event("light.lr", "off", base)]
        manual_events = [_make_manual_event("light.bedroom", "on", base + timedelta(minutes=5))]

        overrides = job._match_overrides(auto_events, manual_events)
        assert len(overrides) == 0

    @pytest.mark.unit
    def test_match_overrides_missing_entity_id(self):
        """Events with empty entity_id are skipped."""
        job, _ = _make_job()
        base = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        auto_events = [_make_auto_event("", "off", base)]
        manual_events = [_make_manual_event("light.lr", "on", base + timedelta(minutes=5))]
        overrides = job._match_overrides(auto_events, manual_events)
        assert len(overrides) == 0

    @pytest.mark.unit
    def test_match_overrides_missing_time(self):
        """Events with no _time are skipped."""
        job, _ = _make_job()
        auto_events = [{"entity_id": "light.lr", "new_state": "off"}]
        manual_events = [{"entity_id": "light.lr", "new_state": "on", "_time": None}]
        overrides = job._match_overrides(auto_events, manual_events)
        assert len(overrides) == 0

    @pytest.mark.unit
    def test_filter_by_threshold_meets(self):
        """Entities with >= OVERRIDE_THRESHOLD overrides pass."""
        job, _ = _make_job()
        base = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        overrides = [
            DetectedOverride("light.lr", base, base + timedelta(minutes=1), "off", "on"),
            DetectedOverride("light.lr", base, base + timedelta(minutes=2), "off", "on"),
            DetectedOverride("light.lr", base, base + timedelta(minutes=3), "off", "on"),
        ]
        filtered = job._filter_by_threshold(overrides)
        assert len(filtered) == 3

    @pytest.mark.unit
    def test_filter_by_threshold_below(self):
        """Entities below threshold are filtered out."""
        job, _ = _make_job()
        base = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        overrides = [
            DetectedOverride("light.lr", base, base + timedelta(minutes=1), "off", "on"),
            DetectedOverride("light.lr", base, base + timedelta(minutes=2), "off", "on"),
        ]
        filtered = job._filter_by_threshold(overrides)
        assert len(filtered) == 0

    @pytest.mark.unit
    def test_filter_by_threshold_mixed(self):
        """Only entities meeting threshold survive."""
        job, _ = _make_job()
        base = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        overrides = [
            DetectedOverride("light.lr", base, base + timedelta(minutes=1), "off", "on"),
            DetectedOverride("light.lr", base, base + timedelta(minutes=2), "off", "on"),
            DetectedOverride("light.lr", base, base + timedelta(minutes=3), "off", "on"),
            DetectedOverride("light.bed", base, base + timedelta(minutes=1), "off", "on"),
        ]
        filtered = job._filter_by_threshold(overrides)
        assert len(filtered) == 3
        assert all(o.entity_id == "light.lr" for o in filtered)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_detect_overrides_not_connected(self):
        """Disconnected InfluxDB returns empty list."""
        job, _ = _make_job(connected=False)
        result = await job._detect_overrides()
        assert result == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_detect_overrides_no_events(self):
        """No automation or manual events returns empty."""
        job, influx = _make_job(connected=True)
        influx._execute_query.return_value = []
        result = await job._detect_overrides()
        assert result == []


# ---------------------------------------------------------------------------
# Usage pattern detection
# ---------------------------------------------------------------------------

class TestUsagePatternDetection:

    @pytest.mark.unit
    def test_aggregate_patterns_basic(self):
        """Events at same time/entity/state group into one pattern."""
        job, _ = _make_job()
        base = datetime(2026, 1, 1, 7, 10, tzinfo=UTC)
        events = [
            _make_pattern_event("light.kitchen", "on", base + timedelta(days=i))
            for i in range(15)
        ]
        patterns = job._aggregate_patterns(events)
        assert len(patterns) == 1
        key = list(patterns.keys())[0]
        assert patterns[key].entity_id == "light.kitchen"
        assert patterns[key].occurrence_count == 15
        assert patterns[key].days_span == 14

    @pytest.mark.unit
    def test_aggregate_patterns_different_windows(self):
        """Events at different time windows create separate patterns."""
        job, _ = _make_job()
        base_morning = datetime(2026, 1, 1, 7, 10, tzinfo=UTC)
        base_evening = datetime(2026, 1, 1, 19, 10, tzinfo=UTC)
        events = (
            [_make_pattern_event("light.kitchen", "on", base_morning + timedelta(days=i)) for i in range(10)]
            + [_make_pattern_event("light.kitchen", "on", base_evening + timedelta(days=i)) for i in range(10)]
        )
        patterns = job._aggregate_patterns(events)
        assert len(patterns) == 2

    @pytest.mark.unit
    def test_aggregate_patterns_skips_empty_fields(self):
        """Events missing entity_id or state or time are skipped."""
        job, _ = _make_job()
        events = [
            {"entity_id": "", "_value": "on", "_time": "2026-01-01T07:00:00+00:00"},
            {"entity_id": "light.x", "_value": "", "_time": "2026-01-01T07:00:00+00:00"},
            {"entity_id": "light.x", "_value": "on", "_time": None},
        ]
        patterns = job._aggregate_patterns(events)
        assert len(patterns) == 0

    @pytest.mark.unit
    def test_filter_patterns_by_criteria_pass(self):
        """Patterns meeting both criteria pass the filter."""
        job, _ = _make_job()
        p = DetectedUsagePattern(
            entity_id="light.kitchen", state="on",
            hour_of_day=7, minute_window_start=0,
            occurrence_count=10, days_span=14,
        )
        result = job._filter_patterns_by_criteria({"k": p})
        assert len(result) == 1

    @pytest.mark.unit
    def test_filter_patterns_by_criteria_fail_occurrences(self):
        """Patterns below min occurrences are filtered out."""
        job, _ = _make_job()
        p = DetectedUsagePattern(
            entity_id="light.kitchen", state="on",
            hour_of_day=7, minute_window_start=0,
            occurrence_count=9, days_span=14,
        )
        result = job._filter_patterns_by_criteria({"k": p})
        assert len(result) == 0

    @pytest.mark.unit
    def test_filter_patterns_by_criteria_fail_days(self):
        """Patterns below min days are filtered out."""
        job, _ = _make_job()
        p = DetectedUsagePattern(
            entity_id="light.kitchen", state="on",
            hour_of_day=7, minute_window_start=0,
            occurrence_count=10, days_span=13,
        )
        result = job._filter_patterns_by_criteria({"k": p})
        assert len(result) == 0

    @pytest.mark.unit
    def test_confidence_max(self):
        """Confidence maxes at 1.0 for 20+ events over 14+ days."""
        job, _ = _make_job()
        base = datetime(2026, 1, 1, 7, 10, tzinfo=UTC)
        events = [
            _make_pattern_event("light.kitchen", "on", base + timedelta(days=i))
            for i in range(20)
        ]
        patterns = job._aggregate_patterns(events)
        p = list(patterns.values())[0]
        assert p.confidence == 1.0

    @pytest.mark.unit
    def test_confidence_partial(self):
        """Partial confidence for fewer events and shorter span."""
        job, _ = _make_job()
        base = datetime(2026, 1, 1, 7, 10, tzinfo=UTC)
        events = [
            _make_pattern_event("light.kitchen", "on", base + timedelta(days=i))
            for i in range(10)
        ]
        patterns = job._aggregate_patterns(events)
        p = list(patterns.values())[0]
        # 10/20 = 0.5, 9 days / 14 ~ 0.643 => 0.5 * 0.643 ~ 0.32
        expected = round(min(1.0, 10 / 20.0) * min(1.0, 9 / 14.0), 2)
        assert p.confidence == expected

    @pytest.mark.unit
    def test_deduplicate_patterns_removes_existing(self):
        """Patterns already in existing memories are removed."""
        job, _ = _make_job()
        p = DetectedUsagePattern(
            entity_id="light.kitchen", state="on",
            hour_of_day=7, minute_window_start=0,
            occurrence_count=10, days_span=14,
        )
        job._existing_pattern_memories["light.kitchen:on:7:0"] = {"id": "existing"}
        result = job._deduplicate_patterns([p])
        assert len(result) == 0

    @pytest.mark.unit
    def test_deduplicate_patterns_keeps_new(self):
        """Patterns not in existing memories are kept."""
        job, _ = _make_job()
        p = DetectedUsagePattern(
            entity_id="light.kitchen", state="on",
            hour_of_day=7, minute_window_start=0,
            occurrence_count=10, days_span=14,
        )
        result = job._deduplicate_patterns([p])
        assert len(result) == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_detect_usage_patterns_not_connected(self):
        """Disconnected InfluxDB returns empty list."""
        job, _ = _make_job(connected=False)
        result = await job._detect_usage_patterns()
        assert result == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_detect_usage_patterns_query_error(self):
        """Query failure returns empty list."""
        job, influx = _make_job(connected=True)
        influx._execute_query.side_effect = Exception("query failed")
        result = await job._detect_usage_patterns()
        assert result == []


# ---------------------------------------------------------------------------
# Pattern drift detection
# ---------------------------------------------------------------------------

class TestPatternDriftDetection:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_existing_memories_no_drift(self):
        """No existing memories means no drift."""
        job, _ = _make_job()
        result = await job._detect_pattern_drift([])
        assert result == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_drift_detected_when_shift_exceeds_threshold(self):
        """Drift detected when pattern shifts >= 60 minutes from memory."""
        job, influx = _make_job()
        job._existing_pattern_memories["light.kitchen:on:7:0"] = {"id": "mem-1"}
        influx._execute_query.return_value = []

        new_pattern = DetectedUsagePattern(
            entity_id="light.kitchen", state="on",
            hour_of_day=9, minute_window_start=0,
            occurrence_count=15, days_span=14,
        )
        drifts = await job._detect_pattern_drift([new_pattern])
        assert len(drifts) == 1
        assert drifts[0].drift_minutes == 120
        assert drifts[0].entity_id == "light.kitchen"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_drift_when_shift_below_threshold(self):
        """No drift when pattern shift < 60 minutes."""
        job, influx = _make_job()
        job._existing_pattern_memories["light.kitchen:on:7:0"] = {"id": "mem-1"}
        influx._execute_query.return_value = []

        new_pattern = DetectedUsagePattern(
            entity_id="light.kitchen", state="on",
            hour_of_day=7, minute_window_start=30,
            occurrence_count=15, days_span=14,
        )
        drifts = await job._detect_pattern_drift([new_pattern])
        assert len(drifts) == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_drift_wrap_around_midnight(self):
        """Drift calculation wraps around midnight correctly."""
        job, influx = _make_job()
        # Memory at 23:00 (hour=23, window=0)
        job._existing_pattern_memories["light.kitchen:on:23:0"] = {"id": "mem-1"}
        influx._execute_query.return_value = []

        # Pattern at 01:00 (only 120 min difference, not 1320)
        new_pattern = DetectedUsagePattern(
            entity_id="light.kitchen", state="on",
            hour_of_day=1, minute_window_start=0,
            occurrence_count=15, days_span=14,
        )
        drifts = await job._detect_pattern_drift([new_pattern])
        assert len(drifts) == 1
        assert drifts[0].drift_minutes == 120


# ---------------------------------------------------------------------------
# Consolidation logic
# ---------------------------------------------------------------------------

class TestConsolidateOverrides:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_consolidator_returns_zero(self):
        job, _ = _make_job(with_consolidator=False)
        result = await job._consolidate_overrides([])
        assert result == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_creates_memories_per_entity(self):
        job, _ = _make_job(with_consolidator=True)
        base = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        overrides = [
            DetectedOverride("light.lr", base, base + timedelta(minutes=1), "off", "on"),
            DetectedOverride("light.lr", base, base + timedelta(minutes=2), "off", "on"),
            DetectedOverride("light.lr", base, base + timedelta(minutes=3), "off", "on"),
        ]
        result = await job._consolidate_overrides(overrides)
        assert result == 1
        job.consolidator.consolidate.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_consolidate_error_continues(self):
        """Error for one entity does not stop others."""
        job, _ = _make_job(with_consolidator=True)
        base = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        overrides = [
            DetectedOverride("light.lr", base, base + timedelta(minutes=1), "off", "on"),
            DetectedOverride("light.bed", base, base + timedelta(minutes=1), "off", "on"),
        ]
        job.consolidator.consolidate.side_effect = [Exception("fail"), None]
        result = await job._consolidate_overrides(overrides)
        assert result == 1  # second succeeded


class TestConsolidatePatterns:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_consolidator_returns_zero(self):
        job, _ = _make_job(with_consolidator=False)
        result = await job._consolidate_patterns([])
        assert result == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_empty_patterns_returns_zero(self):
        job, _ = _make_job(with_consolidator=True)
        result = await job._consolidate_patterns([])
        assert result == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_creates_pattern_memories(self):
        job, _ = _make_job(with_consolidator=True)
        patterns = [
            DetectedUsagePattern("light.kitchen", "on", 7, 0, 15, days_span=14, confidence=0.8),
        ]
        result = await job._consolidate_patterns(patterns)
        assert result == 1
        job.consolidator.consolidate.assert_called_once()


class TestUpdateDriftedPatterns:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_consolidator_returns_zero(self):
        job, _ = _make_job(with_consolidator=False)
        result = await job._update_drifted_patterns([])
        assert result == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_updates_with_memory_id(self):
        job, _ = _make_job(with_consolidator=True)
        drifts = [
            PatternDrift("light.kitchen", "on", "07:00", "09:00", 120, memory_id="mem-1"),
        ]
        result = await job._update_drifted_patterns(drifts)
        assert result == 1
        job.consolidator.update.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_creates_new_when_no_memory_id(self):
        job, _ = _make_job(with_consolidator=True)
        drifts = [
            PatternDrift("light.kitchen", "on", "07:00", "09:00", 120, memory_id=None),
        ]
        result = await job._update_drifted_patterns(drifts)
        assert result == 1
        job.consolidator.consolidate.assert_called_once()


# ---------------------------------------------------------------------------
# Routine synthesis
# ---------------------------------------------------------------------------

class TestRoutineSynthesis:

    @pytest.mark.unit
    def test_should_run_routine_synthesis_first_time_sunday(self):
        """First run on Sunday triggers synthesis."""
        job, _ = _make_job()
        job._last_routine_synthesis = None
        with patch("src.jobs.memory_consolidation.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 15, 12, 0, tzinfo=UTC)  # Sunday
            result = job._should_run_routine_synthesis()
        assert result is True

    @pytest.mark.unit
    def test_should_run_routine_synthesis_not_sunday_first_time(self):
        """First run on non-Sunday does not trigger."""
        job, _ = _make_job()
        job._last_routine_synthesis = None
        with patch("src.jobs.memory_consolidation.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 16, 12, 0, tzinfo=UTC)  # Monday
            result = job._should_run_routine_synthesis()
        assert result is False

    @pytest.mark.unit
    def test_should_run_routine_synthesis_after_7_days(self):
        """Synthesis triggers if > 7 days since last run."""
        job, _ = _make_job()
        job._last_routine_synthesis = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)
        with patch("src.jobs.memory_consolidation.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 11, 12, 0, tzinfo=UTC)
            result = job._should_run_routine_synthesis()
        assert result is True

    @pytest.mark.unit
    def test_should_not_run_routine_synthesis_recent(self):
        """Synthesis does not trigger within 7 days on non-Sunday."""
        job, _ = _make_job()
        job._last_routine_synthesis = datetime(2026, 3, 14, 12, 0, tzinfo=UTC)  # Saturday
        with patch("src.jobs.memory_consolidation.datetime") as mock_dt:
            # Wednesday (3 days later, not Sunday, < 7 days)
            mock_dt.now.return_value = datetime(2026, 3, 18, 12, 0, tzinfo=UTC)  # Wednesday
            result = job._should_run_routine_synthesis()
        assert result is False

    @pytest.mark.unit
    def test_build_profile_insufficient_samples(self):
        """Profile returns None with fewer than ROUTINE_MIN_SAMPLES days."""
        job, _ = _make_job()
        base = datetime(2026, 1, 1, 7, 0, tzinfo=UTC)
        events = {"waking": [base + timedelta(days=i) for i in range(3)],
                  "leaving": [], "arriving": [], "sleeping": []}
        result = job._build_profile("weekday", events)
        assert result is None

    @pytest.mark.unit
    def test_build_profile_sufficient_samples(self):
        """Profile is built with enough samples."""
        job, _ = _make_job()
        base = datetime(2026, 1, 1, 7, 0, tzinfo=UTC)
        waking = [base + timedelta(days=i) for i in range(6)]
        events = {
            "waking": waking,
            "leaving": [base.replace(hour=8) + timedelta(days=i) for i in range(6)],
            "arriving": [base.replace(hour=17) + timedelta(days=i) for i in range(6)],
            "sleeping": [base.replace(hour=22) + timedelta(days=i) for i in range(6)],
        }
        result = job._build_profile("weekday", events)
        assert result is not None
        assert result.day_type == "weekday"
        assert result.wake_time == "07:00"
        assert result.sample_days == 6

    @pytest.mark.unit
    def test_build_profile_no_times_returns_none(self):
        """Profile returns None when no routine times can be calculated."""
        job, _ = _make_job()
        # 6 unique days but only 2 events per label (< ROUTINE_MIN_SAMPLES per label)
        base = datetime(2026, 1, 1, 7, 0, tzinfo=UTC)
        events = {
            "waking": [base, base + timedelta(days=1)],
            "leaving": [base.replace(hour=8), base.replace(hour=8) + timedelta(days=1)],
            "arriving": [base.replace(hour=17), base.replace(hour=17) + timedelta(days=6)],
            "sleeping": [base.replace(hour=22), base.replace(hour=22) + timedelta(days=1)],
        }
        result = job._build_profile("weekday", events)
        # Might be None if sample_days < 5 or all median_time returns None
        # With these events: 4 unique days = under threshold
        assert result is None

    @pytest.mark.unit
    def test_build_routine_content(self):
        """Routine content is formatted correctly."""
        job, _ = _make_job()
        profile = RoutineProfile(
            day_type="weekday",
            wake_time="06:30",
            leave_time="08:00",
            return_time=None,
            sleep_time="22:00",
            confidence=0.8,
            sample_days=10,
        )
        content = job._build_routine_content(profile)
        assert "Weekday:" in content
        assert "wake 06:30" in content
        assert "leave 08:00" in content
        assert "sleep 22:00" in content
        assert "return" not in content

    @pytest.mark.unit
    def test_build_routine_content_weekend(self):
        """Weekend routine is labeled correctly."""
        job, _ = _make_job()
        profile = RoutineProfile(
            day_type="weekend",
            wake_time="09:00",
            leave_time=None,
            return_time=None,
            sleep_time="23:00",
            confidence=0.6,
            sample_days=8,
        )
        content = job._build_routine_content(profile)
        assert "Weekend:" in content

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_synthesize_routines_not_connected(self):
        """Disconnected InfluxDB returns empty list."""
        job, _ = _make_job(connected=False)
        result = await job.synthesize_routines()
        assert result == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_synthesize_routines_no_events(self):
        """No activity events returns empty list."""
        job, influx = _make_job(connected=True)
        influx._execute_query.return_value = []
        result = await job.synthesize_routines()
        assert result == []


# ---------------------------------------------------------------------------
# Routine shift detection
# ---------------------------------------------------------------------------

class TestRoutineShiftDetection:

    @pytest.mark.unit
    def test_detect_routine_shift_significant(self):
        """Shift >= 30 min detected."""
        job, _ = _make_job()
        profile = RoutineProfile(
            day_type="weekday",
            wake_time="08:00",
            leave_time=None, return_time=None, sleep_time=None,
            confidence=0.8, sample_days=10,
        )
        existing = {"content": "Weekday: wake 06:30, leave 08:00, sleep 22:00"}
        assert job._detect_routine_shift(profile, existing) is True

    @pytest.mark.unit
    def test_detect_routine_shift_not_significant(self):
        """Shift < 30 min is stable."""
        job, _ = _make_job()
        profile = RoutineProfile(
            day_type="weekday",
            wake_time="06:50",
            leave_time=None, return_time=None, sleep_time=None,
            confidence=0.8, sample_days=10,
        )
        existing = {"content": "Weekday: wake 06:30, sleep 22:00"}
        assert job._detect_routine_shift(profile, existing) is False

    @pytest.mark.unit
    def test_detect_routine_shift_no_matching_field(self):
        """No shift detected if field not in existing content."""
        job, _ = _make_job()
        profile = RoutineProfile(
            day_type="weekday",
            wake_time="08:00",
            leave_time=None, return_time=None, sleep_time=None,
            confidence=0.8, sample_days=10,
        )
        existing = {"content": "Weekday: leave 08:00, sleep 22:00"}
        assert job._detect_routine_shift(profile, existing) is False

    @pytest.mark.unit
    def test_detect_routine_shift_wrap_around(self):
        """Midnight wrap-around: sleep 23:00 -> 00:30 = 90 min shift."""
        job, _ = _make_job()
        profile = RoutineProfile(
            day_type="weekday",
            wake_time=None, leave_time=None, return_time=None,
            sleep_time="00:30",
            confidence=0.8, sample_days=10,
        )
        existing = {"content": "Weekday: sleep 23:00"}
        assert job._detect_routine_shift(profile, existing) is True

    @pytest.mark.unit
    def test_detect_routine_shift_all_none_times(self):
        """No shift when all new profile times are None."""
        job, _ = _make_job()
        profile = RoutineProfile(
            day_type="weekday",
            wake_time=None, leave_time=None, return_time=None, sleep_time=None,
            confidence=0.5, sample_days=5,
        )
        existing = {"content": "Weekday: wake 06:30, sleep 22:00"}
        assert job._detect_routine_shift(profile, existing) is False


# ---------------------------------------------------------------------------
# Metrics history
# ---------------------------------------------------------------------------

class TestMetricsHistory:

    @pytest.mark.unit
    def test_add_to_history(self):
        job, _ = _make_job()
        m = ConsolidationMetrics(started_at=datetime.now(UTC))
        job._add_to_history(m)
        assert len(job._metrics_history) == 1

    @pytest.mark.unit
    def test_history_max_size(self):
        """History is capped at _max_history_size (24)."""
        job, _ = _make_job()
        for i in range(30):
            m = ConsolidationMetrics(started_at=datetime.now(UTC), memories_created=i)
            job._add_to_history(m)
        assert len(job._metrics_history) == 24
        assert job._metrics_history[0].memories_created == 6
        assert job._metrics_history[-1].memories_created == 29

    @pytest.mark.unit
    def test_get_last_run_metrics_none(self):
        job, _ = _make_job()
        assert job.get_last_run_metrics() is None

    @pytest.mark.unit
    def test_get_last_run_metrics(self):
        job, _ = _make_job()
        m = ConsolidationMetrics(started_at=datetime.now(UTC), overrides_detected=5)
        job.last_run_metrics = m
        result = job.get_last_run_metrics()
        assert result is not None
        assert result["overrides_detected"] == 5

    @pytest.mark.unit
    def test_get_metrics_history(self):
        job, _ = _make_job()
        for i in range(3):
            job._add_to_history(
                ConsolidationMetrics(started_at=datetime.now(UTC), memories_created=i)
            )
        history = job.get_metrics_history()
        assert len(history) == 3
        assert history[0]["memories_created"] == 0
        assert history[2]["memories_created"] == 2


# ---------------------------------------------------------------------------
# get_status
# ---------------------------------------------------------------------------

class TestGetStatus:

    @pytest.mark.unit
    def test_get_status_initial(self):
        job, _ = _make_job()
        status = job.get_status()
        assert status["last_run"] is None
        assert status["last_routine_synthesis"] is None
        assert status["overrides_detected"] == 0
        assert status["config"]["override_window_minutes"] == 15
        assert status["config"]["consolidation_cycle_hours"] == 6
        assert status["metrics_history_count"] == 0

    @pytest.mark.unit
    def test_get_status_after_run(self):
        job, _ = _make_job()
        now = datetime.now(UTC)
        job._last_run = now
        job._overrides_detected = 5
        job._patterns_detected = 3
        status = job.get_status()
        assert status["last_run"] == now.isoformat()
        assert status["overrides_detected"] == 5
        assert status["patterns_detected"] == 3

    @pytest.mark.unit
    def test_get_status_config_completeness(self):
        """All config constants are present in status."""
        job, _ = _make_job()
        config = job.get_status()["config"]
        assert "consolidation_cycle_hours" in config
        assert "override_window_minutes" in config
        assert "override_threshold" in config
        assert "analysis_window_days" in config
        assert "pattern_window_minutes" in config
        assert "pattern_min_occurrences" in config
        assert "pattern_min_days" in config
        assert "pattern_drift_threshold_minutes" in config
        assert "routine_synthesis_days" in config
        assert "routine_min_samples" in config
        assert "routine_time_shift_threshold" in config


# ---------------------------------------------------------------------------
# _extract_pattern_key_from_memory
# ---------------------------------------------------------------------------

class TestExtractPatternKey:

    @pytest.mark.unit
    def test_extracts_key(self):
        job, _ = _make_job()
        memory = {
            "content": "Usage pattern for light.kitchen: state on typically at 07:00",
            "entity_ids": ["light.kitchen"],
        }
        key = job._extract_pattern_key_from_memory(memory)
        assert key == "light.kitchen:on:7:0"

    @pytest.mark.unit
    def test_returns_none_no_entity_ids(self):
        job, _ = _make_job()
        memory = {"content": "Some content", "entity_ids": []}
        assert job._extract_pattern_key_from_memory(memory) is None

    @pytest.mark.unit
    def test_returns_none_no_match(self):
        job, _ = _make_job()
        memory = {"content": "No pattern info here", "entity_ids": ["light.kitchen"]}
        assert job._extract_pattern_key_from_memory(memory) is None


# ---------------------------------------------------------------------------
# _write_metrics_to_influxdb
# ---------------------------------------------------------------------------

class TestWriteMetricsToInfluxDB:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_skips_when_no_token(self):
        """Returns False when INFLUXDB_TOKEN is not set."""
        job, _ = _make_job()
        job._influxdb_write_token = None
        m = ConsolidationMetrics(started_at=datetime.now(UTC))
        result = await job._write_metrics_to_influxdb(m)
        assert result is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_skips_when_influx_client_not_available(self):
        """Returns False when InfluxDB client library not available."""
        job, _ = _make_job()
        m = ConsolidationMetrics(started_at=datetime.now(UTC))
        with patch("src.jobs.memory_consolidation.Point", None), \
             patch("src.jobs.memory_consolidation.InfluxDBClient", None):
            result = await job._write_metrics_to_influxdb(m)
        assert result is False


# ---------------------------------------------------------------------------
# _load_existing_pattern_memories
# ---------------------------------------------------------------------------

class TestLoadExistingPatternMemories:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_memory_client(self):
        """Without memory client, existing patterns stay empty."""
        job, _ = _make_job(with_memory=False)
        await job._load_existing_pattern_memories()
        assert job._existing_pattern_memories == {}

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_loads_pattern_memories(self):
        """Loads and indexes pattern memories by key."""
        job, _ = _make_job(with_memory=True)
        job.memory.query = AsyncMock(return_value=[
            {
                "content": "Usage pattern for light.kitchen: state on typically at 07:00",
                "entity_ids": ["light.kitchen"],
            },
        ])
        await job._load_existing_pattern_memories()
        assert "light.kitchen:on:7:0" in job._existing_pattern_memories

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_skips_non_pattern_memories(self):
        """Non-pattern memories are not loaded."""
        job, _ = _make_job(with_memory=True)
        job.memory.query = AsyncMock(return_value=[
            {
                "content": "User overrides automation for light.kitchen",
                "entity_ids": ["light.kitchen"],
            },
        ])
        await job._load_existing_pattern_memories()
        assert len(job._existing_pattern_memories) == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handles_query_exception(self):
        """Exception during query is caught gracefully."""
        job, _ = _make_job(with_memory=True)
        job.memory.query = AsyncMock(side_effect=Exception("timeout"))
        await job._load_existing_pattern_memories()
        assert job._existing_pattern_memories == {}
