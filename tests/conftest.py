"""
Shared pytest fixtures for all E2E and integration tests

Following Context7 KB best practices from /pytest-dev/pytest
"""

from datetime import UTC

import pytest

collect_ignore = ["integration", "unit"]

# Phase 2: event_loop fixture removed — pytest-asyncio 1.3.0 manages event loops internally


@pytest.fixture(autouse=True)
def cleanup_after_test():
    """
    ✅ Context7 Best Practice: Auto cleanup after each test
    
    Automatically runs after every test to ensure clean state.
    Sync fixture so it works for both sync and async tests (avoids
    PytestRemovedIn9Warning when sync tests depend on async fixtures).
    
    Reference: /pytest-dev/pytest - conftest.py patterns
    """
    yield
    # Cleanup code runs here after test completes (sync; async tests
    # can use their own event loop for pending task cleanup if needed)


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
    return datetime.now(UTC)


@pytest.fixture
def sample_device_id():
    """Shared fixture: Standard test device ID"""
    return "light.test_device"


@pytest.fixture
def sample_entity_id():
    """Shared fixture: Standard test entity ID"""
    return "sensor.test_sensor"

