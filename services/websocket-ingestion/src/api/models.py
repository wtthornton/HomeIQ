"""
Pydantic models for websocket-ingestion API.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    service: str
    uptime: Optional[str] = None
    timestamp: str
    connection: Optional[Dict[str, Any]] = None
    subscription: Optional[Dict[str, Any]] = None


class EventRateResponse(BaseModel):
    """Event rate response model."""
    service: str
    events_per_second: float
    events_per_hour: float
    total_events_processed: int
    uptime_seconds: float
    processing_stats: Dict[str, Any]
    connection_stats: Dict[str, Any]
    timestamp: str


class DiscoveryTriggerResponse(BaseModel):
    """Discovery trigger response model."""
    success: bool
    devices_discovered: Optional[int] = None
    entities_discovered: Optional[int] = None
    timestamp: str
    error: Optional[str] = None


class FilterStatsResponse(BaseModel):
    """Entity filter statistics response model."""
    enabled: bool
    statistics: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


