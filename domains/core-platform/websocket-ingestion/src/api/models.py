"""
Pydantic models for websocket-ingestion API.
"""

from typing import Any

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    service: str
    uptime: str | None = None
    timestamp: str
    connection: dict[str, Any] | None = None
    subscription: dict[str, Any] | None = None


class EventRateResponse(BaseModel):
    """Event rate response model."""
    service: str
    events_per_second: float
    events_per_hour: float
    total_events_processed: int
    uptime_seconds: float
    processing_stats: dict[str, Any]
    connection_stats: dict[str, Any]
    timestamp: str


class DiscoveryTriggerResponse(BaseModel):
    """Discovery trigger response model."""
    success: bool
    devices_discovered: int | None = None
    entities_discovered: int | None = None
    timestamp: str
    error: str | None = None


class FilterStatsResponse(BaseModel):
    """Entity filter statistics response model."""
    enabled: bool
    statistics: dict[str, Any] | None = None
    message: str | None = None
