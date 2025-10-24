"""
Device Intelligence Service Client for AI Automation Service

Provides access to rich device data including capabilities, health scores, and area mappings.
"""

import httpx
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class DeviceIntelligenceClient:
    """Client for accessing device intelligence data"""
    
    def __init__(self, base_url: str = "http://device-intelligence-service:8021"):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        logger.info(f"Device Intelligence client initialized: {self.base_url}")
    
    async def get_devices_by_area(self, area_name: str) -> List[Dict[str, Any]]:
        """Get all devices in a specific area"""
        try:
            response = await self.client.get(f"{self.base_url}/api/discovery/devices")
            if response.status_code == 200:
                devices = response.json()
                # Filter by area name (case insensitive)
                filtered_devices = [
                    d for d in devices 
                    if d.get('area_name', '').lower() == area_name.lower()
                ]
                logger.debug(f"Found {len(filtered_devices)} devices in area '{area_name}'")
                return filtered_devices
            else:
                logger.error(f"Failed to get devices: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error getting devices by area {area_name}: {e}")
            return []
    
    async def get_device_details(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed device information including capabilities"""
        try:
            response = await self.client.get(f"{self.base_url}/api/discovery/devices/{device_id}")
            if response.status_code == 200:
                device_data = response.json()
                logger.debug(f"Retrieved device details for {device_id}")
                return device_data
            elif response.status_code == 404:
                logger.warning(f"Device {device_id} not found")
                return None
            else:
                logger.error(f"Failed to get device {device_id}: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error getting device {device_id}: {e}")
            return None
    
    async def get_all_areas(self) -> List[Dict[str, Any]]:
        """Get all available areas"""
        try:
            response = await self.client.get(f"{self.base_url}/api/discovery/areas")
            if response.status_code == 200:
                areas = response.json()
                logger.debug(f"Retrieved {len(areas)} areas")
                return areas
            else:
                logger.error(f"Failed to get areas: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error getting areas: {e}")
            return []
    
    async def get_device_recommendations(self, device_id: str) -> List[Dict[str, Any]]:
        """Get optimization recommendations for a device"""
        try:
            response = await self.client.get(f"{self.base_url}/api/recommendations/{device_id}")
            if response.status_code == 200:
                data = response.json()
                recommendations = data.get('recommendations', [])
                logger.debug(f"Retrieved {len(recommendations)} recommendations for {device_id}")
                return recommendations
            else:
                logger.error(f"Failed to get recommendations for {device_id}: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error getting recommendations for {device_id}: {e}")
            return []
    
    async def get_all_devices(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all devices with optional limit"""
        try:
            response = await self.client.get(f"{self.base_url}/api/discovery/devices", params={"limit": limit})
            if response.status_code == 200:
                devices = response.json()
                logger.debug(f"Retrieved {len(devices)} devices")
                return devices
            else:
                logger.error(f"Failed to get all devices: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error getting all devices: {e}")
            return []
    
    async def health_check(self) -> bool:
        """Check if device intelligence service is healthy"""
        try:
            response = await self.client.get(f"{self.base_url}/", timeout=5.0)
            if response.status_code == 200:
                logger.debug("Device intelligence service is healthy")
                return True
            else:
                logger.warning(f"Device intelligence service health check failed: {response.status_code}")
                return False
        except Exception as e:
            logger.warning(f"Device intelligence service health check error: {e}")
            return False
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
        logger.info("Device Intelligence client closed")