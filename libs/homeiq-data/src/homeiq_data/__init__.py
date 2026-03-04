"""HomeIQ data access utilities."""

__version__ = "1.0.0"

from .alembic_helpers import (
    get_alembic_config,
    run_async_migrations,
    run_migrations_on_startup,
)
from .base_settings import BaseServiceSettings
from .database_manager import DatabaseManager
from .database_pool import (
    check_pg_connection,
    close_all_engines,
    close_all_engines_async,
    create_pg_engine,
    create_shared_db_engine,
    create_shared_session_maker,
    get_database_url,
    get_pool_stats,
    get_shared_db_session,
    validate_database_url,
)
from .influxdb_manager import InfluxDBManager
from .openai_client import StandardOpenAIClient
from .standard_data_api_client import StandardDataAPIClient

__all__ = [
    "BaseServiceSettings",
    "DatabaseManager",
    "InfluxDBManager",
    "StandardDataAPIClient",
    "StandardOpenAIClient",
    "check_pg_connection",
    "close_all_engines",
    "close_all_engines_async",
    "create_pg_engine",
    "create_shared_db_engine",
    "create_shared_session_maker",
    "get_alembic_config",
    "get_database_url",
    "get_pool_stats",
    "get_shared_db_session",
    "run_async_migrations",
    "run_migrations_on_startup",
    "validate_database_url",
]
