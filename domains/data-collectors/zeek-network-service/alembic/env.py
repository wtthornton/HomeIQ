"""Alembic environment configuration for zeek-network-service.

Manages migrations in the 'devices' PostgreSQL schema.
"""

import os
import re
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text
from sqlalchemy.engine import make_url

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url from environment if available
database_url = os.environ.get("DATABASE_URL")
if database_url:
    # Use sqlalchemy.engine.make_url for reliable driver replacement
    url = make_url(database_url)
    sync_url = url.set(drivername="postgresql")
    config.set_main_option("sqlalchemy.url", str(sync_url))

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


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))
        connection.commit()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=SCHEMA,
            include_schemas=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
