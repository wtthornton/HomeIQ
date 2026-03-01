"""
Database Models and Session Management

SQLAlchemy async models for automation corpus storage.
PostgreSQL via homeiq_data DatabaseManager (standardized lifecycle).
"""

import os
from datetime import UTC, datetime

from homeiq_data import DatabaseManager
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base

# Base class for all models
Base = declarative_base()


class CommunityAutomation(Base):
    """
    Community automation storage model

    Stores normalized automation metadata from community sources.
    """
    __tablename__ = "community_automations"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Source tracking
    source = Column(String(20), nullable=False, index=True)  # 'discourse' or 'github'
    source_id = Column(String(200), nullable=False)  # Post/repo ID (unique per source)

    # Composite unique constraint: source + source_id must be unique together
    __table_args__ = (
        UniqueConstraint('source', 'source_id', name='uq_source_source_id'),
    )

    # Core fields
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)

    # Structured data (stored as JSON)
    devices = Column(JSON, nullable=False, default=list)
    integrations = Column(JSON, nullable=False, default=list)
    triggers = Column(JSON, nullable=False, default=list)
    conditions = Column(JSON, nullable=True, default=list)
    actions = Column(JSON, nullable=False, default=list)

    # Classification
    use_case = Column(String(20), nullable=False, index=True)  # energy/comfort/security/convenience
    complexity = Column(String(10), nullable=False)  # low/medium/high

    # Quality metrics
    quality_score = Column(Float, nullable=False, index=True)
    vote_count = Column(Integer, nullable=False, default=0)

    # Timestamps
    created_at = Column(DateTime, nullable=False)  # Original creation
    updated_at = Column(DateTime, nullable=False)  # Last update
    last_crawled = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))  # Last crawl

    # Additional metadata (JSON) - renamed to avoid SQLAlchemy reserved name
    extra_metadata = Column(JSON, nullable=True)

    # Blueprint flag for efficient filtering
    is_blueprint = Column(Boolean, nullable=False, default=False, index=True)

    def __repr__(self):
        return f"<CommunityAutomation(id={self.id}, title='{self.title}', quality={self.quality_score})>"


# Note: Indexes for use_case, quality_score, and source are created via index=True
# on the Column definitions above. No explicit Index() calls needed.


class MinerState(Base):
    """
    Miner state tracking

    Stores crawler state (last_crawl_timestamp, etc.)
    """
    __tablename__ = "miner_state"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))

    def __repr__(self):
        return f"<MinerState(key='{self.key}', value='{self.value}')>"


# Schema configuration
_schema = os.getenv("DATABASE_SCHEMA", "blueprints")

# Standardized database manager (lazy initialization)
db_manager = DatabaseManager(
    schema=_schema,
    service_name="automation-miner",
    auto_commit_sessions=False,
)

# Module-level alias for backwards compatibility
engine = None


async def init_db() -> bool:
    """
    Initialize database.

    Returns True if successful, False if degraded. Never raises.
    """
    global engine
    result = await db_manager.initialize(base=Base)
    engine = db_manager.engine
    return result


def get_database():
    """Get database manager instance."""
    return db_manager


def reset_database() -> None:
    """Reset the global database (for testing)."""
    pass  # DatabaseManager handles state internally


async def get_db_session():
    """Dependency for FastAPI to get database session."""
    async with db_manager.get_db() as session:
        yield session
