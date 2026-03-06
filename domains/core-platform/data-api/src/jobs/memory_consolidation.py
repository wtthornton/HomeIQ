"""Memory consolidation job - detects implicit feedback from user behavior.

Story 31.1: Override Detection
Story 31.3: Usage Pattern Consolidation
Story 32.1: Consolidation Job Infrastructure
Story 32.2: Routine Synthesis
Epic 31/32: AI Memory & Personalization

This job runs periodically (6-hour cycle) to detect when users override
automation-triggered state changes. Repeated overrides indicate the automation
doesn't match user preferences, creating behavioral memories for future
personalization.

Pattern Detection:
- Manual state change within N minutes of automation change = override
- N+ overrides in analysis window = behavioral memory stored

Usage Pattern Detection (Story 31.3):
- Same device + same action + similar time of day = usage pattern
- Patterns with 10+ occurrences over 2+ weeks create behavioral memories
- Pattern drift detection compares current patterns against stored memories

Routine Synthesis (Story 32.2):
- Weekly aggregation of activity recognition data (wake, leave, arrive, sleep)
- Builds weekday and weekend routine profiles from activity labels
- Compares to existing routine memories - update if shifted, reinforce if stable

Consolidation Infrastructure (Story 32.1):
- ConsolidationMetrics tracks all outcomes from each run
- Metrics written to InfluxDB for observability dashboards
- Endpoint exposes last run metrics for monitoring
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeiq_data.influxdb_query_client import InfluxDBQueryClient

try:
    from influxdb_client import InfluxDBClient, Point, WritePrecision
    from influxdb_client.client.write_api import SYNCHRONOUS
except ImportError:
    InfluxDBClient = None
    Point = None
    WritePrecision = None
    SYNCHRONOUS = None

logger = logging.getLogger(__name__)

OVERRIDE_WINDOW_MINUTES = 15
OVERRIDE_THRESHOLD = 3
ANALYSIS_WINDOW_DAYS = 7

PATTERN_WINDOW_MINUTES = 30
PATTERN_MIN_OCCURRENCES = 10
PATTERN_MIN_DAYS = 14
PATTERN_DRIFT_THRESHOLD_MINUTES = 60

ROUTINE_SYNTHESIS_DAYS = 28
ROUTINE_MIN_SAMPLES = 5
ROUTINE_TIME_SHIFT_THRESHOLD_MINUTES = 30
ROUTINE_LABELS = ("waking", "leaving", "arriving", "sleeping")

CONSOLIDATION_CYCLE_HOURS = 6
METRICS_MEASUREMENT = "memory_consolidation_metrics"


class ConsolidationAction(Enum):
    """Actions that can result from memory consolidation."""

    INSERT = "insert"
    REINFORCE = "reinforce"
    SUPERSEDE = "supersede"
    ARCHIVE = "archive"
    SKIP = "skip"


@dataclass
class ConsolidationMetrics:
    """Metrics from a consolidation run.

    Story 32.1: Tracks all outcomes for observability and debugging.
    """

    started_at: datetime
    completed_at: datetime | None = None
    memories_created: int = 0
    memories_reinforced: int = 0
    memories_superseded: int = 0
    memories_archived: int = 0
    overrides_detected: int = 0
    patterns_detected: int = 0
    pattern_drifts_detected: int = 0
    contradictions_found: int = 0
    garbage_collected: int = 0
    routines_synthesized: int = 0
    error: str | None = None
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary for JSON serialization."""
        return {
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "memories_created": self.memories_created,
            "memories_reinforced": self.memories_reinforced,
            "memories_superseded": self.memories_superseded,
            "memories_archived": self.memories_archived,
            "overrides_detected": self.overrides_detected,
            "patterns_detected": self.patterns_detected,
            "pattern_drifts_detected": self.pattern_drifts_detected,
            "contradictions_found": self.contradictions_found,
            "garbage_collected": self.garbage_collected,
            "routines_synthesized": self.routines_synthesized,
            "error": self.error,
            "duration_ms": round(self.duration_ms, 2),
            "success": self.error is None,
        }


@dataclass
class DetectedUsagePattern:
    """A detected stable device usage pattern."""

    entity_id: str
    state: str
    hour_of_day: int
    minute_window_start: int
    occurrence_count: int
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    days_span: int = 0
    confidence: float = 0.0

    def pattern_key(self) -> str:
        """Generate unique key for deduplication."""
        return f"{self.entity_id}:{self.state}:{self.hour_of_day}:{self.minute_window_start // 30}"


@dataclass
class PatternDrift:
    """Detected drift in an existing pattern."""

    entity_id: str
    state: str
    original_time: str
    new_time: str
    drift_minutes: int
    memory_id: str | None = None


@dataclass
class RoutineProfile:
    """Aggregated routine profile from activity recognition data.

    Represents typical daily patterns for either weekdays or weekends,
    capturing transition times (wake, leave, return, sleep) with confidence
    based on sample size and consistency.
    """

    day_type: str  # "weekday" or "weekend"
    wake_time: str | None  # "06:30" format
    leave_time: str | None
    return_time: str | None
    sleep_time: str | None
    confidence: float
    sample_days: int


@dataclass
class DetectedOverride:
    """A detected automation override event."""

    entity_id: str
    automation_time: datetime
    manual_time: datetime
    automation_state: str
    manual_state: str
    automation_context_id: str | None = None


