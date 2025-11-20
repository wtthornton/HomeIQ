"""
Device Intelligence Service Client for AI Automation Service

Provides access to rich device data including capabilities, health scores, and area mappings.
"""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

class DeviceIntelligenceClient:
    """Client for accessing device intelligence data"""

    def __init__(self, base_url: str = "http://device-intelligence-service:8021"):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(
            timeout=5.0,  # Reduced timeout to 5 seconds
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        logger.info(f"Device Intelligence client initialized: {self.base_url}")

    async def get_devices_by_area(self, area_name: str) -> list[dict[str, Any]]:
        """Get all devices in a specific area"""
        try:
            response = await self.client.get(f"{self.base_url}/api/discovery/devices", timeout=5.0)
            if response.status_code == 200:
                devices = response.json()

                # Handle case where response might be a dict with devices list
                if isinstance(devices, dict):
                    devices = devices.get('devices', []) or devices.get('data', []) or []

                # Ensure devices is a list
                if not isinstance(devices, list):
                    logger.warning(f"Unexpected devices response type: {type(devices)}, expected list")
                    return []

                # Filter by area name (case insensitive)
                filtered_devices = []
                for d in devices:
                    # Handle case where d might be a string or dict
                    if isinstance(d, str):
                        # If device is just an ID string, we can't filter by area
                        logger.debug(f"Device is string ID: {d}, skipping area filter")
                        continue
                    elif isinstance(d, dict):
                        area = d.get('area_name') or d.get('area') or d.get('area_id') or ''
                        if isinstance(area, str) and area.lower() == area_name.lower():
                            filtered_devices.append(d)
                    else:
                        logger.warning(f"Unexpected device type in list: {type(d)}")

                logger.debug(f"Found {len(filtered_devices)} devices in area '{area_name}'")
                return filtered_devices
            else:
                logger.error(f"Failed to get devices: {response.status_code}")
                return []
        except Exception as e:
            logger.warning(f"Device intelligence unavailable for area {area_name}: {e}", exc_info=True)
            return []

    async def get_device_details(self, device_id: str) -> dict[str, Any] | None:
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

    async def get_all_areas(self) -> list[dict[str, Any]]:
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

    async def get_device_recommendations(self, device_id: str) -> list[dict[str, Any]]:
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

    async def get_all_devices(self, limit: int = 100) -> list[dict[str, Any]]:
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

    async def search_sensors_by_condition(
        self,
        trigger_type: str,
        location: str | None = None,
        device_class: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Search for sensors matching trigger condition requirements.
        
        Args:
            trigger_type: Type of trigger (presence, motion, door, etc.)
            location: Optional location/area to search in
            device_class: Optional device class to filter by (occupancy, motion, door, etc.)
            
        Returns:
            List of matching sensor devices
        """
        try:
            # Get devices from area if location specified, otherwise get all devices
            if location:
                devices = await self.get_devices_by_area(location)
                # If no devices found in area, try broader search
                if not devices:
                    logger.debug(f"No devices found in area '{location}', trying broader search")
                    devices = await self.get_all_devices(limit=200)
            else:
                devices = await self.get_all_devices(limit=200)

            if not devices:
                logger.debug("No devices available for sensor search")
                return []

            # Filter devices by device class and domain
            matching_devices = []
            for device in devices:
                # Skip if device is just a string ID
                if isinstance(device, str):
                    continue

                # Get device information
                entity_id = device.get('entity_id') or device.get('id', '')
                device_domain = device.get('domain', '')
                device_device_class = device.get('device_class', '')

                # Extract domain from entity_id if not in device dict
                if not device_domain and '.' in entity_id:
                    device_domain = entity_id.split('.')[0]

                # Filter by domain (sensors should be binary_sensor or sensor)
                if device_domain not in ['binary_sensor', 'sensor']:
                    continue

                # Filter by device class if specified
                if device_class:
                    device_class_lower = device_class.lower()
                    device_device_class_lower = device_device_class.lower() if device_device_class else ''

                    # Check device_class field
                    if device_device_class_lower != device_class_lower:
                        # Also check entity_id for device class keywords
                        entity_id_lower = entity_id.lower()
                        if device_class_lower not in entity_id_lower:
                            # Check trigger type keywords in entity_id
                            trigger_keywords = {
                                'presence': ['presence', 'occupancy', 'occupant'],
                                'motion': ['motion', 'movement', 'pir'],
                                'door': ['door', 'contact'],
                                'window': ['window'],
                                'temperature': ['temperature', 'temp'],
                                'humidity': ['humidity', 'humid']
                            }
                            keywords = trigger_keywords.get(trigger_type, [])
                            if not any(keyword in entity_id_lower for keyword in keywords):
                                continue

                # Check device name for trigger type keywords if device_class not found
                if not device_device_class:
                    device_name = (
                        device.get('name') or
                        device.get('friendly_name') or
                        entity_id
                    ).lower()

                    trigger_keywords_map = {
                        'presence': ['presence', 'occupancy', 'occupant'],
                        'motion': ['motion', 'movement', 'pir'],
                        'door': ['door', 'contact'],
                        'window': ['window'],
                        'temperature': ['temperature', 'temp'],
                        'humidity': ['humidity', 'humid']
                    }

                    keywords = trigger_keywords_map.get(trigger_type, [])
                    if not any(keyword in device_name for keyword in keywords):
                        # Last resort: check entity_id
                        if not any(keyword in entity_id.lower() for keyword in keywords):
                            continue

                matching_devices.append(device)

            logger.debug(
                f"Found {len(matching_devices)} matching sensors for "
                f"trigger_type={trigger_type}, location={location}, device_class={device_class}"
            )
            return matching_devices

        except Exception as e:
            logger.error(f"Error searching sensors by condition: {e}", exc_info=True)
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

    async def get_team_tracker_status(self) -> dict[str, Any] | None:
        """Get Team Tracker integration status"""
        try:
            response = await self.client.get(f"{self.base_url}/api/team-tracker/status", timeout=5.0)
            if response.status_code == 200:
                status = response.json()
                logger.debug(f"Team Tracker status: {status.get('installation_status')}")
                return status
            else:
                logger.warning(f"Failed to get Team Tracker status: {response.status_code}")
                return None
        except Exception as e:
            logger.debug(f"Team Tracker not available: {e}")
            return None

    async def get_team_tracker_teams(self, active_only: bool = True) -> list[dict[str, Any]]:
        """
        Get configured Team Tracker teams for automation context.

        Args:
            active_only: If True, only return active teams

        Returns:
            List of configured teams with metadata
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/team-tracker/teams",
                params={"active_only": active_only},
                timeout=5.0
            )
            if response.status_code == 200:
                teams = response.json()
                logger.debug(f"Retrieved {len(teams)} Team Tracker teams (active_only={active_only})")
                return teams
            else:
                logger.warning(f"Failed to get Team Tracker teams: {response.status_code}")
                return []
        except Exception as e:
            logger.debug(f"Team Tracker teams not available: {e}")
            return []

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
        logger.info("Device Intelligence client closed")
