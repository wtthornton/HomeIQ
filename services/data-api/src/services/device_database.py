"""
Device Database Integration Service
Phase 3.1: Integrate with Device Database client
"""

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class DeviceDatabaseService:
    """Service for Device Database integration"""

    def __init__(self):
        """Initialize Device Database service"""
        self.api_url = os.getenv("DEVICE_DATABASE_API_URL")
        self._db_client = None
        self._cache = None

    def _get_db_client(self):
        """Get Device Database client (lazy import)"""
        if self._db_client is None:
            try:
                import sys
                sys.path.append(os.path.join(os.path.dirname(__file__), '../../../device-database-client/src'))
                from db_client import DeviceDatabaseClient
                self._db_client = DeviceDatabaseClient()
            except ImportError:
                logger.warning("Device Database client not available")
                return None
        return self._db_client

    def _get_cache(self):
        """Get cache instance (lazy import)"""
        if self._cache is None:
            try:
                import sys
                sys.path.append(os.path.join(os.path.dirname(__file__), '../../../device-database-client/src'))
                from cache import DeviceCache
                cache_dir = os.getenv("DEVICE_CACHE_DIR", "data/device_cache")
                self._cache = DeviceCache(cache_dir=cache_dir)
            except ImportError:
                logger.warning("Device cache not available")
                return None
        return self._cache

    async def enrich_device(
        self,
        manufacturer: str,
        model: str
    ) -> dict[str, Any] | None:
        """
        Enrich device with Device Database information.
        
        Args:
            manufacturer: Device manufacturer
            model: Device model
            
        Returns:
            Enriched device information or None
        """
        if not manufacturer or not model or manufacturer == "Unknown" or model == "Unknown":
            return None
        
        # Check cache first
        cache = self._get_cache()
        if cache:
            cached = cache.get(manufacturer, model)
            if cached:
                logger.debug(f"Using cached device info for {manufacturer} {model}")
                return cached
        
        # Query Device Database
        db_client = self._get_db_client()
        if db_client and db_client.is_available():
            try:
                device_info = await db_client.get_device_info(manufacturer, model)
                if device_info:
                    # Cache the result
                    if cache:
                        cache.set(manufacturer, model, device_info)
                    return device_info
            except Exception as e:
                logger.warning(f"Failed to query Device Database: {e}")
        
        return None

    async def update_device_from_database(
        self,
        device: Any,
        device_info: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Update device model with Device Database information.
        
        Args:
            device: Device model instance
            device_info: Device Database info (will fetch if None)
            
        Returns:
            Dictionary of updates to apply
        """
        updates = {}
        
        if device_info is None:
            device_info = await self.enrich_device(device.manufacturer, device.model)
        
        if not device_info:
            return updates
        
        # Update power consumption specs
        if "power_consumption" in device_info:
            power = device_info["power_consumption"]
            if "idle_w" in power:
                updates["power_consumption_idle_w"] = power["idle_w"]
            if "active_w" in power:
                updates["power_consumption_active_w"] = power["active_w"]
            if "max_w" in power:
                updates["power_consumption_max_w"] = power["max_w"]
        
        # Update setup instructions
        if "setup_instructions_url" in device_info:
            updates["setup_instructions_url"] = device_info["setup_instructions_url"]
        
        # Update troubleshooting notes
        if "troubleshooting" in device_info:
            updates["troubleshooting_notes"] = json.dumps(device_info["troubleshooting"])
        
        # Update device features
        if "features" in device_info:
            updates["device_features_json"] = json.dumps(device_info["features"])
        
        # Update community rating
        if "rating" in device_info:
            updates["community_rating"] = device_info["rating"]
        
        # Update infrared codes
        if "infrared_codes" in device_info:
            updates["infrared_codes_json"] = json.dumps(device_info["infrared_codes"])
        
        return updates


# Singleton instance
_device_db_service: DeviceDatabaseService | None = None


def get_device_database_service() -> DeviceDatabaseService:
    """Get singleton Device Database service instance"""
    global _device_db_service
    if _device_db_service is None:
        _device_db_service = DeviceDatabaseService()
    return _device_db_service

