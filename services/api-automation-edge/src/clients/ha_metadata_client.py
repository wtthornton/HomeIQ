"""
Home Assistant Metadata Client

Epic A3: Collect HA version and instance ID
"""

import logging
from typing import Dict, Optional

from .ha_rest_client import HARestClient

logger = logging.getLogger(__name__)


class HAMetadataClient:
    """
    Client for collecting Home Assistant metadata.
    
    Features:
    - Collect HA version via /api/config
    - Collect instance ID if available
    - Record in capability graph metadata
    """
    
    def __init__(self, rest_client: Optional[HARestClient] = None):
        """
        Initialize HA metadata client.
        
        Args:
            rest_client: Optional HARestClient instance
        """
        self.rest_client = rest_client or HARestClient()
    
    async def get_ha_version(self) -> Optional[str]:
        """
        Get Home Assistant version.
        
        Returns:
            HA version string or None if unavailable
        """
        try:
            config = await self.rest_client.get_config()
            version = config.get("version")
            logger.info(f"HA version: {version}")
            return version
        except Exception as e:
            logger.error(f"Failed to get HA version: {e}")
            return None
    
    async def get_instance_id(self) -> Optional[str]:
        """
        Get Home Assistant instance ID.
        
        Returns:
            Instance ID or None if unavailable
        """
        try:
            config = await self.rest_client.get_config()
            # Instance ID may be in different locations depending on HA version
            instance_id = (
                config.get("location_name") or
                config.get("instance_id") or
                config.get("uuid")
            )
            logger.info(f"HA instance ID: {instance_id}")
            return instance_id
        except Exception as e:
            logger.error(f"Failed to get HA instance ID: {e}")
            return None
    
    async def get_metadata(self) -> Dict[str, Optional[str]]:
        """
        Get all HA metadata.
        
        Returns:
            Dictionary with version and instance_id
        """
        version = await self.get_ha_version()
        instance_id = await self.get_instance_id()
        
        return {
            "version": version,
            "instance_id": instance_id,
        }
    
    async def close(self):
        """Close underlying REST client"""
        await self.rest_client.close()
