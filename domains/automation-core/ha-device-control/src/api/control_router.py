"""Control API router — lights, switches, climate, scenes, and device listing.

All endpoints return a standard ``ControlResponse`` format.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/control", tags=["control"])

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class LightRequest(BaseModel):
    """Request to control a single light."""

    entity_id_or_name: str = Field(..., description="Entity ID or friendly name")
    brightness: int = Field(..., ge=0, le=100, description="Brightness 0-100 (0=off)")
    rgb: list[int] | None = Field(None, description="Optional [R, G, B] each 0-255")


class AreaLightRequest(BaseModel):
    """Request to control all lights in an area."""

    area: str = Field(..., description="Area name")
    brightness: int = Field(..., ge=0, le=100, description="Brightness 0-100 (0=off)")
    rgb: list[int] | None = Field(None, description="Optional [R, G, B] each 0-255")


class SwitchRequest(BaseModel):
    """Request to control a switch."""

    entity_id_or_name: str = Field(..., description="Entity ID or friendly name")
    state: str = Field(..., pattern="^(on|off)$", description="'on' or 'off'")


class ClimateSetRequest(BaseModel):
    """Request to set climate/thermostat."""

    entity_id: str = Field(..., description="Climate entity ID")
    temperature: float = Field(..., description="Target temperature")
    hvac_mode: str | None = Field(None, description="Optional HVAC mode (heat, cool, auto)")


class SceneRequest(BaseModel):
    """Request to activate a scene or script."""

    name: str = Field(..., description="Scene or script name")


class ControlResponse(BaseModel):
    """Standard response for control operations."""

    success: bool
    affected: list[str]
    message: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/light", response_model=ControlResponse)
async def control_light(req: LightRequest) -> ControlResponse:
    """Control a single light by name or entity ID."""
    from ..main import light_controller

    if light_controller is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    result = await light_controller.set_light(
        name_or_id=req.entity_id_or_name,
        brightness=req.brightness,
        rgb=req.rgb,
    )
    return ControlResponse(
        success=result.success,
        affected=result.affected,
        message=result.message,
    )


@router.post("/light/area", response_model=ControlResponse)
async def control_area_lights(req: AreaLightRequest) -> ControlResponse:
    """Control all lights in an area."""
    from ..main import light_controller

    if light_controller is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    result = await light_controller.set_area_lights(
        area=req.area,
        brightness=req.brightness,
        rgb=req.rgb,
    )
    return ControlResponse(
        success=result.success,
        affected=result.affected,
        message=result.message,
    )


@router.post("/switch", response_model=ControlResponse)
async def control_switch(req: SwitchRequest) -> ControlResponse:
    """Turn a switch on or off."""
    from ..main import switch_controller

    if switch_controller is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    result = await switch_controller.set_switch(
        name_or_id=req.entity_id_or_name,
        state=req.state,
    )
    return ControlResponse(
        success=result.success,
        affected=result.affected,
        message=result.message,
    )


@router.get("/climate")
async def get_climate() -> list[dict[str, Any]]:
    """List all climate entities with current state."""
    from ..main import climate_controller

    if climate_controller is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    entities = await climate_controller.get_climate_entities()
    return [
        {
            "entity_id": e.entity_id,
            "friendly_name": e.friendly_name,
            "area": e.area,
            "current_temperature": e.current_temperature,
            "target_temperature": e.target_temperature,
            "hvac_mode": e.hvac_mode,
            "hvac_modes": e.hvac_modes,
            "unit": e.unit,
        }
        for e in entities
    ]


@router.post("/climate", response_model=ControlResponse)
async def control_climate(req: ClimateSetRequest) -> ControlResponse:
    """Set temperature on a climate entity."""
    from ..main import climate_controller

    if climate_controller is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    result = await climate_controller.set_climate(
        entity_id=req.entity_id,
        temperature=req.temperature,
        hvac_mode=req.hvac_mode,
    )
    return ControlResponse(
        success=result.success,
        affected=result.affected,
        message=result.message,
    )


@router.get("/scenes")
async def list_scenes() -> list[dict[str, str]]:
    """List all available scenes and scripts."""
    from ..main import scene_controller

    if scene_controller is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    items = await scene_controller.list_scenes_and_scripts()
    return [
        {
            "entity_id": s.entity_id,
            "friendly_name": s.friendly_name,
            "type": s.entity_type,
        }
        for s in items
    ]


@router.post("/scene", response_model=ControlResponse)
async def activate_scene(req: SceneRequest) -> ControlResponse:
    """Activate a scene or script by name."""
    from ..main import scene_controller

    if scene_controller is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    result = await scene_controller.activate(req.name)
    return ControlResponse(
        success=result.success,
        affected=result.affected,
        message=result.message,
    )


@router.get("/devices")
async def list_devices() -> list[dict[str, str]]:
    """List all controllable devices (lights, switches, climate)."""
    from ..main import entity_resolver

    if entity_resolver is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    controllable_domains = ("light", "switch", "climate", "scene", "script", "fan", "cover")
    results: list[dict[str, str]] = []

    for domain in controllable_domains:
        entities = await entity_resolver.list_entities(domain_filter=domain)
        for ent in entities:
            results.append({
                "entity_id": ent.entity_id,
                "friendly_name": ent.friendly_name,
                "domain": ent.domain,
                "area": ent.area,
                "state": ent.state,
            })

    return results
