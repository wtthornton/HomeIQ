"""
Daily Analysis Scheduler
Runs unified AI analysis combining Epic-AI-1 (Pattern Detection) and Epic-AI-2 (Device Intelligence)
on a scheduled basis (default: 3 AM daily)

Story AI2.5: Unified Daily Batch Job
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Epic AI-1 imports (Pattern Detection)
from ..clients.data_api_client import DataAPIClient
from ..clients.device_intelligence_client import DeviceIntelligenceClient
from ..clients.pattern_aggregate_client import (
    PatternAggregateClient,  # Story AI5.4: Incremental processing
)
from ..config import settings
from ..database.crud import (
    get_synergy_opportunities,
    record_analysis_run,
    store_patterns,
    store_suggestion,
)
from ..database.models import get_db_session

# Epic AI-2 imports (Device Intelligence)
from ..device_intelligence import (
    FeatureAnalyzer,
    FeatureSuggestionGenerator,
    update_device_capabilities_batch,
)
from ..llm.openai_client import OpenAIClient
from ..pattern_analyzer.co_occurrence import CoOccurrencePatternDetector
from ..pattern_analyzer.confidence_calibrator import ConfidenceCalibrator
from ..pattern_analyzer.pattern_cross_validator import PatternCrossValidator
from ..pattern_analyzer.pattern_deduplicator import PatternDeduplicator
from ..pattern_analyzer.time_of_day import TimeOfDayPatternDetector
from ..pattern_detection.anomaly_detector import AnomalyDetector
from ..pattern_detection.contextual_detector import ContextualDetector
from ..pattern_detection.day_type_detector import DayTypeDetector
from ..pattern_detection.duration_detector import DurationDetector
from ..pattern_detection.room_based_detector import RoomBasedDetector
from ..pattern_detection.seasonal_detector import SeasonalDetector

# New ML-enhanced pattern detectors
from ..pattern_detection.sequence_detector import SequenceDetector
from ..pattern_detection.session_detector import SessionDetector

logger = logging.getLogger(__name__)


class DailyAnalysisScheduler:
    """Schedules and runs daily pattern analysis and suggestion generation"""

    def __init__(self, cron_schedule: str | None = None, enable_incremental: bool = True):
        """
        Initialize the scheduler.
        
        Args:
            cron_schedule: Cron expression (default: "0 3 * * *" = 3 AM daily)
            enable_incremental: Enable incremental updates for faster processing
        """
        self.scheduler = AsyncIOScheduler()
        self.cron_schedule = cron_schedule or settings.analysis_schedule
        self.is_running = False
        self._job_history = []
        self.enable_incremental = enable_incremental

        # Track last analysis time for incremental updates
        self._last_analysis_time: datetime | None = None
        self._last_pattern_update_time: datetime | None = None

        # MQTT client will be set by main.py
        self.mqtt_client = None

        logger.info(f"DailyAnalysisScheduler initialized with schedule: {self.cron_schedule}, incremental={enable_incremental}")

    def set_mqtt_client(self, mqtt_client):
        """Set the MQTT client from main.py"""
        self.mqtt_client = mqtt_client

    def start(self):
        """
        Start the scheduler and register the daily analysis job.
        """
        try:
            # Add daily analysis job
            self.scheduler.add_job(
                self.run_daily_analysis,
                CronTrigger.from_crontab(self.cron_schedule),
                id='daily_pattern_analysis',
                name='Daily Pattern Analysis and Suggestion Generation',
                replace_existing=True,
                misfire_grace_time=3600  # Allow up to 1 hour late start
            )

            self.scheduler.start()
            logger.info(f"✅ Scheduler started: daily analysis at {self.cron_schedule}")
            logger.info(f"   Next run: {self.scheduler.get_job('daily_pattern_analysis').next_run_time}")

        except Exception as e:
            logger.error(f"❌ Failed to start scheduler: {e}", exc_info=True)
            raise

    def stop(self):
        """
        Stop the scheduler gracefully.
        """
        try:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=True)
                logger.info("✅ Scheduler stopped")

            # Disconnect MQTT
            if self.mqtt_client:
                self.mqtt_client.disconnect()
                logger.info("✅ MQTT disconnected")

        except Exception as e:
            logger.error(f"❌ Failed to stop scheduler: {e}", exc_info=True)

    async def _get_home_type(self) -> str | None:
        """
        Get home type for threshold adjustment (Home Type Integration).
        
        Returns:
            Home type string (e.g., 'standard_home') or None if detection fails
        """
        try:
            from ..clients.home_type_client import HomeTypeClient
            from ..config import settings
            home_type_client = HomeTypeClient(
                base_url="http://ai-automation-service:8018",
                api_key=settings.ai_automation_api_key
            )
            home_type_data = await home_type_client.get_home_type(use_cache=True)
            home_type = home_type_data.get('home_type', 'standard_home')
            logger.info(f"🏠 Home type detected: {home_type} (confidence: {home_type_data.get('confidence', 0.0):.2f})")
            await home_type_client.close()
            return home_type
        except Exception as e:
            logger.warning(f"⚠️ Failed to get home type: {e}, using default thresholds")
            return None

    def _initialize_data_client(self) -> DataAPIClient:
        """
        Initialize DataAPIClient with settings.
        
        Returns:
            Initialized DataAPIClient instance
        """
        return DataAPIClient(
            base_url=settings.data_api_url,
            influxdb_url=settings.influxdb_url,
            influxdb_token=settings.influxdb_token,
            influxdb_org=settings.influxdb_org,
            influxdb_bucket=settings.influxdb_bucket
        )

    async def _phase_1_device_capability_update(
        self,
        data_client: DataAPIClient,
        job_result: dict[str, Any]
    ) -> None:
        """
        Phase 1: Device Capability Update (Epic AI-2).
        
        Updates device capabilities in batch and records statistics.
        
        Args:
            data_client: DataAPIClient instance
            job_result: Job result dictionary to update with statistics
        """
        logger.info("📡 Phase 1/6: Device Capability Update (Epic AI-2)...")

        try:
            capability_stats = await update_device_capabilities_batch(
                mqtt_client=self.mqtt_client,
                data_api_client=data_client,
                db_session_factory=get_db_session
            )

            logger.info("✅ Device capabilities updated:")
            logger.info(f"   - Devices checked: {capability_stats['devices_checked']}")
            logger.info(f"   - Capabilities updated: {capability_stats['capabilities_updated']}")
            logger.info(f"   - New devices: {capability_stats['new_devices']}")
            logger.info(f"   - Errors: {capability_stats['errors']}")

            job_result['devices_checked'] = capability_stats['devices_checked']
            job_result['capabilities_updated'] = capability_stats['capabilities_updated']
            job_result['new_devices'] = capability_stats['new_devices']

        except Exception as e:
            logger.error(f"⚠️ Device capability update failed: {e}")
            logger.info("   → Continuing with pattern analysis...")
            job_result['devices_checked'] = 0
            job_result['capabilities_updated'] = 0

    async def _phase_2_fetch_events(
        self,
        data_client: DataAPIClient,
        job_result: dict[str, Any]
    ) -> Any:  # Returns pd.DataFrame | None
        """
        Phase 2: Fetch Historical Events (Shared by AI-1 + AI-2 + AI-3).
        
        Fetches events from InfluxDB with fallback to shorter time periods if needed.
        
        Args:
            data_client: DataAPIClient instance
            job_result: Job result dictionary to update with statistics
        
        Returns:
            DataFrame with events, or None if no events found (job_result updated to 'no_data')
        """
        logger.info("📊 Phase 2/6: Fetching events (SHARED by AI-1 + AI-2)...")

        # Use 7 days lookback (or adjust based on available data)
        # If no events found, try shorter periods
        start_date = datetime.now(timezone.utc) - timedelta(days=7)

        events_df = await data_client.fetch_events(
            start_time=start_date,
            limit=100000
        )

        # If no events with 7 days, try 24 hours
        if events_df.empty:
            logger.info("No events in last 7 days, trying last 24 hours...")
            start_date = datetime.now(timezone.utc) - timedelta(hours=24)
            events_df = await data_client.fetch_events(
                start_time=start_date,
                limit=100000
            )

        if events_df.empty:
            logger.warning("❌ No events available for analysis")
            job_result['status'] = 'no_data'
            job_result['events_count'] = 0
            return None

        logger.info(f"✅ Fetched {len(events_df)} events")
        job_result['events_count'] = len(events_df)
        return events_df

    async def _phase_4_feature_analysis(
        self,
        data_client: DataAPIClient,
        job_result: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Phase 4: Feature Analysis (Epic AI-2).
        
        Analyzes device features and identifies opportunities.
        
        Args:
            data_client: DataAPIClient instance
            job_result: Job result dictionary to update with statistics
        
        Returns:
            List of feature opportunities (empty list on error)
        """
        logger.info("🧠 Phase 4/7: Feature Analysis (Epic AI-2)...")

        try:
            # Initialize Device Intelligence Service client
            device_intelligence_client = DeviceIntelligenceClient(
                base_url=settings.device_intelligence_url
            )

            feature_analyzer = FeatureAnalyzer(
                device_intelligence_client=device_intelligence_client,
                db_session=get_db_session,
                influxdb_client=data_client.influxdb_client
            )

            analysis_result = await feature_analyzer.analyze_all_devices()

            if analysis_result.get('skipped'):
                skip_reason = analysis_result.get('skip_reason', 'unknown')
                logger.warning(f"⚠️ Feature analysis skipped: {skip_reason}")
                opportunities = []
                job_result['feature_analysis_skipped'] = True
                job_result['feature_analysis_skip_reason'] = skip_reason
                job_result['stale_capabilities'] = analysis_result.get('stale_capabilities', {})
                job_result['devices_analyzed'] = 0
                job_result['opportunities_found'] = 0
                job_result['avg_utilization'] = 0
            else:
                opportunities = analysis_result.get('opportunities', [])

                logger.info("✅ Feature analysis complete:")
                logger.info(f"   - Devices analyzed: {analysis_result.get('devices_analyzed', 0)}")
                logger.info(f"   - Opportunities found: {len(opportunities)}")
                logger.info(f"   - Average utilization: {analysis_result.get('avg_utilization', 0):.1f}%")

                job_result['devices_analyzed'] = analysis_result.get('devices_analyzed', 0)
                job_result['opportunities_found'] = len(opportunities)
                job_result['avg_utilization'] = analysis_result.get('avg_utilization', 0)

            return opportunities

        except Exception as e:
            logger.error(f"⚠️ Feature analysis failed: {e}")
            logger.info("   → Continuing with suggestions...")
            job_result['devices_analyzed'] = 0
            job_result['opportunities_found'] = 0
            return []

    async def run_daily_analysis(self):
        """
        Unified daily batch job workflow (Story AI2.5, Enhanced for Epic AI-3):
        
        Phase 1: Device Capability Update (Epic AI-2)
        Phase 2: Fetch Historical Events (Shared by AI-1 + AI-2 + AI-3)
        Phase 3: Pattern Detection (Epic AI-1)
        Phase 3c: Synergy Detection (Epic AI-3) - NEW
        Phase 4: Feature Analysis (Epic AI-2)
        Phase 5: Combined Suggestion Generation (AI-1 + AI-2 + AI-3)
        Phase 6: Publish Notification & Store Results
        
        This method is called by the scheduler automatically at 3 AM daily.
        Story AI2.5: Unified Daily Batch Job (Enhanced Story AI3.1)
        """
        # Prevent concurrent runs
        if self.is_running:
            logger.warning("⚠️ Previous analysis still running, skipping this run")
            return

        self.is_running = True
        start_time = datetime.now(timezone.utc)
        job_result = {
            'start_time': start_time.isoformat(),
            'status': 'running'
        }

        try:
            logger.info("=" * 80)
            logger.info("🚀 Unified Daily AI Analysis Started (Epic AI-1 + AI-2 + AI-3)")
            logger.info("=" * 80)
            logger.info(f"Timestamp: {start_time.isoformat()}")

            # Get home type for threshold adjustment (Home Type Integration)
            home_type = await self._get_home_type()

            if getattr(settings, "enable_pdl_workflows", False):
                try:
                    from ..pdl.runtime import PDLExecutionError, PDLInterpreter

                    script_path = Path(__file__).resolve().parent.parent / "pdl" / "scripts" / "nightly_batch.yaml"
                    interpreter = PDLInterpreter.from_file(script_path, logger)
                    await interpreter.run(
                        {
                            "mqtt_connected": bool(self.mqtt_client and getattr(self.mqtt_client, "is_connected", False)),
                            "incremental_enabled": self.enable_incremental,
                        }
                    )
                except PDLExecutionError as pdl_exc:
                    logger.error("❌ PDL nightly batch guardrail violation: %s", pdl_exc)
                    return
                except Exception as pdl_exc:  # pragma: no cover - defensive logging
                    logger.warning(
                        "⚠️ Failed to execute nightly batch PDL script (%s). Continuing with standard workflow.",
                        pdl_exc,
                        exc_info=True,
                    )

            # Initialize data client (used by multiple phases)
            data_client = self._initialize_data_client()

            # Phase 1: Device Capability Update
            await self._phase_1_device_capability_update(data_client, job_result)

            # Phase 2: Fetch Events
            events_df = await self._phase_2_fetch_events(data_client, job_result)
            if events_df is None or events_df.empty:
                return  # Early return if no events

            # ================================================================
            # Initialize Pattern Aggregate Client (Story AI5.4)
            # ================================================================
            logger.info("📦 Initializing Pattern Aggregate Client for incremental processing...")

            aggregate_client = PatternAggregateClient(
                url=settings.influxdb_url,
                token=settings.influxdb_token,
                org=settings.influxdb_org,
                bucket_daily="pattern_aggregates_daily",
                bucket_weekly="pattern_aggregates_weekly"
            )

            logger.info("✅ Pattern Aggregate Client initialized")

            # ================================================================
            # Phase 3: Pattern Detection (Epic AI-1) - Incremental Processing (Story AI5.4)
            # ================================================================
            logger.info("🔍 Phase 3/6: Pattern Detection (Epic AI-1) - Incremental Processing (Story AI5.4)...")

            all_patterns = []

            # Improvement: Initialize detector health monitor
            from ..pattern_detection.detector_health_monitor import DetectorHealthMonitor
            import time
            health_monitor = DetectorHealthMonitor()
            
            # Helper function to track detector execution
            async def run_detector_with_monitoring(
                detector_name: str,
                detector_func,
                *args,
                **kwargs
            ) -> list[dict]:
                """Run detector with health monitoring"""
                start_time = time.time()
                patterns = []
                error = None
                try:
                    if asyncio.iscoroutinefunction(detector_func):
                        patterns = await detector_func(*args, **kwargs)
                    else:
                        patterns = detector_func(*args, **kwargs)
                except Exception as e:
                    error = e
                    logger.error(f"Detector {detector_name} failed: {e}", exc_info=True)
                
                processing_time = time.time() - start_time
                health_monitor.track_detection_run(
                    detector_name=detector_name,
                    patterns_found=len(patterns),
                    processing_time=processing_time,
                    error=error
                )
                return patterns
            
            # Time-of-day patterns (Story AI5.3: Incremental processing enabled)
            logger.info("  → Running time-of-day detector (incremental)...")
            try:
                tod_detector = TimeOfDayPatternDetector(
                    min_occurrences=settings.time_of_day_min_occurrences,
                    min_confidence=settings.time_of_day_base_confidence,
                    aggregate_client=aggregate_client,  # Story AI5.4: Pass aggregate client
                    domain_occurrence_overrides=dict(settings.time_of_day_occurrence_overrides),
                    domain_confidence_overrides=dict(settings.time_of_day_confidence_overrides)
                )
                logger.info("  → Running co-occurrence detector (incremental)...")
                # Quality improvement: Increased thresholds for better pattern quality
                # min_support: 5 → 10, min_confidence: 0.7 → 0.75
                co_detector = CoOccurrencePatternDetector(
                    window_minutes=5,
                    min_support=max(10, settings.co_occurrence_min_support),  # Quality: increased from 5 to 10
                    min_confidence=max(0.75, settings.co_occurrence_base_confidence),  # Quality: increased from 0.7 to 0.75
                    aggregate_client=aggregate_client,  # Story AI5.4: Pass aggregate client
                    domain_support_overrides=dict(settings.co_occurrence_support_overrides),
                    domain_confidence_overrides=dict(settings.co_occurrence_confidence_overrides)
                )

                tod_patterns = []
                co_patterns = []
                chain_used = False

                if getattr(settings, "enable_langchain_pattern_chain", False):
                    try:
                        from ..langchain_integration.pattern_chain import build_pattern_detection_chain

                        chain_inputs = {
                            "events_df": events_df,
                            "last_update": self._last_pattern_update_time,
                            "incremental": self.enable_incremental,
                            "current_run_time": datetime.now(timezone.utc),
                        }
                        pattern_chain = build_pattern_detection_chain(
                            tod_detector=tod_detector,
                            co_detector=co_detector,
                        )
                        chain_result = await pattern_chain.ainvoke(chain_inputs)
                        tod_patterns = chain_result.get("time_of_day_patterns", [])
                        co_patterns = chain_result.get("co_occurrence_patterns", [])
                        self._last_pattern_update_time = chain_result.get("last_update", datetime.now(timezone.utc))
                        chain_used = True
                        logger.info("🧱 LangChain pattern chain executed for time-of-day and co-occurrence detectors.")
                    except Exception as chain_exc:  # pragma: no cover - defensive logging
                        logger.warning(
                            "⚠️ LangChain pattern chain failed (%s); reverting to legacy detection.",
                            chain_exc,
                            exc_info=True,
                        )

                if not chain_used:
                    if self.enable_incremental and self._last_pattern_update_time and hasattr(tod_detector, 'incremental_update'):
                        logger.info(f"    → Using incremental update (last update: {self._last_pattern_update_time})")
                        tod_patterns = await run_detector_with_monitoring(
                            'TimeOfDayPatternDetector',
                            tod_detector.incremental_update,
                            events_df,
                            self._last_pattern_update_time
                        )
                    else:
                        tod_patterns = await run_detector_with_monitoring(
                            'TimeOfDayPatternDetector',
                            tod_detector.detect_patterns,
                            events_df
                        )

                    self._last_pattern_update_time = datetime.now(timezone.utc)

                    if self.enable_incremental and self._last_pattern_update_time and hasattr(co_detector, 'incremental_update'):
                        logger.info(f"    → Using incremental update (last update: {self._last_pattern_update_time})")
                        co_patterns = await run_detector_with_monitoring(
                            'CoOccurrencePatternDetector',
                            co_detector.incremental_update,
                            events_df,
                            self._last_pattern_update_time
                        )
                    else:
                        if len(events_df) > 10000:
                            co_patterns = await run_detector_with_monitoring(
                                'CoOccurrencePatternDetector',
                                co_detector.detect_patterns_optimized,
                                events_df
                            )
                        else:
                            co_patterns = await run_detector_with_monitoring(
                                'CoOccurrencePatternDetector',
                                co_detector.detect_patterns,
                                events_df
                            )

                    logger.info(f"    ✅ Legacy detectors found {len(tod_patterns)} time-of-day patterns and {len(co_patterns)} co-occurrence patterns")

                all_patterns.extend(tod_patterns)
                logger.info(f"    ✅ Total time-of-day patterns appended: {len(tod_patterns)}")

                all_patterns.extend(co_patterns)
                logger.info(f"    ✅ Total co-occurrence patterns appended: {len(co_patterns)}")
            except Exception as e:
                logger.error(f"❌ Time-of-day/co-occurrence detection failed: {e}", exc_info=True)
                # Continue with other detectors even if these fail

            # ML-Enhanced Pattern Detection (Story AI5.3: Incremental processing enabled)
            logger.info("  → Running ML-enhanced pattern detectors (incremental)...")

            # Sequence patterns (Story AI5.3: Incremental processing enabled)
            logger.info("    → Running sequence detector (incremental)...")
            sequence_detector = SequenceDetector(
                window_minutes=30,
                min_sequence_length=2,
                min_sequence_occurrences=3,  # Quality: decreased from 5 to 3 for more patterns
                min_confidence=0.65,  # Quality: decreased from 0.7 to 0.65 for more patterns
                enable_incremental=self.enable_incremental,
                aggregate_client=aggregate_client  # Story AI5.4: Pass aggregate client
            )
            # Use incremental update if enabled and previous run exists
            if self.enable_incremental and self._last_pattern_update_time and hasattr(sequence_detector, 'incremental_update'):
                sequence_patterns = await run_detector_with_monitoring(
                    'SequenceDetector',
                    sequence_detector.incremental_update,
                    events_df,
                    self._last_pattern_update_time
                )
            else:
                sequence_patterns = await run_detector_with_monitoring(
                    'SequenceDetector',
                    sequence_detector.detect_patterns,
                    events_df
                )
            all_patterns.extend(sequence_patterns)
            logger.info(f"    ✅ Found {len(sequence_patterns)} sequence patterns (daily aggregates stored)")

            # Contextual patterns (Story AI5.8: Monthly aggregation enabled)
            logger.info("    → Running contextual detector (monthly aggregates)...")
            # Adjust thresholds based on home type (Home Type Integration)
            if home_type:
                from ..home_type.integration_helpers import adjust_pattern_thresholds
                context_min_confidence, context_min_occurrences = adjust_pattern_thresholds(
                    home_type,
                    base_min_confidence=0.6,
                    base_min_occurrences=5
                )
                logger.debug(f"   Adjusted thresholds for {home_type}: confidence={context_min_confidence:.2f}, occurrences={context_min_occurrences}")
            else:
                context_min_confidence = 0.6
                context_min_occurrences = 5
            
            contextual_detector = ContextualDetector(
                weather_weight=0.3,
                presence_weight=0.4,
                time_weight=0.3,
                min_context_occurrences=context_min_occurrences,
                min_confidence=context_min_confidence,
                enable_incremental=self.enable_incremental,
                aggregate_client=aggregate_client  # Story AI5.8: Pass aggregate client for monthly aggregates
            )
            # Use incremental update if enabled and previous run exists
            if self.enable_incremental and self._last_pattern_update_time and hasattr(contextual_detector, 'incremental_update'):
                contextual_patterns = await run_detector_with_monitoring(
                    'ContextualDetector',
                    contextual_detector.incremental_update,
                    events_df,
                    self._last_pattern_update_time
                )
            else:
                contextual_patterns = await run_detector_with_monitoring(
                    'ContextualDetector',
                    contextual_detector.detect_patterns,
                    events_df
                )
            all_patterns.extend(contextual_patterns)
            logger.info(f"    ✅ Found {len(contextual_patterns)} contextual patterns (monthly aggregates stored)")

            # Room-based patterns (Story AI5.3: Incremental processing enabled)
            logger.info("    → Running room-based detector (incremental)...")
            # Adjust thresholds based on home type (Home Type Integration)
            if home_type:
                from ..home_type.integration_helpers import adjust_pattern_thresholds
                room_min_confidence, room_min_occurrences = adjust_pattern_thresholds(
                    home_type,
                    base_min_confidence=0.7,
                    base_min_occurrences=10
                )
                logger.debug(f"   Adjusted thresholds for {home_type}: confidence={room_min_confidence:.2f}, occurrences={room_min_occurrences}")
            else:
                room_min_confidence = 0.7
                room_min_occurrences = 10
            
            room_detector = RoomBasedDetector(
                min_room_occurrences=room_min_occurrences,
                min_confidence=room_min_confidence,
                enable_incremental=self.enable_incremental,
                aggregate_client=aggregate_client  # Story AI5.4: Pass aggregate client
            )
            # Use incremental update if enabled and previous run exists
            if self.enable_incremental and self._last_pattern_update_time and hasattr(room_detector, 'incremental_update'):
                room_patterns = await run_detector_with_monitoring(
                    'RoomBasedDetector',
                    room_detector.incremental_update,
                    events_df,
                    self._last_pattern_update_time
                )
            else:
                room_patterns = await run_detector_with_monitoring(
                    'RoomBasedDetector',
                    room_detector.detect_patterns,
                    events_df
                )
            all_patterns.extend(room_patterns)
            logger.info(f"    ✅ Found {len(room_patterns)} room-based patterns (daily aggregates stored)")

            # Session patterns (Story AI5.6: Weekly aggregation enabled)
            logger.info("    → Running session detector (weekly aggregates)...")
            session_detector = SessionDetector(
                session_gap_minutes=60,
                min_session_occurrences=3,
                min_confidence=0.7,
                enable_incremental=self.enable_incremental,
                aggregate_client=aggregate_client  # Story AI5.6: Pass aggregate client for weekly aggregates
            )
            # Use incremental update if enabled and previous run exists
            if self.enable_incremental and self._last_pattern_update_time and hasattr(session_detector, 'incremental_update'):
                session_patterns = await run_detector_with_monitoring(
                    'SessionDetector',
                    session_detector.incremental_update,
                    events_df,
                    self._last_pattern_update_time
                )
            else:
                session_patterns = await run_detector_with_monitoring(
                    'SessionDetector',
                    session_detector.detect_patterns,
                    events_df
                )
            all_patterns.extend(session_patterns)
            logger.info(f"    ✅ Found {len(session_patterns)} session patterns (weekly aggregates stored)")

            # Duration patterns (Story AI5.3: Incremental processing enabled)
            logger.info("    → Running duration detector (incremental)...")
            duration_detector = DurationDetector(
                min_duration_seconds=300,  # 5 minutes in seconds
                max_duration_hours=24,
                min_occurrences=10,  # Increased from 3 to 10 for better quality
                min_confidence=0.7,
                enable_incremental=self.enable_incremental,
                aggregate_client=aggregate_client  # Story AI5.4: Pass aggregate client
            )
            # Use incremental update if enabled and previous run exists
            if self.enable_incremental and self._last_pattern_update_time and hasattr(duration_detector, 'incremental_update'):
                duration_patterns = await run_detector_with_monitoring(
                    'DurationDetector',
                    duration_detector.incremental_update,
                    events_df,
                    self._last_pattern_update_time
                )
            else:
                duration_patterns = await run_detector_with_monitoring(
                    'DurationDetector',
                    duration_detector.detect_patterns,
                    events_df
                )
            all_patterns.extend(duration_patterns)
            logger.info(f"    ✅ Found {len(duration_patterns)} duration patterns (daily aggregates stored)")

            # Day-type patterns (Story AI5.6: Weekly aggregation enabled)
            logger.info("    → Running day-type detector (weekly aggregates)...")
            day_type_detector = DayTypeDetector(
                min_day_type_occurrences=10,  # Increased from 5 to 10 for better quality
                min_confidence=0.7,
                enable_incremental=self.enable_incremental,
                aggregate_client=aggregate_client  # Story AI5.6: Pass aggregate client for weekly aggregates
            )
            # Use incremental update if enabled and previous run exists
            if self.enable_incremental and self._last_pattern_update_time and hasattr(day_type_detector, 'incremental_update'):
                day_type_patterns = await run_detector_with_monitoring(
                    'DayTypeDetector',
                    day_type_detector.incremental_update,
                    events_df,
                    self._last_pattern_update_time
                )
            else:
                day_type_patterns = await run_detector_with_monitoring(
                    'DayTypeDetector',
                    day_type_detector.detect_patterns,
                    events_df
                )
            all_patterns.extend(day_type_patterns)
            logger.info(f"    ✅ Found {len(day_type_patterns)} day-type patterns (weekly aggregates stored)")

            # Seasonal patterns (Story AI5.8: Monthly aggregation enabled)
            logger.info("    → Running seasonal detector (monthly aggregates)...")
            seasonal_detector = SeasonalDetector(
                min_seasonal_occurrences=10,
                seasonal_window_days=30,
                weather_integration=True,
                min_confidence=0.7,
                enable_incremental=self.enable_incremental,
                aggregate_client=aggregate_client  # Story AI5.8: Pass aggregate client for monthly aggregates
            )
            # Use incremental update if enabled and previous run exists
            if self.enable_incremental and self._last_pattern_update_time and hasattr(seasonal_detector, 'incremental_update'):
                seasonal_patterns = await run_detector_with_monitoring(
                    'SeasonalDetector',
                    seasonal_detector.incremental_update,
                    events_df,
                    self._last_pattern_update_time
                )
            else:
                seasonal_patterns = await run_detector_with_monitoring(
                    'SeasonalDetector',
                    seasonal_detector.detect_patterns,
                    events_df
                )
            all_patterns.extend(seasonal_patterns)
            logger.info(f"    ✅ Found {len(seasonal_patterns)} seasonal patterns (monthly aggregates stored)")

            # Anomaly patterns (Story AI5.3: Incremental processing enabled)
            logger.info("    → Running anomaly detector (incremental)...")
            anomaly_detector = AnomalyDetector(
                contamination=0.1,
                min_anomaly_occurrences=3,
                anomaly_window_hours=24,
                enable_timing_analysis=True,
                enable_behavioral_analysis=True,
                enable_device_analysis=True,
                min_confidence=0.7,
                enable_incremental=self.enable_incremental,
                aggregate_client=aggregate_client  # Story AI5.4: Pass aggregate client
            )
            # Use incremental update if enabled and previous run exists
            if self.enable_incremental and self._last_pattern_update_time and hasattr(anomaly_detector, 'incremental_update'):
                anomaly_patterns = await run_detector_with_monitoring(
                    'AnomalyDetector',
                    anomaly_detector.incremental_update,
                    events_df,
                    self._last_pattern_update_time
                )
            else:
                anomaly_patterns = await run_detector_with_monitoring(
                    'AnomalyDetector',
                    anomaly_detector.detect_patterns,
                    events_df
                )
            all_patterns.extend(anomaly_patterns)
            logger.info(f"    ✅ Found {len(anomaly_patterns)} anomaly patterns (daily aggregates stored)")

            # Multi-factor pattern detection (NEW - Enhanced Pattern Detection)
            logger.info("    → Running multi-factor detector (time + presence + weather)...")
            try:
                from ..pattern_detection.multi_factor_detector import MultiFactorPatternDetector
                multi_factor_detector = MultiFactorPatternDetector(
                    time_factors=['time_of_day', 'day_of_week', 'season'],
                    presence_factors=['presence'],
                    weather_factors=['temperature', 'humidity'],
                    min_pattern_occurrences=5,  # Quality: decreased from 10 to 5 for more patterns
                    min_confidence=0.65,  # Quality: decreased from 0.7 to 0.65 for more patterns
                    aggregate_client=aggregate_client
                )
                multi_factor_patterns = await run_detector_with_monitoring(
                    'MultiFactorPatternDetector',
                    multi_factor_detector.detect_patterns,
                    events_df
                )
                all_patterns.extend(multi_factor_patterns)
                logger.info(f"    ✅ Found {len(multi_factor_patterns)} multi-factor patterns")
            except Exception as e:
                logger.warning(f"    ⚠️ Multi-factor detection failed: {e}")

            # Update last analysis time after pattern detection completes
            self._last_analysis_time = datetime.now(timezone.utc)
            if self._last_pattern_update_time is None:
                self._last_pattern_update_time = self._last_analysis_time

            logger.info(f"✅ Total patterns detected: {len(all_patterns)}")
            
            # Improvement: Pattern lifecycle management
            logger.info("🔄 Running pattern lifecycle management...")
            try:
                from ..pattern_detection.pattern_lifecycle_manager import PatternLifecycleManager
                lifecycle_manager = PatternLifecycleManager(
                    stale_threshold_days=60,
                    deletion_threshold_days=90,
                    validation_window_days=30
                )
                async with get_db_session() as db:
                    lifecycle_results = await lifecycle_manager.manage_pattern_lifecycle(db)
                    logger.info(
                        f"✅ Lifecycle management: {lifecycle_results['deprecated_count']} deprecated, "
                        f"{lifecycle_results['deleted_count']} deleted, "
                        f"{lifecycle_results['needs_review_count']} need review"
                    )
                    job_result['lifecycle_management'] = lifecycle_results
            except Exception as e:
                logger.warning(f"⚠️ Pattern lifecycle management failed: {e}")
                job_result['lifecycle_management'] = {'error': str(e)}
            logger.info("   📦 Aggregates stored: 6 Group A (daily), 2 Group B (weekly), 2 Group C (monthly)")
            if self.enable_incremental:
                stats_summary = {}
                detector_names = [
                    'tod_detector', 'co_detector', 'sequence_detector', 'contextual_detector',
                    'room_detector', 'session_detector', 'duration_detector',
                    'day_type_detector', 'seasonal_detector', 'anomaly_detector'
                ]
                for detector_name in detector_names:
                    if detector_name in locals():
                        detector = locals()[detector_name]
                        if hasattr(detector, 'get_detection_stats'):
                            stats = detector.get_detection_stats()
                            incremental = stats.get('incremental_updates', 0)
                            full = stats.get('full_analyses', 0)
                            if incremental > 0 or full > 0:
                                stats_summary[detector_name] = {
                                    'incremental': incremental,
                                    'full': full
                                }
                if stats_summary:
                    logger.info(f"   ⚡ Incremental update stats: {stats_summary}")
            job_result['patterns_detected'] = len(all_patterns)

            # Quality improvement: Deduplicate patterns
            if all_patterns:
                logger.info("🧹 Deduplicating patterns...")
                try:
                    deduplicator = PatternDeduplicator()
                    all_patterns = deduplicator.deduplicate_patterns(all_patterns)
                    logger.info(f"   ✅ Deduplication complete: {len(all_patterns)} unique patterns")
                except Exception as e:
                    logger.warning(f"⚠️ Pattern deduplication failed: {e}, continuing...")

            # Quality improvement: Cross-validate patterns
            if all_patterns:
                logger.info("🔍 Cross-validating patterns for consistency...")
                try:
                    validator = PatternCrossValidator()
                    validation_results = await validator.cross_validate(all_patterns)

                    contradictions = len(validation_results['contradictions'])
                    redundancies = len(validation_results['redundancies'])
                    reinforcements = len(validation_results['reinforcements'])
                    quality_score = validation_results['quality_score']

                    logger.info("📊 Cross-Validation Results:")
                    logger.info(f"   - Quality Score: {quality_score:.2f}")
                    logger.info(f"   - Contradictions: {contradictions}")
                    logger.info(f"   - Redundancies: {redundancies}")
                    logger.info(f"   - Reinforcements: {reinforcements}")

                    if contradictions > 0:
                        logger.warning(f"   ⚠️ Found {contradictions} contradictory patterns (consider reviewing)")
                    if redundancies > 0:
                        logger.info(f"   ℹ️  Found {redundancies} redundant patterns (consider deduplication)")
                    if reinforcements > 0:
                        logger.info(f"   ✅ Found {reinforcements} reinforcing patterns (high confidence)")

                    # Store quality score in job result
                    job_result['pattern_quality_score'] = quality_score
                    job_result['pattern_contradictions'] = contradictions
                    job_result['pattern_redundancies'] = redundancies
                    job_result['pattern_reinforcements'] = reinforcements

                except Exception as e:
                    logger.warning(f"⚠️ Pattern cross-validation failed: {e}, continuing...")

            # Quality improvement: Calibrate pattern confidences
            if all_patterns:
                logger.info("📊 Calibrating pattern confidences based on historical acceptance...")
                try:
                    async with get_db_session() as db:
                        calibrator = ConfidenceCalibrator(db)
                        all_patterns = await calibrator.calibrate_patterns_batch(all_patterns)

                        # Generate calibration report
                        calibration_report = await calibrator.generate_calibration_report()
                        logger.info("📊 Calibration Report:")
                        for pattern_type, metrics in calibration_report.items():
                            if metrics['reliability'] != 'unknown':
                                logger.info(
                                    f"   - {pattern_type}: {metrics['acceptance_rate']:.1%} acceptance "
                                    f"({metrics['sample_count']} samples, {metrics['reliability']} reliability)"
                                )
                except Exception as e:
                    logger.warning(f"⚠️ Confidence calibration failed: {e}, continuing with uncalibrated patterns")

            # Quality Framework Enhancement: Score and filter patterns by ML-based quality (Story AI13.7)
            if all_patterns and getattr(settings, 'enable_ml_quality_filtering', True):
                logger.info("🎯 Quality Framework: ML-based quality scoring and filtering (Story AI13.7)...")
                try:
                    from ..services.pattern_quality.filter import PatternQualityFilter
                    
                    # Initialize ML-based quality filter
                    quality_threshold = getattr(settings, 'pattern_quality_threshold', 0.7)
                    enable_ml_quality_filtering = getattr(settings, 'enable_ml_quality_filtering', True)
                    
                    quality_filter = PatternQualityFilter(
                        quality_threshold=quality_threshold,
                        enable_filtering=enable_ml_quality_filtering
                    )
                    
                    # Filter and rank patterns by quality
                    filtered_patterns, filter_stats = await quality_filter.filter_and_rank(all_patterns)
                    
                    filtered_count = filter_stats.get('removed', 0)
                    if filtered_count > 0:
                        logger.info(
                            f"   ✅ ML Quality filtering: {filtered_count} patterns filtered "
                            f"(below {quality_threshold:.2f} threshold)"
                        )
                        logger.info(
                            f"   📊 Quality score range: {filter_stats.get('min_quality', 0):.3f} - "
                            f"{filter_stats.get('max_quality', 0):.3f}"
                        )
                        logger.info(
                            f"   📊 Average quality: {filter_stats.get('avg_quality', 0):.3f}"
                        )
                        logger.info(
                            f"   ⏱️  Filtering time: {filter_stats.get('processing_time', 0)*1000:.1f}ms"
                        )
                    
                    all_patterns = filtered_patterns
                    logger.info(
                        f"   ✅ {len(all_patterns)} patterns passed ML quality filter "
                        f"(from {filter_stats.get('total', 0)} total)"
                    )
                    
                    # Store quality metrics
                    job_result['patterns_scored'] = filter_stats.get('total', 0)
                    job_result['patterns_filtered'] = filtered_count
                    job_result['patterns_after_quality_filter'] = len(all_patterns)
                    job_result['quality_filtering_stats'] = filter_stats
                    
                    # Performance check: ensure <100ms overhead
                    processing_time_ms = filter_stats.get('processing_time', 0) * 1000
                    if processing_time_ms > 100:
                        logger.warning(
                            f"   ⚠️ Quality filtering exceeded 100ms target: {processing_time_ms:.1f}ms"
                        )
                    
                except Exception as e:
                    logger.warning(
                        f"⚠️ ML Quality filtering failed: {e}, continuing with all patterns",
                        exc_info=True
                    )
                    job_result['quality_filtering_error'] = str(e)

            # Store patterns (don't fail if no patterns)
            if all_patterns:
                async with get_db_session() as db:
                    patterns_stored = await store_patterns(db, all_patterns)
                logger.info(f"   💾 Stored {patterns_stored} patterns in database")
                job_result['patterns_stored'] = patterns_stored
            else:
                logger.info("   ℹ️  No patterns to store")
                job_result['patterns_stored'] = 0

            # ================================================================
            # Phase 3d: Blueprint Opportunity Discovery (NEW - Epic AI-6)
            # ================================================================
            logger.info("📘 Phase 3d/7: Blueprint Opportunity Discovery (Epic AI-6)...")
            
            blueprint_opportunities_count = 0
            try:
                from ..blueprint_discovery import BlueprintOpportunityFinder
                from ..database.crud import store_blueprint_opportunities
                from ..utils.miner_integration import MinerIntegration
                
                # Check if automation-miner service is available
                miner = MinerIntegration(
                    base_url=getattr(settings, 'automation_miner_url', 'http://automation-miner:8029')
                )
                
                if await miner.is_available():
                    # Initialize BlueprintOpportunityFinder with cached device inventory
                    opportunity_finder = BlueprintOpportunityFinder(
                        data_api_client=data_client,
                        miner=miner
                    )
                    
                    # Discover blueprint opportunities (using cached device inventory)
                    import time
                    phase_3d_start = time.time()
                    
                    opportunities = await opportunity_finder.find_opportunities(
                        min_fit_score=0.6,
                        min_blueprint_quality=0.7,
                        limit=50
                    )
                    
                    phase_3d_duration = (time.time() - phase_3d_start) * 1000  # Convert to ms
                    
                    if opportunities:
                        # Store opportunities in database (link to analysis run)
                        async with get_db_session() as db:
                            # Get current analysis run ID (will be set after recording)
                            opportunities_stored = await store_blueprint_opportunities(
                                db,
                                opportunities,
                                analysis_run_id=None  # Will link after analysis run is recorded
                            )
                            blueprint_opportunities_count = opportunities_stored
                        
                        logger.info(f"   ✅ Discovered {len(opportunities)} blueprint opportunities")
                        logger.info(f"   💾 Stored {blueprint_opportunities_count} opportunities in database")
                        logger.info(f"   ⏱️  Phase 3d duration: {phase_3d_duration:.1f}ms")
                        
                        if phase_3d_duration > 30:
                            logger.warning(f"   ⚠️  Phase 3d exceeded 30ms target: {phase_3d_duration:.1f}ms")
                    else:
                        logger.info("   ℹ️  No blueprint opportunities found")
                else:
                    logger.info("   ⚠️  Automation-miner service unavailable, skipping blueprint discovery")
                    
            except Exception as e:
                logger.warning(f"   ⚠️  Blueprint opportunity discovery failed: {e}")
                logger.info("   → Continuing with synergy detection...")
                # Non-blocking: Continue even if blueprint discovery fails
            
            job_result['blueprint_opportunities_discovered'] = blueprint_opportunities_count

            # ================================================================
            # Phase 3c: Synergy Detection (NEW - Epic AI-3)
            # ================================================================
            logger.info("🔗 Phase 3c/7: Synergy Detection (Epic AI-3)...")
            logger.info("   → Starting synergy detection with relaxed parameters...")

            try:
                from ..clients.ha_client import HomeAssistantClient
                from ..database.crud import store_synergy_opportunities
                from ..synergy_detection import DeviceSynergyDetector
                logger.info("   → Imported synergy detection modules successfully")

                # Story AI4.3: Initialize HA client for automation checking
                ha_client = HomeAssistantClient(
                    ha_url=settings.ha_url,
                    access_token=settings.ha_token,
                    max_retries=settings.ha_max_retries,
                    retry_delay=settings.ha_retry_delay,
                    timeout=settings.ha_timeout
                )
                logger.info("   → HA client initialized for automation filtering")

                # 2025 Enhancement: Initialize enrichment fetcher for multi-modal context
                enrichment_fetcher = None
                try:
                    from ..services.enrichment_context_fetcher import EnrichmentContextFetcher
                    if data_client.influxdb_client:
                        enrichment_fetcher = EnrichmentContextFetcher(data_client.influxdb_client)
                        logger.info("   → Enrichment context fetcher initialized for multi-modal scoring")
                except Exception as e:
                    logger.warning(f"   ⚠️ Failed to initialize enrichment fetcher: {e}")
                
                synergy_detector = DeviceSynergyDetector(
                    data_api_client=data_client,
                    ha_client=ha_client,  # Story AI4.3: Enable automation filtering!
                    influxdb_client=data_client.influxdb_client,  # Enable advanced scoring (Story AI3.2)
                    min_confidence=0.5,  # Lowered from 0.7 to be less restrictive
                    same_area_required=False,  # Relaxed requirement to find more opportunities
                    enrichment_fetcher=enrichment_fetcher  # 2025 Enhancement: Multi-modal context
                )

                logger.info("   → Calling detect_synergies() method...")
                synergies = await synergy_detector.detect_synergies()

                # Enhanced synergy detection (NEW - Sequential, Simultaneous, Complementary)
                logger.info("   → Running enhanced synergy detection...")
                try:
                    from ..synergy_detection.enhanced_synergy_detector import (
                        EnhancedSynergyDetector,
                    )
                    enhanced_detector = EnhancedSynergyDetector(
                        base_synergy_detector=synergy_detector,
                        data_api_client=data_client
                    )
                    enhanced_synergies = await enhanced_detector.detect_enhanced_synergies(
                        events_df=events_df,
                        window_minutes=30
                    )
                    # Merge with base synergies (avoid duplicates)
                    existing_ids = {s.get('synergy_id') for s in synergies}
                    new_enhanced = [s for s in enhanced_synergies if s.get('synergy_id') not in existing_ids]
                    synergies.extend(new_enhanced)
                    logger.info(f"   ✅ Enhanced detection added {len(new_enhanced)} new synergies")
                except Exception as e:
                    logger.warning(f"   ⚠️ Enhanced synergy detection failed: {e}")

                logger.info("✅ Device synergy detection complete:")
                logger.info(f"   - Device synergies detected: {len(synergies)}")
                if synergies:
                    logger.info(f"   - Sample synergies: {[s.get('relationship', 'unknown') for s in synergies[:3]]}")

                # ----------------------------------------------------------------
                # Part B: Weather Opportunities (Epic AI-3, Story AI3.5)
                # ----------------------------------------------------------------
                logger.info("  → Part B: Weather opportunity detection (Epic AI-3)...")

                try:
                    from ..contextual_patterns import WeatherOpportunityDetector

                    weather_detector = WeatherOpportunityDetector(
                        influxdb_client=data_client.influxdb_client,
                        data_api_client=data_client,
                        frost_threshold_f=32.0,
                        heat_threshold_f=85.0
                    )

                    weather_opportunities = await weather_detector.detect_opportunities(days=7)

                    # Add to synergies list
                    synergies.extend(weather_opportunities)

                    logger.info(f"     ✅ Found {len(weather_opportunities)} weather opportunities")

                except Exception as e:
                    logger.warning(f"     ⚠️ Weather opportunity detection failed: {e}")
                    logger.warning("     → Continuing with empty weather opportunities list")
                    # Continue without weather opportunities but don't skip the phase

                # ----------------------------------------------------------------
                # Part C: Energy Opportunities (Epic AI-3, Story AI3.6)
                # ----------------------------------------------------------------
                logger.info("  → Part C: Energy opportunity detection (Epic AI-3)...")

                try:
                    from ..contextual_patterns import EnergyOpportunityDetector

                    energy_detector = EnergyOpportunityDetector(
                        influxdb_client=data_client.influxdb_client,
                        data_api_client=data_client,
                        peak_price_threshold=0.15,  # $/kWh default
                        min_confidence=0.7
                    )

                    energy_opportunities = await energy_detector.detect_opportunities()

                    # Add to synergies list
                    synergies.extend(energy_opportunities)

                    logger.info(f"     ✅ Found {len(energy_opportunities)} energy opportunities")

                except Exception as e:
                    logger.warning(f"     ⚠️ Energy opportunity detection failed: {e}")
                    logger.warning("     → Continuing with empty energy opportunities list")
                    # Continue without energy opportunities but don't skip the phase

                # ----------------------------------------------------------------
                # Part D: Event Opportunities (Epic AI-3, Story AI3.7)
                # ----------------------------------------------------------------
                logger.info("  → Part D: Event opportunity detection (Epic AI-3)...")

                try:
                    from ..contextual_patterns import EventOpportunityDetector

                    event_detector = EventOpportunityDetector(
                        data_api_client=data_client
                    )

                    event_opportunities = await event_detector.detect_opportunities()

                    # Add to synergies list
                    synergies.extend(event_opportunities)

                    logger.info(f"     ✅ Found {len(event_opportunities)} event opportunities")

                except Exception as e:
                    logger.warning(f"     ⚠️ Event opportunity detection failed: {e}")
                    logger.warning("     → Continuing with empty event opportunities list")
                    # Continue without event opportunities but don't skip the phase

                # Calculate counts for each type (handle missing variables gracefully)
                device_count = len(synergies)
                weather_count = len(weather_opportunities) if 'weather_opportunities' in locals() else 0
                energy_count = len(energy_opportunities) if 'energy_opportunities' in locals() else 0
                event_count = len(event_opportunities) if 'event_opportunities' in locals() else 0

                # Subtract contextual opportunities from device count
                device_count = device_count - weather_count - energy_count - event_count

                logger.info(f"✅ Total synergies detected: {len(synergies)}")
                logger.info(f"   → Device synergies: {device_count}")
                logger.info(f"   → Weather synergies: {weather_count}")
                logger.info(f"   → Energy synergies: {energy_count}")
                logger.info(f"   → Event synergies: {event_count}")

                # Quality improvement: ML-discovered synergies
                ml_discovered_count = 0
                ml_validated_count = 0
                try:
                    from ..synergy_detection.ml_enhanced_synergy_detector import (
                        MLEnhancedSynergyDetector,
                    )
                    from ..synergy_detection.ml_synergy_miner import DynamicSynergyMiner

                    logger.info("   → Running ML synergy miner...")
                    ml_miner = DynamicSynergyMiner(
                        influxdb_client=data_client.influxdb_client,
                        min_support=0.05,
                        min_confidence=0.75,
                        min_lift=1.5,
                        min_consistency=0.8,
                        time_window_seconds=60,
                        lookback_days=30,
                        min_occurrences=10
                    )

                    discovered_synergies = await ml_miner.mine_synergies()

                    if discovered_synergies:
                        async with get_db_session() as db:
                            ml_detector = MLEnhancedSynergyDetector(
                                base_synergy_detector=synergy_detector,
                                influxdb_client=data_client.influxdb_client,
                                enable_ml_discovery=True
                            )

                            # Store discovered synergies
                            stored_count = await ml_detector._store_discovered_synergies(
                                discovered_synergies, db
                            )
                            ml_discovered_count = stored_count

                            # Validate against patterns
                            validated_synergies = await ml_detector._validate_discovered_synergies(
                                discovered_synergies, all_patterns, db
                            )
                            ml_validated_count = len(validated_synergies)

                            logger.info(f"   ✅ ML Mining: {ml_discovered_count} discovered, {ml_validated_count} validated")
                except Exception as e:
                    logger.warning(f"   ⚠️ ML synergy discovery failed: {e}")

                # Store synergies in database with Phase 2 pattern validation
                if synergies:
                    async with get_db_session() as db:
                        synergies_stored = await store_synergy_opportunities(
                            db,
                            synergies,
                            validate_with_patterns=True,  # Phase 2: Enable pattern validation
                            min_pattern_confidence=0.7
                        )
                        # Query validated count from database
                        from sqlalchemy import func, select

                        from ..database.models import SynergyOpportunity
                        validated_result = await db.execute(
                            select(func.count()).select_from(SynergyOpportunity).where(
                                SynergyOpportunity.validated_by_patterns == True
                            )
                        )
                        total_validated = validated_result.scalar() or 0
                    logger.info(f"   💾 Stored {synergies_stored} synergies in database")
                    logger.info(f"   ✅ Phase 2: Pattern validation enabled - {total_validated} total validated synergies in database")
                    logger.info(f"   ✅ ML-discovered synergies: {ml_discovered_count} discovered, {ml_validated_count} validated")
                    job_result['synergies_detected'] = len(synergies)
                    job_result['synergies_stored'] = synergies_stored
                    job_result['synergies_validated'] = total_validated
                    job_result['ml_synergies_discovered'] = ml_discovered_count
                    job_result['ml_synergies_validated'] = ml_validated_count
                else:
                    logger.info("   ℹ️  No synergies to store")
                    job_result['synergies_detected'] = 0
                    job_result['synergies_stored'] = 0

            except Exception as e:
                logger.error(f"⚠️ Synergy detection failed: {e}")
                logger.info("   → Continuing with feature analysis...")
                synergies = []
                job_result['synergies_detected'] = 0
                job_result['synergies_stored'] = 0
            finally:
                # Story AI4.3: Clean up HA client resources
                if 'ha_client' in locals() and ha_client:
                    try:
                        await ha_client.close()
                        logger.debug("   → HA client connection closed")
                    except Exception as e:
                        logger.debug(f"   → Failed to close HA client: {e}")

            # Phase 4: Feature Analysis
            opportunities = await self._phase_4_feature_analysis(data_client, job_result)

            # ================================================================
            # Phase 5: Combined Suggestion Generation (AI-1 + AI-2 + AI-3)
            # ================================================================
            logger.info("💡 Phase 5/7: Combined Suggestion Generation (AI-1 + AI-2)...")

            # Initialize unified prompt builder with device intelligence
            from ..prompt_building.unified_prompt_builder import UnifiedPromptBuilder

            device_intel_client = DeviceIntelligenceClient(settings.device_intelligence_url)
            unified_builder = UnifiedPromptBuilder(device_intelligence_client=device_intel_client)

            # Initialize OpenAI client with classification model (Phase 1: gpt-5.1-mini for 80% cost savings)
            from ..config import settings
            classification_model = getattr(settings, 'classification_model', 'gpt-5.1-mini')
            openai_client = OpenAIClient(api_key=settings.openai_api_key, model=classification_model)

            # Phase 4: Pre-fetch device contexts for caching (parallel)
            logger.info("🔍 Phase 4.5/7: Pre-fetching device contexts...")
            device_contexts = {}
            try:
                # Collect all unique device IDs from patterns
                all_device_ids = set()
                for pattern in all_patterns:
                    if 'device_id' in pattern:
                        all_device_ids.add(pattern['device_id'])

                if all_device_ids:
                    logger.info(f"  → Pre-fetching contexts for {len(all_device_ids)} devices")
                    # Fetch contexts in parallel for better performance
                    async def fetch_device_context(device_id):
                        try:
                            context = await unified_builder.get_enhanced_device_context({'device_id': device_id})
                            return device_id, context
                        except Exception as e:
                            logger.warning(f"  ⚠️ Failed to fetch context for {device_id}: {e}")
                            return device_id, {}

                    # Execute all fetches in parallel
                    fetch_tasks = [fetch_device_context(device_id) for device_id in all_device_ids]
                    fetch_results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

                    # Collect results
                    for result in fetch_results:
                        if not isinstance(result, Exception):
                            device_id, context = result
                            device_contexts[device_id] = context

                    logger.info(f"  ✅ Pre-fetched {len(device_contexts)} device contexts")
            except Exception as e:
                logger.warning(f"  ⚠️ Device context pre-fetch failed: {e}")
                device_contexts = {}

            # ----------------------------------------------------------------
            # Part A: Pattern-based suggestions (Epic AI-1) - PARALLEL PROCESSING
            # ----------------------------------------------------------------
            logger.info("  → Part A: Pattern-based suggestions (Epic AI-1)...")

            pattern_suggestions = []

            # Helper function for parallel pattern processing (defined outside loop)
            async def process_pattern_suggestion(pattern, cached_contexts):
                try:
                    # Use cached context if available
                    if cached_contexts and pattern.get('device_id') in cached_contexts:
                        enhanced_context = cached_contexts[pattern['device_id']]
                    else:
                        enhanced_context = await unified_builder.get_enhanced_device_context(pattern)

                    # Build unified prompt
                    prompt_dict = await unified_builder.build_pattern_prompt(
                        pattern=pattern,
                        device_context=enhanced_context,
                        output_mode="description"
                    )

                    # Generate suggestion
                    description_data = await openai_client.generate_with_unified_prompt(
                        prompt_dict=prompt_dict,
                        temperature=settings.default_temperature,
                        max_tokens=settings.description_max_tokens,
                        output_format="description"
                    )

                    # Format suggestion
                    if 'title' in description_data:
                        title = description_data['title']
                        description = description_data['description']
                        rationale = description_data['rationale']
                        category = description_data['category']
                        priority = description_data['priority']
                    else:
                        title = f"Automation for {pattern.get('device_id', 'device')}"
                        description = description_data.get('description', '')
                        rationale = "Based on detected usage pattern"
                        category = "convenience"
                        priority = "medium"

                    suggestion = {
                        'type': 'pattern_automation',
                        'source': 'Epic-AI-1',
                        'pattern_id': pattern.get('id'),
                        'pattern_type': pattern.get('pattern_type'),
                        'title': title,
                        'description': description,
                        'automation_yaml': None,
                        'confidence': pattern['confidence'],
                        'category': category,
                        'priority': priority,
                        'rationale': rationale
                    }

                    return suggestion
                except Exception as e:
                    logger.error(f"     Failed to process pattern: {e}")
                    return None

            if all_patterns:
                # ================================================================
                # Blueprint Validation and Confidence Boosting (Story AI6.5)
                # ================================================================
                logger.info("     → Validating patterns against blueprints (Epic AI-6)...")
                
                validated_count = 0
                total_boost = 0.0
                
                try:
                    from ..blueprint_discovery.blueprint_validator import BlueprintValidator
                    from ..utils.miner_integration import MinerIntegration
                    
                    # Initialize validator
                    miner = MinerIntegration()
                    validator = BlueprintValidator(miner)
                    
                    # Validate each pattern and apply confidence boosts
                    for pattern in all_patterns:
                        try:
                            pattern_type = pattern.get('pattern_type', 'unknown')
                            
                            # Skip validation if automation-miner unavailable (graceful degradation)
                            if not await miner.is_available():
                                logger.debug(f"     ⚠️ automation-miner unavailable, skipping blueprint validation")
                                break
                            
                            # Validate pattern against blueprints
                            validation_result = await validator.validate_pattern(
                                pattern=pattern,
                                pattern_type=pattern_type
                            )
                            
                            # Apply confidence boost if validated
                            if validation_result.get('validated', False):
                                boost = validation_result.get('confidence_boost', 0.0)
                                original_confidence = pattern.get('confidence', 0.0)
                                
                                # Apply boost (clamp to 0.0-1.0 range)
                                boosted_confidence = min(1.0, original_confidence + boost)
                                pattern['confidence'] = boosted_confidence
                                
                                # Store validation metadata (Story AI6.6: Include blueprint title for description generation)
                                # blueprint_match is already the blueprint dictionary (not wrapped)
                                blueprint = validation_result.get('blueprint_match', {})
                                
                                pattern['blueprint_validated'] = True
                                pattern['blueprint_match_score'] = validation_result.get('match_score', 0.0)
                                pattern['blueprint_confidence_boost'] = boost
                                pattern['blueprint_id'] = blueprint.get('id') if blueprint else None
                                # Extract title from blueprint metadata or top-level title field
                                blueprint_title = blueprint.get('title') or (
                                    blueprint.get('metadata', {}).get('_blueprint_metadata', {}).get('name') if blueprint else None
                                )
                                pattern['blueprint_title'] = blueprint_title  # For description hints
                                
                                validated_count += 1
                                total_boost += boost
                                
                                logger.debug(
                                    f"     ✓ Pattern validated: {pattern_type} "
                                    f"(confidence: {original_confidence:.3f} → {boosted_confidence:.3f}, boost: +{boost:.3f})"
                                )
                            else:
                                pattern['blueprint_validated'] = False
                                
                        except Exception as e:
                            # Non-blocking: Continue if validation fails for one pattern
                            logger.warning(
                                f"     ⚠️ Pattern validation failed: {e}",
                                exc_info=True
                            )
                            pattern['blueprint_validated'] = False
                    
                    if validated_count > 0:
                        avg_boost = total_boost / validated_count
                        logger.info(
                            f"     ✅ Validated {validated_count}/{len(all_patterns)} patterns "
                            f"(avg boost: +{avg_boost:.3f}, total boost: +{total_boost:.3f})"
                        )
                    else:
                        logger.info(f"     ℹ️  No patterns validated against blueprints")
                        
                except Exception as e:
                    # Non-blocking: Continue without validation if service unavailable
                    logger.warning(
                        f"     ⚠️ Blueprint validation unavailable: {e}",
                        exc_info=True
                    )
                
                # Quality Framework Enhancement: Sort by quality score if available, otherwise by confidence
                if any(p.get('quality_score') is not None for p in all_patterns):
                    sorted_patterns = sorted(all_patterns, key=lambda p: p.get('quality_score', p.get('confidence', 0.0)), reverse=True)
                    logger.info(f"     → Sorting patterns by quality score")
                else:
                    sorted_patterns = sorted(all_patterns, key=lambda p: p.get('confidence', 0.0), reverse=True)
                    logger.info(f"     → Sorting patterns by confidence (quality scores not available)")
                
                top_patterns = sorted_patterns[:10]
                
                if top_patterns and any(p.get('quality_score') is not None for p in top_patterns):
                    quality_scores = [p.get('quality_score', 0) for p in top_patterns if p.get('quality_score') is not None]
                    if quality_scores:
                        logger.info(f"     → Top pattern quality scores: {[f'{q:.2f}' for q in quality_scores[:3]]}")

                logger.info(f"     Processing top {len(top_patterns)} patterns (parallel)")

                # Process patterns in parallel with batch size limit
                BATCH_SIZE = settings.openai_concurrent_limit

                for i in range(0, len(top_patterns), BATCH_SIZE):
                    batch = top_patterns[i:i + BATCH_SIZE]

                    # Execute batch in parallel
                    tasks = [process_pattern_suggestion(pattern, device_contexts) for pattern in batch]
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    # Collect successful suggestions
                    for result in results:
                        if result and not isinstance(result, Exception):
                            pattern_suggestions.append(result)

                    logger.info(f"     Batch {i//BATCH_SIZE + 1}: {len([r for r in results if r])} suggestions generated")

                logger.info(f"     ✅ Generated {len(pattern_suggestions)} pattern suggestions")
            else:
                logger.info("     ℹ️  No patterns available for suggestions")

            # ----------------------------------------------------------------
            # Part B: Feature-based suggestions (Epic AI-2)
            # ----------------------------------------------------------------
            logger.info("  → Part B: Feature-based suggestions (Epic AI-2)...")

            feature_suggestions = []

            if opportunities:
                try:
                    feature_generator = FeatureSuggestionGenerator(
                        llm_client=openai_client,
                        feature_analyzer=feature_analyzer,
                        db_session=get_db_session
                    )

                    feature_suggestions = await feature_generator.generate_suggestions(max_suggestions=10)
                    logger.info(f"     ✅ Generated {len(feature_suggestions)} feature suggestions")

                except Exception as e:
                    logger.error(f"     ❌ Feature suggestion generation failed: {e}")
            else:
                logger.info("     ℹ️  No opportunities available for suggestions")

            # ----------------------------------------------------------------
            # Part C: Synergy-based suggestions (Epic AI-3)
            # ----------------------------------------------------------------
            logger.info("  → Part C: Synergy-based suggestions (Epic AI-3)...")

            synergy_suggestions = []

            try:
                from ..synergy_detection.synergy_suggestion_generator import (
                    SynergySuggestionGenerator,
                )

                # Query synergies from database with priority-based selection
                async with get_db_session() as db:
                    if settings.synergy_use_priority_scoring:
                        logger.info(f"     → Using priority-based selection (min_priority={settings.synergy_min_priority})")
                        selected_synergies = await get_synergy_opportunities(
                            db,
                            order_by_priority=True,
                            min_priority=settings.synergy_min_priority,
                            limit=settings.synergy_max_suggestions,
                            min_confidence=0.7  # Maintain minimum confidence threshold
                        )
                        logger.info(f"     → Selected {len(selected_synergies)} synergies by priority score")
                    else:
                        # Fallback to impact_score ordering (backward compatible)
                        logger.info("     → Using impact_score-based selection (priority scoring disabled)")
                        selected_synergies = await get_synergy_opportunities(
                            db,
                            order_by_priority=False,
                            limit=settings.synergy_max_suggestions,
                            min_confidence=0.7
                        )
                        logger.info(f"     → Selected {len(selected_synergies)} synergies by impact score")

                if selected_synergies:
                    # Convert SynergyOpportunity objects to dicts for generator
                    synergy_dicts = []
                    for synergy in selected_synergies:
                        import json
                        synergy_dict = {
                            'synergy_id': synergy.synergy_id,
                            'synergy_type': synergy.synergy_type,
                            'devices': json.loads(synergy.device_ids) if synergy.device_ids else [],
                            'impact_score': synergy.impact_score,
                            'complexity': synergy.complexity,
                            'confidence': synergy.confidence,
                            'area': synergy.area,
                            'opportunity_metadata': synergy.opportunity_metadata or {},
                            'pattern_support_score': getattr(synergy, 'pattern_support_score', 0.0),
                            'validated_by_patterns': getattr(synergy, 'validated_by_patterns', False),
                            'relationship': (synergy.opportunity_metadata or {}).get('relationship', ''),
                            'trigger_entity': (synergy.opportunity_metadata or {}).get('trigger_entity', ''),
                            'action_entity': (synergy.opportunity_metadata or {}).get('action_entity', ''),
                            'trigger_name': (synergy.opportunity_metadata or {}).get('trigger_name', ''),
                            'action_name': (synergy.opportunity_metadata or {}).get('action_name', ''),
                            'rationale': (synergy.opportunity_metadata or {}).get('rationale', '')
                        }
                        synergy_dicts.append(synergy_dict)
                    
                    # Quality Framework Enhancement: Score and filter synergies by quality
                    if settings.enable_quality_filtering:
                        logger.info(f"     🎯 Quality Framework: Scoring {len(synergy_dicts)} synergies...")
                        try:
                            from ..testing.synergy_quality_scorer import SynergyQualityScorer
                            synergy_quality_scorer = SynergyQualityScorer()
                            
                            scored_synergies = []
                            for synergy_dict in synergy_dicts:
                                try:
                                    quality_result = synergy_quality_scorer.calculate_quality_score(synergy_dict)
                                    synergy_dict['quality_score'] = quality_result['quality_score']
                                    synergy_dict['quality_breakdown'] = quality_result.get('breakdown', {})
                                    scored_synergies.append(synergy_dict)
                                except Exception as e:
                                    logger.debug(f"     Failed to score synergy: {e}")
                                    # Fallback to confidence as quality score
                                    synergy_dict['quality_score'] = synergy_dict.get('confidence', 0.6)
                                    scored_synergies.append(synergy_dict)
                            
                            # Filter by quality threshold
                            min_synergy_quality = settings.synergy_min_quality_score
                            filtered_synergies = [
                                s for s in scored_synergies 
                                if s.get('quality_score', 0.0) >= min_synergy_quality
                            ]
                            
                            synergy_filtered_count = len(scored_synergies) - len(filtered_synergies)
                            if synergy_filtered_count > 0:
                                logger.info(f"     ✅ Quality filtering: {synergy_filtered_count} synergies filtered (below {min_synergy_quality:.2f} threshold)")
                                quality_scores = [s.get('quality_score', 0) for s in scored_synergies]
                                if quality_scores:
                                    logger.info(f"     📊 Synergy quality score range: {min(quality_scores):.3f} - {max(quality_scores):.3f}")
                            
                            synergy_dicts = filtered_synergies
                            logger.info(f"     ✅ {len(synergy_dicts)} synergies passed quality filter (from {len(scored_synergies)} scored)")
                            
                        except Exception as e:
                            logger.warning(f"     ⚠️ Quality framework filtering for synergies failed: {e}, continuing with all synergies")

                    synergy_generator = SynergySuggestionGenerator(
                        llm_client=openai_client
                    )

                    synergy_suggestions = await synergy_generator.generate_suggestions(
                        synergies=synergy_dicts,
                        max_suggestions=settings.synergy_max_suggestions
                    )
                    logger.info(f"     ✅ Generated {len(synergy_suggestions)} synergy suggestions")
                else:
                    logger.info("     ℹ️  No synergies available for suggestions (database query returned empty)")

            except Exception as e:
                logger.error(f"     ❌ Synergy suggestion generation failed: {e}", exc_info=True)

            # ----------------------------------------------------------------
            # Part D: Combine and rank all suggestions
            # ----------------------------------------------------------------
            logger.info("  → Part D: Combining and ranking all suggestions...")

            all_suggestions = pattern_suggestions + feature_suggestions + synergy_suggestions

            # Apply ranking score with boost for validated synergies
            for suggestion in all_suggestions:
                base_confidence = suggestion.get('confidence', 0.5)
                # Give validated synergies 1.1x boost in ranking
                if suggestion.get('type', '').startswith('synergy_') and suggestion.get('validated_by_patterns', False):
                    suggestion['_ranking_score'] = base_confidence * 1.1
                else:
                    suggestion['_ranking_score'] = base_confidence

            all_suggestions.sort(key=lambda s: s.get('_ranking_score', 0.5), reverse=True)
            
            # Story AI6.11: Apply unified preference-aware ranking
            # Applies all preferences: creativity filtering, blueprint weighting, max_suggestions limit
            try:
                from ..blueprint_discovery.preference_aware_ranker import PreferenceAwareRanker
                preference_ranker = PreferenceAwareRanker(user_id="default")
                original_count = len(all_suggestions)
                all_suggestions = await preference_ranker.rank_suggestions(all_suggestions)
                logger.info(f"   ✅ Applied unified preference-aware ranking: {original_count} → {len(all_suggestions)} suggestions")
            except Exception as e:
                logger.warning(f"   ⚠️ Failed to apply unified preference-aware ranking, using existing ranking: {e}")
                # Continue without unified ranking on error (graceful degradation)
                # Fallback to max_suggestions limit only
                try:
                    from ..blueprint_discovery.preference_manager import PreferenceManager
                    preference_manager = PreferenceManager(user_id="default")
                    max_suggestions = await preference_manager.get_max_suggestions()
                    all_suggestions = all_suggestions[:max_suggestions]
                    logger.info(f"   📊 Applied fallback max_suggestions limit: {max_suggestions}")
                except Exception:
                    all_suggestions = all_suggestions[:10]  # Hard fallback

            # Clean up temporary ranking score
            for suggestion in all_suggestions:
                if '_ranking_score' in suggestion:
                    del suggestion['_ranking_score']

            logger.info(f"✅ Combined suggestions: {len(all_suggestions)} total")
            logger.info(f"   - Pattern-based (AI-1): {len(pattern_suggestions)}")
            logger.info(f"   - Feature-based (AI-2): {len(feature_suggestions)}")
            logger.info(f"   - Synergy-based (AI-3): {len(synergy_suggestions)}")
            logger.info(f"   - Top suggestions kept: {len(all_suggestions)}")

            # Store all combined suggestions in single transaction
            suggestions_stored = 0
            async with get_db_session() as db:
                for suggestion in all_suggestions:
                    try:
                        await store_suggestion(db, suggestion, commit=False)
                        suggestions_stored += 1
                    except Exception as e:
                        logger.error(f"   ❌ Failed to store suggestion: {e}")
                        # Continue with other suggestions

                try:
                    await db.commit()
                    logger.info(f"   💾 Stored {suggestions_stored}/{len(all_suggestions)} suggestions in database")
                except Exception as e:
                    await db.rollback()
                    logger.error(f"   ❌ Failed to commit suggestions: {e}")
                    suggestions_stored = 0

            suggestions_generated = len(all_suggestions)

            # OpenAI usage stats
            openai_cost = (
                (openai_client.total_input_tokens * 0.00000015) +
                (openai_client.total_output_tokens * 0.00000060)
            )
            logger.info(f"  → OpenAI tokens: {openai_client.total_tokens_used}")
            logger.info(f"  → OpenAI cost: ${openai_cost:.6f}")

            job_result['suggestions_generated'] = suggestions_generated
            job_result['pattern_suggestions'] = len(pattern_suggestions)
            job_result['feature_suggestions'] = len(feature_suggestions)
            job_result['synergy_suggestions'] = len(synergy_suggestions)
            job_result['openai_tokens'] = openai_client.total_tokens_used
            job_result['openai_cost_usd'] = round(openai_cost, 6)

            await self._maybe_run_self_improvement(job_result)

            # ================================================================
            # Phase 6: Publish Notification & Results (MQTT)
            # ================================================================
            logger.info("📢 Phase 6/7: Publishing MQTT notification...")

            try:
                notification = {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'epic_ai_1': {
                        'patterns_detected': len(all_patterns),
                        'pattern_suggestions': len(pattern_suggestions)
                    },
                    'epic_ai_2': {
                        'devices_checked': job_result.get('devices_checked', 0),
                        'capabilities_updated': job_result.get('capabilities_updated', 0),
                        'opportunities_found': job_result.get('opportunities_found', 0),
                        'feature_suggestions': len(feature_suggestions)
                    },
                    'combined': {
                        'suggestions_generated': suggestions_generated,
                        'events_analyzed': len(events_df)
                    },
                    'duration_seconds': (datetime.now(timezone.utc) - start_time).total_seconds(),
                    'success': True
                }

                if self.mqtt_client:
                    self.mqtt_client.publish_analysis_complete(notification)
                    logger.info("  ✅ MQTT notification published to ha-ai/analysis/complete")
                else:
                    logger.info("  ⚠️ MQTT client not available, skipping notification")
                    logger.info(f"  → Would have published: {notification}")

            except Exception as e:
                logger.warning(f"  ⚠️ Failed to publish MQTT notification: {e}")

            # ================================================================
            # Complete
            # ================================================================
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()

            job_result['status'] = 'success'
            job_result['end_time'] = end_time.isoformat()
            job_result['duration_seconds'] = round(duration, 2)

            logger.info("=" * 80)
            logger.info("✅ Unified Daily AI Analysis Complete!")
            logger.info("=" * 80)
            logger.info(f"  Duration: {duration:.1f} seconds")
            logger.info("  ")
            logger.info("  Epic AI-1 (Pattern Detection):")
            logger.info(f"    - Events analyzed: {len(events_df)}")
            logger.info(f"    - Patterns detected: {len(all_patterns)}")
            logger.info(f"    - Pattern suggestions: {len(pattern_suggestions)}")
            logger.info("  ")
            logger.info("  Epic AI-2 (Device Intelligence):")
            logger.info(f"    - Devices checked: {job_result.get('devices_checked', 0)}")
            logger.info(f"    - Capabilities updated: {job_result.get('capabilities_updated', 0)}")
            logger.info(f"    - Opportunities found: {job_result.get('opportunities_found', 0)}")
            logger.info(f"    - Feature suggestions: {len(feature_suggestions)}")
            logger.info("  ")
            logger.info("  Combined Results:")
            logger.info(f"    - Total suggestions: {suggestions_generated}")
            logger.info(f"    - OpenAI tokens: {openai_client.total_tokens_used}")
            logger.info(f"    - OpenAI cost: ${openai_cost:.6f}")
            logger.info("=" * 80)

        except Exception as e:
            logger.error(f"❌ Daily analysis job failed: {e}", exc_info=True)
            job_result['status'] = 'failed'
            job_result['error'] = str(e)
            job_result['end_time'] = datetime.now(timezone.utc).isoformat()

        finally:
            self.is_running = False
            self._store_job_history(job_result)
            try:
                async with get_db_session() as db:
                    await record_analysis_run(db, job_result)
            except Exception as e:
                logger.error(f"Failed to persist analysis run summary: {e}")

    def _store_job_history(self, job_result: dict):
        """
        Store job execution history for tracking and debugging.
        
        Args:
            job_result: Dictionary with job execution details
        """
        # Keep last 30 job runs in memory
        self._job_history.append(job_result)
        if len(self._job_history) > 30:
            self._job_history.pop(0)

        logger.info(f"Job history updated: {job_result['status']}")

    def get_job_history(self, limit: int = 10) -> list:
        """
        Get recent job execution history.
        
        Args:
            limit: Maximum number of jobs to return
        
        Returns:
            List of recent job execution results
        """
        return self._job_history[-limit:]

    def get_next_run_time(self) -> datetime | None:
        """
        Get the next scheduled run time.
        
        Returns:
            Next run time as datetime, or None if not scheduled
        """
        try:
            job = self.scheduler.get_job('daily_pattern_analysis')
            if job:
                return job.next_run_time
        except Exception as e:
            logger.error(f"Failed to get next run time: {e}")
        return None

    async def trigger_manual_run(self):
        """
        Manually trigger analysis run (for testing or on-demand execution).
        
        This runs in the background and doesn't block.
        """
        logger.info("🔧 Manual analysis run triggered")
        asyncio.create_task(self.run_daily_analysis())

    async def _maybe_run_self_improvement(self, job_result: dict[str, Any]) -> None:
        """Run weekly LangChain-backed self-improvement summary."""
        if not getattr(settings, "enable_self_improvement_pilot", False):
            return

        run_time = datetime.now(timezone.utc)
        if run_time.weekday() != 0:
            logger.debug("Self-improvement pilot runs on Mondays; skipping for %s.", run_time.date())
            return

        try:
            from ..langchain_integration.self_improvement import generate_prompt_tuning_report

            report = await generate_prompt_tuning_report(get_db_session)
            job_result["self_improvement"] = {
                "generated_at": run_time.isoformat(),
                "recommendations": report.get("recommendations", []),
            }
            logger.info("📈 Self-improvement pilot recommendations:\n%s", report.get("plan_text", ""))
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning(
                "⚠️ Self-improvement pilot could not generate recommendations (%s).",
                exc,
                exc_info=True,
            )

