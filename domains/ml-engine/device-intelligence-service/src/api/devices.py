"""
Device Intelligence Service - Device Endpoints

Provides device CRUD and query endpoints backed by DeviceService.

NOTE: These routes overlap with storage.py (which also serves /devices
endpoints). Only ONE of these routers should be included in main.py at a
time.  Currently storage_router is the active router; this module is kept
as the canonical, well-typed alternative that can replace it when needed.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db_session
from ..services.device_service import DeviceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/devices", tags=["Devices"])


# ---------------------------------------------------------------------------
# Pydantic response models – mirrors the ORM Device / DeviceCapability /
# DeviceHealthMetric columns so callers receive structured, validated JSON.
# ---------------------------------------------------------------------------

class DeviceResponse(BaseModel):
    """Full device representation returned by the API."""

    device_id: str
    name: str
    manufacturer: str | None = None
    model: str | None = None
    area_id: str | None = None
    area_name: str | None = None
    integration: str
    sw_version: str | None = None
    hw_version: str | None = None
    health_score: int | None = None
    device_class: str | None = None
    # Zigbee / connectivity fields
    lqi: int | None = None
    availability_status: str | None = None
    battery_level: int | None = None
    battery_low: bool | None = None
    device_type: str | None = None
    source: str | None = None
    # Timestamps
    last_seen: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class DeviceListResponse(BaseModel):
    """Paginated list of devices."""

    devices: list[DeviceResponse]
    total: int
    page: int
    per_page: int


class DeviceCapabilityResponse(BaseModel):
    """Single device capability."""

    device_id: str
    capability_name: str
    capability_type: str
    properties: dict[str, Any] | None = None
    exposed: bool
    configured: bool
    source: str
    last_updated: datetime


class DeviceHealthMetricResponse(BaseModel):
    """Single device health metric record."""

    device_id: str
    metric_name: str
    metric_value: float
    metric_unit: str | None = None
    metadata_json: dict[str, Any] | None = None
    timestamp: datetime


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------

def get_device_service(
    session: AsyncSession = Depends(get_db_session),
) -> DeviceService:
    """Provide a *DeviceService* bound to the current DB session."""
    return DeviceService(session)


# ---------------------------------------------------------------------------
# Helper – convert an ORM Device to a DeviceResponse
# ---------------------------------------------------------------------------

def _device_to_response(device: Any) -> DeviceResponse:
    """Map an ORM *Device* instance to a *DeviceResponse*."""
    return DeviceResponse(
        device_id=device.id,
        name=device.name,
        manufacturer=device.manufacturer,
        model=device.model,
        area_id=device.area_id,
        area_name=device.area_name,
        integration=device.integration,
        sw_version=device.sw_version,
        hw_version=device.hw_version,
        health_score=device.health_score,
        device_class=device.device_class,
        lqi=device.lqi,
        availability_status=device.availability_status,
        battery_level=device.battery_level,
        battery_low=device.battery_low,
        device_type=device.device_type,
        source=device.source,
        last_seen=device.last_seen.isoformat() if device.last_seen else None,
        created_at=device.created_at.isoformat() if device.created_at else None,
        updated_at=device.updated_at.isoformat() if device.updated_at else None,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _fetch_filtered_devices(
    device_service: DeviceService,
    *,
    area_id: str | None,
    integration: str | None,
    fetch_limit: int,
) -> list[Any]:
    """Fetch devices from the service, applying area/integration filters."""
    if area_id:
        devices = await device_service.get_devices_by_area(area_id)
        if integration:
            devices = [d for d in devices if d.integration == integration]
        return devices

    if integration:
        return await device_service.get_devices_by_integration(integration)

    return await device_service.get_all_devices(limit=fetch_limit)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/", response_model=DeviceListResponse)
async def get_devices(
    skip: int = Query(default=0, ge=0, description="Number of devices to skip"),
    limit: int = Query(default=100, ge=1, le=1000, description="Max devices to return"),
    area_id: str | None = Query(default=None, description="Filter by area ID"),
    integration: str | None = Query(default=None, description="Filter by integration"),
    device_service: DeviceService = Depends(get_device_service),
) -> DeviceListResponse:
    """Return a paginated, optionally filtered list of devices."""
    try:
        devices = await _fetch_filtered_devices(
            device_service,
            area_id=area_id,
            integration=integration,
            fetch_limit=skip + limit,
        )
        total = len(devices)
        paginated = devices[skip : skip + limit]

        return DeviceListResponse(
            devices=[_device_to_response(d) for d in paginated],
            total=total,
            page=(skip // limit + 1) if limit > 0 else 1,
            per_page=limit,
        )
    except Exception as exc:
        logger.error("Error retrieving devices: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: str,
    device_service: DeviceService = Depends(get_device_service),
) -> DeviceResponse:
    """Return a single device by its ID, or 404 if not found."""
    try:
        device = await device_service.get_device_by_id(device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        return _device_to_response(device)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error retrieving device %s: %s", device_id, exc)
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@router.get(
    "/{device_id}/capabilities",
    response_model=list[DeviceCapabilityResponse],
)
async def get_device_capabilities(
    device_id: str,
    device_service: DeviceService = Depends(get_device_service),
) -> list[DeviceCapabilityResponse]:
    """Return all capabilities registered for *device_id*."""
    try:
        # Verify the device exists first.
        device = await device_service.get_device_by_id(device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")

        capabilities = await device_service.get_device_capabilities(device_id)
        return [
            DeviceCapabilityResponse(
                device_id=cap.device_id,
                capability_name=cap.capability_name,
                capability_type=cap.capability_type,
                properties=cap.properties,
                exposed=cap.exposed,
                configured=cap.configured,
                source=cap.source,
                last_updated=cap.last_updated,
            )
            for cap in capabilities
        ]
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Error retrieving capabilities for device %s: %s",
            device_id,
            exc,
        )
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@router.get(
    "/{device_id}/health",
    response_model=list[DeviceHealthMetricResponse],
)
async def get_device_health(
    device_id: str,
    limit: int = Query(default=100, ge=1, le=1000, description="Max metrics to return"),
    device_service: DeviceService = Depends(get_device_service),
) -> list[DeviceHealthMetricResponse]:
    """Return recent health metric records for *device_id*."""
    try:
        # Verify the device exists first.
        device = await device_service.get_device_by_id(device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")

        metrics = await device_service.get_device_health_metrics(device_id, limit)
        return [
            DeviceHealthMetricResponse(
                device_id=metric.device_id,
                metric_name=metric.metric_name,
                metric_value=metric.metric_value,
                metric_unit=metric.metric_unit,
                metadata_json=metric.metadata_json,
                timestamp=metric.timestamp,
            )
            for metric in metrics
        ]
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Error retrieving health metrics for device %s: %s",
            device_id,
            exc,
        )
        raise HTTPException(status_code=500, detail="Internal server error") from exc
