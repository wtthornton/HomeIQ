"""Pydantic schemas for Blueprint Opportunity Engine."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class DeviceSignature(BaseModel):
    """Represents a device's signature for matching."""
    
    entity_id: str
    domain: str
    device_class: Optional[str] = None
    area_id: Optional[str] = None
    area_name: Optional[str] = None
    device_id: Optional[str] = None
    friendly_name: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    integration: Optional[str] = None


class AutofilledInput(BaseModel):
    """Represents an autofilled blueprint input."""
    
    input_name: str
    input_type: str
    value: str
    entity_id: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    is_required: bool = True
    alternatives: list[str] = Field(default_factory=list)


class BlueprintSummary(BaseModel):
    """Summary of a blueprint."""
    
    id: str
    name: str
    description: Optional[str] = None
    source_url: str
    source_type: str
    domain: str = "automation"
    use_case: Optional[str] = None
    required_domains: list[str] = Field(default_factory=list)
    required_device_classes: list[str] = Field(default_factory=list)
    community_rating: float = 0.0
    quality_score: float = 0.5
    stars: int = 0
    complexity: str = "medium"
    author: Optional[str] = None


class BlueprintOpportunity(BaseModel):
    """Represents a blueprint recommendation opportunity."""
    
    id: str
    blueprint: BlueprintSummary
    fit_score: float = Field(ge=0.0, le=1.0)
    
    # Matched devices
    matched_devices: list[DeviceSignature] = Field(default_factory=list)
    matching_domains: list[str] = Field(default_factory=list)
    matching_device_classes: list[str] = Field(default_factory=list)
    
    # Area information
    area_id: Optional[str] = None
    area_name: Optional[str] = None
    same_area: bool = False
    
    # Autofill status
    autofilled_inputs: list[AutofilledInput] = Field(default_factory=list)
    unfilled_inputs: list[str] = Field(default_factory=list)
    autofill_complete: bool = False
    
    # Deployment readiness
    one_click_deploy: bool = False  # True if fit_score >= 0.95 and autofill_complete
    deployment_method: str = "blueprint"  # "blueprint" or "yaml_fallback"
    
    # Metadata
    discovered_at: Optional[datetime] = None
    reason: str = ""  # Why this opportunity was recommended


class BlueprintDeploymentPreview(BaseModel):
    """Preview of a blueprint deployment."""
    
    blueprint_id: str
    blueprint_name: str
    automation_name: str
    
    # Input configuration
    inputs: dict[str, Any] = Field(default_factory=dict)
    autofilled_inputs: list[AutofilledInput] = Field(default_factory=list)
    manual_inputs_required: list[str] = Field(default_factory=list)
    
    # Target entities
    target_entities: list[str] = Field(default_factory=list)
    
    # Estimated impact
    estimated_complexity: str = "medium"
    
    # Deployment readiness
    ready_to_deploy: bool = False
    deployment_issues: list[str] = Field(default_factory=list)
    
    # YAML preview (optional)
    yaml_preview: Optional[str] = None


class OpportunityDiscoveryRequest(BaseModel):
    """Request for opportunity discovery."""
    
    min_fit_score: float = Field(default=0.8, ge=0.0, le=1.0)
    limit: int = Field(default=10, ge=1, le=100)
    use_cases: Optional[list[str]] = None
    area_id: Optional[str] = None
    exclude_blueprint_ids: list[str] = Field(default_factory=list)


class OpportunityDiscoveryResponse(BaseModel):
    """Response from opportunity discovery."""
    
    opportunities: list[BlueprintOpportunity]
    total_found: int
    device_count: int
    area_count: int
    discovery_time_ms: float
