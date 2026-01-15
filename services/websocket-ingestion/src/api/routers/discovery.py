"""
Discovery router for websocket-ingestion service.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request

from ...utils.logger import logger
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
        # Use connection manager for device discovery (enables message routing)
        # This allows discovery to work even when listen loop is active
        connection_manager = service.connection_manager
        websocket = None
        if connection_manager and connection_manager.client and hasattr(connection_manager.client, 'websocket'):
            websocket = connection_manager.client.websocket
            logger.info("Using connection manager with message routing for device discovery")
        else:
            logger.warning("⚠️  Connection manager not available - device discovery will try HTTP API fallback")

        try:
            logger.info("Calling discover_all()...")
            discovery_result = await service.connection_manager.discovery_service.discover_all(
                websocket=websocket,
                connection_manager=connection_manager,
                store=True
            )
            logger.info(f"Discovery completed: {len(discovery_result.get('devices', []))} devices, {len(discovery_result.get('entities', []))} entities")

            return {
                "success": True,
                "devices_discovered": len(discovery_result.get("devices", [])),
                "entities_discovered": len(discovery_result.get("entities", [])),
                "timestamp": datetime.now(timezone.utc).isoformat()
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

