from tests.path_setup import add_service_src

add_service_src(__file__)
"""
Shared pytest fixtures for Automation Miner service tests

Following Context7 KB best practices from /pytest-dev/pytest
"""

import os
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient

# Mark for tests that require external services (integration tests)
needs_external = pytest.mark.skipif(
    not os.getenv("AUTOMATION_MINER_TESTS"),
    reason="Requires external services (set AUTOMATION_MINER_TESTS=1 to enable)",
)


@pytest.fixture
async def client():
    """Async HTTP client for Automation Miner API"""
    from src.api.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def test_db():
    """The app's own DatabaseManager, initialised and emptied for this test.

    ``init_db`` normally runs only from the lifespan, and ``httpx.ASGITransport``
    emits no lifespan events, so ASGI-driven tests otherwise reach endpoints in
    degraded mode. Initialising the real manager (schema, search_path, tables)
    is the only way the app and the test see the same tables; a side engine
    with its own search_path writes rows the app cannot read. Function-scoped
    because each test gets its own event loop.
    """
    from src.miner.database import Base, db_manager, init_db

    if not await init_db():
        pytest.fail(
            "DatabaseManager could not initialise; set POSTGRES_URL (or DATABASE_URL) "
            "to a reachable PostgreSQL for the blueprints schema"
        )
    async with db_manager.engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())
    yield db_manager
    await db_manager.close()


@pytest.fixture
async def test_repository(test_db):
    """Test repository with database session"""
    from src.miner.repository import CorpusRepository

    async with test_db.get_db() as session:
        repo = CorpusRepository(session)
        yield repo


@pytest.fixture
def sample_automation_metadata():
    """Sample automation metadata for testing"""
    from src.miner.models import AutomationMetadata

    return AutomationMetadata(
        title="Test Automation",
        description="Test automation for unit tests",
        devices=["light", "motion_sensor"],
        integrations=["mqtt", "homeassistant"],
        triggers=[{"type": "state", "entity_id": "binary_sensor.motion"}],
        conditions=[{"condition": "time", "after": "18:00"}],
        actions=[{"service": "light.turn_on", "entity_id": "light.living_room"}],
        use_case="comfort",
        complexity="low",
        quality_score=0.85,
        vote_count=500,
        source="discourse",
        source_id="test123",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture(
    params=[
        {"device": "light", "min_quality": 0.7, "limit": 10},
        {"device": "motion_sensor", "min_quality": 0.8, "limit": 5},
        {"use_case": "security", "min_quality": 0.9, "limit": 20},
    ]
)
def search_params(request):
    """Parametrized search query fixtures"""
    return request.param


def pytest_configure(config):
    """Register custom pytest markers"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "database: Database tests")
    config.addinivalue_line("markers", "api: API tests")
    config.addinivalue_line("markers", "parser: Parser tests")
