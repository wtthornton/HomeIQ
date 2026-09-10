"""
Alembic Migration Environment for automation-domain's authoring slice
Configured for async SQLAlchemy with PostgreSQL.
Uses shared helpers from homeiq_data.alembic_helpers.
"""

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import Base from our application
from src.authoring.database.models import Base  # noqa: E402

# --- Service-specific configuration ---
# AUTOMATION_DB_SCHEMA, not DATABASE_SCHEMA (TAP-7275): automation-domain runs
# three slices against three schemas in one process, so each names its own var.
# Only the authoring slice has migrations -- the agent and proactive services
# shipped empty alembic/versions/ directories.
SCHEMA_NAME = os.getenv("AUTOMATION_DB_SCHEMA", "automation")

# Resolve database URL from environment
_database_url = os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL") or ""

# Alembic Config object
config = context.config

# Override sqlalchemy.url from environment
config.set_main_option("sqlalchemy.url", _database_url)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata


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
