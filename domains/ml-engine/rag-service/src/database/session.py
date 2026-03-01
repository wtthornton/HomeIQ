"""
Database Session Management

Provides async database session factory and initialization.
PostgreSQL via homeiq_data DatabaseManager (standardized lifecycle).
"""

import logging
import os

from homeiq_data import DatabaseManager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base

logger = logging.getLogger(__name__)

# Base class for database models
Base = declarative_base()

# Schema configuration
_schema = os.getenv("DATABASE_SCHEMA", "rag")

# Standardized database manager (lazy initialization)
db = DatabaseManager(
    schema=_schema,
    service_name="rag-service",
    auto_commit_sessions=False,
)

# Module-level aliases for backwards compatibility
engine = None
async_session_maker = None


async def get_db() -> AsyncSession:
    """Dependency function to get database session."""
    async with db.get_db() as session:
        yield session


async def init_db() -> bool:
    """
    Initialize database (create tables).

    Returns True if successful, False if degraded. Never raises.
    """
    global engine, async_session_maker

    # Import models to ensure they're registered with Base
    from .models import RAGKnowledge  # noqa: F401

    result = await db.initialize(base=Base)
    engine = db.engine
    async_session_maker = db.session_maker
    return result
