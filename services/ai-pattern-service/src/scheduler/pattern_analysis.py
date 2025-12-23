"""
Pattern Analysis Scheduler

Epic 39, Story 39.6: Daily Scheduler Migration
Simplified scheduler focused on pattern detection and synergy detection.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from ..clients.data_api_client import DataAPIClient
from ..clients.mqtt_client import MQTTNotificationClient
from ..config import settings
from ..crud import store_patterns, store_synergy_opportunities
from ..database import get_db
from ..pattern_analyzer.co_occurrence import CoOccurrencePatternDetector
from ..pattern_analyzer.time_of_day import TimeOfDayPatternDetector
from ..synergy_detection.synergy_detector import DeviceSynergyDetector

logger = logging.getLogger(__name__)


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
            self.is_running = False
            logger.info("✅ Pattern analysis scheduler stopped")
        except Exception as e:
            logger.error(f"❌ Failed to stop scheduler: {e}", exc_info=True)

    async def run_pattern_analysis(self):
        """
        Run pattern detection and synergy detection analysis.
        
        Epic 39, Story 39.6: Simplified version focusing on:
        1. Pattern detection (time-of-day, co-occurrence)
        2. Synergy detection
        3. Store results
        4. Publish MQTT notifications
        """
        start_time = datetime.now(timezone.utc)
        logger.info("=" * 80)
        logger.info("🔍 Starting Pattern Analysis Run")
        logger.info("=" * 80)

        job_result = {
            "status": "running",
            "start_time": start_time.isoformat(),
            "patterns_detected": 0,
            "synergies_detected": 0,
            "errors": []
        }

        try:
            # Phase 1: Fetch Events
            logger.info("Phase 1: Fetching events from Data API...")
            async with DataAPIClient(base_url=settings.data_api_url) as data_client:
                # Fetch last 7 days of events for pattern detection
                end_time = datetime.now(timezone.utc)
                start_time_events = end_time - timedelta(days=7)
                
                events_df = await data_client.fetch_events(
                    start_time=start_time_events,
                    end_time=end_time,
                    limit=50000  # Reasonable limit for pattern detection
                )

                if events_df.empty:
                    logger.warning("⚠️ No events found for pattern analysis")
                    job_result["status"] = "completed"
                    job_result["end_time"] = datetime.now(timezone.utc).isoformat()
                    await self._publish_notification(job_result)
                    return

                logger.info(f"✅ Fetched {len(events_df)} events for analysis")

                # Phase 2: Pattern Detection
                logger.info("Phase 2: Running pattern detection...")
                all_patterns = []

                # Time-of-day patterns
                logger.info("  → Running time-of-day detector...")
                try:
                    tod_detector = TimeOfDayPatternDetector(
                        min_occurrences=settings.time_of_day_occurrence_overrides.get('min_occurrences', 3),
                        min_confidence=settings.time_of_day_confidence_overrides.get('min_confidence', 0.6)
                    )
                    tod_patterns = await asyncio.to_thread(tod_detector.detect_patterns, events_df)
                    all_patterns.extend(tod_patterns)
                    logger.info(f"    ✅ Found {len(tod_patterns)} time-of-day patterns")
                except Exception as e:
                    logger.error(f"    ❌ Time-of-day detection failed: {e}", exc_info=True)
                    job_result["errors"].append(f"Time-of-day detection: {str(e)}")

                # Co-occurrence patterns
                logger.info("  → Running co-occurrence detector...")
                try:
                    co_detector = CoOccurrencePatternDetector(
                        min_support=settings.co_occurrence_support_overrides.get('min_support', 0.1),
                        min_confidence=settings.co_occurrence_confidence_overrides.get('min_confidence', 0.5),
                        window_minutes=5
                    )
                    co_patterns = await asyncio.to_thread(co_detector.detect_patterns, events_df)
                    all_patterns.extend(co_patterns)
                    logger.info(f"    ✅ Found {len(co_patterns)} co-occurrence patterns")
                except Exception as e:
                    logger.error(f"    ❌ Co-occurrence detection failed: {e}", exc_info=True)
                    job_result["errors"].append(f"Co-occurrence detection: {str(e)}")

                job_result["patterns_detected"] = len(all_patterns)
                logger.info(f"✅ Total patterns detected: {len(all_patterns)}")

                # Phase 3: Synergy Detection
                logger.info("Phase 3: Running synergy detection...")
                synergies = []
                try:
                    # Fetch devices for synergy detection
                    devices = await data_client.fetch_devices(limit=1000)
                    entities = await data_client.fetch_entities(limit=1000)
                    
                    synergy_detector = DeviceSynergyDetector()
                    synergies = await synergy_detector.detect_synergies(
                        events_df=events_df,
                        devices=devices,
                        entities=entities
                    )
                    job_result["synergies_detected"] = len(synergies)
                    logger.info(f"✅ Found {len(synergies)} synergy opportunities")
                except Exception as e:
                    logger.error(f"❌ Synergy detection failed: {e}", exc_info=True)
                    job_result["errors"].append(f"Synergy detection: {str(e)}")

                # Phase 4: Store Results
                logger.info("Phase 4: Storing results in database...")
                async for db in get_db():
                    try:
                        # Store patterns
                        if all_patterns:
                            stored_patterns = await store_patterns(db, all_patterns)
                            logger.info(f"✅ Stored {stored_patterns} patterns in database")
                        
                        # Store synergies
                        if synergies:
                            stored_synergies = await store_synergy_opportunities(
                                db,
                                synergies,
                                validate_with_patterns=False  # Disabled for Story 39.6
                            )
                            logger.info(f"✅ Stored {stored_synergies} synergies in database")
                    except Exception as e:
                        logger.error(f"❌ Failed to store results: {e}", exc_info=True)
                        job_result["errors"].append(f"Storage: {str(e)}")
                    break  # Exit async generator

        except Exception as e:
            logger.error(f"❌ Pattern analysis failed: {e}", exc_info=True)
            job_result["status"] = "failed"
            job_result["errors"].append(f"Analysis failed: {str(e)}")

        # Phase 5: Publish Notification
        end_time = datetime.now(timezone.utc)
        job_result["status"] = "completed" if job_result["status"] == "running" else job_result["status"]
        job_result["end_time"] = end_time.isoformat()
        job_result["duration_seconds"] = (end_time - start_time).total_seconds()

        await self._publish_notification(job_result)

        logger.info("=" * 80)
        logger.info(f"✅ Pattern Analysis Complete ({job_result['duration_seconds']:.1f}s)")
        logger.info(f"   Patterns: {job_result['patterns_detected']}, Synergies: {job_result['synergies_detected']}")
        if job_result["errors"]:
            logger.warning(f"   Errors: {len(job_result['errors'])}")
        logger.info("=" * 80)

    async def _publish_notification(self, job_result: dict[str, Any]):
        """Publish MQTT notification about analysis completion"""
        if not self.mqtt_client:
            logger.debug("MQTT client not configured, skipping notification")
            return

        try:
            topic = "homeiq/ai-automation/analysis/pattern/complete"
            payload = {
                "service": "ai-pattern-service",
                "timestamp": datetime.now(timezone.utc).isoformat(),
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

