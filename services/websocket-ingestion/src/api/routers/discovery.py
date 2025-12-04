"""
Discovery router for websocket-ingestion service.
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException, Request

from ...main import logger
from ...api.models import DiscoveryTriggerResponse

router = APIRouter(prefix="/api/v1/discovery", tags=["discovery"])


@router.post("/trigger", response_model=DiscoveryTriggerResponse)
async def trigger_discovery(request: Request):
    """
    Manually trigger device/entity discovery.
    
    Triggers a full discovery of Home Assistant devices and entities.
    """
    service = request.app.state.service
    try:
        if not service.connection_manager or not service.connection_manager.discovery_service:
            raise HTTPException(
                status_code=503,
                detail={
                    "success": False,
                    "error": "Connection manager or discovery service not available"
                }
            )

        logger.info("Manual discovery trigger requested")
        # Device discovery requires WebSocket (HA doesn't have HTTP API for device registry)
        # Entity discovery uses HTTP API (no WebSocket needed)
        websocket = None
        if service.connection_manager.client and hasattr(service.connection_manager.client, 'websocket'):
            websocket = service.connection_manager.client.websocket
            logger.info("Using WebSocket connection for device discovery")
        else:
            logger.warning("⚠️  WebSocket not available - device discovery will be skipped (entities will still be discovered)")

        try:
            logger.info("Calling discover_all()...")
            discovery_result = await service.connection_manager.discovery_service.discover_all(
                websocket=websocket,
                store=True
            )
            logger.info(f"Discovery completed: {len(discovery_result.get('devices', []))} devices, {len(discovery_result.get('entities', []))} entities")

            return {
                "success": True,
                "devices_discovered": len(discovery_result.get("devices", [])),
                "entities_discovered": len(discovery_result.get("entities", [])),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error in discover_all(): {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering discovery: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": str(e)
            }
        )

