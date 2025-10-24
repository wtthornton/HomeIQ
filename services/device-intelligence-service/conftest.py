"""
Device Intelligence Service - Test Configuration

Test configuration and fixtures for pytest.
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from src.main import app
from src.core.database import initialize_database
from src.config import Settings

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def test_settings():
    """Get test settings with in-memory database."""
    return Settings(
        SQLITE_DATABASE_URL="sqlite+aiosqlite:///:memory:",
        HA_URL="http://test-ha:8123",
        HA_TOKEN="test-token",
        MQTT_BROKER="mqtt://test-mqtt:1883",
        LOG_LEVEL="DEBUG"
    )

@pytest.fixture(scope="session")
async def initialized_app(test_settings):
    """Initialize the app with database for testing."""
    await initialize_database(test_settings)
    return app

@pytest.fixture
def client(initialized_app):
    """Create test client."""
    return TestClient(initialized_app)
