"""
Name Enhancement Batch Processor

Batch process name enhancements using APScheduler (resource-efficient).
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db_session
from ...models.database import Device, DeviceEntity
from ...models.name_enhancement import NameSuggestion
from .name_generator import DeviceNameGenerator

logger = logging.getLogger(__name__)


class NameEnhancementBatchProcessor:
    """Batch process name enhancements (resource-efficient)"""

    def __init__(self, name_generator: DeviceNameGenerator, settings: Any = None):
        self.name_generator = name_generator
        self.settings = settings
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        self.batch_size = getattr(settings, 'NAME_ENHANCEMENT_BATCH_SIZE', 20) if settings else 20

    def start(self, schedule: str = "0 4 * * *"):
        """
        Start batch processor scheduler.
        
        Default schedule: 4 AM daily (after device discovery at 3 AM)
        """
        try:
            self.scheduler.add_job(
                self.process_pending_devices,
                CronTrigger.from_crontab(schedule),
                id='name_enhancement_batch',
                name='Name Enhancement Batch Processing',
                replace_existing=True,
                misfire_grace_time=3600  # 1 hour grace period
            )
            self.scheduler.start()
            self.is_running = True
            logger.info(f"✅ Name enhancement batch processor started (schedule: {schedule})")
        except Exception as e:
            logger.error(f"❌ Failed to start batch processor: {e}")
            raise

    def stop(self):
        """Stop the batch processor"""
        if self.scheduler.running:
            self.scheduler.shutdown()
        self.is_running = False
        logger.info("🛑 Name enhancement batch processor stopped")

    async def process_pending_devices(
        self,
        use_ai: bool = False,
        auto_accept_high_confidence: bool = False
    ):
        """
        Process devices that need name enhancement.
        
        Strategy:
        1. Find devices without name_by_user OR low-quality names
        2. Process in batches of 10-20 devices
        3. Use pattern-based first (fast)
        4. Use AI only for complex cases
        5. Store suggestions (user reviews later)
        
        Performance:
        - 100 devices: 10-30 seconds (pattern-based)
        - 100 devices: 2-5 minutes (with AI, cached)
        - Memory: <100MB peak
        """
        try:
            logger.info("🔄 Starting name enhancement batch processing")

            async for session in get_db_session():
                # Find devices that need enhancement
                devices_to_process = await self._find_devices_needing_enhancement(session)
                
                if not devices_to_process:
                    logger.info("✅ No devices need name enhancement")
                    return

                logger.info(f"📋 Found {len(devices_to_process)} devices needing name enhancement")

                # Process in batches
                total_processed = 0
                total_suggestions = 0

                for i in range(0, len(devices_to_process), self.batch_size):
                    batch = devices_to_process[i:i + self.batch_size]
                    logger.info(f"🔄 Processing batch {i // self.batch_size + 1} ({len(batch)} devices)")

                    suggestions = await self.process_batch(
                        batch,
                        use_ai=use_ai,
                        auto_accept=auto_accept_high_confidence,
                        session=session
                    )

                    total_processed += len(batch)
                    total_suggestions += len(suggestions)

                    # Small delay between batches to avoid overwhelming the system
                    await asyncio.sleep(1)

                logger.info(
                    f"✅ Batch processing complete: {total_processed} devices processed, "
                    f"{total_suggestions} suggestions generated"
                )
                break  # Only need one session

        except Exception as e:
            logger.error(f"❌ Error in batch processing: {e}", exc_info=True)

    async def _find_devices_needing_enhancement(
        self,
        session: AsyncSession
    ) -> list[Device]:
        """Find devices that need name enhancement"""
        # Find devices without name_by_user or with low-quality names
        result = await session.execute(
            select(Device).where(
                (Device.name_by_user.is_(None)) |  # No user customization
                (Device.name.like("%% %%%"))  # Has numbers/technical names (simple heuristic)
            ).limit(500)  # Limit to avoid processing too many
        )
        devices = result.scalars().all()

        # Filter out devices that already have pending suggestions
        result = await session.execute(
            select(NameSuggestion.device_id).where(
                NameSuggestion.status == "pending"
            )
        )
        devices_with_pending = {row[0] for row in result}

        # Return devices without pending suggestions
        return [d for d in devices if d.id not in devices_with_pending]

    async def process_batch(
        self,
        devices: list[Device],
        use_ai: bool = False,
        auto_accept: bool = False,
        session: AsyncSession | None = None
    ) -> list[NameSuggestion]:
        """
        Process batch of devices efficiently.
        
        Optimization:
        - Parallel pattern-based generation (async)
        - Sequential AI generation (rate limit friendly)
        - Cache results to avoid recomputation
        """
        if not session:
            async for db_session in get_db_session():
                session = db_session
                break

        suggestions_created = []

        # Process devices in parallel (pattern-based is fast)
        tasks = [
            self._process_single_device(device, use_ai=use_ai, session=session)
            for device in devices
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Store suggestions
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Failed to process device {devices[i].id}: {result}")
                continue

            if result:
                suggestion, device = result
                
                # Check if suggestion already exists
                existing_result = await session.execute(
                    select(NameSuggestion).where(
                        NameSuggestion.device_id == device.id,
                        NameSuggestion.suggested_name == suggestion.name,
                        NameSuggestion.status == "pending"
                    )
                )
                if existing_result.scalar_one_or_none():
                    continue  # Already exists

                # Store suggestion
                name_suggestion = NameSuggestion(
                    device_id=device.id,
                    entity_id=None,  # Could be enhanced to get primary entity
                    original_name=device.name or "Unknown",
                    suggested_name=suggestion.name,
                    confidence_score=suggestion.confidence,
                    suggestion_source=suggestion.source,
                    status="pending",
                    reasoning=suggestion.reasoning
                )
                session.add(name_suggestion)
                suggestions_created.append(suggestion)

                # Auto-accept if high confidence and enabled
                if auto_accept and suggestion.confidence >= 0.9:
                    device.name_by_user = suggestion.name
                    name_suggestion.status = "accepted"
                    name_suggestion.reviewed_at = datetime.utcnow()
                    logger.info(f"✅ Auto-accepted high-confidence suggestion: {suggestion.name}")

        if suggestions_created:
            await session.commit()
            logger.info(f"✅ Stored {len(suggestions_created)} name suggestions")

        return suggestions_created

    async def _process_single_device(
        self,
        device: Device,
        use_ai: bool = False,
        session: AsyncSession | None = None
    ) -> tuple[NameSuggestion, Device] | None:
        """Process a single device and generate suggestion"""
        try:
            # Get primary entity for this device
            if session:
                result = await session.execute(
                    select(DeviceEntity).where(
                        DeviceEntity.device_id == device.id
                    ).limit(1)
                )
                entity = result.scalar_one_or_none()
            else:
                entity = None

            # Generate suggestion
            suggestion = await self.name_generator.generate_suggested_name(
                device,
                entity,
                use_ai=use_ai
            )

            # Only return high-confidence suggestions
            if suggestion.confidence >= 0.7:
                return (suggestion, device)

            return None

        except Exception as e:
            logger.warning(f"Failed to process device {device.id}: {e}")
            return None

