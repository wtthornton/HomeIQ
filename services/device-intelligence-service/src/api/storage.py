"""
Device Intelligence Service - Simple Storage API Endpoints

Simplified storage API endpoints for device data management.
No complex repository pattern - just simple database operations.
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.cache import DeviceCache
from ..core.database import get_db_session
from ..services.device_service import DeviceService

logger = logging.getLogger(__name__)
router = APIRouter()

# Response Models
class DeviceResponse(BaseModel):
    device_id: str
    name: str
    manufacturer: str | None
    model: str | None
    sw_version: str | None
    area_id: str | None
    entity_count: int
    timestamp: str

class DeviceCapabilityResponse(BaseModel):
    device_id: str
    capability_name: str
    capability_type: str
    properties: dict[str, Any]
    exposed: bool
    configured: bool
    source: str
    last_updated: datetime

class DeviceHealthResponse(BaseModel):
    device_id: str
    metric_name: str
    metric_value: float
    metric_unit: str | None
    metadata_json: dict[str, Any] | None
    timestamp: datetime

class DeviceStatsResponse(BaseModel):
    total_devices: int
    devices_by_integration: dict[str, int]
    devices_by_area: dict[str, int]
    average_health_score: float
    total_capabilities: int

class DevicesListResponse(BaseModel):
    """Devices list response - compatible with data-api format"""
    devices: list[DeviceResponse]
    count: int
    limit: int

# Dependencies
def get_device_cache() -> DeviceCache:
    """Get device cache instance."""
    return DeviceCache()

def get_device_service(session: AsyncSession = Depends(get_db_session)) -> DeviceService:
    """Get device service instance."""
    return DeviceService(session)

# Device Endpoints
@router.get("/devices", response_model=DevicesListResponse, summary="Get all devices")
async def get_devices(
    limit: int = 100,
    device_service: DeviceService = Depends(get_device_service),
):
    """Get all devices with optional limit - compatible with data-api format."""
    try:
        devices = await device_service.get_all_devices(limit)
        device_responses = [
            DeviceResponse(
                device_id=device.id,
                name=device.name,
                manufacturer=device.manufacturer,
                model=device.model,
                sw_version=None,  # Not available in Device Intelligence Service yet
                area_id=device.area_id,
                entity_count=0,  # Not available in Device Intelligence Service yet
                timestamp=device.updated_at.isoformat() if device.updated_at else datetime.now().isoformat(),
            )
            for device in devices
        ]

        return DevicesListResponse(
            devices=device_responses,
            count=len(device_responses),
            limit=limit,
        )
    except Exception as e:
        logger.exception(f"Error retrieving devices: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/devices/{device_id}/capabilities", response_model=list[DeviceCapabilityResponse], summary="Get device capabilities")
async def get_device_capabilities(
    device_id: str,
    device_service: DeviceService = Depends(get_device_service),
):
    """Get capabilities for a specific device."""
    try:
        capabilities = await device_service.get_device_capabilities(device_id)
        return [
            DeviceCapabilityResponse(
                device_id=cap.device_id,
                capability_name=cap.capability_name,
                capability_type=cap.capability_type,
                properties=cap.properties,
                exposed=cap.exposed,
                configured=cap.configured,
                source=cap.source,
                last_updated=cap.last_updated,
            )
            for cap in capabilities
        ]
    except Exception as e:
        logger.exception(f"Error retrieving capabilities for device {device_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/devices/{device_id}/health", response_model=list[DeviceHealthResponse], summary="Get device health metrics")
async def get_device_health(
    device_id: str,
    limit: int = 100,
    device_service: DeviceService = Depends(get_device_service),
):
    """Get health metrics for a specific device."""
    try:
        metrics = await device_service.get_device_health_metrics(device_id, limit)
        return [
            DeviceHealthResponse(
                device_id=metric.device_id,
                metric_name=metric.metric_name,
                metric_value=metric.metric_value,
                metric_unit=metric.metric_unit,
                metadata_json=metric.metadata_json,
                timestamp=metric.timestamp,
            )
            for metric in metrics
        ]
    except Exception as e:
        logger.exception(f"Error retrieving health metrics for device {device_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/devices/{device_id}", response_model=DeviceResponse, summary="Get device by ID")
async def get_device(
    device_id: str,
    device_service: DeviceService = Depends(get_device_service),
):
    """Get specific device by ID - compatible with data-api format."""
    try:
        device = await device_service.get_device_by_id(device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")

        return DeviceResponse(
            device_id=device.id,
            name=device.name,
            manufacturer=device.manufacturer,
            model=device.model,
            sw_version=None,  # Not available in Device Intelligence Service yet
            area_id=device.area_id,
            entity_count=0,  # Not available in Device Intelligence Service yet
            timestamp=device.updated_at.isoformat() if device.updated_at else datetime.now().isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving device {device_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/devices/area/{area_id}", response_model=list[DeviceResponse], summary="Get devices by area")
async def get_devices_by_area(
    area_id: str,
    device_service: DeviceService = Depends(get_device_service),
):
    """Get all devices in a specific area - compatible with data-api format."""
    try:
        devices = await device_service.get_devices_by_area(area_id)
        return [
            DeviceResponse(
                device_id=device.id,
                name=device.name,
                manufacturer=device.manufacturer,
                model=device.model,
                sw_version=None,  # Not available in Device Intelligence Service yet
                area_id=device.area_id,
                entity_count=0,  # Not available in Device Intelligence Service yet
                timestamp=device.updated_at.isoformat() if device.updated_at else datetime.now().isoformat(),
            )
            for device in devices
        ]
    except Exception as e:
        logger.exception(f"Error retrieving devices for area {area_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/devices/integration/{integration}", response_model=list[DeviceResponse], summary="Get devices by integration")
async def get_devices_by_integration(
    integration: str,
    device_service: DeviceService = Depends(get_device_service),
):
    """Get all devices for a specific integration - compatible with data-api format."""
    try:
        devices = await device_service.get_devices_by_integration(integration)
        return [
            DeviceResponse(
                device_id=device.id,
                name=device.name,
                manufacturer=device.manufacturer,
                model=device.model,
                sw_version=None,  # Not available in Device Intelligence Service yet
                area_id=device.area_id,
                entity_count=0,  # Not available in Device Intelligence Service yet
                timestamp=device.updated_at.isoformat() if device.updated_at else datetime.now().isoformat(),
            )
            for device in devices
        ]
    except Exception as e:
        logger.exception(f"Error retrieving devices for integration {integration}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Statistics Endpoints
@router.get("/stats", response_model=DeviceStatsResponse, summary="Get device statistics")
async def get_device_stats(
    device_service: DeviceService = Depends(get_device_service),
):
    """Get device statistics and analytics."""
    try:
        stats = await device_service.get_device_stats()
        return DeviceStatsResponse(**stats)
    except Exception as e:
        logger.exception(f"Error retrieving device statistics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Cache Management Endpoints
@router.post("/cache/invalidate/{device_id}", summary="Invalidate device cache")
async def invalidate_device_cache(
    device_id: str,
    cache: DeviceCache = Depends(get_device_cache),
):
    """Invalidate cache for a specific device."""
    await cache.invalidate_device(device_id)
    return {"message": f"Cache invalidated for device {device_id}"}

@router.post("/cache/invalidate-all", summary="Invalidate all caches")
async def invalidate_all_caches(
    cache: DeviceCache = Depends(get_device_cache),
):
    """Invalidate all device caches."""
    await cache.invalidate_all_device_cache()
    return {"message": "All caches invalidated"}
