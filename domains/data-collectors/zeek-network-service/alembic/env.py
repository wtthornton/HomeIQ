"""Alembic environment configuration for zeek-network-service.

Manages migrations in the 'devices' PostgreSQL schema.
"""

import asyncio
import os
import re
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

config = context.config

# When the service runs migrations in-process at startup, re-running
# fileConfig() would reset the root logger and silence every logger created
# before it — including uvicorn's and the service's own structured logging,
# which then goes quiet for the rest of the process's life. The caller sets
# ``configure_logger`` False; the alembic CLI leaves it unset and still gets
# the ini's logging config.
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# Override sqlalchemy.url from environment if available. The service only
# ships asyncpg, so migrations run on the async engine like data-api's do —
# no sync-driver rewrite, which would require psycopg2.
database_url = os.environ.get("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

target_metadata = None

SCHEMA = os.environ.get("DATABASE_SCHEMA", "devices")
if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", SCHEMA):
    raise ValueError(f"Invalid DATABASE_SCHEMA: {SCHEMA!r}")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema=SCHEMA,
        include_schemas=True,
    )

    with context.begin_transaction():
        context.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table_schema=SCHEMA,
        include_schemas=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))
        await connection.commit()
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
