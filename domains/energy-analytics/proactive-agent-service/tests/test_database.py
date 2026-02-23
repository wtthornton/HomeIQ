"""
Tests for database initialization and session management
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from src.database import get_async_session_maker, init_database
from src.config import Settings


def test_get_async_session_maker_returns_none_before_init():
    """Test that get_async_session_maker returns None before database initialization"""
    # Ensure database is not initialized by patching the global variable
    with patch('src.database._async_session_maker', None):
        session_maker = get_async_session_maker()
        assert session_maker is None


@pytest.mark.asyncio
async def test_get_async_session_maker_returns_maker_after_init():
    """Test that get_async_session_maker returns session maker after initialization"""
    # Create test settings
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        log_level="INFO",
    )
    
    # Initialize database
    await init_database(settings)
    
    # Get session maker
    session_maker = get_async_session_maker()
    
    # Verify it's not None
    assert session_maker is not None
    # Verify it's callable (session factory)
    assert callable(session_maker)
