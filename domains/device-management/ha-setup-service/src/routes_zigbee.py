"""Zigbee2MQTT bridge and setup wizard route handlers."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from .zigbee_setup_wizard import SetupWizardRequest

logger = logging.getLogger(__name__)

bridge_router = APIRouter(prefix="/api/zigbee2mqtt", tags=["Zigbee2MQTT Bridge"])
setup_router = APIRouter(prefix="/api/zigbee2mqtt/setup", tags=["Zigbee2MQTT Setup"])


# ---------------------------------------------------------------------------
# Bridge management
# ---------------------------------------------------------------------------


@bridge_router.get("/bridge/status")
async def get_bridge_status(request: Request) -> dict[str, Any]:
    """Get comprehensive Zigbee2MQTT bridge health status."""
    try:
        bridge_manager = getattr(request.app.state, "bridge_manager", None)
        if not bridge_manager:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Bridge manager not initialized")
        health_status = await bridge_manager.get_bridge_health_status()

        return {
            "bridge_state": health_status.bridge_state.value,
            "is_connected": health_status.is_connected,
            "health_score": health_status.health_score,
            "device_count": health_status.metrics.device_count,
            "response_time_ms": health_status.metrics.response_time_ms,
            "signal_strength_avg": health_status.metrics.signal_strength_avg,
            "network_health_score": health_status.metrics.network_health_score,
            "consecutive_failures": health_status.consecutive_failures,
            "recommendations": health_status.recommendations,
            "last_check": health_status.last_check,
            "recovery_attempts": [
                {
                    "timestamp": attempt.timestamp,
                    "action": attempt.action.value,
                    "success": attempt.success,
                    "error_message": attempt.error_message,
                    "duration_seconds": attempt.duration_seconds,
                }
                for attempt in health_status.recovery_attempts
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get bridge status")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@bridge_router.post("/bridge/recovery")
async def attempt_bridge_recovery(request: Request, force: bool = False) -> dict[str, Any]:
    """Attempt to recover Zigbee2MQTT bridge connectivity."""
    try:
        bridge_manager = getattr(request.app.state, "bridge_manager", None)
        if not bridge_manager:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Bridge manager not initialized")
        success, message = await bridge_manager.attempt_bridge_recovery(force=force)
        return {"success": success, "message": message, "timestamp": datetime.now(UTC)}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Recovery failed")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@bridge_router.post("/bridge/restart")
async def restart_bridge(request: Request) -> dict[str, Any]:
    """Restart Zigbee2MQTT bridge (alias for recovery)."""
    try:
        bridge_manager = getattr(request.app.state, "bridge_manager", None)
        if not bridge_manager:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Bridge manager not initialized")
        success, message = await bridge_manager.attempt_bridge_recovery(force=True)
        return {"success": success, "message": message, "timestamp": datetime.now(UTC)}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Bridge restart failed")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@bridge_router.get("/bridge/health")
async def get_bridge_health(request: Request) -> dict[str, Any]:
    """Simple health check endpoint for bridge status."""
    try:
        bridge_manager = getattr(request.app.state, "bridge_manager", None)
        if not bridge_manager:
            return {
                "healthy": False, "state": "uninitialized",
                "health_score": 0, "error": "Bridge manager not initialized",
                "last_check": datetime.now(UTC),
            }
        health_status = await bridge_manager.get_bridge_health_status()
        return {
            "healthy": health_status.bridge_state.value == "online",
            "state": health_status.bridge_state.value,
            "health_score": health_status.health_score,
            "device_count": health_status.metrics.device_count,
            "last_check": health_status.last_check,
        }
    except Exception as e:
        return {
            "healthy": False, "state": "error",
            "health_score": 0, "error": str(e),
            "last_check": datetime.now(UTC),
        }


# ---------------------------------------------------------------------------
# Setup wizard
# ---------------------------------------------------------------------------


@setup_router.post("/start")
async def start_zigbee_setup_wizard(req: Request, request: SetupWizardRequest) -> dict[str, Any]:
    """Start a new Zigbee2MQTT setup wizard."""
    try:
        setup_wizard = getattr(req.app.state, "zigbee_setup_wizard", None)
        if not setup_wizard:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Setup wizard not initialized")
        return await setup_wizard.start_setup_wizard(request)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to start setup wizard")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@setup_router.post("/{wizard_id}/continue")
async def continue_zigbee_setup_wizard(request: Request, wizard_id: str) -> dict[str, Any]:
    """Continue the setup wizard to the next step."""
    try:
        setup_wizard = getattr(request.app.state, "zigbee_setup_wizard", None)
        if not setup_wizard:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Setup wizard not initialized")
        return await setup_wizard.continue_wizard(wizard_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.exception("Failed to continue wizard")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@setup_router.get("/{wizard_id}/status")
async def get_zigbee_setup_wizard_status(request: Request, wizard_id: str) -> dict[str, Any]:
    """Get current wizard status."""
    try:
        setup_wizard = getattr(request.app.state, "zigbee_setup_wizard", None)
        if not setup_wizard:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Setup wizard not initialized")
        response = await setup_wizard.get_wizard_status(wizard_id)
        if response is None:
            raise HTTPException(status_code=404, detail="Wizard not found")
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get wizard status")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@setup_router.delete("/{wizard_id}")
async def cancel_zigbee_setup_wizard(request: Request, wizard_id: str) -> dict[str, Any]:
    """Cancel an active setup wizard."""
    try:
        setup_wizard = getattr(request.app.state, "zigbee_setup_wizard", None)
        if not setup_wizard:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Setup wizard not initialized")
        success = await setup_wizard.cancel_wizard(wizard_id)
        if success:
            return {"message": "Wizard cancelled successfully", "wizard_id": wizard_id}
        raise HTTPException(status_code=404, detail="Wizard not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to cancel wizard")
        raise HTTPException(status_code=500, detail="Internal server error") from e
