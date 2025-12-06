"""
Base Device Handler Interface

All device handlers must implement this abstract base class.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class DeviceType(Enum):
    """Device type enumeration."""
    MASTER = "master"  # Master entity (e.g., WLED master)
    SEGMENT = "segment"  # Segment entity (e.g., WLED segment)
    GROUP = "group"  # Group entity (e.g., Hue Room/Zone)
    INDIVIDUAL = "individual"  # Individual device


class DeviceHandler(ABC):
    """
    Abstract base class for device handlers.
    
    All device handlers must implement these methods to provide
    device-specific intelligence to the AI agent.
    """
    
    @abstractmethod
    def can_handle(self, device: dict[str, Any]) -> bool:
        """
        Check if this handler can process the given device.
        
        Args:
            device: Device dictionary from Device Registry
            
        Returns:
            True if this handler can process the device, False otherwise
        """
        pass
    
    @abstractmethod
    def identify_type(self, device: dict[str, Any], entity: dict[str, Any]) -> DeviceType:
        """
        Identify the device type (master, segment, group, individual).
        
        Args:
            device: Device dictionary from Device Registry
            entity: Entity dictionary from Entity Registry or States
            
        Returns:
            DeviceType enum value
        """
        pass
    
    @abstractmethod
    def get_relationships(self, device: dict[str, Any], entities: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Get device relationships (e.g., segments to master, lights to room).
        
        Args:
            device: Device dictionary from Device Registry
            entities: List of related entities
            
        Returns:
            Dictionary with relationship information
        """
        pass
    
    @abstractmethod
    def enrich_context(self, device: dict[str, Any], entity: dict[str, Any]) -> dict[str, Any]:
        """
        Add device-specific context for AI agent.
        
        Args:
            device: Device dictionary from Device Registry
            entity: Entity dictionary from Entity Registry or States
            
        Returns:
            Dictionary with enriched context information
        """
        pass

