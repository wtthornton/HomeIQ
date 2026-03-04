"""
Common utilities for PostgreSQL database operations.
"""
from typing import Optional

from .config import DATABASE_CONFIGS, POSTGRES_URL


def get_postgres_url() -> str:
    """Get PostgreSQL connection URL."""
    return POSTGRES_URL


def get_database_config(db_key: str) -> Optional[dict]:
    """Get database configuration by key."""
    return DATABASE_CONFIGS.get(db_key)


def get_database_schema(db_key: str) -> Optional[str]:
    """Get the PostgreSQL schema for a database key."""
    config = DATABASE_CONFIGS.get(db_key)
    if config:
        return config.get('schema')
    return None


def list_all_databases() -> list[str]:
    """List all available database keys."""
    return list(DATABASE_CONFIGS.keys())
