"""
Devices and Entities Endpoints for Admin API
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel, Field

from .influxdb_client import AdminAPIInfluxDBClient
from .device_intelligence_client import get_device_intelligence_client

logger = logging.getLogger(__name__)


# Response Models
class DeviceResponse(BaseModel):
    """Device response model"""
    device_id: str = Field(description="Unique device identifier")
    name: str = Field(description="Device name")
    manufacturer: str = Field(description="Device manufacturer")
    model: str = Field(description="Device model")
    sw_version: Optional[str] = Field(default=None, description="Software/firmware version")
    area_id: Optional[str] = Field(default=None, description="Area/room ID")
    entity_count: int = Field(default=0, description="Number of entities")
    timestamp: str = Field(description="Last update timestamp")


class EntityResponse(BaseModel):
    """Entity response model"""
    entity_id: str = Field(description="Unique entity identifier")
    device_id: Optional[str] = Field(default=None, description="Associated device ID")
    domain: str = Field(description="Entity domain (light, sensor, etc)")
    platform: str = Field(description="Integration platform")
    unique_id: Optional[str] = Field(default=None, description="Unique ID within platform")
    area_id: Optional[str] = Field(default=None, description="Area/room ID")
    disabled: bool = Field(default=False, description="Whether entity is disabled")
    timestamp: str = Field(description="Last update timestamp")


class IntegrationResponse(BaseModel):
    """Integration/Config Entry response model"""
    entry_id: str = Field(description="Config entry ID")
    domain: str = Field(description="Integration domain")
    title: str = Field(description="Integration title")
    state: str = Field(description="Setup state")
    version: int = Field(default=1, description="Config version")
    timestamp: str = Field(description="Last update timestamp")


class DevicesListResponse(BaseModel):
    """Devices list response"""
    devices: List[DeviceResponse]
    count: int
    limit: int


class EntitiesListResponse(BaseModel):
    """Entities list response"""
    entities: List[EntityResponse]
    count: int
    limit: int


class IntegrationsListResponse(BaseModel):
    """Integrations list response"""
    integrations: List[IntegrationResponse]
    count: int


# Create router
router = APIRouter(tags=["Devices & Entities"])


# InfluxDB client (initialized on startup)
influxdb_client = AdminAPIInfluxDBClient()


@router.get("/api/devices", response_model=DevicesListResponse)
async def list_devices(
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of devices to return"),
    manufacturer: Optional[str] = Query(default=None, description="Filter by manufacturer"),
    model: Optional[str] = Query(default=None, description="Filter by model"),
    area_id: Optional[str] = Query(default=None, description="Filter by area/room")
):
    """
    List all discovered devices from Device Intelligence Service
    
    Returns devices with their metadata, optionally filtered by manufacturer, model, or area.
    """
    try:
        device_intelligence_client = get_device_intelligence_client()
        response = await device_intelligence_client.get_devices(
            limit=limit,
            manufacturer=manufacturer,
            model=model,
            area_id=area_id
        )
        devices = [
            DeviceResponse(
                device_id=device.get("device_id", ""),
                name=device.get("name", "Unknown"),
                manufacturer=device.get("manufacturer", "Unknown"),
                model=device.get("model", "Unknown"),
                sw_version=device.get("sw_version"),
                area_id=device.get("area_id"),
                entity_count=device.get("entity_count", 0),
                timestamp=device.get("timestamp", datetime.now().isoformat())
            )
            for device in response.get("devices", [])
        ]
        return DevicesListResponse(
            devices=devices,
            count=response.get("count", len(devices)),
            limit=response.get("limit", limit)
        )
    except Exception as e:
        logger.warning(f"Device Intelligence unavailable, falling back to InfluxDB: {e}")
        filters = {}
        if manufacturer:
            filters["manufacturer"] = manufacturer
        if model:
            filters["model"] = model
        if area_id:
            filters["area_id"] = area_id
        query = _build_devices_query(filters, limit)
        records = await influxdb_client.query(query)
        devices = [
            DeviceResponse(
                device_id=record.get("device_id", ""),
                name=record.get("name", "Unknown"),
                manufacturer=record.get("manufacturer", "Unknown"),
                model=record.get("model", "Unknown"),
                sw_version=record.get("sw_version"),
                area_id=record.get("area_id"),
                entity_count=record.get("entity_count", 0),
                timestamp=record.get("time", datetime.now().isoformat())
            )
            for record in records
        ]
        return DevicesListResponse(
            devices=devices,
            count=len(devices),
            limit=limit
        )


@router.get("/api/devices/{device_id}", response_model=DeviceResponse)
async def get_device(device_id: str):
    """
    Get details for a specific device from Device Intelligence Service
    
    Args:
        device_id: Device identifier
        
    Returns:
        Device details
    """
    try:
        device_intelligence_client = get_device_intelligence_client()
        device_data = await device_intelligence_client.get_device_by_id(device_id)
        if not device_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device {device_id} not found"
            )
        device = DeviceResponse(
            device_id=device_data.get("device_id", device_id),
            name=device_data.get("name", "Unknown"),
            manufacturer=device_data.get("manufacturer", "Unknown"),
            model=device_data.get("model", "Unknown"),
            sw_version=device_data.get("sw_version"),
            area_id=device_data.get("area_id"),
            entity_count=device_data.get("entity_count", 0),
            timestamp=device_data.get("timestamp", datetime.now().isoformat())
        )
        return device
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Device Intelligence unavailable for {device_id}, falling back to InfluxDB: {e}")
        query = _build_devices_query({"device_id": device_id}, limit=1)
        records = await influxdb_client.query(query)
        if not records:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device {device_id} not found"
            )
        record = records[0]
        return DeviceResponse(
            device_id=record.get("device_id", device_id),
            name=record.get("name", "Unknown"),
            manufacturer=record.get("manufacturer", "Unknown"),
            model=record.get("model", "Unknown"),
            sw_version=record.get("sw_version"),
            area_id=record.get("area_id"),
            entity_count=record.get("entity_count", 0),
            timestamp=record.get("time", datetime.now().isoformat())
        )


@router.get("/api/entities", response_model=EntitiesListResponse)
async def list_entities(
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of entities to return"),
    domain: Optional[str] = Query(default=None, description="Filter by domain (light, sensor, etc)"),
    platform: Optional[str] = Query(default=None, description="Filter by platform"),
    device_id: Optional[str] = Query(default=None, description="Filter by device ID")
):
    """
    List all discovered entities from Home Assistant
    
    Returns entities with their configuration, optionally filtered by domain, platform, or device.
    """
    try:
        # Build filters
        filters = {}
        if domain:
            filters["domain"] = domain
        if platform:
            filters["platform"] = platform
        if device_id:
            filters["device_id"] = device_id
        
        # Query entities from InfluxDB
        query = _build_entities_query(filters, limit)
        results = await influxdb_client.query(query)
        
        # Convert results to response models
        entities = []
        for record in results:
            entity = EntityResponse(
                entity_id=record.get("entity_id", ""),
                device_id=record.get("device_id"),
                domain=record.get("domain", "unknown"),
                platform=record.get("platform", "unknown"),
                unique_id=record.get("unique_id"),
                area_id=record.get("area_id"),
                disabled=bool(record.get("disabled", False)),
                timestamp=record.get("time", datetime.now().isoformat())
            )
            entities.append(entity)
        
        return EntitiesListResponse(
            entities=entities,
            count=len(entities),
            limit=limit
        )
        
    except Exception as e:
        logger.error(f"Error listing entities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve entities: {str(e)}"
        )


@router.get("/api/entities/{entity_id}", response_model=EntityResponse)
async def get_entity(entity_id: str):
    """
    Get details for a specific entity
    
    Args:
        entity_id: Entity identifier (e.g., light.living_room)
        
    Returns:
        Entity details
    """
    try:
        # Query specific entity
        query = f'''
            from(bucket: "entities")
                |> range(start: -90d)
                |> filter(fn: (r) => r["_measurement"] == "entities")
                |> filter(fn: (r) => r["entity_id"] == "{entity_id}")
                |> last()
        '''
        
        results = await influxdb_client.query(query)
        
        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity {entity_id} not found"
            )
        
        record = results[0]
        entity = EntityResponse(
            entity_id=record.get("entity_id", entity_id),
            device_id=record.get("device_id"),
            domain=record.get("domain", "unknown"),
            platform=record.get("platform", "unknown"),
            unique_id=record.get("unique_id"),
            area_id=record.get("area_id"),
            disabled=bool(record.get("disabled", False)),
            timestamp=record.get("time", datetime.now().isoformat())
        )
        
        return entity
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting entity {entity_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve entity: {str(e)}"
        )


@router.get("/api/integrations", response_model=IntegrationsListResponse)
async def list_integrations(
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of integrations to return")
):
    """
    List all Home Assistant integrations (config entries)
    
    Returns all discovered integrations with their setup status.
    """
    try:
        # Query config entries from InfluxDB
        query = f'''
            from(bucket: "home_assistant_events")
                |> range(start: -90d)
                |> filter(fn: (r) => r["_measurement"] == "config_entries")
                |> last()
                |> limit(n: {limit})
        '''
        
        results = await influxdb_client.query(query)
        
        # Convert results to response models
        integrations = []
        for record in results:
            integration = IntegrationResponse(
                entry_id=record.get("entry_id", ""),
                domain=record.get("domain", "unknown"),
                title=record.get("title", "Unknown"),
                state=record.get("state", "unknown"),
                version=int(record.get("version", 1)),
                timestamp=record.get("time", datetime.now().isoformat())
            )
            integrations.append(integration)
        
        return IntegrationsListResponse(
            integrations=integrations,
            count=len(integrations)
        )
        
    except Exception as e:
        logger.error(f"Error listing integrations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve integrations: {str(e)}"
        )


# Helper functions
def _build_devices_query(filters: Dict[str, str], limit: int) -> str:
    """Build Flux query for devices with filters"""
    query = f'''
        from(bucket: "devices")
            |> range(start: -90d)
            |> filter(fn: (r) => r["_measurement"] == "devices")
    '''
    
    # Add filters
    if filters.get("manufacturer"):
        query += f'\n    |> filter(fn: (r) => r["manufacturer"] == "{filters["manufacturer"]}")'
    if filters.get("model"):
        query += f'\n    |> filter(fn: (r) => r["model"] == "{filters["model"]}")'
    if filters.get("area_id"):
        query += f'\n    |> filter(fn: (r) => r["area_id"] == "{filters["area_id"]}")'
    if filters.get("device_id"):
        query += f'\n    |> filter(fn: (r) => r["device_id"] == "{filters["device_id"]}")'
    
    query += f'\n    |> last()\n    |> limit(n: {limit})'
    
    return query


def _build_entities_query(filters: Dict[str, str], limit: int) -> str:
    """Build Flux query for entities with filters"""
    query = f'''
        from(bucket: "entities")
            |> range(start: -90d)
            |> filter(fn: (r) => r["_measurement"] == "entities")
    '''
    
    # Add filters
    if filters.get("domain"):
        query += f'\n    |> filter(fn: (r) => r["domain"] == "{filters["domain"]}")'
    if filters.get("platform"):
        query += f'\n    |> filter(fn: (r) => r["platform"] == "{filters["platform"]}")'
    if filters.get("device_id"):
        query += f'\n    |> filter(fn: (r) => r["device_id"] == "{filters["device_id"]}")'
    
    query += f'\n    |> last()\n    |> limit(n: {limit})'
    
    return query

