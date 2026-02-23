"""Pydantic schemas for Blueprint Suggestion API."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DeviceMatch(BaseModel):
    """Matched device information."""

    entity_id: str
    domain: str
    device_class: str | None = None
    area_id: str | None = None
    area_name: str | None = None
    device_id: str | None = None
    friendly_name: str | None = None


class BlueprintSuggestionResponse(BaseModel):
    """Blueprint suggestion response."""

    id: str
    blueprint_id: str
    blueprint_name: str
    blueprint_description: str | None = None
    suggestion_score: float = Field(ge=0.0, le=1.0)
    matched_devices: list[DeviceMatch]
    use_case: str | None = None
    status: str = Field(default="pending")
    created_at: datetime
    updated_at: datetime
    accepted_at: datetime | None = None
    declined_at: datetime | None = None
    conversation_id: str | None = None


class BlueprintSuggestionListResponse(BaseModel):
    """List of blueprint suggestions."""

    suggestions: list[BlueprintSuggestionResponse]
    total: int
    limit: int
    offset: int


class AcceptSuggestionResponse(BaseModel):
    """Response when accepting a suggestion."""

    id: str
    status: str
    blueprint_id: str
    blueprint_yaml: str | None = None
    blueprint_inputs: dict[str, Any] = Field(default_factory=dict)
    matched_devices: list[DeviceMatch]
    suggestion_score: float
    conversation_id: str | None = None


class SuggestionStatsResponse(BaseModel):
    """Statistics about suggestions."""

    total_suggestions: int
    pending_count: int
    accepted_count: int
    declined_count: int
    average_score: float
    min_score: float
    max_score: float


class GenerateSuggestionsRequest(BaseModel):
    """Request schema for generating suggestions with parameters."""

    device_ids: list[str] | None = Field(default=None, description="Specific device entity IDs to use, or None for all devices")
    complexity: str | None = Field(default=None, description="Filter by complexity: 'simple', 'medium', 'high', or None for all")
    use_case: str | None = Field(default=None, description="Filter by use case: 'convenience', 'security', 'energy', 'comfort', or None for all")
    min_score: float = Field(default=0.6, ge=0.0, le=1.0, description="Minimum suggestion score threshold")
    max_suggestions: int = Field(default=10, ge=1, le=100, description="Maximum number of suggestions to generate")
    min_quality_score: float | None = Field(default=None, ge=0.0, le=1.0, description="Minimum blueprint quality score filter")
    domain: str | None = Field(default=None, description="Filter by device domain (e.g., 'light', 'switch', 'sensor')")


class GenerateSuggestionsResponse(BaseModel):
    """Response schema for suggestion generation."""

    generated: int
    status: str
    message: str | None = None