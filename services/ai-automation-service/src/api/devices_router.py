"""
Devices Router - Device listing endpoints
"""

from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["devices"])

# Will be set by main.py
_device_intelligence_client = None

def set_device_intelligence_client(client):
    """Set the device intelligence client from main.py"""
    global _device_intelligence_client
    _device_intelligence_client = client

@router.get("/devices")
async def get_devices():
    """Get devices from Device Intelligence Service"""
    try:
        devices = await _device_intelligence_client.get_devices(limit=1000)
        return {
            "success": True,
            "devices": devices,
            "count": len(devices)
        }
    except Exception as e:
        logger.error(f"Failed to fetch devices from Device Intelligence Service: {e}")
        return {
            "success": False,
            "devices": [],
            "count": 0,
            "error": str(e)
        }

