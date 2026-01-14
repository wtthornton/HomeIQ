"""Pydantic schemas for Blueprint Suggestion API."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class DeviceMatch(BaseModel):
    """Matched device information."""
    
    entity_id: str
    domain: str
    device_class: Optional[str] = None
    area_id: Optional[str] = None
    area_name: Optional[str] = None
    device_id: Optional[str] = None
    friendly_name: Optional[str] = None


class BlueprintSuggestionResponse(BaseModel):
    """Blueprint suggestion response."""
    
    id: str
    blueprint_id: str
    blueprint_name: str
    blueprint_description: Optional[str] = None
    suggestion_score: float = Field(ge=0.0, le=1.0)
    matched_devices: list[DeviceMatch]
    use_case: Optional[str] = None
    status: str = Field(default="pending")
    created_at: datetime
    updated_at: datetime
    accepted_at: Optional[datetime] = None
    declined_at: Optional[datetime] = None
    conversation_id: Optional[str] = None


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
    blueprint_yaml: Optional[str] = None
    blueprint_inputs: dict[str, Any] = Field(default_factory=dict)
    matched_devices: list[DeviceMatch]
    suggestion_score: float
    conversation_id: Optional[str] = None


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
    
    device_ids: Optional[list[str]] = Field(default=None, description="Specific device entity IDs to use, or None for all devices")
    complexity: Optional[str] = Field(default=None, description="Filter by complexity: 'simple', 'medium', 'high', or None for all")
    use_case: Optional[str] = Field(default=None, description="Filter by use case: 'convenience', 'security', 'energy', 'comfort', or None for all")
    min_score: float = Field(default=0.6, ge=0.0, le=1.0, description="Minimum suggestion score threshold")
    max_suggestions: int = Field(default=10, ge=1, le=100, description="Maximum number of suggestions to generate")
    min_quality_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Minimum blueprint quality score filter")
    domain: Optional[str] = Field(default=None, description="Filter by device domain (e.g., 'light', 'switch', 'sensor')")


class GenerateSuggestionsResponse(BaseModel):
    """Response schema for suggestion generation."""
    
    generated: int
    status: str
    message: Optional[str] = None