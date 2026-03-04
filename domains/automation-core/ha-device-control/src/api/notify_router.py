"""Notification API router — send HA mobile app notifications."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/control", tags=["notify"])


class NotifyRequest(BaseModel):
    """Request to send a notification."""

    message: str = Field(..., description="Notification body text")
    title: str | None = Field(None, description="Optional notification title")
    target: str | None = Field(
        None,
        description="Optional notify service override (e.g. mobile_app_phone)",
    )


class NotifyResponse(BaseModel):
    """Notification response."""

    success: bool
    affected: list[str]
    message: str


@router.post("/notify", response_model=NotifyResponse)
async def send_notification(req: NotifyRequest) -> NotifyResponse:
    """Send a notification via HA's notify service platform."""
    from ..main import notification_service

    if notification_service is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    result = await notification_service.send(
        message=req.message,
        title=req.title,
        target=req.target,
    )
    return NotifyResponse(
        success=result.success,
        affected=result.affected,
        message=result.message,
    )
