"""
Data API Router

Endpoints for fetching historical data from Data API.
"""

from fastapi import APIRouter, HTTPException, Query, status
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging

from ..clients.data_api_client import DataAPIClient
from ..config import settings

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/data", tags=["Data"])

# Initialize Data API client (will be shared across requests)
data_api_client = DataAPIClient(base_url=settings.data_api_url)


@router.get("/health")
async def check_data_api_health():
    """Check Data API health status"""
    try:
        health = await data_api_client.health_check()
        return {
            "success": True,
            "data": health,
            "message": "Data API is healthy"
        }
    except Exception as e:
        logger.error(f"Data API health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Data API health check failed: {str(e)}"
        )


@router.get("/events")
async def get_events(
    days: int = Query(default=7, ge=1, le=30, description="Number of days of history to fetch"),
    entity_id: Optional[str] = Query(default=None, description="Filter by entity ID"),
    device_id: Optional[str] = Query(default=None, description="Filter by device ID"),
    event_type: Optional[str] = Query(default=None, description="Filter by event type"),
    limit: int = Query(default=1000, ge=1, le=10000, description="Maximum number of events")
) -> Dict[str, Any]:
    """
    Fetch historical events from Data API.
    
    Returns events as JSON array with DataFrame structure.
    """
    try:
        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        
        logger.info(f"Fetching events: days={days}, entity_id={entity_id}, device_id={device_id}, limit={limit}")
        
        # Fetch events
        df = await data_api_client.fetch_events(
            start_time=start_time,
            end_time=end_time,
            entity_id=entity_id,
            device_id=device_id,
            event_type=event_type,
            limit=limit
        )
        
        # Convert DataFrame to JSON-serializable format
        if df.empty:
            return {
                "success": True,
                "data": {
                    "events": [],
                    "count": 0,
                    "time_range": {
                        "start": start_time.isoformat(),
                        "end": end_time.isoformat(),
                        "days": days
                    }
                },
                "message": "No events found for the specified criteria"
            }
        
        # Convert timestamps to ISO format strings
        events_dict = df.to_dict(orient='records')
        for event in events_dict:
            if 'timestamp' in event and hasattr(event['timestamp'], 'isoformat'):
                event['timestamp'] = event['timestamp'].isoformat()
        
        return {
            "success": True,
            "data": {
                "events": events_dict,
                "count": len(events_dict),
                "time_range": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                    "days": days
                },
                "columns": list(df.columns)
            },
            "message": f"Fetched {len(events_dict)} events successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch events: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch events: {str(e)}"
        )


@router.get("/devices")
async def get_devices(
    manufacturer: Optional[str] = Query(default=None, description="Filter by manufacturer"),
    model: Optional[str] = Query(default=None, description="Filter by model"),
    area_id: Optional[str] = Query(default=None, description="Filter by area/room"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of devices")
) -> Dict[str, Any]:
    """
    Fetch devices from Data API.
    """
    try:
        logger.info(f"Fetching devices: manufacturer={manufacturer}, model={model}, area_id={area_id}, limit={limit}")
        
        devices = await data_api_client.fetch_devices(
            manufacturer=manufacturer,
            model=model,
            area_id=area_id,
            limit=limit
        )
        
        return {
            "success": True,
            "data": {
                "devices": devices,
                "count": len(devices)
            },
            "message": f"Fetched {len(devices)} devices successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch devices: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch devices: {str(e)}"
        )


@router.get("/entities")
async def get_entities(
    device_id: Optional[str] = Query(default=None, description="Filter by device ID"),
    domain: Optional[str] = Query(default=None, description="Filter by domain (light, sensor, etc)"),
    platform: Optional[str] = Query(default=None, description="Filter by platform"),
    area_id: Optional[str] = Query(default=None, description="Filter by area/room"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of entities")
) -> Dict[str, Any]:
    """
    Fetch entities from Data API.
    """
    try:
        logger.info(f"Fetching entities: device_id={device_id}, domain={domain}, platform={platform}, area_id={area_id}, limit={limit}")
        
        entities = await data_api_client.fetch_entities(
            device_id=device_id,
            domain=domain,
            platform=platform,
            area_id=area_id,
            limit=limit
        )
        
        return {
            "success": True,
            "data": {
                "entities": entities,
                "count": len(entities)
            },
            "message": f"Fetched {len(entities)} entities successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch entities: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch entities: {str(e)}"
        )


@router.get("/devices")
async def get_devices(
    manufacturer: Optional[str] = Query(default=None, description="Filter by manufacturer"),
    model: Optional[str] = Query(default=None, description="Filter by model"),
    area_id: Optional[str] = Query(default=None, description="Filter by area ID"),
    limit: int = Query(default=1000, ge=1, le=10000, description="Maximum number of devices")
) -> Dict[str, Any]:
    """
    Get devices from Home Assistant via Data API.
    
    Args:
        manufacturer: Filter devices by manufacturer
        model: Filter devices by model
        area_id: Filter devices by area ID
        limit: Maximum number of devices to return
        
    Returns:
        Dictionary containing devices list and metadata
    """
    try:
        devices = await data_api_client.fetch_devices(
            manufacturer=manufacturer,
            model=model,
            area_id=area_id,
            limit=limit
        )
        
        return {
            "success": True,
            "devices": devices,
            "count": len(devices),
            "filters": {
                "manufacturer": manufacturer,
                "model": model,
                "area_id": area_id,
                "limit": limit
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch devices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch devices: {str(e)}"
        )


@router.on_event("shutdown")
async def shutdown_data_client():
    """Close Data API client on shutdown"""
    await data_api_client.close()
    logger.info("Data API client closed")

