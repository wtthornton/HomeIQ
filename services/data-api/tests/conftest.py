from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio

# Set test database URL BEFORE any imports
# This ensures the database module uses in-memory database for tests
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
# Allow data-api to start without DATA_API_API_KEY (for test_main and app imports)
os.environ.setdefault("DATA_API_ALLOW_ANONYMOUS", "true")

# Load path_setup dynamically
def _load_add_service_src():
    repo_root = Path(__file__).resolve().parents[3]
    path_setup = repo_root / "tests" / "path_setup.py"
    spec = importlib.util.spec_from_file_location("repo_tests.path_setup", path_setup)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load shared test path utilities")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.add_service_src

add_service_src = _load_add_service_src()
add_service_src(__file__)

"""
Shared pytest fixtures for Data API service tests

Following Context7 KB best practices from /pytest-dev/pytest
"""

ROOT_DIR = Path(__file__).resolve().parents[3]
sys.path.append(str(ROOT_DIR))
from datetime import datetime
from unittest.mock import patch

from httpx import ASGITransport, AsyncClient

# Only skip integration tests, not unit tests
# Unit tests should run without external services
# Integration tests can check for DATA_API_TESTS env var individually


# ✅ Context7 Best Practice: Shared async HTTP client fixture
@pytest_asyncio.fixture
async def client():
    """
    Async HTTP client for testing Data API endpoints
    
    Automatically closes connection after test completes.
    Use with async tests: async def test_endpoint(client):
    """
    from src.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ✅ Context7 Best Practice: Shared mock fixture with cleanup
@pytest.fixture
def mock_influxdb():
    """
    Mock InfluxDB client for testing without database dependency
    
    Automatically cleaned up after each test.
    """
    with patch('shared.influxdb_query_client.InfluxDBQueryClient') as mock:
        mock.return_value.connect.return_value = True
        mock.return_value.query.return_value = []
        yield mock


# ✅ Context7 Best Practice: Shared SQLite mock fixture
@pytest.fixture
def mock_sqlite():
    """Mock SQLite database for testing"""
    with patch('src.database.get_session') as mock:
        yield mock


# ✅ Context7 Best Practice: Fresh database for each test
@pytest_asyncio.fixture(autouse=True)
async def fresh_db():
    """
    Create a fresh in-memory database for each test.
    Ensures tests don't interfere with each other and use latest schema.
    """
    from src.database import Base, async_engine

    # Register all models with Base before create_all (else entities, devices, etc. missing)
    import src.models  # noqa: F401

    # Drop all tables first, then create fresh schema
    async with async_engine.begin() as conn:
        # Drop all tables (if they exist)
        await conn.run_sync(Base.metadata.drop_all)
        # Create all tables with latest schema
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Cleanup: Delete all data but keep table structure
    # This preserves the SQLAlchemy mapping while clearing test data
    async with async_engine.begin() as conn:
        # Delete all rows from all tables
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


# ✅ Context7 Best Practice: Shared test data fixtures
@pytest.fixture
async def sample_event_data():
    """Sample Home Assistant event data for testing"""
    return {
        'entity_id': 'light.living_room',
        'state': 'on',
        'timestamp': datetime.utcnow(),
        'attributes': {
            'brightness': 255,
            'color_temp': 370
        }
    }


@pytest.fixture
async def sample_device_data():
    """Sample device data for testing"""
    return {
        'id': 'test-device-1',
        'name': 'Test Light',
        'model': 'Smart Bulb v2',
        'manufacturer': 'Test Co',
        'sw_version': '1.0.0'
    }


@pytest.fixture
async def sample_stats_data():
    """Sample statistics data for testing"""
    return {
        'total_events': 12345,
        'events_per_minute': 42,
        'error_rate': 0.01,
        'uptime_seconds': 86400
    }


# ✅ Context7 Best Practice: Pytest markers for test organization
def pytest_configure(config):
    """Register custom pytest markers"""
    config.addinivalue_line("markers", "unit: Unit tests for isolated components")
    config.addinivalue_line("markers", "integration: Integration tests with dependencies")
    config.addinivalue_line("markers", "slow: Slow-running tests (>1s)")
    config.addinivalue_line("markers", "database: Tests requiring database access")
    config.addinivalue_line("markers", "api: API endpoint tests")

