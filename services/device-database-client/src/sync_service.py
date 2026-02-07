"""
Background Sync Service
Phase 3.1: Periodically sync device capabilities from Device Database
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger("device-database-client")

# Backoff constants
MIN_BACKOFF_SECONDS = 60       # 1 minute
MAX_BACKOFF_SECONDS = 3600     # 1 hour


class DeviceSyncService:
    """Background service for syncing device data"""

    def __init__(
        self,
        db_client: Any,
        cache: Any,
        sync_interval_hours: int = 24
    ):
        """
        Initialize sync service.

        Args:
            db_client: Device Database client
            cache: Device cache
            sync_interval_hours: Hours between syncs
        """
        self.db_client = db_client
        self.cache = cache
        self.sync_interval = timedelta(hours=sync_interval_hours)
        self._running = False
        self._task: asyncio.Task | None = None
        self.last_sync: datetime | None = None
        self._consecutive_failures = 0

    async def start(self):
        """Start background sync service"""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._sync_loop())
        logger.info("Device sync service started")

    async def stop(self):
        """Stop background sync service"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Device sync service stopped")

    async def _sync_loop(self):
        """Background sync loop"""
        while self._running:
            try:
                await self._sync_devices()
                self._consecutive_failures = 0
                await asyncio.sleep(self.sync_interval.total_seconds())
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._consecutive_failures += 1
                # Exponential backoff: 60s, 120s, 240s, ... capped at 3600s
                backoff = min(
                    MIN_BACKOFF_SECONDS * (2 ** (self._consecutive_failures - 1)),
                    MAX_BACKOFF_SECONDS,
                )
                logger.error(
                    f"Error in sync loop (attempt {self._consecutive_failures}): {e}. "
                    f"Retrying in {backoff}s"
                )
                await asyncio.sleep(backoff)

    async def _sync_devices(self):
        """Sync device data from Device Database"""
        if not self.db_client.is_configured():
            logger.debug("Device Database not configured, skipping sync")
            return

        logger.info("Starting device sync from Device Database...")
        synced = 0
        failed = 0

        # Get all cached entries and check staleness
        if hasattr(self.cache, 'cache_dir') and self.cache.cache_dir.exists():
            for cache_file in self.cache.cache_dir.glob("*.json"):
                try:
                    with open(cache_file) as f:
                        data = json.load(f)
                    manufacturer = data.get("manufacturer")
                    model = data.get("model")
                    if manufacturer and model and self.cache.is_stale(manufacturer, model):
                        device_info = await self.db_client.get_device_info(manufacturer, model)
                        if device_info:
                            self.cache.set(manufacturer, model, device_info)
                            synced += 1
                except Exception as e:
                    logger.warning(f"Failed to sync cache entry {cache_file.name}: {e}")
                    failed += 1

        self.last_sync = datetime.now(timezone.utc)
        logger.info(f"Device sync completed: {synced} updated, {failed} failed")
