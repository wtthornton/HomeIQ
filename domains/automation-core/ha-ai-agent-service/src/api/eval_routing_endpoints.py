"""
Eval Routing API Endpoints (Epic 69, Stories 69.2, 69.3, 69.4, 69.6, 69.7).

Endpoints:
  GET  /api/v1/model-routing          — Current routing table
  GET  /api/v1/model-routing/decisions — Recent routing decisions
  GET  /api/v1/eval-alerts             — Active eval alerts
  POST /api/v1/eval-alerts/{id}/ack    — Acknowledge an alert
  GET  /api/v1/eval-alerts/trackers    — Dimension tracker status
  GET  /api/v1/cost-tracking           — Cost savings report
  GET  /api/v1/cost-tracking/daily     — Daily cost summaries
  GET  /api/v1/cost-tracking/spike     — Cost spike check
  PUT  /api/v1/model-routing/config    — Update routing config
  PUT  /api/v1/model-routing/agent-override — Set per-agent override
  PUT  /api/v1/model-routing/lock      — Lock/unlock model
  GET  /api/v1/eval-investigation/{alert_id} — Investigation report
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Eval Routing"])

# Module-level singletons (set during startup)
_model_router = None
_alert_service = None
_cost_tracker = None
_investigator = None


def set_eval_routing_services(
    model_router=None,
    alert_service=None,
    cost_tracker=None,
    investigator=None,
):
    """Set service instances (called during app startup)."""
    global _model_router, _alert_service, _cost_tracker, _investigator
    _model_router = model_router
    _alert_service = alert_service
    _cost_tracker = cost_tracker
    _investigator = investigator


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------


class RoutingConfigUpdate(BaseModel):
    routing_enabled: bool | None = None
    eval_floor: float | None = Field(default=None, ge=0, le=100)
    primary_model: str | None = None
    cheap_model: str | None = None


class AgentOverrideRequest(BaseModel):
    agent_id: str
    model: str | None = Field(
        default=None,
        description="Model to force for this agent, or null to clear",
    )


class ModelLockRequest(BaseModel):
    model: str | None = Field(
        default=None,
        description="Model to lock to, or null to unlock",
    )


# ---------------------------------------------------------------------------
# Routing endpoints
# ---------------------------------------------------------------------------


@router.get("/model-routing")
async def get_routing_table():
    """Get current routing table and eval score status."""
    if not _model_router:
        raise HTTPException(status_code=503, detail="Model router not initialized")
    return _model_router.get_routing_table()


@router.get("/model-routing/decisions")
async def get_routing_decisions(
    limit: int = Query(default=50, ge=1, le=200),
):
    """Get recent routing decisions for correlation analysis."""
    if not _model_router:
        raise HTTPException(status_code=503, detail="Model router not initialized")
    return {"decisions": _model_router.get_recent_decisions(limit)}


@router.put("/model-routing/config")
async def update_routing_config(update: RoutingConfigUpdate):
    """Update routing configuration (Story 69.7)."""
    if not _model_router:
        raise HTTPException(status_code=503, detail="Model router not initialized")

    config = _model_router.config
    if update.routing_enabled is not None:
        config.routing_enabled = update.routing_enabled
    if update.eval_floor is not None:
        config.eval_floor = update.eval_floor
    if update.primary_model is not None:
        config.primary_model = update.primary_model
    if update.cheap_model is not None:
        config.cheap_model = update.cheap_model

    logger.info("Routing config updated: %s", update.model_dump(exclude_none=True))
    return {"success": True, "config": _model_router.get_routing_table()["config"]}


@router.put("/model-routing/agent-override")
async def set_agent_override(request: AgentOverrideRequest):
    """Set or clear a per-agent model override (Story 69.7)."""
    if not _model_router:
        raise HTTPException(status_code=503, detail="Model router not initialized")

    _model_router.set_agent_override(request.agent_id, request.model)
    action = f"set to {request.model}" if request.model else "cleared"
    logger.info("Agent override for %s: %s", request.agent_id, action)
    return {"success": True, "agent_id": request.agent_id, "action": action}


@router.put("/model-routing/lock")
async def lock_model(request: ModelLockRequest):
    """Lock or unlock model selection (incident mode, Story 69.7)."""
    if not _model_router:
        raise HTTPException(status_code=503, detail="Model router not initialized")

    _model_router.config.locked_model = request.model
    action = f"locked to {request.model}" if request.model else "unlocked"
    logger.info("Model routing %s", action)
    return {"success": True, "action": action}


# ---------------------------------------------------------------------------
# Alert endpoints
# ---------------------------------------------------------------------------


@router.get("/eval-alerts")
async def get_eval_alerts(
    limit: int = Query(default=50, ge=1, le=200),
    unacknowledged_only: bool = Query(default=False),
):
    """Get eval degradation alerts (Story 69.4)."""
    if not _alert_service:
        raise HTTPException(status_code=503, detail="Alert service not initialized")
    return {"alerts": _alert_service.get_alerts(limit, unacknowledged_only)}


@router.post("/eval-alerts/{alert_id}/ack")
async def acknowledge_alert(alert_id: str):
    """Acknowledge an eval alert."""
    if not _alert_service:
        raise HTTPException(status_code=503, detail="Alert service not initialized")
    if not _alert_service.acknowledge_alert(alert_id):
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"success": True, "alert_id": alert_id}


@router.get("/eval-alerts/trackers")
async def get_tracker_status():
    """Get eval dimension tracker status."""
    if not _alert_service:
        raise HTTPException(status_code=503, detail="Alert service not initialized")
    return {"trackers": _alert_service.get_tracker_status()}


# ---------------------------------------------------------------------------
# Cost tracking endpoints
# ---------------------------------------------------------------------------


@router.get("/cost-tracking")
async def get_cost_savings():
    """Get cost savings report (Story 69.6)."""
    if not _cost_tracker:
        raise HTTPException(status_code=503, detail="Cost tracker not initialized")
    return _cost_tracker.get_savings_report()


@router.get("/cost-tracking/daily")
async def get_daily_costs(days: int = Query(default=7, ge=1, le=30)):
    """Get daily cost summaries."""
    if not _cost_tracker:
        raise HTTPException(status_code=503, detail="Cost tracker not initialized")
    return {"daily": _cost_tracker.get_daily_summaries(days)}


@router.get("/cost-tracking/spike")
async def check_cost_spike():
    """Check for cost spikes."""
    if not _cost_tracker:
        raise HTTPException(status_code=503, detail="Cost tracker not initialized")
    spike = _cost_tracker.check_cost_spike()
    return {"spike": spike}


# ---------------------------------------------------------------------------
# Investigation endpoints
# ---------------------------------------------------------------------------


@router.get("/eval-investigation/{alert_id}")
async def get_investigation(alert_id: str):
    """Get investigation report for an eval alert (Story 69.5)."""
    if not _investigator:
        raise HTTPException(status_code=503, detail="Investigator not initialized")
    report = _investigator.get_report(alert_id)
    if not report:
        raise HTTPException(status_code=404, detail="Investigation report not found")
    return report
