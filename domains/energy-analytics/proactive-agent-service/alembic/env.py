"""
Alembic Migration Environment for proactive-agent-service
Configured for async SQLAlchemy with dual-mode support (PostgreSQL + SQLite).
Uses shared helpers from homeiq_data.alembic_helpers.
"""

import os
import sys
from logging.config import fileConfig

from alembic import context

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.config import Settings  # noqa: E402
from src.database import Base  # noqa: E402
from src.models import InvalidSuggestionReport, Suggestion  # noqa: E402, F401

# --- Service-specific configuration ---
SCHEMA_NAME = os.getenv("DATABASE_SCHEMA", "energy")
settings = Settings()

# Resolve database URL: prefer PostgreSQL, fall back to SQLite
_pg_url = os.getenv("POSTGRES_URL") or ""
_is_postgres = _pg_url.startswith("postgresql") or _pg_url.startswith("postgres")
_database_url = _pg_url if _is_postgres else settings.database_url

# Alembic Config object
config = context.config

# Override sqlalchemy.url from settings so Alembic uses the same database
config.set_main_option("sqlalchemy.url", _database_url)

# Set up loggers from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

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
