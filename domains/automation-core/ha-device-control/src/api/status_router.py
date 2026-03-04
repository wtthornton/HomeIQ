"""Status API router — full house status snapshot."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/control", tags=["status"])


@router.get("/status")
async def get_house_status() -> dict[str, Any]:
    """Return a comprehensive house status snapshot.

    Includes climate zones, presence tracking, lights by area,
    binary sensors, active switches, and active automations.
    """
    from ..main import status_service

    if status_service is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    status = await status_service.get_house_status()

    return {
        "climate": [
            {
                "entity_id": c.entity_id,
                "friendly_name": c.friendly_name,
                "area": c.area,
                "current_temperature": c.current_temperature,
                "target_temperature": c.target_temperature,
                "hvac_mode": c.hvac_mode,
                "unit": c.unit,
            }
            for c in status.climate
        ],
        "presence": status.presence,
        "lights_by_area": [
            {
                "area": a.area,
                "on_count": a.on_count,
                "off_count": a.off_count,
                "lights": a.lights,
            }
            for a in status.lights_by_area
        ],
        "binary_sensors": [
            {
                "entity_id": s.entity_id,
                "friendly_name": s.friendly_name,
                "device_class": s.device_class,
                "state": s.state,
                "area": s.area,
            }
            for s in status.binary_sensors
        ],
        "active_switches": status.active_switches,
        "active_automations": status.active_automations,
    }
