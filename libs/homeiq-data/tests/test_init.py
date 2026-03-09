"""Tests for homeiq_data package initialization and public API."""

from __future__ import annotations

import importlib


def test_package_imports() -> None:
    """All public symbols should be importable from the top-level package."""
    import homeiq_data

    expected_exports = [
        "BaseServiceSettings",
        "DatabaseManager",
        "StandardDataAPIClient",
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
    for name in expected_exports:
        assert hasattr(homeiq_data, name), f"Missing export: {name}"


def test_all_attribute() -> None:
    """__all__ should match the expected export count."""
    import homeiq_data

    assert hasattr(homeiq_data, "__all__")
    assert len(homeiq_data.__all__) == 18


def test_version_attribute() -> None:
    """Package should expose a __version__ string."""
    import homeiq_data

    assert hasattr(homeiq_data, "__version__")
    assert isinstance(homeiq_data.__version__, str)


def test_module_reimport() -> None:
    """Re-importing the package should return the cached module."""
    import homeiq_data

    mod = importlib.import_module("homeiq_data")
    assert mod is homeiq_data


def test_validate_database_url_rejects_empty() -> None:
    """validate_database_url should raise ValueError on empty input."""
    import pytest
    from homeiq_data import validate_database_url

    with pytest.raises(ValueError, match="empty"):
        validate_database_url("")


def test_validate_database_url_rejects_non_postgres() -> None:
    """validate_database_url should reject non-PostgreSQL URLs."""
    import pytest
    from homeiq_data import validate_database_url

    with pytest.raises(ValueError, match="Not a PostgreSQL"):
        validate_database_url("sqlite:///test.db")


def test_validate_database_url_accepts_postgres() -> None:
    """validate_database_url should accept valid PostgreSQL URLs."""
    from homeiq_data import validate_database_url

    url = "postgresql+asyncpg://user:pass@localhost:5432/db"
    assert validate_database_url(url) == url
