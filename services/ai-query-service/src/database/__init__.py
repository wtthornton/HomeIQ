"""
Database initialization and session management for AI Query Service

Epic 39, Story 39.9: Query Service Foundation
"""

import logging
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from ..config import settings

logger = logging.getLogger(__name__)

# Create async engine with connection pooling
# SQLite doesn't support pool_size/max_overflow - use StaticPool only
if "sqlite" in settings.database_url:
    # SQLite configuration (no pool_size/max_overflow)
    engine = create_async_engine(
        settings.database_url,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False,
    )
else:
    # PostgreSQL/MySQL configuration (supports pooling)
    engine = create_async_engine(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        echo=False,
    )

# Create session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """
    Dependency for getting database session.
    
    Usage:
        @router.get("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database connection and verify connectivity."""
    try:
        from sqlalchemy import text
        async with engine.begin() as conn:
            # Test connection
            await conn.execute(text("SELECT 1"))
        logger.info("✅ Database connection initialized")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise

