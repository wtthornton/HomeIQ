"""
Training Scheduler

Built-in nightly training scheduler for Device Intelligence models.
Uses APScheduler to automatically train models on a configurable schedule.

Epic 46, Story 46.2: Built-in Nightly Training Scheduler
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from ..config import Settings
from ..core.predictive_analytics import PredictiveAnalyticsEngine

logger = logging.getLogger(__name__)


class TrainingScheduler:
    """
    Schedules and executes automatic model training.
    
    Follows APScheduler pattern from ai-automation-service:
    - AsyncIOScheduler for async support
    - CronTrigger for flexible scheduling
    - Graceful shutdown handling
    - Concurrent run prevention
    """

    def __init__(self, settings: Settings, analytics_engine: PredictiveAnalyticsEngine | None = None):
        """
        Initialize training scheduler.
        
        Args:
            settings: Application settings
            analytics_engine: Optional analytics engine instance (created if not provided)
        """
        self.settings = settings
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        self.analytics_engine = analytics_engine
        self._last_training_time: datetime | None = None
        self._last_training_status: str = "never_run"
        self._last_training_error: str | None = None
        
        logger.info(
            f"TrainingScheduler initialized: "
            f"schedule={settings.ML_TRAINING_SCHEDULE}, "
            f"enabled={settings.ML_TRAINING_ENABLED}, "
            f"mode={settings.ML_TRAINING_MODE}"
        )

    def start(self):
        """
        Start the training scheduler and register the training job.
        """
        if not self.settings.ML_TRAINING_ENABLED:
            logger.info("Training scheduler disabled (ML_TRAINING_ENABLED=false)")
            return
        
        try:
            # Validate cron expression
            try:
                CronTrigger.from_crontab(self.settings.ML_TRAINING_SCHEDULE)
            except Exception as e:
                logger.error(f"❌ Invalid cron expression '{self.settings.ML_TRAINING_SCHEDULE}': {e}")
                raise ValueError(f"Invalid cron expression: {e}") from e
            
            # Validate training mode
            if self.settings.ML_TRAINING_MODE not in ['full', 'incremental']:
                logger.error(f"❌ Invalid training mode '{self.settings.ML_TRAINING_MODE}'. Must be 'full' or 'incremental'")
                raise ValueError(f"Invalid training mode: {self.settings.ML_TRAINING_MODE}")
            
            # Add scheduled job
            self.scheduler.add_job(
                self._run_training,
                CronTrigger.from_crontab(self.settings.ML_TRAINING_SCHEDULE),
                id='nightly_training',
                name='Nightly Model Training',
                replace_existing=True,
                misfire_grace_time=3600  # Allow up to 1 hour late start
            )
            
            self.scheduler.start()
            job = self.scheduler.get_job('nightly_training')
            next_run = job.next_run_time if job else None
            
            logger.info(f"✅ Training scheduler started: schedule={self.settings.ML_TRAINING_SCHEDULE}")
            logger.info(f"   Mode: {self.settings.ML_TRAINING_MODE}")
            if next_run:
                logger.info(f"   Next run: {next_run}")
        
        except Exception as e:
            logger.error(f"❌ Failed to start training scheduler: {e}", exc_info=True)
            raise

    def stop(self):
        """
        Stop the training scheduler gracefully.
        """
        try:
            if self.scheduler.running:
                # Wait for running training to complete (with timeout)
                if self.is_running:
                    logger.info("Waiting for running training to complete (max 5 minutes)...")
                    # Note: We can't actually wait for async function, but we can shutdown gracefully
                
                self.scheduler.shutdown(wait=True)
                logger.info("✅ Training scheduler stopped")
        except Exception as e:
            logger.error(f"❌ Failed to stop training scheduler: {e}", exc_info=True)

    async def _run_training(self):
        """
        Execute scheduled training.
        
        This method is called by the scheduler automatically at the configured time.
        """
        # Prevent concurrent runs
        if self.is_running:
            logger.warning("⚠️ Training already running, skipping scheduled run")
            return
        
        self.is_running = True
        start_time = datetime.now(timezone.utc)
        
        try:
            logger.info("=" * 80)
            logger.info("🚀 Starting scheduled model training")
            logger.info(f"   Mode: {self.settings.ML_TRAINING_MODE}")
            logger.info(f"   Time: {start_time.isoformat()}")
            logger.info("=" * 80)
            
            # Get or create analytics engine
            if not self.analytics_engine:
                self.analytics_engine = PredictiveAnalyticsEngine(self.settings)
                await self.analytics_engine.initialize_models()
            
            # Execute training based on mode
            if self.settings.ML_TRAINING_MODE == "incremental":
                # Use incremental update if available (10-50x faster)
                logger.info("Using incremental update mode (faster)")
                await self._run_incremental_training()
            else:
                # Full retrain
                logger.info("Using full retrain mode")
                await self._run_full_training()
            
            # Update status
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            self._last_training_time = end_time
            self._last_training_status = "success"
            self._last_training_error = None
            
            logger.info("=" * 80)
            logger.info(f"✅ Scheduled training completed successfully")
            logger.info(f"   Duration: {duration:.1f} seconds")
            logger.info("=" * 80)
        
        except Exception as e:
            # Update error status
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            self._last_training_time = end_time
            self._last_training_status = "failed"
            self._last_training_error = str(e)
            
            logger.error("=" * 80)
            logger.error(f"❌ Scheduled training failed: {e}")
            logger.error(f"   Duration: {duration:.1f} seconds")
            logger.error("=" * 80, exc_info=True)
        
        finally:
            self.is_running = False

    async def _run_full_training(self):
        """Execute full model retraining."""
        await self.analytics_engine.train_models(days_back=180)

    async def _run_incremental_training(self):
        """
        Execute incremental model update (10-50x faster).
        
        Falls back to full training if incremental learning not available.
        """
        # Check if incremental learning is supported
        if hasattr(self.analytics_engine, 'update_models_incremental'):
            try:
                await self.analytics_engine.update_models_incremental(days_back=180)
                logger.info("✅ Incremental update completed")
                return
            except Exception as e:
                logger.warning(f"⚠️ Incremental update failed, falling back to full training: {e}")
                # Fall through to full training
        
        # Fallback to full training
        logger.info("Using full training (incremental not available)")
        await self._run_full_training()

    async def trigger_training_now(self, mode: str | None = None) -> dict[str, Any]:
        """
        Manually trigger training immediately.
        
        Args:
            mode: Optional training mode override ('full' or 'incremental')
        
        Returns:
            Dictionary with training status and information
        """
        if self.is_running:
            return {
                "status": "running",
                "message": "Training is already running",
                "last_training_time": self._last_training_time.isoformat() if self._last_training_time else None,
                "last_training_status": self._last_training_status
            }
        
        # Use provided mode or default from settings
        training_mode = mode or self.settings.ML_TRAINING_MODE
        
        # Run training in background
        asyncio.create_task(self._run_training_with_mode(training_mode))
        
        return {
            "status": "triggered",
            "message": f"Training triggered in {training_mode} mode",
            "mode": training_mode,
            "estimated_duration": "30-300 seconds (incremental) or 60-600 seconds (full)"
        }

    async def _run_training_with_mode(self, mode: str):
        """Run training with specific mode (for manual trigger)."""
        original_mode = self.settings.ML_TRAINING_MODE
        try:
            # Temporarily override mode
            self.settings.ML_TRAINING_MODE = mode
            await self._run_training()
        finally:
            # Restore original mode
            self.settings.ML_TRAINING_MODE = original_mode

    def get_status(self) -> dict[str, Any]:
        """
        Get scheduler status and information.
        
        Returns:
            Dictionary with scheduler status, last training info, and next run time
        """
        job = self.scheduler.get_job('nightly_training')
        next_run = job.next_run_time if job else None
        
        return {
            "enabled": self.settings.ML_TRAINING_ENABLED,
            "schedule": self.settings.ML_TRAINING_SCHEDULE,
            "mode": self.settings.ML_TRAINING_MODE,
            "running": self.is_running,
            "next_run_time": next_run.isoformat() if next_run else None,
            "last_training_time": self._last_training_time.isoformat() if self._last_training_time else None,
            "last_training_status": self._last_training_status,
            "last_training_error": self._last_training_error
        }

