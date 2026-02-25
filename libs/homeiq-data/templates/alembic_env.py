"""
Alembic Environment Configuration Template
Copy this to your service's alembic/env.py and customize.

Usage:
    1. Copy to your-service/alembic/env.py
    2. Update SCHEMA_NAME to your domain schema
    3. Update the Base import to your service's models
    4. Update settings import
"""

from logging.config import fileConfig

from alembic import context

# --- CUSTOMIZE THESE ---
SCHEMA_NAME = "core"  # Change to your domain schema

# Import your service's Base and settings
# from src.models import Base
# from src.config import settings
# --- END CUSTOMIZE ---

# Alembic Config object
config = context.config

# Set up loggers from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata from your models
# target_metadata = Base.metadata
target_metadata = None  # Replace with your Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    from homeiq_data.alembic_helpers import run_migrations_offline as _run_offline

    url = config.get_main_option("sqlalchemy.url")
    _run_offline(
        target_metadata=target_metadata,
        schema_name=SCHEMA_NAME,
        database_url=url,
    )


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    from homeiq_data.alembic_helpers import run_async_migrations

    url = config.get_main_option("sqlalchemy.url")
    run_async_migrations(
        target_metadata=target_metadata,
        schema_name=SCHEMA_NAME,
        database_url=url,
    )


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
