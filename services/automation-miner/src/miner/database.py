"""
Database Models and Session Management

SQLAlchemy async models for automation corpus storage.
"""
import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from ..config import settings

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
    last_crawled = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))  # Last crawl

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
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<MinerState(key='{self.key}', value='{self.value}')>"


# Database engine and session factory
class Database:
    """Database connection manager"""

    def __init__(self, db_path: str = None):
        """
        Initialize database connection
        
        Args:
            db_path: Path to SQLite database file (default from settings)
        """
        self.db_path = db_path or settings.miner_db_path

        # Validate and create database directory if needed
        db_file = Path(self.db_path)
        db_dir = db_file.parent

        # Create directory if it doesn't exist
        if not db_dir.exists():
            try:
                db_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                raise RuntimeError(f"Failed to create database directory {db_dir}: {e}")

        # Check if directory is writable
        if not os.access(db_dir, os.W_OK):
            raise RuntimeError(f"Database directory is not writable: {db_dir}")

        # Create async engine
        self.engine = create_async_engine(
            f"sqlite+aiosqlite:///{self.db_path}",
            echo=False,  # Set to True for SQL logging
            future=True
        )

        # Create async session factory
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    async def create_tables(self):
        """Create all tables (for testing/initialization)"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables(self):
        """Drop all tables (for testing)"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def close(self):
        """Close database connection"""
        await self.engine.dispose()

    def get_session(self) -> AsyncSession:
        """Get new async session"""
        return self.async_session()


# Global database instance
_db: Database | None = None


def get_database(db_path: str | None = None) -> Database:
    """Get database instance. Uses singleton for default path, new instance for custom paths."""
    if db_path:
        return Database(db_path)
    global _db
    if _db is None:
        _db = Database()
    return _db


def reset_database() -> None:
    """Reset the global database singleton (for testing)."""
    global _db
    _db = None


async def get_db_session():
    """
    Dependency for FastAPI to get database session
    
    Usage:
        @app.get("/...")
        async def endpoint(db: AsyncSession = Depends(get_db_session)):
            ...
    """
    db = get_database()
    async with db.get_session() as session:
        yield session

