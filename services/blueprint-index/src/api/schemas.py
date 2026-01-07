"""Pydantic schemas for Blueprint Index API."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class BlueprintInputSchema(BaseModel):
    """Schema for a blueprint input parameter."""
    
    name: str
    input_type: Optional[str] = None
    description: Optional[str] = None
    domain: Optional[str] = None
    device_class: Optional[str] = None
    selector_type: Optional[str] = None
    default_value: Optional[str] = None
    is_required: bool = True


class BlueprintSummary(BaseModel):
    """Summary schema for blueprint list responses."""
    
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


class BlueprintResponse(BaseModel):
    """Full blueprint details response."""
    
    id: str
    name: str
    description: Optional[str] = None
    source_url: str
    source_type: str
    source_id: Optional[str] = None
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
    use_case: Optional[str] = None
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
    author: Optional[str] = None
    ha_min_version: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # YAML content
    yaml_content: Optional[str] = None
    
    class Config:
        from_attributes = True


class BlueprintSearchRequest(BaseModel):
    """Request schema for blueprint search."""
    
    # Domain/device filters
    domains: Optional[list[str]] = Field(default=None, description="Required entity domains (e.g., binary_sensor, light)")
    device_classes: Optional[list[str]] = Field(default=None, description="Required device classes (e.g., motion, door)")
    
    # Pattern matching
    trigger_domain: Optional[str] = Field(default=None, description="Trigger entity domain")
    action_domain: Optional[str] = Field(default=None, description="Action entity domain")
    
    # Classification filters
    use_case: Optional[str] = Field(default=None, description="Use case category (energy, comfort, security, convenience)")
    domain_type: Optional[str] = Field(default="automation", description="Blueprint domain type")
    
    # Text search
    query: Optional[str] = Field(default=None, description="Text search in name and description")
    tags: Optional[list[str]] = Field(default=None, description="Filter by tags")
    
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
    trigger_device_class: Optional[str] = None
    action_device_class: Optional[str] = None
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
    last_indexed_at: Optional[datetime] = None
    indexing_in_progress: bool = False
    current_job_id: Optional[str] = None
    current_job_progress: Optional[float] = None


class IndexingJobResponse(BaseModel):
    """Response schema for indexing job details."""
    
    id: str
    job_type: str
    status: str
    total_items: int
    processed_items: int
    indexed_items: int
    failed_items: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class TriggerIndexingRequest(BaseModel):
    """Request schema for triggering indexing."""
    
    job_type: str = Field(default="full", description="Type of indexing job: 'github', 'discourse', 'full'")
    force_refresh: bool = Field(default=False, description="Force re-index even if recently indexed")
