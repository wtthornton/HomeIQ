"""
Zigbee2MQTT Bridge Management API Endpoints

Provides REST API endpoints for bridge health monitoring, recovery, and management.
Implements Story 31.3: Bridge Health Monitoring & Auto-Recovery

Context7 Best Practices Applied:
- FastAPI async endpoints with proper error handling
- Pydantic models for request/response validation
- Structured logging with correlation IDs
- Proper HTTP status codes and error messages
"""
import logging
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException

from .schemas import (
    BridgeHealthResponse,
    RecoveryAttemptResponse,
    RecoveryRequest,
    RecoveryResponse,
)
from .zigbee_bridge_manager import (
    BridgeState,
    ZigbeeBridgeManager,
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/zigbee2mqtt", tags=["Zigbee2MQTT Bridge"])

# Global bridge manager instance
bridge_manager = ZigbeeBridgeManager()


@router.get("/bridge/status", response_model=BridgeHealthResponse)
async def get_bridge_status():
    """
    Get comprehensive Zigbee2MQTT bridge health status
    
    Returns detailed bridge metrics, health score, and recommendations.
    """
    try:
        health_status = await bridge_manager.get_bridge_health_status()

        return BridgeHealthResponse(
            bridge_state=health_status.bridge_state.value,
            is_connected=health_status.is_connected,
            health_score=health_status.health_score,
            device_count=health_status.metrics.device_count,
            response_time_ms=health_status.metrics.response_time_ms,
            signal_strength_avg=health_status.metrics.signal_strength_avg,
            network_health_score=health_status.metrics.network_health_score,
            consecutive_failures=health_status.consecutive_failures,
            recommendations=health_status.recommendations,
            last_check=health_status.last_check,
            recovery_attempts=[
                RecoveryAttemptResponse(
                    timestamp=attempt.timestamp,
                    action=attempt.action.value,
                    success=attempt.success,
                    error_message=attempt.error_message,
                    duration_seconds=attempt.duration_seconds
                ) for attempt in health_status.recovery_attempts
            ]
        )

    except Exception as e:
        logger.error(f"Failed to get bridge status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get bridge status: {str(e)}")


@router.post("/bridge/recovery", response_model=RecoveryResponse)
async def attempt_bridge_recovery(request: RecoveryRequest):
    """
    Attempt to recover Zigbee2MQTT bridge connectivity
    
    Executes recovery actions based on current bridge status.
    """
    try:
        success, message = await bridge_manager.attempt_bridge_recovery(force=request.force)

        return RecoveryResponse(
            success=success,
            message=message,
            timestamp=datetime.now()
        )

    except Exception as e:
        logger.error(f"Bridge recovery failed: {e}")
        raise HTTPException(status_code=500, detail=f"Recovery failed: {str(e)}")


@router.get("/bridge/logs")
async def get_bridge_logs():
    """
    Get Zigbee2MQTT bridge logs from Home Assistant
    
    Returns recent bridge logs for troubleshooting.
    """
    try:
        # This would integrate with HA's log API
        # For now, return a placeholder response
        return {
            "logs": [
                "Bridge log retrieval not yet implemented",
                "Will integrate with HA log API in future update"
            ],
            "timestamp": datetime.now()
        }

    except Exception as e:
        logger.error(f"Failed to get bridge logs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get bridge logs: {str(e)}")


@router.post("/bridge/monitoring/start")
async def start_bridge_monitoring(background_tasks: BackgroundTasks):
    """
    Start continuous bridge health monitoring
    
    Begins background monitoring with auto-recovery capabilities.
    """
    try:
        if bridge_manager.monitoring_active:
            return {"message": "Bridge monitoring already active", "status": "active"}

        # Start monitoring in background
        background_tasks.add_task(bridge_manager.start_monitoring)

        return {
            "message": "Bridge monitoring started",
            "status": "started",
            "monitoring_interval": bridge_manager.monitoring_interval
        }

    except Exception as e:
        logger.error(f"Failed to start bridge monitoring: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start monitoring: {str(e)}")


@router.post("/bridge/monitoring/stop")
async def stop_bridge_monitoring():
    """
    Stop continuous bridge health monitoring
    """
    try:
        await bridge_manager.stop_monitoring()

        return {
            "message": "Bridge monitoring stopped",
            "status": "stopped"
        }

    except Exception as e:
        logger.error(f"Failed to stop bridge monitoring: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop monitoring: {str(e)}")


@router.get("/bridge/recovery/history")
async def get_recovery_history():
    """
    Get recovery attempt history
    
    Returns list of recent recovery attempts with results.
    """
    try:
        history = bridge_manager.get_recovery_history()

        return {
            "recovery_attempts": [
                {
                    "timestamp": attempt.timestamp,
                    "action": attempt.action.value,
                    "success": attempt.success,
                    "error_message": attempt.error_message,
                    "duration_seconds": attempt.duration_seconds
                } for attempt in history
            ],
            "total_attempts": len(history),
            "successful_attempts": sum(1 for attempt in history if attempt.success),
            "failed_attempts": sum(1 for attempt in history if not attempt.success)
        }

    except Exception as e:
        logger.error(f"Failed to get recovery history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get recovery history: {str(e)}")


@router.delete("/bridge/recovery/history")
async def clear_recovery_history():
    """
    Clear recovery attempt history
    
    Removes all recovery attempt records.
    """
    try:
        bridge_manager.clear_recovery_history()

        return {
            "message": "Recovery history cleared",
            "timestamp": datetime.now()
        }

    except Exception as e:
        logger.error(f"Failed to clear recovery history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear recovery history: {str(e)}")


@router.get("/bridge/metrics")
async def get_bridge_metrics():
    """
    Get detailed bridge performance metrics
    
    Returns comprehensive metrics for network analysis.
    """
    try:
        health_status = await bridge_manager.get_bridge_health_status()
        metrics = health_status.metrics

        return {
            "response_time_ms": metrics.response_time_ms,
            "device_count": metrics.device_count,
            "signal_strength_avg": metrics.signal_strength_avg,
            "network_health_score": metrics.network_health_score,
            "last_seen_devices": metrics.last_seen_devices,
            "coordinator_uptime_hours": metrics.coordinator_uptime_hours,
            "health_score": health_status.health_score,
            "bridge_state": health_status.bridge_state.value,
            "last_check": health_status.last_check
        }

    except Exception as e:
        logger.error(f"Failed to get bridge metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get bridge metrics: {str(e)}")


@router.post("/bridge/restart")
async def restart_bridge():
    """
    Restart Zigbee2MQTT bridge (alias for recovery)
    
    Convenience endpoint for bridge restart.
    """
    try:
        success, message = await bridge_manager.attempt_bridge_recovery(force=True)

        if success:
            return {
                "message": "Bridge restart initiated successfully",
                "success": True,
                "timestamp": datetime.now()
            }
        else:
            return {
                "message": f"Bridge restart failed: {message}",
                "success": False,
                "timestamp": datetime.now()
            }

    except Exception as e:
        logger.error(f"Bridge restart failed: {e}")
        raise HTTPException(status_code=500, detail=f"Bridge restart failed: {str(e)}")


@router.get("/bridge/health")
async def get_bridge_health():
    """
    Simple health check endpoint for bridge status
    
    Returns basic health information for monitoring systems.
    """
    try:
        health_status = await bridge_manager.get_bridge_health_status()

        return {
            "healthy": health_status.bridge_state == BridgeState.ONLINE,
            "state": health_status.bridge_state.value,
            "health_score": health_status.health_score,
            "device_count": health_status.metrics.device_count,
            "last_check": health_status.last_check
        }

    except Exception as e:
        logger.error(f"Bridge health check failed: {e}")
        return {
            "healthy": False,
            "state": "error",
            "health_score": 0,
            "error": str(e),
            "last_check": datetime.now()
        }
