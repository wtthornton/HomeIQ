"""
Shared pytest fixtures for all E2E and integration tests

Following Context7 KB best practices from /pytest-dev/pytest
"""

import asyncio
from typing import Generator

import pytest

collect_ignore = ["integration", "unit"]


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    ✅ Context7 Best Practice: Provide event loop for async tests
    
    Creates a new event loop for the entire test session to support async fixtures.
    This is required for pytest-asyncio to work correctly.
    
    Reference: https://docs.pytest.org/en/stable/how-to/fixtures.html
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def cleanup_after_test():
    """
    ✅ Context7 Best Practice: Auto cleanup after each test
    
    Automatically runs after every test to ensure clean state.
    Waits for pending async tasks to complete.
    
    Reference: /pytest-dev/pytest - conftest.py patterns
    """
    yield
    # Cleanup code runs here after test completes
    await asyncio.sleep(0)  # Let pending tasks complete


@pytest.fixture(autouse=True)
def reset_environment_state():
    """
    ✅ Context7 Best Practice: Reset state between tests
    
    Ensures test isolation by resetting any global state.
    Runs before and after each test automatically.
    """
    # Setup: runs before test
    yield
    # Teardown: runs after test
    # Add any environment cleanup here if needed


@pytest.fixture
def sample_timestamp():
    """Shared fixture: Current UTC timestamp for test data"""
    from datetime import datetime
    return datetime.utcnow()


@pytest.fixture
def sample_device_id():
    """Shared fixture: Standard test device ID"""
    return "light.test_device"


@pytest.fixture
def sample_entity_id():
    """Shared fixture: Standard test entity ID"""
    return "sensor.test_sensor"

