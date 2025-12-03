"""
Mock Device Intelligence Client

Pre-computed device capabilities for simulation.
Maintains same interface as production DeviceIntelligenceClient.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class MockDeviceIntelligenceClient:
    """
    Mock Device Intelligence client for simulation.
    
    Returns pre-computed device capabilities.
    Maintains same interface as production DeviceIntelligenceClient.
    """

    def __init__(self, base_url: str = "http://mock-device-intelligence:8019"):
        """
        Initialize mock Device Intelligence client.
        
        Args:
            base_url: Mock base URL (not used)
        """
        self.base_url = base_url
        
        # Pre-computed device capabilities
        self._devices: dict[str, dict[str, Any]] = {}
        self._capabilities: dict[str, list[dict[str, Any]]] = {}
        
        logger.info(f"MockDeviceIntelligenceClient initialized: base_url={base_url}")

    async def get_devices_by_area(self, area_name: str) -> list[dict[str, Any]]:
        """
        Get devices by area name.
        
        Args:
            area_name: Area/room name
            
        Returns:
            List of device dictionaries
        """
        # Filter devices by area
        devices = [
            device for device in self._devices.values()
            if device.get('area_id') == area_name or device.get('area_name') == area_name
        ]
        
        logger.debug(f"Found {len(devices)} devices in area {area_name}")
        return devices

    async def get_device_details(self, device_id: str) -> dict[str, Any] | None:
        """
        Get detailed device information including capabilities.
        
        Args:
            device_id: Device identifier
            
        Returns:
            Device dictionary with capabilities, or None if not found
        """
        device = self._devices.get(device_id)
        if not device:
            logger.warning(f"Device {device_id} not found")
            return None
        
        # Add capabilities
        device_copy = device.copy()
        device_copy['capabilities'] = self._capabilities.get(device_id, [])
        
        logger.debug(f"Retrieved device details for {device_id}")
        return device_copy

    async def get_all_areas(self) -> list[dict[str, Any]]:
        """
        Get all available areas.
        
        Returns:
            List of area dictionaries
        """
        # Extract unique areas from devices
        areas = {}
        for device in self._devices.values():
            area_id = device.get('area_id')
            area_name = device.get('area_name')
            if area_id and area_id not in areas:
                areas[area_id] = {
                    'area_id': area_id,
                    'name': area_name or area_id
                }
        
        area_list = list(areas.values())
        logger.debug(f"Found {len(area_list)} areas")
        return area_list

    async def get_device_capabilities(self, device_id: str) -> list[dict[str, Any]]:
        """
        Get device capabilities.
        
        Args:
            device_id: Device identifier
            
        Returns:
            List of capability dictionaries
        """
        capabilities = self._capabilities.get(device_id, [])
        logger.debug(f"Retrieved {len(capabilities)} capabilities for {device_id}")
        return capabilities

    def register_device(self, device_id: str, device_data: dict[str, Any]) -> None:
        """
        Register a device in mock storage.
        
        Args:
            device_id: Device identifier
            device_data: Device information dictionary
        """
        self._devices[device_id] = device_data
        logger.debug(f"Registered device {device_id}")

    def register_capabilities(self, device_id: str, capabilities: list[dict[str, Any]]) -> None:
        """
        Register capabilities for a device.
        
        Args:
            device_id: Device identifier
            capabilities: List of capability dictionaries
        """
        self._capabilities[device_id] = capabilities
        logger.debug(f"Registered {len(capabilities)} capabilities for {device_id}")

    def clear_storage(self) -> None:
        """Clear mock storage."""
        self._devices.clear()
        self._capabilities.clear()
        logger.info("Cleared mock Device Intelligence storage")

    async def close(self) -> None:
        """Close the mock client (no-op)."""
        logger.debug("MockDeviceIntelligenceClient closed")

