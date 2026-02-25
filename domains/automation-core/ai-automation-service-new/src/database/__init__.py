"""
Database initialization and connection management

Epic 39, Story 39.10: Automation Service Foundation
Database connection pooling for shared SQLite database.
Epics 3-4: Dual-mode PostgreSQL/SQLite support.
"""

import asyncio
import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..config import settings

logger = logging.getLogger("ai-automation-service")

# Determine effective database URL and backend type
_db_url = settings.effective_database_url
_is_postgres = _db_url.startswith("postgresql") or _db_url.startswith("postgres")

if _is_postgres:
    # PostgreSQL via shared library (schema isolation, real connection pool)
    from homeiq_data.database_pool import create_pg_engine

    engine = create_pg_engine(
        database_url=_db_url,
        schema=settings.database_schema,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
    )
else:
    # SQLite configuration (backward compatible - original code preserved)
    from sqlalchemy import event
    from sqlalchemy.pool import StaticPool

    engine = create_async_engine(
        _db_url,
        poolclass=StaticPool,
        connect_args={
            "check_same_thread": False,
            "timeout": 30.0,  # 30 second timeout for database operations
        },
        echo=False,
    )

    # Set PRAGMA settings on connection pool initialization
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_conn, _connection_record):
        """Set SQLite PRAGMA settings for optimal performance."""
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for concurrent reads
        cursor.execute("PRAGMA synchronous=NORMAL")  # Fast writes, survives OS crash
        cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache (negative = KB)
        cursor.execute("PRAGMA temp_store=MEMORY")  # Fast temp tables
        cursor.execute("PRAGMA foreign_keys=ON")  # Referential integrity
        cursor.execute("PRAGMA busy_timeout=30000")  # 30s lock wait (vs fail immediately)
        cursor.close()

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

    For PostgreSQL: runs Alembic migrations, tests connectivity.
    For SQLite: runs Alembic migrations, tests connectivity, performs manual schema sync.
    """
    try:
        # Step 1: Run Alembic migrations first
        await run_migrations()

        # Step 2: Test connection
        from sqlalchemy import text

        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))

            # Step 3: SQLite-only manual schema sync (fallback for missing columns)
            if not _is_postgres:
                result = await conn.execute(
                    text("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name='suggestions'
                """)
                )
                table_exists = result.scalar() is not None

                if not table_exists:
                    logger.info("Creating suggestions table (table doesn't exist)")
                    from .models import Base

                    await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn))
                    logger.info("Created suggestions table")
                else:
                    # Table exists - check which columns exist and add missing ones
                    result = await conn.execute(text("PRAGMA table_info(suggestions)"))
                    columns = result.fetchall()
                    column_names = [col[1] for col in columns]

                    required_columns = {
                        "description": "TEXT",
                        "automation_json": "TEXT",
                        "automation_yaml": "TEXT",
                        "ha_version": "TEXT",
                        "json_schema_version": "TEXT",
                        "automation_id": "TEXT",
                        "deployed_at": "TEXT",
                        "confidence_score": "REAL",
                        "safety_score": "REAL",
                        "user_feedback": "TEXT",
                        "feedback_at": "TEXT",
                        "plan_id": "TEXT",
                        "compiled_id": "TEXT",
                        "deployment_id": "TEXT",
                    }

                    for col_name, col_type in required_columns.items():
                        if col_name not in column_names:
                            logger.info(f"Adding missing '{col_name}' column to suggestions table")
                            try:
                                await conn.execute(
                                    text(f"""
                                    ALTER TABLE suggestions
                                    ADD COLUMN {col_name} {col_type}
                                """)
                                )
                                logger.info(f"Added '{col_name}' column to suggestions table")
                            except Exception as e:
                                logger.warning(f"Failed to add column '{col_name}': {e}")

        logger.info("Database connection initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        raise
