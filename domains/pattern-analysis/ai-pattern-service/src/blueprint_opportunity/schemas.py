"""Pydantic schemas for Blueprint Opportunity Engine."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DeviceSignature(BaseModel):
    """Represents a device's signature for matching."""

    entity_id: str
    domain: str
    device_class: str | None = None
    area_id: str | None = None
    area_name: str | None = None
    device_id: str | None = None
    friendly_name: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    integration: str | None = None


class AutofilledInput(BaseModel):
    """Represents an autofilled blueprint input."""

    input_name: str
    input_type: str
    value: str
    entity_id: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    is_required: bool = True
    alternatives: list[str] = Field(default_factory=list)


class BlueprintSummary(BaseModel):
    """Summary of a blueprint."""

    id: str
    name: str
    description: str | None = None
    source_url: str
    source_type: str
    domain: str = "automation"
    use_case: str | None = None
    required_domains: list[str] = Field(default_factory=list)
    required_device_classes: list[str] = Field(default_factory=list)
    community_rating: float = 0.0
    quality_score: float = 0.5
    stars: int = 0
    complexity: str = "medium"
    author: str | None = None


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
    area_id: str | None = None
    area_name: str | None = None
    same_area: bool = False

    # Autofill status
    autofilled_inputs: list[AutofilledInput] = Field(default_factory=list)
    unfilled_inputs: list[str] = Field(default_factory=list)
    autofill_complete: bool = False

    # Deployment readiness
    one_click_deploy: bool = False  # True if fit_score >= 0.95 and autofill_complete
    deployment_method: str = "blueprint"  # "blueprint" or "yaml_fallback"

    # Metadata
    discovered_at: datetime | None = None
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
    yaml_preview: str | None = None


class OpportunityDiscoveryRequest(BaseModel):
    """Request for opportunity discovery."""

    min_fit_score: float = Field(default=0.8, ge=0.0, le=1.0)
    limit: int = Field(default=10, ge=1, le=100)
    use_cases: list[str] | None = None
    area_id: str | None = None
    exclude_blueprint_ids: list[str] = Field(default_factory=list)


class OpportunityDiscoveryResponse(BaseModel):
    """Response from opportunity discovery."""

    opportunities: list[BlueprintOpportunity]
    total_found: int
    device_count: int
    area_count: int
    discovery_time_ms: float
