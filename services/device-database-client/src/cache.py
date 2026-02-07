"""
Local Caching Layer
Phase 3.1: Cache device information locally
"""

import hashlib
import json
import logging
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("device-database-client")


class DeviceCache:
    """Local cache for device information"""

    def __init__(self, cache_dir: str | None = None, ttl_hours: int = 24):
        """
        Initialize device cache.

        Args:
            cache_dir: Directory for cache files
            ttl_hours: Time-to-live in hours
        """
        cache_dir = cache_dir or os.getenv("DEVICE_CACHE_DIR", "data/device_cache")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(hours=ttl_hours)

    def _get_cache_path(self, manufacturer: str, model: str) -> Path:
        """Get cache file path for device using hash-based filenames to prevent path traversal."""
        key = f"{manufacturer}:{model}"
        filename = hashlib.sha256(key.encode()).hexdigest() + ".json"
        return self.cache_dir / filename

    def get(self, manufacturer: str, model: str) -> dict[str, Any] | None:
        """
        Get device info from cache.

        Args:
            manufacturer: Device manufacturer
            model: Device model

        Returns:
            Cached device info or None if not found or stale
        """
        cache_path = self._get_cache_path(manufacturer, model)

        if not cache_path.exists():
            return None

        try:
            # Check staleness via file mtime before reading
            if self.is_stale(manufacturer, model):
                logger.debug(f"Cache expired for {manufacturer} {model}")
                return None

            with open(cache_path, "r") as f:
                data = json.load(f)

            return data.get("device_info")

        except Exception as e:
            logger.warning(f"Error reading cache for {manufacturer} {model}: {e}")
            return None

    def set(self, manufacturer: str, model: str, device_info: dict[str, Any]):
        """
        Cache device info using atomic file writes.

        Args:
            manufacturer: Device manufacturer
            model: Device model
            device_info: Device information to cache
        """
        cache_path = self._get_cache_path(manufacturer, model)

        try:
            data = {
                "manufacturer": manufacturer,
                "model": model,
                "device_info": device_info,
                "cached_at": datetime.now(timezone.utc).isoformat()
            }

            # Atomic write: write to temp file then replace
            fd, tmp_path = tempfile.mkstemp(
                dir=str(self.cache_dir), suffix=".tmp"
            )
            try:
                with os.fdopen(fd, "w") as f:
                    json.dump(data, f, indent=2)
                os.replace(tmp_path, str(cache_path))
            except Exception:
                # Clean up temp file on failure
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise

            logger.debug(f"Cached device info for {manufacturer} {model}")

        except Exception as e:
            logger.warning(f"Error caching device info for {manufacturer} {model}: {e}")

    def is_stale(self, manufacturer: str, model: str) -> bool:
        """
        Check if cache entry is stale using file modification time.

        Args:
            manufacturer: Device manufacturer
            model: Device model

        Returns:
            True if cache is stale or doesn't exist
        """
        cache_path = self._get_cache_path(manufacturer, model)
        if not cache_path.exists():
            return True
        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime, tz=timezone.utc)
        return datetime.now(timezone.utc) - mtime > self.ttl
