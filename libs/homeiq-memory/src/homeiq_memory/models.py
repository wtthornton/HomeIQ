"""
SQLAlchemy models for HomeIQ Memory Brain.

Provides persistent storage for semantic memories with confidence decay,
vector embeddings for similarity search, and full audit trail.

Schema: memory (PostgreSQL schema isolation)
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all memory models."""

    pass


class MemoryType(str, Enum):
    """Classification of memory content type."""

    BEHAVIORAL = "behavioral"
    PREFERENCE = "preference"
    BOUNDARY = "boundary"
    OUTCOME = "outcome"
    ROUTINE = "routine"


class SourceChannel(str, Enum):
    """How the memory was acquired."""

    EXPLICIT = "explicit"
    IMPLICIT = "implicit"
    SYNTHESIZED = "synthesized"


class Memory(Base):
    """
    Core memory storage model.

    Stores semantic memories with vector embeddings for similarity search,
    confidence scores with decay, and full provenance tracking.

    Indexes (create in migrations):
        - idx_memories_memory_type: (memory_type) for filtering by type
        - idx_memories_confidence: (confidence DESC) for confidence-based queries
        - idx_memories_created_at: (created_at DESC) for recency queries
        - idx_memories_entity_ids: GIN index on entity_ids array
        - idx_memories_area_ids: GIN index on area_ids array
        - idx_memories_tags: GIN index on tags array
        - idx_memories_embedding: HNSW index on embedding for vector search
        - idx_memories_source_channel: (source_channel) for filtering by source
        - idx_memories_superseded_by: (superseded_by) for chain traversal
    """

    __tablename__ = "memories"
    __table_args__ = {"schema": "memory"}

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    content: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
    )
    memory_type: Mapped[MemoryType] = mapped_column(
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.5,
    )
    source_channel: Mapped[SourceChannel] = mapped_column(
        nullable=False,
    )
    source_service: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    entity_ids: Mapped[list[str] | None] = mapped_column(
        ARRAY(String),
        nullable=True,
    )
    area_ids: Mapped[list[str] | None] = mapped_column(
        ARRAY(String),
        nullable=True,
    )
    domain: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
        index=True,
    )
    tags: Mapped[list[str] | None] = mapped_column(
        ARRAY(String),
        nullable=True,
    )
    embedding: Mapped[Any | None] = mapped_column(
        Vector(384),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    last_accessed: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    access_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )
    superseded_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("memory.memories.id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<Memory(id={self.id}, type={self.memory_type.value}, "
            f"confidence={self.confidence:.2f})>"
        )


class MemoryArchive(Base):
    """
    Archive storage for superseded or expired memories.

    Maintains full history of memory evolution for audit and potential restoration.
    Same schema as Memory for seamless migration between tables.

    Indexes (create in migrations):
        - idx_memory_archive_original_id: (original_id) for lookup
        - idx_memory_archive_archived_at: (archived_at DESC) for recency
        - idx_memory_archive_archive_reason: (archive_reason) for filtering
    """

    __tablename__ = "memory_archive"
    __table_args__ = {"schema": "memory"}

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    original_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
    )
    memory_type: Mapped[MemoryType] = mapped_column(
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.5,
    )
    source_channel: Mapped[SourceChannel] = mapped_column(
        nullable=False,
    )
    source_service: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    entity_ids: Mapped[list[str] | None] = mapped_column(
        ARRAY(String),
        nullable=True,
    )
    area_ids: Mapped[list[str] | None] = mapped_column(
        ARRAY(String),
        nullable=True,
    )
    domain: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )
    tags: Mapped[list[str] | None] = mapped_column(
        ARRAY(String),
        nullable=True,
    )
    embedding: Mapped[Any | None] = mapped_column(
        Vector(384),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    last_accessed: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    access_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )
    superseded_by: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
    )
    archived_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    archive_reason: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    def __repr__(self) -> str:
        return (
            f"<MemoryArchive(id={self.id}, original_id={self.original_id}, "
            f"type={self.memory_type.value})>"
        )
