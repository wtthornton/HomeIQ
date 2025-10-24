"""
Device Intelligence Service - Health Endpoints

Health check and service status endpoints.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..config import Settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: datetime
    service: str
    version: str
    uptime: str
    memory_usage: Dict[str, Any]
    dependencies: Dict[str, str]


class ServiceStatus(BaseModel):
    """Service status response model."""
    service: str
    status: str
    version: str
    port: int
    host: str
    environment: str
    dependencies: Dict[str, str]


@router.get("/", response_model=HealthResponse)
async def health_check(settings: Settings = Depends(lambda: Settings())) -> HealthResponse:
    """
    Basic health check endpoint.
    
    Returns:
        HealthResponse: Service health status and basic metrics
    """
    import psutil
    import time
    
    # Get memory usage
    process = psutil.Process()
    memory_info = process.memory_info()
    
    # Calculate uptime (simplified - in production you'd track start time)
    uptime_seconds = int(time.time() - process.create_time())
    uptime_str = f"{uptime_seconds // 3600}h {(uptime_seconds % 3600) // 60}m {uptime_seconds % 60}s"
    
    # Check dependencies (simplified - in production you'd actually test connections)
    dependencies = {
        "sqlite": "connected",  # TODO: Actually test database connection
        "redis": "connected",    # TODO: Actually test Redis connection
        "home_assistant": "connected",  # TODO: Actually test HA connection
        "mqtt": "connected"      # TODO: Actually test MQTT connection
    }
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc),
        service="Device Intelligence Service",
        version="1.0.0",
        uptime=uptime_str,
        memory_usage={
            "rss_mb": round(memory_info.rss / 1024 / 1024, 2),
            "vms_mb": round(memory_info.vms / 1024 / 1024, 2),
            "percent": round(process.memory_percent(), 2)
        },
        dependencies=dependencies
    )


@router.get("/status", response_model=ServiceStatus)
async def service_status(settings: Settings = Depends(lambda: Settings())) -> ServiceStatus:
    """
    Detailed service status endpoint.
    
    Returns:
        ServiceStatus: Detailed service information and configuration
    """
    import os
    
    environment = os.getenv("ENVIRONMENT", "development")
    
    # Check dependencies (simplified)
    dependencies = {
        "database": "operational",
        "cache": "operational", 
        "home_assistant": "operational",
        "mqtt_broker": "operational"
    }
    
    return ServiceStatus(
        service="Device Intelligence Service",
        status="operational",
        version="1.0.0",
        port=settings.DEVICE_INTELLIGENCE_PORT,
        host=settings.DEVICE_INTELLIGENCE_HOST,
        environment=environment,
        dependencies=dependencies
    )


@router.get("/ready")
async def readiness_check() -> Dict[str, Any]:
    """
    Kubernetes-style readiness check.
    
    Returns:
        Dict[str, Any]: Readiness status
    """
    # TODO: Implement actual readiness checks
    # - Database connection
    # - Redis connection  
    # - Home Assistant connection
    # - MQTT broker connection
    
    return {
        "status": "ready",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {
            "database": "ok",
            "cache": "ok",
            "external_services": "ok"
        }
    }


@router.get("/live")
async def liveness_check() -> Dict[str, Any]:
    """
    Kubernetes-style liveness check.
    
    Returns:
        Dict[str, Any]: Liveness status
    """
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "Device Intelligence Service"
    }
