"""
Standardized PostgreSQL Database Lifecycle Manager

Provides a single class that encapsulates the full database lifecycle:
URL resolution, validation, engine creation with schema isolation,
async session factory, initialization with graceful degradation,
health checks, Alembic migration support, and cleanup.

Usage:
    from homeiq_data import DatabaseManager

    db = DatabaseManager(schema="energy", service_name="proactive-agent-service")

    # In lifespan:
    success = await db.initialize(base=Base)
    if not success:
        logger.warning("Starting in degraded mode")

    # In FastAPI:
    @app.get("/endpoint")
    async def endpoint(session: AsyncSession = Depends(db.get_db)):
        ...

    # Cleanup:
    await db.close()
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)

from .database_pool import create_pg_engine, get_database_url, validate_database_url

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Standardized PostgreSQL database lifecycle manager.

    Handles URL resolution, validation, engine creation with schema isolation,
    async session factory, initialization with graceful degradation,
    health checks, Alembic migration support, and cleanup.
    """

    def __init__(
        self,
        schema: str,
        service_name: str = "",
        pool_size: int = 10,
        max_overflow: int = 5,
        pool_recycle: int = 3600,
        database_url: str | None = None,
        auto_commit_sessions: bool = True,
    ):
        """
        Configure the database manager. Does NOT create the engine yet.

        Args:
            schema: PostgreSQL schema name for search_path isolation.
            service_name: Service name for logging context.
            pool_size: Connection pool size (default: 10).
            max_overflow: Max overflow connections (default: 5).
            pool_recycle: Recycle connections after N seconds (default: 3600).
            database_url: Explicit database URL override. If None, resolves
                from POSTGRES_URL -> DATABASE_URL -> default fallback.
            auto_commit_sessions: If True, get_db() auto-commits on success.
                If False, caller manages commits explicitly.
        """
        self._schema = schema
        self._service_name = service_name or schema
        self._pool_size = pool_size
        self._max_overflow = max_overflow
        self._pool_recycle = pool_recycle
        self._auto_commit = auto_commit_sessions
        self._available = False
        self._engine: AsyncEngine | None = None
        self._session_maker: async_sessionmaker[AsyncSession] | None = None

        # Resolve URL: explicit param > env vars > default
        self._url = self._resolve_url(database_url)

    def _resolve_url(self, explicit_url: str | None) -> str:
        """Resolve database URL from explicit param or environment."""
        if explicit_url and explicit_url.strip():
            return explicit_url
        return get_database_url(self._service_name)

    async def initialize(
        self,
        base=None,
        run_alembic: bool = False,
        alembic_ini_path: str | Path | None = None,
    ) -> bool:
        """
        Initialize database connection, optionally create tables and run migrations.

        NEVER raises — returns False and sets available=False on failure.
        Services should start in degraded mode when this returns False.

        Args:
            base: SQLAlchemy DeclarativeBase subclass for create_all.
                Pass None to skip table creation (e.g., Alembic-only services).
            run_alembic: If True, run Alembic migrations before table creation.
            alembic_ini_path: Path to alembic.ini file (required if run_alembic=True).

        Returns:
            True if initialization succeeded, False if degraded.
        """
        try:
            # Validate URL
            validate_database_url(self._url)

            # Create engine
            self._engine = create_pg_engine(
                database_url=self._url,
                schema=self._schema,
                pool_size=self._pool_size,
                max_overflow=self._max_overflow,
                pool_recycle=self._pool_recycle,
            )

            # Create session factory
            self._session_maker = async_sessionmaker(
                self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False,
            )

            # Test connection
            async with self._engine.begin() as conn:
                await conn.execute(text("SELECT 1"))

            # Optionally run Alembic migrations
            if run_alembic and alembic_ini_path:
                await self._run_alembic(alembic_ini_path)

            # Optionally create tables
            if base is not None:
                async with self._engine.begin() as conn:
                    await conn.run_sync(base.metadata.create_all)

            self._available = True
            logger.info(
                "DatabaseManager[%s] initialized: schema=%s",
                self._service_name,
                self._schema,
            )
            return True

        except Exception as e:
            logger.error(
                "DatabaseManager[%s] initialization failed (schema=%s): %s",
                self._service_name,
                self._schema,
                e,
                exc_info=True,
            )
            self._available = False
            return False

    async def close(self) -> None:
        """Dispose engine and clean up."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_maker = None
            self._available = False
            logger.info(
                "DatabaseManager[%s] connections closed",
                self._service_name,
            )

    @asynccontextmanager
    async def get_db(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Async context manager for database sessions.

        Compatible with both ``async with db.get_db()`` and FastAPI ``Depends()``.
        Raises RuntimeError if database is not available.
        """
        if not self._available or self._session_maker is None:
            raise RuntimeError(
                f"Database not available for {self._service_name}. "
                "Service is in degraded mode."
            )
        async with self._session_maker() as session:
            try:
                yield session
                if self._auto_commit:
                    await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    @asynccontextmanager
    async def get_db_context(self) -> AsyncGenerator[AsyncSession, None]:
        """Context manager for non-FastAPI database session usage."""
        if not self._available or self._session_maker is None:
            raise RuntimeError(
                f"Database not available for {self._service_name}. "
                "Service is in degraded mode."
            )
        async with self._session_maker() as session:
            try:
                yield session
                if self._auto_commit:
                    await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def check_health(self) -> dict:
        """
        Check database health and return status dict.

        Always returns HTTP-200-safe status. Never raises.
        """
        if not self._available or self._engine is None:
            return {
                "status": "unavailable",
                "backend": "postgresql",
                "schema": self._schema,
                "connection": "not initialized",
            }
        try:
            async with self._session_maker() as session:
                await session.execute(text("SELECT 1"))
                pool = self._engine.pool
                return {
                    "status": "healthy",
                    "backend": "postgresql",
                    "schema": self._schema,
                    "pool_size": pool.size(),
                    "pool_checked_in": pool.checkedin(),
                    "pool_checked_out": pool.checkedout(),
                    "pool_overflow": pool.overflow(),
                    "connection": "ok",
                }
        except Exception as e:
            logger.error("DatabaseManager[%s] health check failed: %s", self._service_name, e)
            return {
                "status": "unhealthy",
                "backend": "postgresql",
                "schema": self._schema,
                "connection": str(e),
            }

    @property
    def available(self) -> bool:
        """Whether the database is initialized and available."""
        return self._available

    @property
    def engine(self) -> AsyncEngine | None:
        """The underlying AsyncEngine, or None if not initialized."""
        return self._engine

    @property
    def session_maker(self) -> async_sessionmaker[AsyncSession] | None:
        """The async session maker, or None if not initialized."""
        return self._session_maker

    async def _run_alembic(self, alembic_ini_path: str | Path) -> bool:
        """Run Alembic upgrade head in a thread executor."""
        try:
            path = Path(alembic_ini_path)
            if not path.exists():
                logger.warning(
                    "DatabaseManager[%s] Alembic config not found: %s",
                    self._service_name,
                    path,
                )
                return False

            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None, self._alembic_upgrade_sync, str(path)
            )
            logger.info(
                "DatabaseManager[%s] Alembic migrations completed (schema=%s)",
                self._service_name,
                self._schema,
            )
            return True
        except Exception as e:
            logger.error(
                "DatabaseManager[%s] Alembic migration failed: %s",
                self._service_name,
                e,
                exc_info=True,
            )
            return False

    @staticmethod
    def _alembic_upgrade_sync(alembic_ini_path: str) -> None:
        """Run Alembic upgrade synchronously (called from thread executor)."""
        from alembic import command
        from alembic.config import Config

        alembic_cfg = Config(alembic_ini_path)
        command.upgrade(alembic_cfg, "head")
