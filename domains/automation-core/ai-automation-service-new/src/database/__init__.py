"""
Database initialization and connection management

Epic 39, Story 39.10: Automation Service Foundation
PostgreSQL connection pooling via homeiq_data shared library.
"""

import asyncio
import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from homeiq_data.database_pool import create_pg_engine

from ..config import settings

logger = logging.getLogger("ai-automation-service")

# PostgreSQL engine via shared library (schema isolation, real connection pool)
_db_url = settings.effective_database_url

engine = create_pg_engine(
    database_url=_db_url,
    schema=settings.database_schema,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
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

    M9 fix: No longer auto-commits. Service methods should manage their own
    transactions explicitly via session.commit(). The session auto-rolls back
    on exception and closes in the finally block.
    """
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def _run_alembic_upgrade(alembic_ini_path: str) -> None:
    """Run Alembic upgrade synchronously (called from thread executor)."""
    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config(alembic_ini_path)
    command.upgrade(alembic_cfg, "head")


async def run_migrations():
    """
    Run Alembic migrations to ensure database schema is up to date.

    M8 fix: Runs the synchronous Alembic command in a thread executor
    to avoid blocking the async event loop.
    """
    try:
        # Get the service directory (parent of src/)
        service_dir = Path(__file__).parent.parent.parent
        alembic_ini_path = service_dir / "alembic.ini"

        if not alembic_ini_path.exists():
            logger.warning(f"Alembic config not found at {alembic_ini_path}, skipping migrations")
            return

        # Run migrations in a thread executor to avoid blocking the event loop
        logger.info("Running Alembic migrations...")
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _run_alembic_upgrade, str(alembic_ini_path))
        logger.info("Alembic migrations completed")
    except Exception as e:
        logger.error(f"Failed to run Alembic migrations: {e}", exc_info=True)
        # Don't raise - fallback to manual schema sync
        logger.warning("Will attempt manual schema sync as fallback")


async def init_db():
    """
    Initialize database connection and verify connectivity.

    Runs Alembic migrations and tests connectivity.
    """
    try:
        # Step 1: Run Alembic migrations first
        await run_migrations()

        # Step 2: Test connection
        from sqlalchemy import text

        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))

        logger.info("Database connection initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        raise
