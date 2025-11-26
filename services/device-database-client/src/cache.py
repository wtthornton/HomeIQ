"""
Local Caching Layer
Phase 3.1: Cache device information locally
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class DeviceCache:
    """Local cache for device information"""

    def __init__(self, cache_dir: str = "data/device_cache", ttl_hours: int = 24):
        """
        Initialize device cache.
        
        Args:
            cache_dir: Directory for cache files
            ttl_hours: Time-to-live in hours
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(hours=ttl_hours)

    def _get_cache_path(self, manufacturer: str, model: str) -> Path:
        """Get cache file path for device"""
        # Sanitize filename
        safe_manufacturer = manufacturer.replace("/", "_").replace("\\", "_")
        safe_model = model.replace("/", "_").replace("\\", "_")
        filename = f"{safe_manufacturer}_{safe_model}.json"
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
            with open(cache_path, "r") as f:
                data = json.load(f)
            
            # Check if cache is stale
            cached_time = datetime.fromisoformat(data.get("cached_at", ""))
            if datetime.now() - cached_time > self.ttl:
                logger.debug(f"Cache expired for {manufacturer} {model}")
                return None
            
            return data.get("device_info")
            
        except Exception as e:
            logger.warning(f"Error reading cache for {manufacturer} {model}: {e}")
            return None

    def set(self, manufacturer: str, model: str, device_info: dict[str, Any]):
        """
        Cache device info.
        
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
                "cached_at": datetime.now().isoformat()
            }
            
            with open(cache_path, "w") as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Cached device info for {manufacturer} {model}")
            
        except Exception as e:
            logger.warning(f"Error caching device info for {manufacturer} {model}: {e}")

    def is_stale(self, manufacturer: str, model: str) -> bool:
        """
        Check if cache entry is stale.
        
        Args:
            manufacturer: Device manufacturer
            model: Device model
            
        Returns:
            True if cache is stale or doesn't exist
        """
        cached = self.get(manufacturer, model)
        return cached is None

