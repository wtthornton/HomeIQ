"""
Device Intelligence Service - Discovery API Endpoints

API endpoints for device discovery management and status.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..config import Settings
from ..core.discovery_service import DiscoveryService, DiscoveryStatus, UnifiedDevice

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/discovery", tags=["Discovery"])

# Global discovery service instance
_discovery_service: Optional[DiscoveryService] = None


class DiscoveryStatusResponse(BaseModel):
    """Discovery service status response."""
    service_running: bool
    ha_connected: bool
    mqtt_connected: bool
    last_discovery: Optional[str]
    devices_count: int
    areas_count: int
    errors: List[str]


class DiscoverySourcesResponse(BaseModel):
    """Available discovery sources response."""
    sources: List[Dict[str, Any]]


class DeviceSummaryResponse(BaseModel):
    """Device discovery summary response."""
    total_devices: int
    devices_by_integration: Dict[str, int]
    devices_by_area: Dict[str, int]
    devices_with_capabilities: int
    last_updated: str


class DeviceResponse(BaseModel):
    """Individual device response."""
    id: str
    name: str
    manufacturer: str
    model: str
    area_id: Optional[str]
    area_name: Optional[str]
    integration: str
    capabilities: List[Dict[str, Any]]
    entities: List[Dict[str, Any]]
    health_score: Optional[int]
    last_seen: Optional[str]
    created_at: str
    updated_at: str


async def get_discovery_service() -> DiscoveryService:
    """Get the global discovery service instance."""
    global _discovery_service
    
    if _discovery_service is None:
        settings = Settings()
        _discovery_service = DiscoveryService(settings)
        
        # Start the service
        if not await _discovery_service.start():
            raise HTTPException(status_code=500, detail="Failed to start discovery service")
    
    return _discovery_service


async def shutdown_discovery_service():
    """Stop the global discovery service if it is running."""
    global _discovery_service
    
    if _discovery_service:
        try:
            await _discovery_service.stop()
        finally:
            _discovery_service = None


@router.get("/status", response_model=DiscoveryStatusResponse)
async def get_discovery_status(
    discovery_service: DiscoveryService = Depends(get_discovery_service)
) -> DiscoveryStatusResponse:
    """
    Get discovery service status.
    
    Returns:
        DiscoveryStatusResponse: Current status of the discovery service
    """
    try:
        status = discovery_service.get_status()
        
        return DiscoveryStatusResponse(
            service_running=status.service_running,
            ha_connected=status.ha_connected,
            mqtt_connected=status.mqtt_connected,
            last_discovery=status.last_discovery.isoformat() if status.last_discovery else None,
            devices_count=status.devices_count,
            areas_count=status.areas_count,
            errors=status.errors
        )
        
    except Exception as e:
        logger.error(f"❌ Error getting discovery status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting discovery status: {str(e)}")


@router.get("/sources", response_model=DiscoverySourcesResponse)
async def get_discovery_sources(
    discovery_service: DiscoveryService = Depends(get_discovery_service)
) -> DiscoverySourcesResponse:
    """
    Get available discovery sources and their status.
    
    Returns:
        DiscoverySourcesResponse: Available discovery sources
    """
    try:
        status = discovery_service.get_status()
        
        sources = [
            {
                "name": "Home Assistant",
                "type": "websocket",
                "connected": status.ha_connected,
                "description": "Device, entity, and area registry discovery via WebSocket API"
            },
            {
                "name": "Zigbee2MQTT",
                "type": "mqtt",
                "connected": status.mqtt_connected,
                "description": "Device capabilities and network topology via MQTT bridge"
            }
        ]
        
        return DiscoverySourcesResponse(sources=sources)
        
    except Exception as e:
        logger.error(f"❌ Error getting discovery sources: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting discovery sources: {str(e)}")


@router.post("/refresh")
async def refresh_discovery(
    discovery_service: DiscoveryService = Depends(get_discovery_service)
) -> Dict[str, Any]:
    """
    Force a complete discovery refresh.
    
    Returns:
        Dict[str, Any]: Refresh operation result
    """
    try:
        logger.info("🔄 Manual discovery refresh requested")
        
        success = await discovery_service.force_refresh()
        
        if success:
            status = discovery_service.get_status()
            return {
                "status": "success",
                "message": "Discovery refresh completed",
                "devices_discovered": status.devices_count,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            return {
                "status": "error",
                "message": "Discovery refresh failed",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
    except Exception as e:
        logger.error(f"❌ Error during discovery refresh: {e}")
        raise HTTPException(status_code=500, detail=f"Error during discovery refresh: {str(e)}")


@router.get("/devices", response_model=DeviceSummaryResponse)
async def get_devices_summary(
    discovery_service: DiscoveryService = Depends(get_discovery_service)
) -> DeviceSummaryResponse:
    """
    Get summary of discovered devices.
    
    Returns:
        DeviceSummaryResponse: Device discovery summary
    """
    try:
        devices = discovery_service.get_devices()
        areas = discovery_service.get_areas()
        
        # Count devices by integration
        devices_by_integration = {}
        for device in devices:
            integration = device.integration if isinstance(device.integration, str) and device.integration.strip() else "Unknown"
            devices_by_integration[integration] = devices_by_integration.get(integration, 0) + 1
        
        # Count devices by area
        devices_by_area = {}
        for device in devices:
            area_name = device.area_name or "Unknown"
            devices_by_area[area_name] = devices_by_area.get(area_name, 0) + 1
        
        # Count devices with capabilities
        devices_with_capabilities = len([d for d in devices if d.capabilities])
        
        return DeviceSummaryResponse(
            total_devices=len(devices),
            devices_by_integration=devices_by_integration,
            devices_by_area=devices_by_area,
            devices_with_capabilities=devices_with_capabilities,
            last_updated=datetime.now(timezone.utc).isoformat()
        )
        
    except Exception as e:
        logger.error(f"❌ Error getting devices summary: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting devices summary: {str(e)}")


@router.get("/devices/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: str,
    discovery_service: DiscoveryService = Depends(get_discovery_service)
) -> DeviceResponse:
    """
    Get specific device by ID.
    
    Args:
        device_id: Device identifier
        
    Returns:
        DeviceResponse: Device information
        
    Raises:
        HTTPException: If device not found
    """
    try:
        device = discovery_service.get_device(device_id)
        
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        
        return DeviceResponse(
            id=device.id,
            name=device.name,
            manufacturer=device.manufacturer,
            model=device.model,
            area_id=device.area_id,
            area_name=device.area_name,
            integration=device.integration,
            capabilities=device.capabilities,
            entities=device.entities,
            health_score=device.health_score,
            last_seen=device.last_seen.isoformat() if device.last_seen else None,
            created_at=device.created_at.isoformat(),
            updated_at=device.updated_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting device: {str(e)}")


@router.get("/devices", response_model=List[DeviceResponse])
async def get_all_devices(
    area_id: Optional[str] = None,
    integration: Optional[str] = None,
    limit: int = 100,
    discovery_service: DiscoveryService = Depends(get_discovery_service)
) -> List[DeviceResponse]:
    """
    Get all discovered devices with optional filtering.
    
    Args:
        area_id: Filter by area ID
        integration: Filter by integration type
        limit: Maximum number of devices to return
        
    Returns:
        List[DeviceResponse]: List of devices
    """
    try:
        devices = discovery_service.get_devices()
        
        # Apply filters
        if area_id:
            devices = [d for d in devices if d.area_id == area_id]
        
        if integration:
            devices = [d for d in devices if d.integration == integration]
        
        # Apply limit
        devices = devices[:limit]
        
        # Convert to response format
        device_responses = []
        for device in devices:
            device_responses.append(DeviceResponse(
                id=device.id,
                name=device.name,
                manufacturer=device.manufacturer,
                model=device.model,
                area_id=device.area_id,
                area_name=device.area_name,
                integration=device.integration,
                capabilities=device.capabilities,
                entities=device.entities,
                health_score=device.health_score,
                last_seen=device.last_seen.isoformat() if device.last_seen else None,
                created_at=device.created_at.isoformat(),
                updated_at=device.updated_at.isoformat()
            ))
        
        return device_responses
        
    except Exception as e:
        logger.error(f"❌ Error getting devices: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting devices: {str(e)}")


@router.get("/areas")
async def get_areas(
    discovery_service: DiscoveryService = Depends(get_discovery_service)
) -> List[Dict[str, Any]]:
    """
    Get all discovered areas.
    
    Returns:
        List[Dict[str, Any]]: List of areas
    """
    try:
        areas = discovery_service.get_areas()
        
        return [
            {
                "area_id": area.area_id,
                "name": area.name,
                "normalized_name": area.normalized_name,
                "aliases": area.aliases,
                "created_at": area.created_at.isoformat(),
                "updated_at": area.updated_at.isoformat()
            }
            for area in areas
        ]
        
    except Exception as e:
        logger.error(f"❌ Error getting areas: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting areas: {str(e)}")


@router.get("/groups")
async def get_zigbee_groups(
    discovery_service: DiscoveryService = Depends(get_discovery_service)
) -> List[Dict[str, Any]]:
    """
    Get all discovered Zigbee groups.
    
    Returns:
        List[Dict[str, Any]]: List of Zigbee groups
    """
    try:
        groups = discovery_service.get_zigbee_groups()
        
        return [
            {
                "id": group.id,
                "friendly_name": group.friendly_name,
                "members": group.members,
                "scenes": group.scenes
            }
            for group in groups
        ]
        
    except Exception as e:
        logger.error(f"❌ Error getting Zigbee groups: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting Zigbee groups: {str(e)}")
