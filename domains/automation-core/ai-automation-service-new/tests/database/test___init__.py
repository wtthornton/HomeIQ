"""
Tests for __init__.py
"""

from src.database import async_session_maker, get_db, init_db


def test_database_module_exports():
    """Test that database module exports session maker, get_db, and init_db."""
    assert async_session_maker is not None
    assert get_db is not None
    assert init_db is not None
