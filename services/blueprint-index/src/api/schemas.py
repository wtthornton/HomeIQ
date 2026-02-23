"""Pydantic schemas for Blueprint Index API."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class BlueprintInputSchema(BaseModel):
    """Schema for a blueprint input parameter."""

    name: str
    input_type: str | None = None
    description: str | None = None
    domain: str | None = None
    device_class: str | None = None
    selector_type: str | None = None
    default_value: str | None = None
    is_required: bool = True


class BlueprintSummary(BaseModel):
    """Summary schema for blueprint list responses."""

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


class BlueprintResponse(BaseModel):
    """Full blueprint details response."""

    id: str
    name: str
    description: str | None = None
    source_url: str
    source_type: str
    source_id: str | None = None
    domain: str = "automation"

    # Device requirements
    required_domains: list[str] = Field(default_factory=list)
    required_device_classes: list[str] = Field(default_factory=list)
    optional_domains: list[str] = Field(default_factory=list)
    optional_device_classes: list[str] = Field(default_factory=list)

    # Input definitions
    inputs: dict[str, Any] = Field(default_factory=dict)

    # Pattern matching
    trigger_platforms: list[str] = Field(default_factory=list)
    action_services: list[str] = Field(default_factory=list)

    # Classification
    use_case: str | None = None
    tags: list[str] = Field(default_factory=list)

    # Community metrics
    stars: int = 0
    downloads: int = 0
    installs: int = 0
    community_rating: float = 0.0
    vote_count: int = 0

    # Quality
    quality_score: float = 0.5
    complexity: str = "medium"

    # Metadata
    author: str | None = None
    ha_min_version: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # YAML content
    yaml_content: str | None = None

    class Config:
        from_attributes = True


class BlueprintSearchRequest(BaseModel):
    """Request schema for blueprint search."""

    # Domain/device filters
    domains: list[str] | None = Field(default=None, description="Required entity domains (e.g., binary_sensor, light)")
    device_classes: list[str] | None = Field(default=None, description="Required device classes (e.g., motion, door)")

    # Pattern matching
    trigger_domain: str | None = Field(default=None, description="Trigger entity domain")
    action_domain: str | None = Field(default=None, description="Action entity domain")

    # Classification filters
    use_case: str | None = Field(default=None, description="Use case category (energy, comfort, security, convenience)")
    domain_type: str | None = Field(default="automation", description="Blueprint domain type")

    # Text search
    query: str | None = Field(default=None, description="Text search in name and description")
    tags: list[str] | None = Field(default=None, description="Filter by tags")

    # Quality filters
    min_quality_score: float = Field(default=0.5, ge=0.0, le=1.0)
    min_community_rating: float = Field(default=0.0, ge=0.0, le=1.0)

    # Pagination
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)

    # Sorting
    sort_by: str = Field(default="quality_score", description="Sort field")
    sort_order: str = Field(default="desc", description="Sort order (asc/desc)")


class BlueprintSearchResponse(BaseModel):
    """Response schema for blueprint search."""

    blueprints: list[BlueprintSummary]
    total: int
    limit: int
    offset: int
    has_more: bool


class PatternMatchRequest(BaseModel):
    """Request schema for pattern-based blueprint matching."""

    trigger_domain: str
    action_domain: str
    trigger_device_class: str | None = None
    action_device_class: str | None = None
    min_quality_score: float = Field(default=0.7, ge=0.0, le=1.0)
    limit: int = Field(default=10, ge=1, le=50)


class PatternMatchResponse(BaseModel):
    """Response schema for pattern-based blueprint matching."""

    blueprints: list[BlueprintSummary]
    match_count: int


class IndexingStatusResponse(BaseModel):
    """Response schema for indexing status."""

    total_blueprints: int
    github_blueprints: int
    discourse_blueprints: int
    last_indexed_at: datetime | None = None
    indexing_in_progress: bool = False
    current_job_id: str | None = None
    current_job_progress: float | None = None


class IndexingJobResponse(BaseModel):
    """Response schema for indexing job details."""

    id: str
    job_type: str
    status: str
    total_items: int
    processed_items: int
    indexed_items: int
    failed_items: int
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None


class TriggerIndexingRequest(BaseModel):
    """Request schema for triggering indexing."""

    job_type: str = Field(default="full", description="Type of indexing job: 'github', 'discourse', 'full'")
    force_refresh: bool = Field(default=False, description="Force re-index even if recently indexed")
