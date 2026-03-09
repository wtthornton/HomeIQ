"""
Pattern Analysis Scheduler

Epic 39, Story 39.6: Daily Scheduler Migration
Simplified scheduler focused on pattern detection and synergy detection.
"""

import asyncio
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pandas as pd
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession

from ..clients.data_api_client import DataAPIClient
from ..clients.mqtt_client import MQTTNotificationClient
from ..config import settings
from ..crud import store_patterns, store_synergy_opportunities
from ..database import AsyncSessionLocal
from ..pattern_analyzer.anomaly import AnomalyPatternDetector
from ..pattern_analyzer.co_occurrence import CoOccurrencePatternDetector
from ..pattern_analyzer.contextual import ContextualPatternDetector
from ..pattern_analyzer.day_type import DayTypePatternDetector
from ..pattern_analyzer.duration import DurationPatternDetector
from ..pattern_analyzer.filters import EventFilter
from ..pattern_analyzer.frequency import FrequencyPatternDetector
from ..pattern_analyzer.room_based import RoomBasedPatternDetector
from ..pattern_analyzer.seasonal import SeasonalPatternDetector
from ..pattern_analyzer.sequence import SequencePatternDetector
from ..pattern_analyzer.time_of_day import TimeOfDayPatternDetector
from ..synergy_detection.synergy_detector import DeviceSynergyDetector

logger = logging.getLogger(__name__)

# 2026 Enhancement: Relationship discovery from events
try:
    from ..synergy_detection.relationship_discovery import RelationshipDiscoveryEngine
    RELATIONSHIP_DISCOVERY_AVAILABLE = True
except ImportError as e:
    logger.warning(f"RelationshipDiscoveryEngine not available: {e}")
    RELATIONSHIP_DISCOVERY_AVAILABLE = False
    RelationshipDiscoveryEngine = None

# 2026 Enhancement: Temporal synergy detector
try:
    from ..synergy_detection.temporal_detector import TemporalSynergyDetector
    TEMPORAL_DETECTOR_AVAILABLE = True
except ImportError as e:
    logger.warning(f"TemporalSynergyDetector not available: {e}")
    TEMPORAL_DETECTOR_AVAILABLE = False
    TemporalSynergyDetector = None


