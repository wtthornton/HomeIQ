"""
Proactive Agent API Router (Epic 68).

Endpoints:
- GET  /api/proactive/metrics       — Agent loop metrics
- GET  /api/proactive/audit         — Audit trail of autonomous actions
- POST /api/proactive/undo/{id}     — Undo an autonomous action
- GET  /api/proactive/preferences   — Get user preferences
- PUT  /api/proactive/preferences   — Update user preferences
- POST /api/proactive/trigger-cycle — Manually trigger an observe-reason-act cycle
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

router = APIRouter(prefix="/api/proactive", tags=["proactive"])

logger = logging.getLogger(__name__)

# Module-level references set by main.py on startup
_agent_loop = None
_autonomous_executor = None


def set_agent_loop(loop: Any) -> None:
    """Set the agent loop reference for endpoint handlers."""
    global _agent_loop
    _agent_loop = loop


def set_autonomous_executor(executor: Any) -> None:
    """Set the autonomous executor reference for undo operations."""
    global _autonomous_executor
    _autonomous_executor = executor


# --- Request/Response Models ---


class PreferenceUpdate(BaseModel):
    """Request to update user preferences."""

    autonomous_execution_enabled: bool | None = None
    confidence_threshold: int | None = Field(None, ge=0, le=100)
    excluded_categories: list[str] | None = None
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None


class PreferenceResponse(BaseModel):
    """Current user preference configuration."""

    autonomous_execution_enabled: bool
    confidence_threshold: int
    safety_blocked_domains: list[str]
    quiet_hours_start: str
    quiet_hours_end: str
    undo_window_minutes: int


# --- Endpoints ---


@router.get("/metrics")
async def get_agent_metrics() -> dict[str, Any]:
    """Get proactive agent loop metrics (Story 68.1)."""
    if _agent_loop is None:
        return {"status": "not_initialized", "message": "Agent loop not started"}
    return _agent_loop.get_metrics()


@router.get("/audit")
async def get_audit_trail(
    limit: int = 20,
    offset: int = 0,
    entity_id: str | None = None,
) -> dict[str, Any]:
    """Get audit trail of autonomous actions (Story 68.7)."""
    from ..database import db
    from ..models.autonomous_action import AutonomousActionAudit

    try:
        async with db.get_db() as session:
            stmt = select(AutonomousActionAudit).order_by(
                AutonomousActionAudit.executed_at.desc(),
            )
            if entity_id:
                stmt = stmt.where(AutonomousActionAudit.entity_id == entity_id)
            stmt = stmt.offset(offset).limit(limit)

            result = await session.execute(stmt)
            audits = result.scalars().all()

            return {
                "audits": [
                    {
                        "id": a.id,
                        "action_type": a.action_type,
                        "entity_id": a.entity_id,
                        "action_description": a.action_description,
                        "confidence_score": a.confidence_score,
                        "risk_level": a.risk_level,
                        "outcome": a.outcome,
                        "success": a.success,
                        "undone": a.undone,
                        "executed_at": a.executed_at.isoformat() if a.executed_at else None,
                        "undo_expires_at": a.undo_expires_at.isoformat() if a.undo_expires_at else None,
                        "can_undo": (
                            not a.undone
                            and a.undo_expires_at is not None
                            and datetime.now(UTC) < a.undo_expires_at
                        ),
                    }
                    for a in audits
                ],
                "total": len(audits),
                "limit": limit,
                "offset": offset,
            }
    except Exception as e:
        logger.error("Failed to query audit trail: %s", e)
        raise HTTPException(status_code=500, detail="Failed to query audit trail") from e


@router.post("/undo/{audit_id}")
async def undo_action(audit_id: str) -> dict[str, Any]:
    """Undo an autonomous action (Story 68.7)."""
    if _autonomous_executor is None:
        raise HTTPException(status_code=503, detail="Autonomous executor not initialized")

    success = await _autonomous_executor.undo_action(audit_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Could not undo action (expired, already undone, or not found)",
        )
    return {"status": "undone", "audit_id": audit_id}


@router.get("/preferences", response_model=PreferenceResponse)
async def get_preferences() -> PreferenceResponse:
    """Get current user preference configuration (Story 68.6)."""
    from ..config import Settings

    settings = Settings()
    blocked = [d.strip() for d in settings.safety_blocked_domains.split(",") if d.strip()]

    return PreferenceResponse(
        autonomous_execution_enabled=settings.autonomous_execution_enabled,
        confidence_threshold=settings.auto_execute_confidence_threshold,
        safety_blocked_domains=blocked,
        quiet_hours_start=settings.quiet_hours_start,
        quiet_hours_end=settings.quiet_hours_end,
        undo_window_minutes=settings.undo_window_minutes,
    )


@router.put("/preferences")
async def update_preferences(update: PreferenceUpdate) -> dict[str, Any]:
    """Update user preferences (Story 68.6).

    Note: Preferences that can be dynamically updated are stored in DB.
    Environment-level settings require service restart.
    """
    from ..database import db
    from ..models.autonomous_action import UserPreference

    try:
        async with db.get_db() as session:
            updates = update.model_dump(exclude_none=True)
            for key, value in updates.items():
                stmt = select(UserPreference).where(UserPreference.preference_key == key)
                result = await session.execute(stmt)
                pref = result.scalar_one_or_none()
                if pref:
                    pref.preference_value = {"value": value}
                else:
                    pref = UserPreference(
                        preference_key=key,
                        preference_value={"value": value},
                        description=f"User preference: {key}",
                    )
                    session.add(pref)
            await session.commit()

        return {"status": "updated", "updated_keys": list(updates.keys())}
    except Exception as e:
        logger.error("Failed to update preferences: %s", e)
        raise HTTPException(status_code=500, detail="Failed to update preferences") from e


@router.post("/trigger-cycle")
async def trigger_cycle() -> dict[str, Any]:
    """Manually trigger an observe-reason-act cycle (useful for testing)."""
    if _agent_loop is None:
        raise HTTPException(status_code=503, detail="Agent loop not initialized")

    result = await _agent_loop.run_cycle()
    return result
