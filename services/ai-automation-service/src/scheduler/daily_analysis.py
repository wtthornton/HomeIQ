"""
Daily Analysis Scheduler
Runs unified AI analysis combining Epic-AI-1 (Pattern Detection) and Epic-AI-2 (Device Intelligence)
on a scheduled basis (default: 3 AM daily)

Story AI2.5: Unified Daily Batch Job
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timezone, timedelta
import logging
from typing import Optional, Dict
import asyncio

# Epic AI-1 imports (Pattern Detection)
from ..clients.data_api_client import DataAPIClient
from ..clients.device_intelligence_client import DeviceIntelligenceClient
from ..clients.pattern_aggregate_client import PatternAggregateClient  # Story AI5.4: Incremental processing
from ..api.suggestion_router import _build_device_context
from ..clients.mqtt_client import MQTTNotificationClient
from ..pattern_analyzer.time_of_day import TimeOfDayPatternDetector
from ..pattern_analyzer.co_occurrence import CoOccurrencePatternDetector

# New ML-enhanced pattern detectors
from ..pattern_detection.sequence_detector import SequenceDetector
from ..pattern_detection.contextual_detector import ContextualDetector
from ..pattern_detection.room_based_detector import RoomBasedDetector
from ..pattern_detection.session_detector import SessionDetector
from ..pattern_detection.duration_detector import DurationDetector
from ..pattern_detection.day_type_detector import DayTypeDetector
from ..pattern_detection.seasonal_detector import SeasonalDetector
from ..pattern_detection.anomaly_detector import AnomalyDetector

from ..llm.openai_client import OpenAIClient
from ..database.crud import store_patterns, store_suggestion
from ..database.models import get_db, get_db_session
from ..config import settings

# Epic AI-2 imports (Device Intelligence)
from ..device_intelligence import (
    update_device_capabilities_batch,
    FeatureAnalyzer,
    FeatureSuggestionGenerator
)

logger = logging.getLogger(__name__)


class DailyAnalysisScheduler:
    """Schedules and runs daily pattern analysis and suggestion generation"""
    
    def __init__(self, cron_schedule: Optional[str] = None, enable_incremental: bool = True):
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
        self._last_analysis_time: Optional[datetime] = None
        self._last_pattern_update_time: Optional[datetime] = None
        
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
            
            # ================================================================
            # Phase 1: Device Capability Update (NEW - Epic AI-2)
            # ================================================================
            logger.info("📡 Phase 1/6: Device Capability Update (Epic AI-2)...")
            
            data_client = DataAPIClient(
                base_url=settings.data_api_url,
                influxdb_url=settings.influxdb_url,
                influxdb_token=settings.influxdb_token,
                influxdb_org=settings.influxdb_org,
                influxdb_bucket=settings.influxdb_bucket
            )
            
            try:
                capability_stats = await update_device_capabilities_batch(
                    mqtt_client=self.mqtt_client,
                    data_api_client=data_client,
                    db_session_factory=get_db_session
                )
                
                logger.info(f"✅ Device capabilities updated:")
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
            
            # ================================================================
            # Phase 2: Fetch Events (SHARED by AI-1 + AI-2)
            # ================================================================
            logger.info("📊 Phase 2/6: Fetching events (SHARED by AI-1 + AI-2)...")
            
            data_client = DataAPIClient(
                base_url=settings.data_api_url,
                influxdb_url=settings.influxdb_url,
                influxdb_token=settings.influxdb_token,
                influxdb_org=settings.influxdb_org,
                influxdb_bucket=settings.influxdb_bucket
            )
            start_date = datetime.now(timezone.utc) - timedelta(days=30)
            
            events_df = await data_client.fetch_events(
                start_time=start_date,
                limit=100000
            )
            
            if events_df.empty:
                logger.warning("❌ No events available for analysis")
                job_result['status'] = 'no_data'
                job_result['events_count'] = 0
                return
            
            logger.info(f"✅ Fetched {len(events_df)} events")
            job_result['events_count'] = len(events_df)
            
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
            
            # Time-of-day patterns (Story AI5.3: Incremental processing enabled)
            logger.info("  → Running time-of-day detector (incremental)...")
            tod_detector = TimeOfDayPatternDetector(
                min_occurrences=5,
                min_confidence=0.7,
                aggregate_client=aggregate_client  # Story AI5.4: Pass aggregate client
            )
            
            # Use incremental update if enabled and previous run exists
            if self.enable_incremental and self._last_pattern_update_time and hasattr(tod_detector, 'incremental_update'):
                logger.info(f"    → Using incremental update (last update: {self._last_pattern_update_time})")
                tod_patterns = tod_detector.incremental_update(events_df, self._last_pattern_update_time)
            else:
                # Full analysis
                tod_patterns = tod_detector.detect_patterns(events_df)
            
            all_patterns.extend(tod_patterns)
            logger.info(f"    ✅ Found {len(tod_patterns)} time-of-day patterns (daily aggregates stored)")
            
            # Update last pattern update time after first detector
            self._last_pattern_update_time = datetime.now(timezone.utc)
            
            # Co-occurrence patterns (Story AI5.3: Incremental processing enabled)
            logger.info("  → Running co-occurrence detector (incremental)...")
            co_detector = CoOccurrencePatternDetector(
                window_minutes=5,
                min_support=5,
                min_confidence=0.7,
                aggregate_client=aggregate_client  # Story AI5.4: Pass aggregate client
            )
            # Use incremental update if enabled and previous run exists
            if self.enable_incremental and self._last_pattern_update_time and hasattr(co_detector, 'incremental_update'):
                logger.info(f"    → Using incremental update (last update: {self._last_pattern_update_time})")
                co_patterns = co_detector.incremental_update(events_df, self._last_pattern_update_time)
            else:
                # Full analysis
                if len(events_df) > 10000:
                    co_patterns = co_detector.detect_patterns_optimized(events_df)
                else:
                    co_patterns = co_detector.detect_patterns(events_df)
            
            all_patterns.extend(co_patterns)
            logger.info(f"    ✅ Found {len(co_patterns)} co-occurrence patterns (daily aggregates stored)")
            
            # ML-Enhanced Pattern Detection (Story AI5.3: Incremental processing enabled)
            logger.info("  → Running ML-enhanced pattern detectors (incremental)...")
            
            # Sequence patterns (Story AI5.3: Incremental processing enabled)
            logger.info("    → Running sequence detector (incremental)...")
            sequence_detector = SequenceDetector(
                window_minutes=30,
                min_sequence_length=2,
                min_sequence_occurrences=3,
                min_confidence=0.7,
                enable_incremental=self.enable_incremental,
                aggregate_client=aggregate_client  # Story AI5.4: Pass aggregate client
            )
            # Use incremental update if enabled and previous run exists
            if self.enable_incremental and self._last_pattern_update_time and hasattr(sequence_detector, 'incremental_update'):
                sequence_patterns = sequence_detector.incremental_update(events_df, self._last_pattern_update_time)
            else:
                sequence_patterns = sequence_detector.detect_patterns(events_df)
            all_patterns.extend(sequence_patterns)
            logger.info(f"    ✅ Found {len(sequence_patterns)} sequence patterns (daily aggregates stored)")
            
            # Contextual patterns (Story AI5.8: Monthly aggregation enabled)
            logger.info("    → Running contextual detector (monthly aggregates)...")
            contextual_detector = ContextualDetector(
                weather_weight=0.3,
                presence_weight=0.4,
                time_weight=0.3,
                min_confidence=0.7,
                enable_incremental=self.enable_incremental,
                aggregate_client=aggregate_client  # Story AI5.8: Pass aggregate client for monthly aggregates
            )
            # Use incremental update if enabled and previous run exists
            if self.enable_incremental and self._last_pattern_update_time and hasattr(contextual_detector, 'incremental_update'):
                contextual_patterns = contextual_detector.incremental_update(events_df, self._last_pattern_update_time)
            else:
                contextual_patterns = contextual_detector.detect_patterns(events_df)
            all_patterns.extend(contextual_patterns)
            logger.info(f"    ✅ Found {len(contextual_patterns)} contextual patterns (monthly aggregates stored)")
            
            # Room-based patterns (Story AI5.3: Incremental processing enabled)
            logger.info("    → Running room-based detector (incremental)...")
            room_detector = RoomBasedDetector(
                min_room_activity_events=5,
                min_confidence=0.7,
                enable_incremental=self.enable_incremental,
                aggregate_client=aggregate_client  # Story AI5.4: Pass aggregate client
            )
            # Use incremental update if enabled and previous run exists
            if self.enable_incremental and self._last_pattern_update_time and hasattr(room_detector, 'incremental_update'):
                room_patterns = room_detector.incremental_update(events_df, self._last_pattern_update_time)
            else:
                room_patterns = room_detector.detect_patterns(events_df)
            all_patterns.extend(room_patterns)
            logger.info(f"    ✅ Found {len(room_patterns)} room-based patterns (daily aggregates stored)")
            
            # Session patterns (Story AI5.6: Weekly aggregation enabled)
            logger.info("    → Running session detector (weekly aggregates)...")
            session_detector = SessionDetector(
                session_timeout_minutes=60,
                min_session_events=3,
                min_session_occurrences=3,
                min_confidence=0.7,
                enable_incremental=self.enable_incremental,
                aggregate_client=aggregate_client  # Story AI5.6: Pass aggregate client for weekly aggregates
            )
            # Use incremental update if enabled and previous run exists
            if self.enable_incremental and self._last_pattern_update_time and hasattr(session_detector, 'incremental_update'):
                session_patterns = session_detector.incremental_update(events_df, self._last_pattern_update_time)
            else:
                session_patterns = session_detector.detect_patterns(events_df)
            all_patterns.extend(session_patterns)
            logger.info(f"    ✅ Found {len(session_patterns)} session patterns (weekly aggregates stored)")
            
            # Duration patterns (Story AI5.3: Incremental processing enabled)
            logger.info("    → Running duration detector (incremental)...")
            duration_detector = DurationDetector(
                min_duration_minutes=5,
                max_duration_hours=24,
                min_occurrences=3,
                min_confidence=0.7,
                enable_incremental=self.enable_incremental,
                aggregate_client=aggregate_client  # Story AI5.4: Pass aggregate client
            )
            # Use incremental update if enabled and previous run exists
            if self.enable_incremental and self._last_pattern_update_time and hasattr(duration_detector, 'incremental_update'):
                duration_patterns = duration_detector.incremental_update(events_df, self._last_pattern_update_time)
            else:
                duration_patterns = duration_detector.detect_patterns(events_df)
            all_patterns.extend(duration_patterns)
            logger.info(f"    ✅ Found {len(duration_patterns)} duration patterns (daily aggregates stored)")
            
            # Day-type patterns (Story AI5.6: Weekly aggregation enabled)
            logger.info("    → Running day-type detector (weekly aggregates)...")
            day_type_detector = DayTypeDetector(
                min_weekday_occurrences=5,
                min_weekend_occurrences=3,
                min_confidence=0.7,
                enable_incremental=self.enable_incremental,
                aggregate_client=aggregate_client  # Story AI5.6: Pass aggregate client for weekly aggregates
            )
            # Use incremental update if enabled and previous run exists
            if self.enable_incremental and self._last_pattern_update_time and hasattr(day_type_detector, 'incremental_update'):
                day_type_patterns = day_type_detector.incremental_update(events_df, self._last_pattern_update_time)
            else:
                day_type_patterns = day_type_detector.detect_patterns(events_df)
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
                seasonal_patterns = seasonal_detector.incremental_update(events_df, self._last_pattern_update_time)
            else:
                seasonal_patterns = seasonal_detector.detect_patterns(events_df)
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
                anomaly_patterns = anomaly_detector.incremental_update(events_df, self._last_pattern_update_time)
            else:
                anomaly_patterns = anomaly_detector.detect_patterns(events_df)
            all_patterns.extend(anomaly_patterns)
            logger.info(f"    ✅ Found {len(anomaly_patterns)} anomaly patterns (daily aggregates stored)")
            
            # Update last analysis time after pattern detection completes
            self._last_analysis_time = datetime.now(timezone.utc)
            if self._last_pattern_update_time is None:
                self._last_pattern_update_time = self._last_analysis_time
            
            logger.info(f"✅ Total patterns detected: {len(all_patterns)}")
            logger.info(f"   📦 Aggregates stored: 6 Group A (daily), 2 Group B (weekly), 2 Group C (monthly)")
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
            # Phase 3c: Synergy Detection (NEW - Epic AI-3)
            # ================================================================
            logger.info("🔗 Phase 3c/7: Synergy Detection (Epic AI-3)...")
            logger.info("   → Starting synergy detection with relaxed parameters...")
            
            try:
                from ..synergy_detection import DeviceSynergyDetector
                from ..database.crud import store_synergy_opportunities
                from ..clients.ha_client import HomeAssistantClient
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
                
                synergy_detector = DeviceSynergyDetector(
                    data_api_client=data_client,
                    ha_client=ha_client,  # Story AI4.3: Enable automation filtering!
                    influxdb_client=data_client.influxdb_client,  # Enable advanced scoring (Story AI3.2)
                    min_confidence=0.5,  # Lowered from 0.7 to be less restrictive
                    same_area_required=False  # Relaxed requirement to find more opportunities
                )
                
                logger.info("   → Calling detect_synergies() method...")
                synergies = await synergy_detector.detect_synergies()
                
                logger.info(f"✅ Device synergy detection complete:")
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
                    logger.warning(f"     → Continuing with empty weather opportunities list")
                    # Continue without weather opportunities but don't skip the phase
                
                logger.info(f"✅ Total synergies (device + weather): {len(synergies)}")
                logger.info(f"   → Device synergies: {len(synergies) - len(weather_opportunities) if 'weather_opportunities' in locals() else len(synergies)}")
                logger.info(f"   → Weather synergies: {len(weather_opportunities) if 'weather_opportunities' in locals() else 0}")
                
                # Store synergies in database
                if synergies:
                    async with get_db_session() as db:
                        synergies_stored = await store_synergy_opportunities(db, synergies)
                    logger.info(f"   💾 Stored {synergies_stored} synergies in database")
                    job_result['synergies_detected'] = len(synergies)
                    job_result['synergies_stored'] = synergies_stored
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
            
            # ================================================================
            # Phase 4: Feature Analysis (Epic AI-2)
            # ================================================================
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
                opportunities = analysis_result.get('opportunities', [])
                
                logger.info(f"✅ Feature analysis complete:")
                logger.info(f"   - Devices analyzed: {analysis_result.get('devices_analyzed', 0)}")
                logger.info(f"   - Opportunities found: {len(opportunities)}")
                logger.info(f"   - Average utilization: {analysis_result.get('avg_utilization', 0):.1f}%")
                
                job_result['devices_analyzed'] = analysis_result.get('devices_analyzed', 0)
                job_result['opportunities_found'] = len(opportunities)
                job_result['avg_utilization'] = analysis_result.get('avg_utilization', 0)
                
            except Exception as e:
                logger.error(f"⚠️ Feature analysis failed: {e}")
                logger.info("   → Continuing with suggestions...")
                opportunities = []
                job_result['devices_analyzed'] = 0
                job_result['opportunities_found'] = 0
            
            # ================================================================
            # Phase 5: Combined Suggestion Generation (AI-1 + AI-2 + AI-3)
            # ================================================================
            logger.info("💡 Phase 5/7: Combined Suggestion Generation (AI-1 + AI-2)...")
            
            # Initialize unified prompt builder with device intelligence
            from ..prompt_building.unified_prompt_builder import UnifiedPromptBuilder
            
            device_intel_client = DeviceIntelligenceClient(settings.device_intelligence_url)
            unified_builder = UnifiedPromptBuilder(device_intelligence_client=device_intel_client)
            
            # Initialize OpenAI client
            openai_client = OpenAIClient(api_key=settings.openai_api_key)
            
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
                sorted_patterns = sorted(all_patterns, key=lambda p: p['confidence'], reverse=True)
                top_patterns = sorted_patterns[:10]
                
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
            
            if synergies:
                try:
                    from ..synergy_detection.synergy_suggestion_generator import SynergySuggestionGenerator
                    
                    synergy_generator = SynergySuggestionGenerator(
                        llm_client=openai_client
                    )
                    
                    synergy_suggestions = await synergy_generator.generate_suggestions(
                        synergies=synergies,
                        max_suggestions=5
                    )
                    logger.info(f"     ✅ Generated {len(synergy_suggestions)} synergy suggestions")
                    
                except Exception as e:
                    logger.error(f"     ❌ Synergy suggestion generation failed: {e}")
            else:
                logger.info("     ℹ️  No synergies available for suggestions")
            
            # ----------------------------------------------------------------
            # Part D: Combine and rank all suggestions
            # ----------------------------------------------------------------
            logger.info("  → Part D: Combining and ranking all suggestions...")
            
            all_suggestions = pattern_suggestions + feature_suggestions + synergy_suggestions
            all_suggestions.sort(key=lambda s: s.get('confidence', 0.5), reverse=True)
            all_suggestions = all_suggestions[:10]  # Top 10 total
            
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
            logger.info(f"  ")
            logger.info(f"  Epic AI-1 (Pattern Detection):")
            logger.info(f"    - Events analyzed: {len(events_df)}")
            logger.info(f"    - Patterns detected: {len(all_patterns)}")
            logger.info(f"    - Pattern suggestions: {len(pattern_suggestions)}")
            logger.info(f"  ")
            logger.info(f"  Epic AI-2 (Device Intelligence):")
            logger.info(f"    - Devices checked: {job_result.get('devices_checked', 0)}")
            logger.info(f"    - Capabilities updated: {job_result.get('capabilities_updated', 0)}")
            logger.info(f"    - Opportunities found: {job_result.get('opportunities_found', 0)}")
            logger.info(f"    - Feature suggestions: {len(feature_suggestions)}")
            logger.info(f"  ")
            logger.info(f"  Combined Results:")
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
    
    def _store_job_history(self, job_result: Dict):
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
    
    def get_next_run_time(self) -> Optional[datetime]:
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

