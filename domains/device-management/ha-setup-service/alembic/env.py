"""
Alembic Migration Environment for ha-setup-service
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

from src.config import get_settings  # noqa: E402
from src.database import Base  # noqa: E402
from src.models import (  # noqa: E402, F401
    EnvironmentHealth,
    IntegrationBlocker,
    IntegrationHealth,
    PerformanceMetric,
    SetupWizardSession,
)

# --- Service-specific configuration ---
SCHEMA_NAME = os.getenv("DATABASE_SCHEMA", "devices")

# This service shares the `devices` schema with zeek-network-service, which has
# its own migration chain and is already at its revision 004 in the default
# `alembic_version` table. Sharing that table would make alembic look for
# *this* chain's revision 004, fail to find it, and refuse to run. Each service
# therefore owns a version table named after itself.
VERSION_TABLE = "alembic_version_ha_setup"
settings = get_settings()

# Resolve database URL from environment
_database_url = os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL") or settings.database_url

# Alembic Config object
config = context.config

# Override sqlalchemy.url from settings so Alembic uses the same database
config.set_main_option("sqlalchemy.url", _database_url)

# When the service runs migrations in-process at startup, re-running
# fileConfig() would reset the root logger and silence every logger created
# before it — including uvicorn's and the service's own structured logging,
# which then goes quiet for the rest of the process's life. The caller sets
# ``configure_logger`` False; the alembic CLI leaves it unset and still gets
# the ini's logging config.
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# Set target metadata from models
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    from homeiq_data.alembic_helpers import run_migrations_offline as _run_offline

    url = config.get_main_option("sqlalchemy.url")
    _run_offline(
        target_metadata=target_metadata,
        schema_name=SCHEMA_NAME,
        database_url=url,
        version_table=VERSION_TABLE,
    )


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    from homeiq_data.alembic_helpers import run_async_migrations

    url = config.get_main_option("sqlalchemy.url")
    run_async_migrations(
        target_metadata=target_metadata,
        schema_name=SCHEMA_NAME,
        database_url=url,
        version_table=VERSION_TABLE,
    )


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
