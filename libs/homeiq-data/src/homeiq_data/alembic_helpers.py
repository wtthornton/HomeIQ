"""
Shared Alembic Helpers for Schema-Per-Domain Migrations

Provides reusable migration utilities for HomeIQ services that use
PostgreSQL with schema isolation. Each service runs its own Alembic
migrations within its assigned schema.

Usage in a service's alembic/env.py:
    from homeiq_data.alembic_helpers import run_async_migrations

    def run_migrations_online():
        run_async_migrations(
            target_metadata=Base.metadata,
            schema_name="core",
            database_url=settings.database_url,
        )
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from alembic import context
from alembic.config import Config
from sqlalchemy import pool, text
from sqlalchemy.ext.asyncio import create_async_engine

logger = logging.getLogger(__name__)


def run_migrations_offline(
    target_metadata,
    schema_name: str,
    database_url: str,
) -> None:
    """
    Run migrations in 'offline' mode (generates SQL without connecting).

    Args:
        target_metadata: SQLAlchemy MetaData with model definitions
        schema_name: PostgreSQL schema to target
        database_url: Database connection URL
    """
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema=schema_name,
        include_schemas=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_async_migrations(
    target_metadata,
    schema_name: str,
    database_url: str,
    version_table: str = "alembic_version",
) -> None:
    """
    Run async migrations online against a PostgreSQL schema.

    This is the main entry point for service-level alembic/env.py files.
    It creates an async engine, sets the search_path to the target schema,
    and runs all pending migrations.

    Args:
        target_metadata: SQLAlchemy MetaData with model definitions
        schema_name: PostgreSQL schema for this service's tables
        database_url: PostgreSQL connection URL
        version_table: Name of the Alembic version table
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(
                asyncio.run,
                _run_async_migrations(
                    target_metadata, schema_name, database_url, version_table
                ),
            )
            future.result()
    else:
        asyncio.run(
            _run_async_migrations(
                target_metadata, schema_name, database_url, version_table
            )
        )


async def _run_async_migrations(
    target_metadata,
    schema_name: str,
    database_url: str,
    version_table: str,
) -> None:
    """Internal async migration runner."""
    engine = create_async_engine(
        database_url,
        poolclass=pool.NullPool,
    )

    async with engine.connect() as connection:
        await connection.execute(
            text("SET search_path TO :schema, public"),
            {"schema": schema_name},
        )
        await connection.commit()

        await connection.run_sync(
            _do_run_migrations,
            target_metadata=target_metadata,
            schema_name=schema_name,
            version_table=version_table,
        )

    await engine.dispose()


def _do_run_migrations(
    connection,
    target_metadata,
    schema_name: str,
    version_table: str,
) -> None:
    """Synchronous migration execution within an async connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table=version_table,
        version_table_schema=schema_name,
        include_schemas=True,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.execute(f"SET search_path TO {schema_name}, public")
        context.run_migrations()


async def run_migrations_on_startup(
    _target_metadata,
    schema_name: str,
    database_url: str,
) -> None:
    """
    Run pending Alembic migrations on service startup.

    Call this from your FastAPI lifespan or startup event to ensure
    the database schema is up-to-date before handling requests.

    Args:
        target_metadata: SQLAlchemy MetaData with model definitions
        schema_name: PostgreSQL schema for this service
        database_url: PostgreSQL connection URL
    """
    logger.info("Running startup migrations for schema '%s'...", schema_name)

    try:
        engine = create_async_engine(database_url, poolclass=pool.NullPool)

        async with engine.begin() as conn:
            await conn.execute(
                text("CREATE SCHEMA IF NOT EXISTS :schema"),
                {"schema": schema_name},
            )
            logger.info("Schema '%s' verified/created", schema_name)

        await engine.dispose()
        logger.info("Startup migrations complete for schema '%s'", schema_name)
    except Exception:
        logger.exception(
            "Startup migration failed for schema '%s'", schema_name
        )
        raise


def get_alembic_config(
    service_dir: str,
    schema_name: str,
    database_url: str | None = None,
) -> Config:
    """
    Build an Alembic Config object for a service.

    Args:
        service_dir: Path to the service directory containing alembic/
        schema_name: PostgreSQL schema name
        database_url: Optional database URL override

    Returns:
        Configured Alembic Config object
    """
    alembic_ini = str(Path(service_dir) / "alembic.ini")
    config = Config(alembic_ini)

    if database_url:
        config.set_main_option("sqlalchemy.url", database_url)

    config.set_main_option("version_table_schema", schema_name)

    return config
