"""
Database initialization and connection management

Epic 39, Story 39.10: Automation Service Foundation
PostgreSQL connection pooling via homeiq_data DatabaseManager.
"""

import asyncio
import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from homeiq_data import DatabaseManager

from ..config import settings

logger = logging.getLogger("ai-automation-service")

# Standardized database manager (lazy initialization)
db = DatabaseManager(
    schema=settings.database_schema,
    service_name="ai-automation-service",
    database_url=settings.effective_database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    auto_commit_sessions=False,  # M9 fix: service manages its own commits
)

# Module-level aliases for backwards compatibility
engine = None
async_session_maker = None


async def get_db() -> AsyncSession:
    """
    Dependency for getting database session.

    M9 fix: No longer auto-commits. Service methods should manage their own
    transactions explicitly via session.commit(). The session auto-rolls back
    on exception and closes in the finally block.
    """
    async with db.get_db() as session:
        yield session


async def run_migrations():
    """Run Alembic migrations to ensure database schema is up to date."""
    service_dir = Path(__file__).parent.parent.parent
    alembic_ini_path = service_dir / "alembic.ini"
    if not alembic_ini_path.exists():
        logger.warning("Alembic config not found at %s, skipping migrations", alembic_ini_path)
        return
    try:
        logger.info("Running Alembic migrations...")
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _run_alembic_upgrade, str(alembic_ini_path))
        logger.info("Alembic migrations completed")
    except Exception as e:
        logger.error("Failed to run Alembic migrations: %s", e, exc_info=True)
        logger.warning("Will attempt manual schema sync as fallback")


def _run_alembic_upgrade(alembic_ini_path: str) -> None:
    """Run Alembic upgrade synchronously (called from thread executor)."""
    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config(alembic_ini_path)
    command.upgrade(alembic_cfg, "head")


async def init_db() -> bool:
    """
    Initialize database connection and verify connectivity.

    Runs Alembic migrations and tests connectivity.
    Returns True if successful, False if degraded. Never raises.
    """
    global engine, async_session_maker

    # Run Alembic migrations first (non-fatal)
    await run_migrations()

    # Initialize via DatabaseManager
    result = await db.initialize()
    engine = db.engine
    async_session_maker = db.session_maker
    return result