class PatternAnalysisScheduler:
    """
    Schedules and runs daily pattern analysis and synergy detection.

    Epic 39, Story 39.6: Daily Scheduler Migration
    Simplified version focused on pattern detection and synergy detection.
    """

    def __init__(self, cron_schedule: str | None = None, enable_incremental: bool = True):
        """
        Initialize the scheduler.

        Args:
            cron_schedule: Cron expression (default: "0 3 * * *" = 3 AM daily)
            enable_incremental: Enable incremental updates (for future use)
        """
        self.scheduler = AsyncIOScheduler()
        self.cron_schedule = cron_schedule or settings.analysis_schedule
        self.is_running = False
        self.enable_incremental = enable_incremental
        self.mqtt_client: MQTTNotificationClient | None = None

        logger.info(
            f"PatternAnalysisScheduler initialized with schedule: {self.cron_schedule}, "
            f"incremental={enable_incremental}"
        )

    def set_mqtt_client(self, mqtt_client: MQTTNotificationClient) -> None:
        """
        Set the MQTT client for notifications.

        Args:
            mqtt_client: MQTT client instance for publishing notifications
        """
        self.mqtt_client = mqtt_client

    def start(self) -> None:
        """
        Start the scheduler and register the daily analysis job.

        Raises:
            Exception: If scheduler fails to start
        """
        try:
            # Add daily analysis job
            self.scheduler.add_job(
                self.run_pattern_analysis,
                CronTrigger.from_crontab(self.cron_schedule),
                id='daily_pattern_analysis',
                name='Daily Pattern Analysis and Synergy Detection',
                replace_existing=True,
                max_instances=1,  # Prevent overlapping runs
            )
            self.scheduler.start()
            self.is_running = True
            logger.info(f"✅ Pattern analysis scheduler started with schedule: {self.cron_schedule}")
        except Exception as e:
            logger.error(f"❌ Failed to start scheduler: {e}", exc_info=True)
            raise

    def stop(self) -> None:
        """
        Stop the scheduler.

        Gracefully shuts down the scheduler and all running jobs.
        """
        try:
            self.scheduler.shutdown(wait=True)
            logger.info("✅ Pattern analysis scheduler stopped")
        except Exception as e:
            logger.error(f"❌ Failed to stop scheduler: {e}", exc_info=True)
        finally:
            # Always mark as stopped, even if shutdown failed
            self.is_running = False

    async def run_pattern_analysis(self) -> None:
        """
        Run pattern detection and synergy detection analysis.

        Epic 39, Story 39.6 + Epic 37, Story 37.9: Full detection pipeline:
        1. Pattern detection (10 detectors: time-of-day, co-occurrence,
           sequence, duration, anomaly, day-type, frequency, room-based,
           seasonal, contextual)
        2. Synergy detection
        3. Store results
        4. Publish MQTT notifications
        """
        start_time = datetime.now(UTC)
        self._log_analysis_start()

        job_result: dict[str, Any] = {
            "status": "running",
            "start_time": start_time.isoformat(),
            "patterns_detected": 0,
            "pattern_based_synergies": 0,
            "regular_synergies": 0,
            "synergies_detected": 0,
            "errors": [],
            "warnings": []
        }

        try:
            async with DataAPIClient(base_url=settings.data_api_url) as data_client:
                events_df = await self._fetch_events(data_client)

                if events_df.empty:
                    await self._handle_empty_events(job_result)
                    return

                # Pre-filter events to exclude external data sources and system noise
                # Recommendation: Add pre-filtering in pattern analysis scheduler
                logger.info("Phase 1.5: Pre-filtering events (external data/system noise)...")
                original_event_count = len(events_df)
                events_df = EventFilter.filter_events(events_df, entity_column='entity_id')
                filtered_event_count = len(events_df)
                if original_event_count != filtered_event_count:
                    logger.info(
                        f"✅ Pre-filtered events: {original_event_count} → {filtered_event_count} "
                        f"({original_event_count - filtered_event_count} excluded)"
                    )

                if events_df.empty:
                    logger.warning("⚠️ No actionable events after filtering")
                    await self._handle_empty_events(job_result)
                    return

                all_patterns = await self._detect_patterns(events_df, job_result)

                # Story 40.8: Cross-detector pattern fusion
                try:
                    from ..services.pattern_fusion import PatternFusionEngine
                    fusion = PatternFusionEngine()
                    all_patterns = fusion.deduplicate(all_patterns)
                    all_patterns = fusion.fuse_patterns(all_patterns)
                    job_result["patterns_detected"] = len(all_patterns)
                except Exception as e:
                    logger.warning(f"Pattern fusion failed (continuing without): {e}")

                # Create database session for pattern validation and storage
                # Patterns are stored first, then synergies are detected with pattern validation
                async with AsyncSessionLocal() as db:
                    # Store patterns first (needed for synergy validation)
                    if all_patterns:
                        automation_validator = None  # Placeholder for future integration
                        stored_patterns = await store_patterns(
                            db,
                            all_patterns,
                            automation_validator=automation_validator
                        )
                        logger.info(f"✅ Stored {stored_patterns} patterns in database")
                        await db.commit()  # Commit patterns so they're available for validation

                        # Story 40.1: Record training data
                        try:
                            from ..services.training_data_service import TrainingDataService
                            training_svc = TrainingDataService(db)
                            events_summary = {
                                "event_count": len(events_df),
                                "time_range_start": str(events_df["timestamp"].min()),
                                "time_range_end": str(events_df["timestamp"].max()),
                                "unique_devices": int(events_df["device_id"].nunique()),
                            }
                            await training_svc.record_detection_run(all_patterns, events_summary)
                            await training_svc.cleanup_old_data()
                            await db.commit()
                        except Exception as e:
                            logger.warning(f"Failed to record training data: {e}")

                        # Recommendation 5.1: Track pattern evolution
                        evolution_results = await self._track_pattern_evolution(all_patterns, job_result, db=db)
                        if evolution_results:
                            job_result["pattern_evolution"] = evolution_results.get('summary', {})
                            logger.info(
                                f"✅ Pattern evolution: {evolution_results['summary'].get('stable_count', 0)} stable, "
                                f"{evolution_results['summary'].get('evolving_count', 0)} evolving, "
                                f"{evolution_results['summary'].get('new_count', 0)} new, "
                                f"{evolution_results['summary'].get('deprecated_count', 0)} deprecated"
                            )

                    # Recommendation 3.1: Generate synergies from patterns
                    pattern_based_synergies = await self._generate_synergies_from_patterns(
                        data_client, all_patterns, job_result, db=db
                    )
                    job_result["pattern_based_synergies"] = len(pattern_based_synergies)
                    logger.info(f"✅ Generated {len(pattern_based_synergies)} synergies from patterns")

                    # Detect synergies with pattern validation (uses patterns just stored)
                    regular_synergies = await self._detect_synergies(data_client, events_df, job_result, db=db)
                    job_result["regular_synergies"] = len(regular_synergies)

                    # Merge pattern-based and regular synergies (pattern-based take precedence for duplicates)
                    synergies = self._merge_synergies(pattern_based_synergies, regular_synergies)
                    job_result["synergies_detected"] = len(synergies)

                    # Story 3.1: Enrich synergies with activity context (same time window as analysis)
                    synergies = await self._enrich_synergies_with_activity(
                        data_client, synergies, events_df, job_result
                    )

                    # Validate pattern-synergy alignment
                    await self._validate_pattern_synergy_alignment(
                        all_patterns, synergies, job_result
                    )

                    # Store synergies (with pattern validation already done during detection)
                    if synergies:
                        stored_result = await store_synergy_opportunities(
                            db,
                            synergies,
                            validate_with_patterns=False  # Already validated during detection
                        )
                        stored_count, filtered_count = stored_result
                        logger.info(f"✅ Stored {stored_count} synergies in database" + (f", filtered {filtered_count} low-quality" if filtered_count > 0 else ""))
                        await db.commit()

        except Exception as e:
            logger.error(f"❌ Pattern analysis failed: {e}", exc_info=True)
            job_result["status"] = "failed"
            job_result["errors"].append(f"Analysis failed: {str(e)}")

        await self._finalize_analysis(start_time, job_result)

    def _log_analysis_start(self) -> None:
        """Log the start of pattern analysis."""
        logger.info("=" * 80)
        logger.info("🔍 Starting Pattern Analysis Run")
        logger.info("=" * 80)

    async def _fetch_events(self, data_client: DataAPIClient) -> pd.DataFrame:
        """
        Fetch events from Data API for pattern detection.

        Args:
            data_client: Data API client instance

        Returns:
            DataFrame containing events from the last 7 days
        """
        logger.info("Phase 1: Fetching events from Data API...")
        end_time = datetime.now(UTC)
        start_time_events = end_time - timedelta(days=7)

        events_df = await data_client.fetch_events(
            start_time=start_time_events,
            end_time=end_time,
            limit=50000  # Reasonable limit for pattern detection
        )

        if not events_df.empty:
            logger.info(f"✅ Fetched {len(events_df)} events for analysis")

        return events_df

    async def _handle_empty_events(self, job_result: dict[str, Any]) -> None:
        """
        Handle the case when no events are found.

        Args:
            job_result: Job result dictionary to update
        """
        logger.warning("⚠️ No events found for pattern analysis")
        job_result["status"] = "completed"
        job_result["end_time"] = datetime.now(UTC).isoformat()
        await self._publish_notification(job_result)

    async def _detect_patterns(
        self,
        events_df: pd.DataFrame,
        job_result: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Detect patterns using all registered detectors.

        Epic 37, Story 37.9: Pattern Service Integration
        Runs all 10 detector types with individual error isolation.

        Args:
            events_df: DataFrame containing events (already pre-filtered)
            job_result: Job result dictionary to update with errors

        Returns:
            List of detected patterns
        """
        logger.info("Phase 2: Running pattern detection (10 detectors)...")
        logger.info(f"  → Input events: {len(events_df)} (pre-filtered)")
        all_patterns: list[dict[str, Any]] = []
        counts: dict[str, int] = {}

        # Define detector pipeline — each entry: (name, coroutine)
        detectors = [
            ("time_of_day", self._detect_time_of_day_patterns(events_df, job_result)),
            ("co_occurrence", self._detect_co_occurrence_patterns(events_df, job_result)),
            ("sequence", self._run_sync_detector("sequence", SequencePatternDetector(), events_df, job_result)),
            ("duration", self._run_sync_detector("duration", DurationPatternDetector(), events_df, job_result)),
            ("anomaly", self._run_sync_detector("anomaly", AnomalyPatternDetector(), events_df, job_result)),
            ("day_type", self._run_sync_detector("day_type", DayTypePatternDetector(), events_df, job_result)),
            ("frequency", self._run_sync_detector("frequency", FrequencyPatternDetector(), events_df, job_result)),
            ("room_based", self._run_sync_detector("room_based", RoomBasedPatternDetector(), events_df, job_result)),
            ("seasonal", self._run_sync_detector("seasonal", SeasonalPatternDetector(min_days_total=10), events_df, job_result)),
            ("contextual", self._run_sync_detector("contextual", ContextualPatternDetector(latitude=settings.contextual_latitude, longitude=settings.contextual_longitude), events_df, job_result)),
        ]

        for name, coro in detectors:
            patterns = await coro
            counts[name] = len(patterns)
            all_patterns.extend(patterns)

        job_result["patterns_detected"] = len(all_patterns)
        job_result["pattern_counts"] = counts
        count_summary = ", ".join(f"{k}:{v}" for k, v in counts.items() if v > 0)
        logger.info(f"✅ Total patterns detected: {len(all_patterns)} ({count_summary})")

        return all_patterns

    async def _run_sync_detector(
        self,
        name: str,
        detector: Any,
        events_df: pd.DataFrame,
        job_result: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Run a synchronous detector in a thread with error isolation.

        Args:
            name: Detector name for logging
            detector: Detector instance with detect_patterns method
            events_df: DataFrame containing events
            job_result: Job result dictionary to update with errors

        Returns:
            List of detected patterns (empty on error)
        """
        try:
            patterns = await asyncio.to_thread(detector.detect_patterns, events_df)
            if patterns:
                logger.info(f"    ✅ {name}: {len(patterns)} patterns")
            return patterns
        except Exception as e:
            logger.error(f"    ❌ {name} detection failed: {e}", exc_info=True)
            job_result["errors"].append(f"{name} detection: {str(e)}")
            return []

    async def _detect_time_of_day_patterns(
        self,
        events_df: pd.DataFrame,
        job_result: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Detect time-of-day patterns.

        Args:
            events_df: DataFrame containing events
            job_result: Job result dictionary to update with errors

        Returns:
            List of time-of-day patterns
        """
        logger.info("  → Running time-of-day detector...")
        try:
            tod_detector = TimeOfDayPatternDetector(
                min_occurrences=settings.time_of_day_occurrence_overrides.get('min_occurrences', 3),
                min_confidence=settings.time_of_day_confidence_overrides.get('min_confidence', 0.6)
            )
            tod_patterns = await asyncio.to_thread(tod_detector.detect_patterns, events_df)
            logger.info(f"    ✅ Found {len(tod_patterns)} time-of-day patterns")
            return tod_patterns
        except Exception as e:
            logger.error(f"    ❌ Time-of-day detection failed: {e}", exc_info=True)
            job_result["errors"].append(f"Time-of-day detection: {str(e)}")
            return []

    async def _detect_co_occurrence_patterns(
        self,
        events_df: pd.DataFrame,
        job_result: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Detect co-occurrence patterns.

        Args:
            events_df: DataFrame containing events
            job_result: Job result dictionary to update with errors

        Returns:
            List of co-occurrence patterns
        """
        logger.info("  → Running co-occurrence detector...")
        try:
            co_detector = CoOccurrencePatternDetector(
                min_support=settings.co_occurrence_support_overrides.get('min_support', 0.1),
                min_confidence=settings.co_occurrence_confidence_overrides.get('min_confidence', 0.5),
                window_minutes=5
            )
            # detect_patterns is now async (Recommendation 2.1: Feedback integration)
            co_patterns = await co_detector.detect_patterns(events_df)
            logger.info(f"    ✅ Found {len(co_patterns)} co-occurrence patterns")
            return co_patterns
        except Exception as e:
            logger.error(f"    ❌ Co-occurrence detection failed: {e}", exc_info=True)
            job_result["errors"].append(f"Co-occurrence detection: {str(e)}")
            return []

    async def _generate_synergies_from_patterns(
        self,
        data_client: DataAPIClient,
        patterns: list[dict[str, Any]],
        job_result: dict[str, Any],
        db: AsyncSession | None = None
    ) -> list[dict[str, Any]]:
        """
        Generate synergies directly from patterns.

        Recommendation 3.1: Use Patterns to Generate Synergies
        - Co-occurrence patterns → device pair synergies
        - Time-of-day patterns → schedule-based synergies
        - Pattern confidence → synergy confidence

        Args:
            data_client: Data API client instance
            patterns: List of detected patterns
            job_result: Job result dictionary to update with errors
            db: Optional database session for additional lookups

        Returns:
            List of synergies generated from patterns
        """
        if not patterns:
            return []

        logger.info("Phase 3.1: Generating synergies from patterns...")
        try:
            # Initialize detector with data_api_client (REQUIRED parameter)
            synergy_detector = DeviceSynergyDetector(data_api_client=data_client)

            # Generate synergies from patterns
            synergies = await synergy_detector.detect_synergies_from_patterns(patterns, db=db)
            logger.info(f"✅ Generated {len(synergies)} synergies from {len(patterns)} patterns")
            return synergies
        except Exception as e:
            logger.error(f"❌ Pattern-to-synergy generation failed: {e}", exc_info=True)
            job_result["errors"].append(f"Pattern-to-synergy generation: {str(e)}")
            return []

    async def _detect_synergies(
        self,
        data_client: DataAPIClient,
        events_df: pd.DataFrame,
        job_result: dict[str, Any],
        db: AsyncSession | None = None
    ) -> list[dict[str, Any]]:
        """
        Detect device synergies.

        Args:
            data_client: Data API client instance
            events_df: DataFrame containing events
            job_result: Job result dictionary to update with errors
            db: Optional database session for pattern validation

        Returns:
            List of detected synergies
        """
        logger.info("Phase 3.2: Running regular synergy detection...")
        all_synergies: list[dict[str, Any]] = []

        try:
            synergy_detector = DeviceSynergyDetector(data_api_client=data_client)
            regular_synergies = await synergy_detector.detect_synergies(db=db)
            logger.info(f"✅ Found {len(regular_synergies)} regular synergy opportunities")
            all_synergies.extend(regular_synergies)

            # 2026 Enhancement: Discover relationships from events
            relationship_synergies = await self._discover_relationships(
                events_df, job_result
            )
            all_synergies.extend(relationship_synergies)

            return all_synergies
        except Exception as e:
            logger.error(f"❌ Synergy detection failed: {e}", exc_info=True)
            job_result["errors"].append(f"Synergy detection: {str(e)}")
            return []

    async def _discover_relationships(
        self,
        events_df: pd.DataFrame,
        job_result: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Discover relationships from events and convert to synergies."""
        if not RELATIONSHIP_DISCOVERY_AVAILABLE or events_df.empty:
            return []

        try:
            logger.info("Phase 3.3: Discovering relationships from events...")
            relationship_engine = RelationshipDiscoveryEngine()
            discovered = await relationship_engine.discover_from_events(events_df)

            if not discovered:
                return []

            logger.info(f"✅ Discovered {len(discovered)} relationships from events")
            synergies = [
                self._relationship_to_synergy(r)
                for r in discovered
                if r.get('confidence', 0.0) >= 0.6
            ]

            if synergies:
                logger.info(f"✅ Converted {len(synergies)} relationships to synergies")
            return synergies
        except Exception as e:
            logger.warning(f"⚠️ Relationship discovery failed: {e}", exc_info=True)
            job_result["errors"].append(f"Relationship discovery: {str(e)}")
            return []

    @staticmethod
    def _relationship_to_synergy(relationship: dict[str, Any]) -> dict[str, Any]:
        """Convert a discovered relationship to a synergy dict."""
        return {
            'synergy_id': str(uuid.uuid4()),
            'synergy_type': 'device_pair',
            'devices': [relationship['device1'], relationship['device2']],
            'trigger_entity': relationship['device1'],
            'action_entity': relationship['device2'],
            'impact_score': relationship.get('confidence', 0.7),
            'confidence': relationship.get('confidence', 0.7),
            'rationale': (
                f"Discovered from event co-occurrence: "
                f"{relationship.get('frequency', 0)} occurrences"
            ),
            'synergy_depth': 2,
            'chain_devices': [relationship['device1'], relationship['device2']],
            'discovery_method': 'relationship_discovery',
        }

    def _merge_synergies(
        self,
        pattern_based_synergies: list[dict[str, Any]],
        regular_synergies: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Merge pattern-based and regular synergies, avoiding duplicates.

        Pattern-based synergies take precedence for duplicates (higher confidence from patterns).

        Args:
            pattern_based_synergies: Synergies generated from patterns
            regular_synergies: Synergies from regular detection

        Returns:
            Merged list of synergies without duplicates
        """
        if not pattern_based_synergies:
            return regular_synergies
        if not regular_synergies:
            return pattern_based_synergies

        # Create a set of device pairs from pattern-based synergies for duplicate detection
        pattern_device_pairs = set()
        for synergy in pattern_based_synergies:
            devices = synergy.get('devices', [])
            if len(devices) >= 2:
                # Create a canonical device pair key (sorted for consistency)
                device_pair = tuple(sorted([devices[0], devices[1]]))
                pattern_device_pairs.add(device_pair)

        # Filter regular synergies to exclude duplicates
        merged_synergies = list(pattern_based_synergies)  # Start with pattern-based

        for synergy in regular_synergies:
            devices = synergy.get('devices', [])
            if len(devices) >= 2:
                device_pair = tuple(sorted([devices[0], devices[1]]))
                if device_pair not in pattern_device_pairs:
                    # Not a duplicate - add to merged list
                    merged_synergies.append(synergy)

        logger.info(
            f"✅ Merged synergies: {len(pattern_based_synergies)} pattern-based + "
            f"{len(regular_synergies)} regular → {len(merged_synergies)} total "
            f"({len(regular_synergies) - (len(merged_synergies) - len(pattern_based_synergies))} duplicates removed)"
        )

        return merged_synergies

    async def _enrich_synergies_with_activity(
        self,
        data_client: DataAPIClient,
        synergies: list[dict[str, Any]],
        _events_df: pd.DataFrame,
        job_result: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Enrich synergy metadata with activity_context from data-api (Story 3.1).

        Fetches activity history for the same time window as events; adds
        activity_context to each synergy's context_metadata. Graceful degradation:
        on data-api failure or empty activity, returns synergies unchanged.
        """
        if not synergies:
            return synergies
        try:
            # Same window as pattern analysis: last 24h (events_df is 7 days but we use 24h for activity)
            activity_items = await data_client.fetch_activity_history(hours=24, limit=100)
            if not activity_items:
                logger.debug("No activity history for enrichment; continuing without activity_context")
                return synergies
            unique_activities = sorted(
                {str(item.get("activity", "")).strip() for item in activity_items if item.get("activity")},
                key=str.lower,
            )
            if not unique_activities:
                return synergies
            logger.info("Enriched synergies with activity_context: %s", unique_activities[:10])
            for syn in synergies:
                ctx = syn.get("context_metadata") or {}
                ctx["activity_context"] = unique_activities
                syn["context_metadata"] = ctx
            return synergies
        except Exception as e:
            logger.warning("Activity enrichment failed (graceful degradation): %s", e)
            job_result.setdefault("warnings", []).append(f"Activity enrichment skipped: {e}")
            return synergies

    async def _validate_pattern_synergy_alignment(
        self,
        all_patterns: list[dict[str, Any]],
        synergies: list[dict[str, Any]],
        job_result: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Validate pattern-synergy alignment.

        Checks if detected patterns have matching synergies and flags misalignments.
        Recommendation: Add pattern-synergy alignment validation with automatic flagging

        Args:
            all_patterns: List of detected patterns
            synergies: List of detected synergies
            job_result: Job result dictionary to update with alignment metrics

        Returns:
            Dictionary with alignment metrics
        """
        logger.info("Phase 3.5: Validating pattern-synergy alignment...")

        if not all_patterns:
            logger.info("  → No patterns to validate")
            return {
                'total_patterns': 0,
                'total_synergies': len(synergies),
                'aligned_patterns': 0,
                'misaligned_patterns': 0,
                'mismatch_rate': 0.0
            }

        # Extract entity IDs from synergies
        synergy_entities: set[str] = set()
        for synergy in synergies:
            synergy_entities.update(self._extract_entities(synergy))

        # Calculate alignment
        aligned_patterns = sum(
            1 for p in all_patterns
            if self._extract_entities(p).intersection(synergy_entities)
        )
        misaligned_patterns = len(all_patterns) - aligned_patterns

        total_patterns = len(all_patterns)
        mismatch_rate = misaligned_patterns / total_patterns if total_patterns > 0 else 0.0

        alignment_results = {
            'total_patterns': total_patterns,
            'total_synergies': len(synergies),
            'aligned_patterns': aligned_patterns,
            'misaligned_patterns': misaligned_patterns,
            'mismatch_rate': mismatch_rate
        }

        # Log alignment results
        logger.info(
            f"  ✅ Alignment validation: {aligned_patterns}/{total_patterns} patterns aligned "
            f"({(1 - mismatch_rate) * 100:.1f}%), {misaligned_patterns} misaligned "
            f"({mismatch_rate * 100:.1f}%)"
        )

        # Flag high mismatch rate
        if mismatch_rate > 0.5:
            logger.warning(
                f"⚠️ High pattern-synergy mismatch rate: {mismatch_rate:.0%} "
                f"({misaligned_patterns}/{total_patterns} patterns without matching synergies)"
            )
            job_result["warnings"] = job_result.get("warnings", [])
            job_result["warnings"].append(
                f"High pattern-synergy mismatch: {mismatch_rate:.0%} "
                f"({misaligned_patterns} patterns without synergies)"
            )

        # Store alignment metrics in job result
        job_result["alignment_metrics"] = alignment_results

        return alignment_results

    async def _track_pattern_evolution(
        self,
        current_patterns: list[dict[str, Any]],
        job_result: dict[str, Any],
        db: AsyncSession | None = None
    ) -> dict[str, Any] | None:
        """
        Track pattern evolution over time.

        Recommendation 5.1: Pattern Evolution Tracking
        - Detect pattern drift (patterns changing)
        - Identify new patterns emerging
        - Flag patterns that are no longer valid

        Args:
            current_patterns: List of currently detected patterns
            job_result: Job result dictionary to update with errors
            db: Database session for retrieving historical patterns

        Returns:
            Evolution analysis results or None if tracking fails
        """
        if not db:
            logger.debug("No database session available for pattern evolution tracking")
            return None

        try:
            from ..services.pattern_evolution_tracker import PatternEvolutionTracker

            tracker = PatternEvolutionTracker(db=db)
            evolution_results = await tracker.track_pattern_evolution(
                current_patterns,
                historical_window_days=30
            )

            return evolution_results
        except Exception as e:
            logger.error(f"Failed to track pattern evolution: {e}", exc_info=True)
            job_result["errors"].append(f"Pattern evolution tracking: {str(e)}")
            return None

    async def _store_results(
        self,
        all_patterns: list[dict[str, Any]],
        synergies: list[dict[str, Any]],
        job_result: dict[str, Any]
    ) -> None:
        """
        Store patterns and synergies in the database.

        Args:
            all_patterns: List of detected patterns
            synergies: List of detected synergies
            job_result: Job result dictionary to update with errors
        """
        logger.info("Phase 4: Storing results in database...")
        from ..database import AsyncSessionLocal

        # Initialize automation validator if HA client available
        automation_validator = None
        # Note: HA client not currently available in pattern service
        # This is a placeholder for future integration
        # For now, external data filtering in EventFilter handles most cases

        async with AsyncSessionLocal() as db:
            try:
                if all_patterns:
                    stored_patterns = await store_patterns(
                        db,
                        all_patterns,
                        automation_validator=automation_validator
                    )
                    logger.info(f"✅ Stored {stored_patterns} patterns in database")

                if synergies:
                    stored_result = await store_synergy_opportunities(
                        db,
                        synergies,
                        validate_with_patterns=False  # Disabled for Story 39.6
                    )
                    stored_count, filtered_count = stored_result
                    logger.info(f"✅ Stored {stored_count} synergies in database" + (f", filtered {filtered_count} low-quality" if filtered_count > 0 else ""))
            except Exception as e:
                logger.error(f"❌ Failed to store results: {e}", exc_info=True)
                job_result["errors"].append(f"Storage: {str(e)}")
                await db.rollback()
            else:
                await db.commit()

    async def _finalize_analysis(
        self,
        start_time: datetime,
        job_result: dict[str, Any]
    ) -> None:
        """
        Finalize analysis and publish notification.

        Args:
            start_time: Analysis start time
            job_result: Job result dictionary to finalize
        """
        end_time = datetime.now(UTC)
        job_result["status"] = "completed" if job_result["status"] == "running" else job_result["status"]
        job_result["end_time"] = end_time.isoformat()
        job_result["duration_seconds"] = (end_time - start_time).total_seconds()

        await self._publish_notification(job_result)

        logger.info("=" * 80)
        logger.info(f"✅ Pattern Analysis Complete ({job_result['duration_seconds']:.1f}s)")
        logger.info(f"   Patterns: {job_result['patterns_detected']}, Synergies: {job_result['synergies_detected']}")

        # Log alignment metrics if available
        if 'alignment_metrics' in job_result:
            alignment = job_result['alignment_metrics']
            logger.info(
                f"   Alignment: {alignment['aligned_patterns']}/{alignment['total_patterns']} patterns "
                f"({(1 - alignment['mismatch_rate']) * 100:.1f}% aligned)"
            )

        if job_result.get("warnings"):
            logger.warning(f"   Warnings: {len(job_result['warnings'])}")
            for warning in job_result['warnings']:
                logger.warning(f"     - {warning}")

        if job_result["errors"]:
            logger.error(f"   Errors: {len(job_result['errors'])}")
            for error in job_result['errors']:
                logger.error(f"     - {error}")
        logger.info("=" * 80)

    async def _publish_notification(self, job_result: dict[str, Any]) -> None:
        """
        Publish MQTT notification about analysis completion.

        Args:
            job_result: Job result dictionary containing analysis results
        """
        if not self.mqtt_client:
            logger.debug("MQTT client not configured, skipping notification")
            return

        try:
            topic = "homeiq/ai-automation/analysis/pattern/complete"
            payload: dict[str, Any] = {
                "service": "ai-pattern-service",
                "timestamp": datetime.now(UTC).isoformat(),
                "status": job_result["status"],
                "patterns_detected": job_result["patterns_detected"],
                "synergies_detected": job_result["synergies_detected"],
                "duration_seconds": job_result.get("duration_seconds", 0),
                "errors": job_result.get("errors", [])
            }

            await self.mqtt_client.publish(topic, payload)
            logger.info(f"✅ Published analysis notification to {topic}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to publish MQTT notification: {e}")

    @staticmethod
    def _extract_entities(item: dict[str, Any]) -> set[str]:
        """Extract entity IDs from a pattern or synergy dict."""
        entities: set[str] = set()
        if 'entities' in item:
            entities.update(item['entities'])
        elif 'device_id' in item:
            entities.add(item['device_id'])
        if 'device1' in item and 'device2' in item:
            entities.update([item['device1'], item['device2']])
        if 'trigger' in item and 'action' in item:
            entities.update([item['trigger'], item['action']])
        return entities

