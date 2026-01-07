"""SQLAlchemy models for Blueprint Index Service."""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    Index,
)
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all models."""
    pass


class IndexedBlueprint(Base):
    """
    Represents an indexed Home Assistant blueprint.
    
    Stores blueprint metadata, device requirements, and community metrics
    for efficient searching and matching.
    """
    __tablename__ = "indexed_blueprints"
    
    # Primary key - unique blueprint identifier
    id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Source information
    source_url = Column(String(1024), nullable=False, unique=True)
    source_type = Column(String(50), nullable=False)  # 'github', 'discourse', 'manual'
    source_id = Column(String(255))  # External ID from source
    
    # Blueprint metadata
    name = Column(String(255), nullable=False)
    description = Column(Text)
    domain = Column(String(50), default="automation")  # 'automation', 'script', 'template'
    
    # Device requirements (JSON arrays for flexible querying)
    required_domains = Column(JSON, default=list)  # ["binary_sensor", "light"]
    required_device_classes = Column(JSON, default=list)  # ["motion", "door"]
    optional_domains = Column(JSON, default=list)
    optional_device_classes = Column(JSON, default=list)
    
    # Input definitions (full blueprint input schema)
    inputs = Column(JSON, default=dict)
    
    # Trigger/Action metadata for pattern matching
    trigger_platforms = Column(JSON, default=list)  # ["state", "time", "event"]
    action_services = Column(JSON, default=list)  # ["light.turn_on", "notify.mobile"]
    
    # Use case classification
    use_case = Column(String(50))  # 'energy', 'comfort', 'security', 'convenience'
    tags = Column(JSON, default=list)
    
    # Community metrics
    stars = Column(Integer, default=0)
    downloads = Column(Integer, default=0)
    installs = Column(Integer, default=0)
    community_rating = Column(Float, default=0.0)
    vote_count = Column(Integer, default=0)
    
    # Quality metrics
    quality_score = Column(Float, default=0.5)
    complexity = Column(String(20), default="medium")  # 'low', 'medium', 'high'
    has_description = Column(Boolean, default=False)
    has_inputs = Column(Boolean, default=False)
    
    # Author and version
    author = Column(String(255))
    ha_min_version = Column(String(20))
    ha_max_version = Column(String(20))
    blueprint_version = Column(String(20))
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    indexed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_checked_at = Column(DateTime)
    
    # Full YAML content
    yaml_content = Column(Text)
    
    # Relationships
    inputs_rel = relationship("BlueprintInput", back_populates="blueprint", cascade="all, delete-orphan")
    
    # Indexes for efficient querying
    __table_args__ = (
        Index("ix_blueprints_domain", "domain"),
        Index("ix_blueprints_use_case", "use_case"),
        Index("ix_blueprints_quality_score", "quality_score"),
        Index("ix_blueprints_community_rating", "community_rating"),
        Index("ix_blueprints_source_type", "source_type"),
    )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "source_url": self.source_url,
            "source_type": self.source_type,
            "name": self.name,
            "description": self.description,
            "domain": self.domain,
            "required_domains": self.required_domains or [],
            "required_device_classes": self.required_device_classes or [],
            "optional_domains": self.optional_domains or [],
            "optional_device_classes": self.optional_device_classes or [],
            "inputs": self.inputs or {},
            "trigger_platforms": self.trigger_platforms or [],
            "action_services": self.action_services or [],
            "use_case": self.use_case,
            "tags": self.tags or [],
            "stars": self.stars,
            "downloads": self.downloads,
            "installs": self.installs,
            "community_rating": self.community_rating,
            "quality_score": self.quality_score,
            "complexity": self.complexity,
            "author": self.author,
            "ha_min_version": self.ha_min_version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class BlueprintInput(Base):
    """
    Represents a single input parameter for a blueprint.
    
    Normalized table for efficient querying by input requirements.
    """
    __tablename__ = "blueprint_inputs"
    
    id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    blueprint_id = Column(String(255), ForeignKey("indexed_blueprints.id", ondelete="CASCADE"), nullable=False)
    
    # Input definition
    input_name = Column(String(255), nullable=False)
    input_type = Column(String(50))  # 'entity', 'device', 'target', 'text', 'number', etc.
    description = Column(Text)
    
    # Entity/Device requirements
    domain = Column(String(50))  # Required entity domain
    device_class = Column(String(50))  # Required device class
    
    # Selector info
    selector_type = Column(String(50))  # 'entity', 'device', 'target', 'number', 'text', etc.
    selector_config = Column(JSON)  # Full selector configuration
    
    # Default value
    default_value = Column(Text)
    is_required = Column(Boolean, default=True)
    
    # Relationship
    blueprint = relationship("IndexedBlueprint", back_populates="inputs_rel")
    
    __table_args__ = (
        Index("ix_inputs_blueprint_id", "blueprint_id"),
        Index("ix_inputs_domain", "domain"),
        Index("ix_inputs_device_class", "device_class"),
    )


class IndexingJob(Base):
    """
    Tracks indexing job status and history.
    """
    __tablename__ = "indexing_jobs"
    
    id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Job info
    job_type = Column(String(50), nullable=False)  # 'github', 'discourse', 'full'
    status = Column(String(20), default="pending")  # 'pending', 'running', 'completed', 'failed'
    
    # Progress
    total_items = Column(Integer, default=0)
    processed_items = Column(Integer, default=0)
    indexed_items = Column(Integer, default=0)
    failed_items = Column(Integer, default=0)
    
    # Timestamps
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Error info
    error_message = Column(Text)
    error_details = Column(JSON)
    
    # Configuration
    config = Column(JSON)  # Job-specific configuration