class MemoryConsolidationJob:
    """Periodic job that extracts implicit memories from user behavior.

    Detects overrides by comparing:
    1. Automation-triggered state changes (context_user_id is null/empty)
    2. Manual state changes (context_user_id is set) within OVERRIDE_WINDOW

    When OVERRIDE_THRESHOLD+ overrides are detected for an entity in
    ANALYSIS_WINDOW_DAYS, stores a behavioral memory for personalization.

    Story 32.1: Enhanced with ConsolidationMetrics tracking and InfluxDB
    metrics writing for observability.
    """

    def __init__(
        self,
        influxdb: InfluxDBQueryClient,
        memory_client: object | None = None,
        consolidator: object | None = None,
    ) -> None:
        """Initialize the consolidation job.

        Args:
            influxdb: InfluxDB query client for event lookups
            memory_client: Optional MemoryClient for storing memories
            consolidator: Optional MemoryConsolidator for memory processing
        """
        self.influxdb = influxdb
        self.memory = memory_client
        self.consolidator = consolidator
        self._last_run: datetime | None = None
        self._last_routine_synthesis: datetime | None = None
        self._overrides_detected = 0
        self._memories_created = 0
        self._patterns_detected = 0
        self._pattern_drifts_detected = 0
        self._routines_synthesized = 0
        self._existing_pattern_memories: dict[str, dict] = {}
        self._existing_routine_memories: dict[str, dict] = {}

        self.last_run_metrics: ConsolidationMetrics | None = None
        self._metrics_history: list[ConsolidationMetrics] = []
        self._max_history_size = 24

        self._influxdb_write_url = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
        self._influxdb_write_token = os.getenv("INFLUXDB_TOKEN")
        self._influxdb_write_org = os.getenv("INFLUXDB_ORG", "homeiq")
        self._influxdb_metrics_bucket = os.getenv(
            "INFLUXDB_METRICS_BUCKET", "homeiq_metrics"
        )
        self._write_client: InfluxDBClient | None = None
        self._write_api = None

    async def run(self) -> ConsolidationMetrics:
        """Execute full consolidation cycle.

        Story 32.1: Enhanced with ConsolidationMetrics tracking.

        Returns:
            ConsolidationMetrics with all outcomes from the run.
        """
        metrics = ConsolidationMetrics(started_at=datetime.now(UTC))
        logger.info(
            "Starting memory consolidation job (cycle: %dh)",
            CONSOLIDATION_CYCLE_HOURS,
        )

        try:
            logger.debug("Step 1/6: Loading existing pattern memories")
            await self._load_existing_pattern_memories()
            logger.debug(
                "Loaded %d existing pattern memories",
                len(self._existing_pattern_memories),
            )

            logger.debug("Step 2/6: Detecting automation overrides")
            overrides = await self._detect_overrides()
            metrics.overrides_detected = len(overrides)
            logger.info(
                "Detected %d potential overrides (threshold: %d)",
                len(overrides),
                OVERRIDE_THRESHOLD,
            )

            logger.debug("Step 3/6: Detecting usage patterns")
            patterns = await self._detect_usage_patterns()
            metrics.patterns_detected = len(patterns)
            logger.info(
                "Detected %d new usage patterns (min occurrences: %d, min days: %d)",
                len(patterns),
                PATTERN_MIN_OCCURRENCES,
                PATTERN_MIN_DAYS,
            )

            logger.debug("Step 4/6: Detecting pattern drift")
            drifts = await self._detect_pattern_drift(patterns)
            metrics.pattern_drifts_detected = len(drifts)
            logger.info(
                "Detected %d pattern drifts (threshold: %d min)",
                len(drifts),
                PATTERN_DRIFT_THRESHOLD_MINUTES,
            )

            routines: list[RoutineProfile] = []
            if self._should_run_routine_synthesis():
                logger.debug("Step 4b: Running routine synthesis")
                routines = await self.synthesize_routines()
                metrics.routines_synthesized = len(routines)
                logger.info("Synthesized %d routine profiles", len(routines))
                self._last_routine_synthesis = datetime.now(UTC)
            else:
                logger.debug("Skipping routine synthesis (not due)")

            logger.debug("Step 5/6: Consolidating memories")
            if self.consolidator is not None:
                override_memories = await self._consolidate_overrides(overrides)
                metrics.memories_created += override_memories
                logger.debug("Created %d memories from overrides", override_memories)

                pattern_memories = await self._consolidate_patterns(patterns)
                metrics.memories_created += pattern_memories
                logger.debug("Created %d memories from patterns", pattern_memories)

                drift_updates = await self._update_drifted_patterns(drifts)
                metrics.memories_superseded = drift_updates
                logger.debug("Updated %d drifted pattern memories", drift_updates)

                routine_memories = await self._consolidate_routines(routines)
                metrics.memories_created += routine_memories
                logger.debug("Created %d memories from routines", routine_memories)

            logger.debug("Step 6/6: Running garbage collection")
            if self.consolidator is not None and hasattr(
                self.consolidator, "run_garbage_collection"
            ):
                archived = await self.consolidator.run_garbage_collection()
                metrics.garbage_collected = archived
                metrics.memories_archived = archived
                logger.info("Garbage collection archived %d memories", archived)

            if self.consolidator is not None and hasattr(
                self.consolidator, "detect_contradictions"
            ):
                contradictions = await self.consolidator.detect_contradictions()
                metrics.contradictions_found = len(contradictions)
                if contradictions:
                    logger.warning(
                        "Found %d contradictions in memory store",
                        len(contradictions),
                    )

            metrics.completed_at = datetime.now(UTC)
            metrics.duration_ms = (
                metrics.completed_at - metrics.started_at
            ).total_seconds() * 1000

            self._last_run = metrics.completed_at
            self._overrides_detected = metrics.overrides_detected
            self._patterns_detected = metrics.patterns_detected
            self._pattern_drifts_detected = metrics.pattern_drifts_detected
            self._routines_synthesized = metrics.routines_synthesized
            self._memories_created = metrics.memories_created

            logger.info(
                "Consolidation complete: overrides=%d, patterns=%d, drifts=%d, "
                "routines=%d, memories_created=%d, reinforced=%d, superseded=%d, "
                "archived=%d, contradictions=%d (%.0fms)",
                metrics.overrides_detected,
                metrics.patterns_detected,
                metrics.pattern_drifts_detected,
                metrics.routines_synthesized,
                metrics.memories_created,
                metrics.memories_reinforced,
                metrics.memories_superseded,
                metrics.memories_archived,
                metrics.contradictions_found,
                metrics.duration_ms,
            )

        except Exception as e:
            metrics.error = str(e)
            metrics.completed_at = datetime.now(UTC)
            metrics.duration_ms = (
                metrics.completed_at - metrics.started_at
            ).total_seconds() * 1000
            logger.error(
                "Memory consolidation failed after %.0fms: %s",
                metrics.duration_ms,
                e,
                exc_info=True,
            )

        self.last_run_metrics = metrics
        self._add_to_history(metrics)
        await self._write_metrics_to_influxdb(metrics)

        return metrics

    def _add_to_history(self, metrics: ConsolidationMetrics) -> None:
        """Add metrics to history, maintaining max size."""
        self._metrics_history.append(metrics)
        if len(self._metrics_history) > self._max_history_size:
            self._metrics_history = self._metrics_history[-self._max_history_size :]

    async def _write_metrics_to_influxdb(self, metrics: ConsolidationMetrics) -> bool:
        """Write consolidation metrics to InfluxDB for observability.

        Story 32.1: Enables dashboarding and alerting on consolidation job health.

        Args:
            metrics: The metrics from the consolidation run.

        Returns:
            True if write succeeded, False otherwise.
        """
        if Point is None or InfluxDBClient is None:
            logger.debug("InfluxDB client not available, skipping metrics write")
            return False

        if not self._influxdb_write_token:
            logger.debug("INFLUXDB_TOKEN not set, skipping metrics write")
            return False

        try:
            if self._write_client is None:
                self._write_client = InfluxDBClient(
                    url=self._influxdb_write_url,
                    token=self._influxdb_write_token,
                    org=self._influxdb_write_org,
                    timeout=30000,
                )
                self._write_api = self._write_client.write_api(
                    write_options=SYNCHRONOUS
                )

            point = (
                Point(METRICS_MEASUREMENT)
                .tag("job", "memory_consolidation")
                .tag("success", "true" if metrics.error is None else "false")
                .field("memories_created", metrics.memories_created)
                .field("memories_reinforced", metrics.memories_reinforced)
                .field("memories_superseded", metrics.memories_superseded)
                .field("memories_archived", metrics.memories_archived)
                .field("overrides_detected", metrics.overrides_detected)
                .field("patterns_detected", metrics.patterns_detected)
                .field("pattern_drifts_detected", metrics.pattern_drifts_detected)
                .field("contradictions_found", metrics.contradictions_found)
                .field("garbage_collected", metrics.garbage_collected)
                .field("routines_synthesized", metrics.routines_synthesized)
                .field("duration_ms", metrics.duration_ms)
                .time(metrics.started_at, WritePrecision.S)
            )

            await asyncio.to_thread(
                self._write_api.write,
                bucket=self._influxdb_metrics_bucket,
                org=self._influxdb_write_org,
                record=point,
            )

            logger.debug(
                "Wrote consolidation metrics to InfluxDB bucket %s",
                self._influxdb_metrics_bucket,
            )
            return True

        except Exception as e:
            logger.warning("Failed to write metrics to InfluxDB: %s", e)
            return False

    def get_last_run_metrics(self) -> dict[str, Any] | None:
        """Get the metrics from the last consolidation run.

        Story 32.1: Endpoint support for observability.

        Returns:
            Dictionary representation of last run metrics, or None if no runs yet.
        """
        if self.last_run_metrics is None:
            return None
        return self.last_run_metrics.to_dict()

    def get_metrics_history(self) -> list[dict[str, Any]]:
        """Get historical metrics from recent consolidation runs.

        Returns:
            List of metrics dictionaries, most recent last.
        """
        return [m.to_dict() for m in self._metrics_history]

    async def _detect_overrides(self) -> list[DetectedOverride]:
        """Query InfluxDB for manual state changes following automation changes.

        Detection logic:
        1. Find automation-triggered state changes (no user context)
        2. Find manual state changes (has user context)
        3. Match pairs where manual change follows automation within window
        4. Filter to entities with OVERRIDE_THRESHOLD+ matches

        Returns:
            List of detected override events.
        """
        if not self.influxdb.is_connected:
            logger.warning("InfluxDB not connected, skipping override detection")
            return []

        automation_events = await self._get_automation_events()
        manual_events = await self._get_manual_events()

        if not automation_events or not manual_events:
            logger.debug(
                "No events to compare (auto=%d, manual=%d)",
                len(automation_events),
                len(manual_events),
            )
            return []

        overrides = self._match_overrides(automation_events, manual_events)
        filtered = self._filter_by_threshold(overrides)

        return filtered

    async def _get_automation_events(self) -> list[dict]:
        """Query for automation-triggered state changes."""
        query = f'''
from(bucket: "{self.influxdb.bucket}")
    |> range(start: -{ANALYSIS_WINDOW_DAYS}d)
    |> filter(fn: (r) => r._measurement == "state_changed")
    |> filter(fn: (r) => r.context_user_id == "" or not exists r.context_user_id)
    |> filter(fn: (r) => exists r.entity_id)
    |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    |> keep(columns: ["_time", "entity_id", "new_state", "context_id"])
    |> sort(columns: ["_time"])
'''
        try:
            return await self.influxdb._execute_query(query)
        except Exception as e:
            logger.error("Failed to query automation events: %s", e)
            return []

    async def _get_manual_events(self) -> list[dict]:
        """Query for manual (user-triggered) state changes."""
        query = f'''
from(bucket: "{self.influxdb.bucket}")
    |> range(start: -{ANALYSIS_WINDOW_DAYS}d)
    |> filter(fn: (r) => r._measurement == "state_changed")
    |> filter(fn: (r) => r.context_user_id != "" and exists r.context_user_id)
    |> filter(fn: (r) => exists r.entity_id)
    |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    |> keep(columns: ["_time", "entity_id", "new_state", "context_user_id"])
    |> sort(columns: ["_time"])
'''
        try:
            return await self.influxdb._execute_query(query)
        except Exception as e:
            logger.error("Failed to query manual events: %s", e)
            return []

    def _match_overrides(
        self,
        automation_events: list[dict],
        manual_events: list[dict],
    ) -> list[DetectedOverride]:
        """Match manual events that follow automation events within the window."""
        overrides: list[DetectedOverride] = []
        window = timedelta(minutes=OVERRIDE_WINDOW_MINUTES)

        auto_by_entity: dict[str, list[dict]] = {}
        for event in automation_events:
            entity_id = event.get("entity_id", "")
            if entity_id:
                auto_by_entity.setdefault(entity_id, []).append(event)

        for manual in manual_events:
            entity_id = manual.get("entity_id", "")
            manual_time = manual.get("_time")
            manual_state = manual.get("new_state", "")

            if not entity_id or not manual_time:
                continue

            if isinstance(manual_time, str):
                manual_time = datetime.fromisoformat(manual_time.replace("Z", "+00:00"))

            auto_events = auto_by_entity.get(entity_id, [])
            for auto in auto_events:
                auto_time = auto.get("_time")
                auto_state = auto.get("new_state", "")

                if not auto_time:
                    continue

                if isinstance(auto_time, str):
                    auto_time = datetime.fromisoformat(auto_time.replace("Z", "+00:00"))

                time_diff = manual_time - auto_time
                if timedelta(0) < time_diff <= window and manual_state != auto_state:
                    overrides.append(
                        DetectedOverride(
                            entity_id=entity_id,
                            automation_time=auto_time,
                            manual_time=manual_time,
                            automation_state=auto_state,
                            manual_state=manual_state,
                            automation_context_id=auto.get("context_id"),
                        )
                    )
                    break

        return overrides

    def _filter_by_threshold(
        self, overrides: list[DetectedOverride]
    ) -> list[DetectedOverride]:
        """Filter to entities meeting the override threshold."""
        entity_counts = Counter(o.entity_id for o in overrides)
        qualifying_entities = {
            e for e, count in entity_counts.items() if count >= OVERRIDE_THRESHOLD
        }

        return [o for o in overrides if o.entity_id in qualifying_entities]

    async def _consolidate_overrides(self, overrides: list[DetectedOverride]) -> int:
        """Store detected overrides as behavioral memories.

        Returns:
            Number of memories created.
        """
        if not self.consolidator:
            logger.debug("No consolidator configured, skipping memory storage")
            return 0

        entity_counts = Counter(o.entity_id for o in overrides)
        memories_created = 0

        for entity_id, count in entity_counts.items():
            entity_overrides = [o for o in overrides if o.entity_id == entity_id]

            common_states = Counter(o.manual_state for o in entity_overrides)
            preferred_state, _ = common_states.most_common(1)[0]

            description = (
                f"User overrides automation for {entity_id} "
                f"({count}x in {ANALYSIS_WINDOW_DAYS} days, "
                f"prefers state: {preferred_state})"
            )

            try:
                await self.consolidator.consolidate(
                    content=description,
                    memory_type="behavioral",
                    source_channel="implicit",
                    entity_ids=[entity_id],
                )
                memories_created += 1
                logger.debug("Created memory for entity %s: %s", entity_id, description)
            except Exception as e:
                logger.error("Failed to create memory for %s: %s", entity_id, e)

        return memories_created

    async def _load_existing_pattern_memories(self) -> None:
        """Load existing pattern memories for deduplication and drift detection."""
        self._existing_pattern_memories = {}

        if not self.memory:
            return

        try:
            if hasattr(self.memory, "query"):
                memories = await self.memory.query(
                    memory_type="behavioral",
                    source_channel="implicit",
                    limit=1000,
                )
                for mem in memories:
                    content = mem.get("content", "")
                    if "usage pattern" in content.lower():
                        entity_id = None
                        entity_ids = mem.get("entity_ids", [])
                        if entity_ids:
                            entity_id = entity_ids[0]

                        if entity_id:
                            key = self._extract_pattern_key_from_memory(mem)
                            if key:
                                self._existing_pattern_memories[key] = mem
        except Exception as e:
            logger.warning("Failed to load existing pattern memories: %s", e)

    def _extract_pattern_key_from_memory(self, memory: dict) -> str | None:
        """Extract pattern key from an existing memory for matching."""
        content = memory.get("content", "")
        entity_ids = memory.get("entity_ids", [])

        if not entity_ids:
            return None

        entity_id = entity_ids[0]

        import re

        state_match = re.search(r"state[:\s]+(\w+)", content, re.IGNORECASE)
        time_match = re.search(r"(\d{1,2}):(\d{2})", content)

        if state_match and time_match:
            state = state_match.group(1)
            hour = int(time_match.group(1))
            minute = int(time_match.group(2))
            window = minute // 30
            return f"{entity_id}:{state}:{hour}:{window}"

        return None

    async def _detect_usage_patterns(self) -> list[DetectedUsagePattern]:
        """Query InfluxDB for stable device usage patterns.

        Criteria:
        - Same device
        - Same action (on/off/specific state)
        - Similar time of day (within 30 min window)
        - 10+ occurrences over 2+ weeks

        Returns:
            List of detected patterns, excluding those already stored as memories.
        """
        if not self.influxdb.is_connected:
            logger.warning("InfluxDB not connected, skipping pattern detection")
            return []

        query = f'''
from(bucket: "{self.influxdb.bucket}")
    |> range(start: -{PATTERN_MIN_DAYS}d)
    |> filter(fn: (r) => r._measurement == "state_changed")
    |> filter(fn: (r) => r._field == "state" or r._field == "new_state")
    |> filter(fn: (r) => exists r.entity_id)
    |> keep(columns: ["_time", "entity_id", "_value"])
    |> sort(columns: ["_time"])
'''
        try:
            events = await self.influxdb._execute_query(query)
        except Exception as e:
            logger.error("Failed to query usage pattern events: %s", e)
            return []

        if not events:
            logger.debug("No events found for pattern detection")
            return []

        patterns = self._aggregate_patterns(events)
        filtered = self._filter_patterns_by_criteria(patterns)
        deduplicated = self._deduplicate_patterns(filtered)

        return deduplicated

    def _aggregate_patterns(self, events: list[dict]) -> dict[str, DetectedUsagePattern]:
        """Aggregate events into potential patterns by entity, state, and time window."""
        pattern_buckets: dict[str, list[dict]] = {}

        for event in events:
            entity_id = event.get("entity_id", "")
            state = event.get("_value", "")
            event_time = event.get("_time")

            if not entity_id or not state or not event_time:
                continue

            if isinstance(event_time, str):
                event_time = datetime.fromisoformat(event_time.replace("Z", "+00:00"))

            hour = event_time.hour
            minute_window = (event_time.minute // PATTERN_WINDOW_MINUTES) * PATTERN_WINDOW_MINUTES

            key = f"{entity_id}:{state}:{hour}:{minute_window // 30}"
            if key not in pattern_buckets:
                pattern_buckets[key] = []
            pattern_buckets[key].append({"time": event_time, "event": event})

        patterns: dict[str, DetectedUsagePattern] = {}
        for key, bucket_events in pattern_buckets.items():
            parts = key.split(":")
            entity_id = parts[0]
            state = parts[1]
            hour = int(parts[2])
            window = int(parts[3])

            times = [e["time"] for e in bucket_events]
            first_seen = min(times)
            last_seen = max(times)
            days_span = (last_seen - first_seen).days

            confidence = min(1.0, len(bucket_events) / 20.0) * min(1.0, days_span / 14.0)

            patterns[key] = DetectedUsagePattern(
                entity_id=entity_id,
                state=state,
                hour_of_day=hour,
                minute_window_start=window * 30,
                occurrence_count=len(bucket_events),
                first_seen=first_seen,
                last_seen=last_seen,
                days_span=days_span,
                confidence=round(confidence, 2),
            )

        return patterns

    def _filter_patterns_by_criteria(
        self, patterns: dict[str, DetectedUsagePattern]
    ) -> list[DetectedUsagePattern]:
        """Filter patterns to those meeting minimum occurrence and timespan criteria."""
        filtered = []
        for pattern in patterns.values():
            if (
                pattern.occurrence_count >= PATTERN_MIN_OCCURRENCES
                and pattern.days_span >= PATTERN_MIN_DAYS
            ):
                filtered.append(pattern)

        return filtered

    def _deduplicate_patterns(
        self, patterns: list[DetectedUsagePattern]
    ) -> list[DetectedUsagePattern]:
        """Remove patterns that already have matching memories stored."""
        deduplicated = []
        for pattern in patterns:
            key = pattern.pattern_key()
            if key not in self._existing_pattern_memories:
                deduplicated.append(pattern)
            else:
                logger.debug("Pattern %s already exists as memory, skipping", key)

        return deduplicated

    async def _detect_pattern_drift(
        self, new_patterns: list[DetectedUsagePattern]
    ) -> list[PatternDrift]:
        """Compare current patterns against existing behavioral memories.

        Detects when a pattern has shifted significantly in time, indicating
        the user's routine has changed and memories should be updated.

        Args:
            new_patterns: Newly detected patterns (used to avoid re-querying)

        Returns:
            List of pattern drifts where existing memories need updating.
        """
        drifts: list[PatternDrift] = []

        if not self._existing_pattern_memories:
            return drifts

        all_patterns = await self._get_all_detected_patterns()
        all_patterns.extend(new_patterns)

        for pattern in all_patterns:
            entity_id = pattern.entity_id
            state = pattern.state

            matching_memories = [
                (key, mem)
                for key, mem in self._existing_pattern_memories.items()
                if key.startswith(f"{entity_id}:{state}:")
            ]

            for mem_key, memory in matching_memories:
                mem_parts = mem_key.split(":")
                if len(mem_parts) < 4:
                    continue

                mem_hour = int(mem_parts[2])
                mem_window = int(mem_parts[3])
                mem_minute = mem_window * 30

                pattern_minute = pattern.hour_of_day * 60 + pattern.minute_window_start
                mem_total_minute = mem_hour * 60 + mem_minute

                drift = abs(pattern_minute - mem_total_minute)
                if drift > 720:
                    drift = 1440 - drift

                if drift >= PATTERN_DRIFT_THRESHOLD_MINUTES:
                    original_time = f"{mem_hour:02d}:{mem_minute:02d}"
                    new_time = f"{pattern.hour_of_day:02d}:{pattern.minute_window_start:02d}"

                    drifts.append(
                        PatternDrift(
                            entity_id=entity_id,
                            state=state,
                            original_time=original_time,
                            new_time=new_time,
                            drift_minutes=drift,
                            memory_id=memory.get("id"),
                        )
                    )
                    logger.info(
                        "Pattern drift detected for %s (%s): %s -> %s (%d min)",
                        entity_id,
                        state,
                        original_time,
                        new_time,
                        drift,
                    )

        return drifts

    async def _get_all_detected_patterns(self) -> list[DetectedUsagePattern]:
        """Get all patterns including those that exist as memories for drift comparison."""
        query = f'''
from(bucket: "{self.influxdb.bucket}")
    |> range(start: -{PATTERN_MIN_DAYS}d)
    |> filter(fn: (r) => r._measurement == "state_changed")
    |> filter(fn: (r) => r._field == "state" or r._field == "new_state")
    |> filter(fn: (r) => exists r.entity_id)
    |> keep(columns: ["_time", "entity_id", "_value"])
    |> sort(columns: ["_time"])
'''
        try:
            events = await self.influxdb._execute_query(query)
        except Exception as e:
            logger.error("Failed to query events for drift detection: %s", e)
            return []

        if not events:
            return []

        patterns = self._aggregate_patterns(events)
        return self._filter_patterns_by_criteria(patterns)

    async def _consolidate_patterns(
        self, patterns: list[DetectedUsagePattern]
    ) -> int:
        """Store detected usage patterns as behavioral memories.

        Args:
            patterns: List of new patterns to store

        Returns:
            Number of memories created.
        """
        if not self.consolidator or not patterns:
            return 0

        memories_created = 0

        for pattern in patterns:
            time_str = f"{pattern.hour_of_day:02d}:{pattern.minute_window_start:02d}"
            description = (
                f"Usage pattern for {pattern.entity_id}: "
                f"state {pattern.state} typically at {time_str} "
                f"({pattern.occurrence_count} occurrences over {pattern.days_span} days, "
                f"confidence: {pattern.confidence:.0%})"
            )

            try:
                await self.consolidator.consolidate(
                    content=description,
                    memory_type="behavioral",
                    source_channel="implicit",
                    entity_ids=[pattern.entity_id],
                )
                memories_created += 1
                logger.debug(
                    "Created pattern memory for %s: %s",
                    pattern.entity_id,
                    description,
                )
            except Exception as e:
                logger.error(
                    "Failed to create pattern memory for %s: %s",
                    pattern.entity_id,
                    e,
                )

        return memories_created

    async def _update_drifted_patterns(self, drifts: list[PatternDrift]) -> int:
        """Update memories for patterns that have drifted.

        Args:
            drifts: List of detected pattern drifts

        Returns:
            Number of memories updated.
        """
        if not self.consolidator or not drifts:
            return 0

        memories_updated = 0

        for drift in drifts:
            description = (
                f"Usage pattern for {drift.entity_id}: "
                f"state {drift.state} shifted from {drift.original_time} "
                f"to {drift.new_time} (drift: {drift.drift_minutes} min)"
            )

            try:
                if drift.memory_id and hasattr(self.consolidator, "update"):
                    await self.consolidator.update(
                        memory_id=drift.memory_id,
                        content=description,
                    )
                else:
                    await self.consolidator.consolidate(
                        content=description,
                        memory_type="behavioral",
                        source_channel="implicit",
                        entity_ids=[drift.entity_id],
                    )
                memories_updated += 1
                logger.debug(
                    "Updated drifted pattern for %s: %s",
                    drift.entity_id,
                    description,
                )
            except Exception as e:
                logger.error(
                    "Failed to update drifted pattern for %s: %s",
                    drift.entity_id,
                    e,
                )

        return memories_updated

    def _should_run_routine_synthesis(self) -> bool:
        """Check if routine synthesis should run.

        Runs weekly: on Sundays, or if > 7 days since last routine synthesis.
        """
        now = datetime.now(UTC)
        is_sunday = now.weekday() == 6

        if self._last_routine_synthesis is None:
            return is_sunday

        days_since_last = (now - self._last_routine_synthesis).days
        return is_sunday or days_since_last >= 7

    async def synthesize_routines(self) -> list[RoutineProfile]:
        """Weekly job to synthesize routine profiles from activity data.

        Queries InfluxDB for activity recognition labels over past 4 weeks.
        Builds weekday and weekend profiles.
        Compares to existing routine memories - update if shifted, reinforce if stable.

        Returns:
            List of synthesized RoutineProfile objects.
        """
        if not self.influxdb.is_connected:
            logger.warning("InfluxDB not connected, skipping routine synthesis")
            return []

        await self._load_existing_routine_memories()

        query = f'''
from(bucket: "{self.influxdb.bucket}")
    |> range(start: -{ROUTINE_SYNTHESIS_DAYS}d)
    |> filter(fn: (r) => r._measurement == "activity_label")
    |> filter(fn: (r) => r._field == "label")
    |> filter(fn: (r) => r._value == "waking" or r._value == "leaving"
                      or r._value == "arriving" or r._value == "sleeping")
    |> keep(columns: ["_time", "_value"])
    |> sort(columns: ["_time"])
'''
        try:
            events = await self.influxdb._execute_query(query)
        except Exception as e:
            logger.error("Failed to query activity labels: %s", e)
            return []

        if not events:
            logger.debug("No activity label events found for routine synthesis")
            return []

        weekday_events: dict[str, list[datetime]] = {
            label: [] for label in ROUTINE_LABELS
        }
        weekend_events: dict[str, list[datetime]] = {
            label: [] for label in ROUTINE_LABELS
        }

        for event in events:
            label = event.get("_value", "")
            event_time = event.get("_time")

            if not label or not event_time or label not in ROUTINE_LABELS:
                continue

            if isinstance(event_time, str):
                event_time = datetime.fromisoformat(event_time.replace("Z", "+00:00"))

            is_weekend = event_time.weekday() >= 5
            target = weekend_events if is_weekend else weekday_events
            target[label].append(event_time)

        profiles: list[RoutineProfile] = []

        weekday_profile = self._build_profile("weekday", weekday_events)
        if weekday_profile:
            profiles.append(weekday_profile)

        weekend_profile = self._build_profile("weekend", weekend_events)
        if weekend_profile:
            profiles.append(weekend_profile)

        return profiles

    def _build_profile(
        self, day_type: str, events_by_label: dict[str, list[datetime]]
    ) -> RoutineProfile | None:
        """Build a routine profile from grouped activity events.

        Args:
            day_type: "weekday" or "weekend"
            events_by_label: Dict mapping label names to list of event timestamps

        Returns:
            RoutineProfile if sufficient data, None otherwise.
        """
        sample_days = set()
        for label_events in events_by_label.values():
            for event_time in label_events:
                sample_days.add(event_time.date())

        if len(sample_days) < ROUTINE_MIN_SAMPLES:
            logger.debug(
                "Insufficient sample days for %s profile: %d < %d",
                day_type,
                len(sample_days),
                ROUTINE_MIN_SAMPLES,
            )
            return None

        def median_time(times: list[datetime]) -> str | None:
            if len(times) < ROUTINE_MIN_SAMPLES:
                return None
            minutes = sorted(t.hour * 60 + t.minute for t in times)
            median_mins = minutes[len(minutes) // 2]
            return f"{median_mins // 60:02d}:{median_mins % 60:02d}"

        wake_time = median_time(events_by_label.get("waking", []))
        leave_time = median_time(events_by_label.get("leaving", []))
        return_time = median_time(events_by_label.get("arriving", []))
        sleep_time = median_time(events_by_label.get("sleeping", []))

        if not any([wake_time, leave_time, return_time, sleep_time]):
            logger.debug("No routine times could be calculated for %s", day_type)
            return None

        total_events = sum(len(e) for e in events_by_label.values())
        confidence = min(1.0, len(sample_days) / 14.0) * min(1.0, total_events / 50.0)

        return RoutineProfile(
            day_type=day_type,
            wake_time=wake_time,
            leave_time=leave_time,
            return_time=return_time,
            sleep_time=sleep_time,
            confidence=round(confidence, 2),
            sample_days=len(sample_days),
        )

    def _build_routine_content(self, profile: RoutineProfile) -> str:
        """Format routine as readable content for memory storage.

        Args:
            profile: The routine profile to format

        Returns:
            Human-readable string describing the routine.
        """
        parts = [f"{profile.day_type.title()}:"]
        if profile.wake_time:
            parts.append(f"wake {profile.wake_time}")
        if profile.leave_time:
            parts.append(f"leave {profile.leave_time}")
        if profile.return_time:
            parts.append(f"return {profile.return_time}")
        if profile.sleep_time:
            parts.append(f"sleep {profile.sleep_time}")
        return ", ".join(parts)

    async def _load_existing_routine_memories(self) -> None:
        """Load existing routine memories for comparison and drift detection."""
        self._existing_routine_memories = {}

        if not self.memory:
            return

        try:
            if hasattr(self.memory, "query"):
                memories = await self.memory.query(
                    memory_type="behavioral",
                    source_channel="implicit",
                    limit=100,
                )
                for mem in memories:
                    content = mem.get("content", "")
                    if "routine" in content.lower() and (
                        "weekday" in content.lower() or "weekend" in content.lower()
                    ):
                        day_type = "weekday" if "weekday" in content.lower() else "weekend"
                        self._existing_routine_memories[day_type] = mem
        except Exception as e:
            logger.warning("Failed to load existing routine memories: %s", e)

    async def _consolidate_routines(self, profiles: list[RoutineProfile]) -> int:
        """Store or update routine profiles as behavioral memories.

        For each profile:
        - If no existing memory: create new routine memory
        - If existing but shifted significantly: supersede with new
        - If existing and stable: reinforce (update confidence)

        Args:
            profiles: List of synthesized routine profiles

        Returns:
            Number of memories created or updated.
        """
        if not self.consolidator or not profiles:
            return 0

        memories_created = 0

        for profile in profiles:
            content = self._build_routine_content(profile)
            description = (
                f"Routine profile ({profile.day_type}): {content} "
                f"(confidence: {profile.confidence:.0%}, "
                f"based on {profile.sample_days} days)"
            )

            existing = self._existing_routine_memories.get(profile.day_type)

            try:
                if existing:
                    shift_detected = self._detect_routine_shift(profile, existing)
                    if shift_detected:
                        logger.info(
                            "Routine shift detected for %s, superseding memory",
                            profile.day_type,
                        )
                        if hasattr(self.consolidator, "supersede"):
                            await self.consolidator.supersede(
                                memory_id=existing.get("id"),
                                new_content=description,
                            )
                        else:
                            await self.consolidator.consolidate(
                                content=description,
                                memory_type="behavioral",
                                source_channel="implicit",
                            )
                    else:
                        logger.debug(
                            "Routine %s stable, reinforcing memory",
                            profile.day_type,
                        )
                        if hasattr(self.consolidator, "reinforce"):
                            await self.consolidator.reinforce(
                                memory_id=existing.get("id"),
                            )
                        continue
                else:
                    await self.consolidator.consolidate(
                        content=description,
                        memory_type="behavioral",
                        source_channel="implicit",
                    )

                memories_created += 1
                logger.debug(
                    "Created/updated routine memory for %s: %s",
                    profile.day_type,
                    description,
                )
            except Exception as e:
                logger.error(
                    "Failed to store routine memory for %s: %s",
                    profile.day_type,
                    e,
                )

        return memories_created

    def _detect_routine_shift(
        self, profile: RoutineProfile, existing_memory: dict
    ) -> bool:
        """Detect if a routine has shifted significantly from existing memory.

        Args:
            profile: New routine profile
            existing_memory: Existing routine memory dict

        Returns:
            True if routine has shifted beyond threshold.
        """
        import re

        content = existing_memory.get("content", "")

        time_fields = [
            ("wake", profile.wake_time),
            ("leave", profile.leave_time),
            ("return", profile.return_time),
            ("sleep", profile.sleep_time),
        ]

        for field_name, new_time in time_fields:
            if not new_time:
                continue

            pattern = rf"{field_name}\s+(\d{{2}}):(\d{{2}})"
            match = re.search(pattern, content, re.IGNORECASE)
            if not match:
                continue

            old_hour, old_minute = int(match.group(1)), int(match.group(2))
            new_hour, new_minute = map(int, new_time.split(":"))

            old_total = old_hour * 60 + old_minute
            new_total = new_hour * 60 + new_minute

            diff = abs(new_total - old_total)
            if diff > 720:
                diff = 1440 - diff

            if diff >= ROUTINE_TIME_SHIFT_THRESHOLD_MINUTES:
                logger.debug(
                    "Routine shift detected: %s changed by %d minutes",
                    field_name,
                    diff,
                )
                return True

        return False

    def get_status(self) -> dict:
        """Get job status and statistics.

        Story 32.1: Enhanced with last_run_metrics and history count.
        """
        return {
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "last_routine_synthesis": (
                self._last_routine_synthesis.isoformat()
                if self._last_routine_synthesis
                else None
            ),
            "overrides_detected": self._overrides_detected,
            "patterns_detected": self._patterns_detected,
            "pattern_drifts_detected": self._pattern_drifts_detected,
            "routines_synthesized": self._routines_synthesized,
            "memories_created": self._memories_created,
            "existing_pattern_memories": len(self._existing_pattern_memories),
            "existing_routine_memories": len(self._existing_routine_memories),
            "last_run_metrics": self.get_last_run_metrics(),
            "metrics_history_count": len(self._metrics_history),
            "config": {
                "consolidation_cycle_hours": CONSOLIDATION_CYCLE_HOURS,
                "override_window_minutes": OVERRIDE_WINDOW_MINUTES,
                "override_threshold": OVERRIDE_THRESHOLD,
                "analysis_window_days": ANALYSIS_WINDOW_DAYS,
                "pattern_window_minutes": PATTERN_WINDOW_MINUTES,
                "pattern_min_occurrences": PATTERN_MIN_OCCURRENCES,
                "pattern_min_days": PATTERN_MIN_DAYS,
                "pattern_drift_threshold_minutes": PATTERN_DRIFT_THRESHOLD_MINUTES,
                "routine_synthesis_days": ROUTINE_SYNTHESIS_DAYS,
                "routine_min_samples": ROUTINE_MIN_SAMPLES,
                "routine_time_shift_threshold": ROUTINE_TIME_SHIFT_THRESHOLD_MINUTES,
            },
        }
