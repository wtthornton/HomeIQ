"""
Device Mappings API Router

API endpoints for device mapping library (Epic AI-24).
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..device_mappings import get_registry, reload_registry
from ..device_mappings.cache import clear_cache, get_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/device-mappings", tags=["Device Mappings"])


class DeviceData(BaseModel):
    """Device data model for device mapping endpoints."""
    device_id: str
    manufacturer: str | None = None
    model: str | None = None
    name: str | None = None
    area_id: str | None = None
    integration: str | None = None
    # Allow additional fields
    class Config:
        extra = "allow"


@router.post("/reload")
async def reload_device_mappings() -> dict[str, Any]:
    """
    Reload device mapping registry.
    
    This endpoint clears the registry cache and re-discovers all handlers.
    Useful after updating handler configurations.
    
    Also clears the device mapping cache to ensure fresh data.
    
    Returns:
        Dictionary with reload status and handler count
    """
    try:
        # Clear cache before reloading
        clear_cache()
        
        registry = reload_registry()
        handlers = registry.get_all_handlers()
        
        logger.info(f"✅ Device mapping registry reloaded: {len(handlers)} handlers, cache cleared")
        
        return {
            "status": "success",
            "message": "Device mapping registry reloaded successfully",
            "handler_count": len(handlers),
            "handlers": list(handlers.keys()),
            "cache_cleared": True
        }
    except Exception as e:
        logger.error(f"❌ Error reloading device mappings: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reload device mappings: {str(e)}"
        )


@router.get("/status")
async def get_device_mappings_status() -> dict[str, Any]:
    """
    Get device mapping registry status.
    
    Returns:
        Dictionary with registry status and handler information
    """
    try:
        registry = get_registry()
        handlers = registry.get_all_handlers()
        cache = get_cache()
        
        return {
            "status": "operational",
            "handler_count": len(handlers),
            "handlers": list(handlers.keys()),
            "cache_size": cache.size()
        }
    except Exception as e:
        logger.error(f"❌ Error getting device mappings status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get device mappings status: {str(e)}"
        )


@router.post("/{device_id}/type")
async def get_device_type(device_id: str, device_data: DeviceData) -> dict[str, Any]:
    """
    Get device type for a specific device.
    
    Args:
        device_id: Device ID (must match device_data.device_id)
        device_data: Device data dictionary
        
    Returns:
        Dictionary with device type information
    """
    if device_data.device_id != device_id:
        raise HTTPException(
            status_code=400,
            detail="Device ID in path must match device_id in body"
        )
    
    cache = get_cache()
    cache_key = f"device_mapping_{device_id}_type"
    
    # Check cache
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Cache hit for device type: {device_id}")
        return cached_result
    
    try:
        registry = get_registry()
        device_dict = device_data.model_dump(exclude_none=True)
        
        # Find handler for this device
        handler = registry.find_handler(device_dict)
        
        if handler is None:
            # No handler found - return default type
            result = {
                "device_id": device_id,
                "type": "individual",
                "handler": None,
                "message": "No specific handler found for this device"
            }
        else:
            # Get device type from handler
            device_type = handler.identify_type(device_dict, [])
            result = {
                "device_id": device_id,
                "type": device_type.value if device_type else "individual",
                "handler": handler.__class__.__name__,
                "handler_name": registry.get_handler_name(handler)
            }
        
        # Cache the result
        cache.set(cache_key, result)
        
        return result
    except Exception as e:
        logger.error(f"❌ Error getting device type for {device_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get device type: {str(e)}"
        )


@router.post("/{device_id}/relationships")
async def get_device_relationships(
    device_id: str,
    device_data: DeviceData,
    all_devices: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """
    Get device relationships for a specific device.
    
    Args:
        device_id: Device ID (must match device_data.device_id)
        device_data: Device data dictionary
        all_devices: Optional list of all devices for relationship discovery
        
    Returns:
        Dictionary with device relationships
    """
    if device_data.device_id != device_id:
        raise HTTPException(
            status_code=400,
            detail="Device ID in path must match device_id in body"
        )
    
    cache = get_cache()
    cache_key = f"device_mapping_{device_id}_relationships"
    
    # Check cache
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Cache hit for device relationships: {device_id}")
        return cached_result
    
    try:
        registry = get_registry()
        device_dict = device_data.model_dump(exclude_none=True)
        
        # Find handler for this device
        handler = registry.find_handler(device_dict)
        
        if handler is None:
            # No handler found - return empty relationships
            result = {
                "device_id": device_id,
                "relationships": [],
                "handler": None,
                "message": "No specific handler found for this device"
            }
        else:
            # Get relationships from handler
            all_devices_list = all_devices or []
            relationships = handler.get_relationships(device_dict, all_devices_list)
            result = {
                "device_id": device_id,
                "relationships": relationships,
                "handler": handler.__class__.__name__,
                "handler_name": registry.get_handler_name(handler)
            }
        
        # Cache the result
        cache.set(cache_key, result)
        
        return result
    except Exception as e:
        logger.error(f"❌ Error getting device relationships for {device_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get device relationships: {str(e)}"
        )


@router.post("/{device_id}/context")
async def get_device_context(
    device_id: str,
    device_data: DeviceData,
    entities: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """
    Get enriched context for a specific device.
    
    Args:
        device_id: Device ID (must match device_data.device_id)
        device_data: Device data dictionary
        entities: Optional list of entities associated with the device
        
    Returns:
        Dictionary with enriched device context
    """
    if device_data.device_id != device_id:
        raise HTTPException(
            status_code=400,
            detail="Device ID in path must match device_id in body"
        )
    
    cache = get_cache()
    cache_key = f"device_mapping_{device_id}_context"
    
    # Check cache
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        logger.debug(f"Cache hit for device context: {device_id}")
        return cached_result
    
    try:
        registry = get_registry()
        device_dict = device_data.model_dump(exclude_none=True)
        
        # Find handler for this device
        handler = registry.find_handler(device_dict)
        
        if handler is None:
            # No handler found - return basic context
            result = {
                "device_id": device_id,
                "context": f"{device_dict.get('name', device_id)}",
                "handler": None,
                "message": "No specific handler found for this device"
            }
        else:
            # Get enriched context from handler
            entities_list = entities or []
            context = handler.enrich_context(device_dict, entities_list)
            result = {
                "device_id": device_id,
                "context": context,
                "handler": handler.__class__.__name__,
                "handler_name": registry.get_handler_name(handler)
            }
        
        # Cache the result
        cache.set(cache_key, result)
        
        return result
    except Exception as e:
        logger.error(f"❌ Error getting device context for {device_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get device context: {str(e)}"
        )

