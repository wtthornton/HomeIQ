"""
Capability Discovery Service
Phase 3.2: Discover device capabilities from HA API only
"""

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class CapabilityDiscoveryService:
    """Service for discovering device capabilities from HA API"""

    def __init__(self):
        """Initialize capability discovery service"""
        self._discoverer = None

    def _get_discoverer(self):
        """Get capability discoverer (lazy import)"""
        if self._discoverer is None:
            try:
                import sys
                sys.path.append(os.path.join(os.path.dirname(__file__), '../../../device-intelligence-service/src'))
                from capability_discovery.ha_api_discovery import HACapabilityDiscoverer
                self._discoverer = HACapabilityDiscoverer()
            except ImportError:
                logger.warning("HA capability discoverer not available")
                return None
        return self._discoverer

    async def discover_device_capabilities(
        self,
        device_id: str,
        entity_ids: list[str]
    ) -> dict[str, Any]:
        """
        Discover capabilities for a device.
        
        Args:
            device_id: Device identifier
            entity_ids: List of entity IDs for this device
            
        Returns:
            Dictionary with capabilities and features
        """
        discoverer = self._get_discoverer()
        if not discoverer:
            return {"capabilities": [], "features": {}}
        
        try:
            result = await discoverer.discover_capabilities(device_id, entity_ids)
            return result
        except Exception as e:
            logger.error(f"Error discovering capabilities for {device_id}: {e}")
            return {"capabilities": [], "features": {}}

    def format_capabilities_for_storage(self, capabilities_data: dict[str, Any]) -> str | None:
        """
        Format capabilities data for storage in Device model.
        
        Args:
            capabilities_data: Capabilities dictionary
            
        Returns:
            JSON string for device_features_json field
        """
        if not capabilities_data:
            return None
        
        try:
            return json.dumps(capabilities_data)
        except Exception as e:
            logger.error(f"Error formatting capabilities: {e}")
            return None


# Singleton instance
_capability_service: CapabilityDiscoveryService | None = None


def get_capability_service() -> CapabilityDiscoveryService:
    """Get singleton capability discovery service instance"""
    global _capability_service
    if _capability_service is None:
        _capability_service = CapabilityDiscoveryService()
    return _capability_service

