from tests.path_setup import add_service_src

add_service_src(__file__)
"""
Shared pytest fixtures for Automation Miner service tests

Following Context7 KB best practices from /pytest-dev/pytest
"""

import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient

# Mark for tests that require external services (integration tests)
needs_external = pytest.mark.skipif(
    not os.getenv("AUTOMATION_MINER_TESTS"),
    reason="Requires external services (set AUTOMATION_MINER_TESTS=1 to enable)",
)


class MinerTestDatabase:
    """The shape the fixtures were written against.

    The old ``Database`` class was replaced by the shared ``DatabaseManager``
    (which has no create_tables/drop_tables/get_session), so the fixtures'
    ``from src.miner.database import Database`` raised ImportError at
    collection time (TAP-6175). This helper owns the test lifecycle directly
    over the models' metadata.
    """

    def __init__(self, url: str):
        from sqlalchemy.ext.asyncio import (
            AsyncSession,
            async_sessionmaker,
            create_async_engine,
        )

        self.engine = create_async_engine(url, echo=False)
        self.async_session = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def create_tables(self) -> None:
        from src.miner.database import Base

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables(self) -> None:
        from src.miner.database import Base

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    @asynccontextmanager
    async def get_session(self):
        async with self.async_session() as session:
            yield session

    async def close(self) -> None:
        await self.engine.dispose()


@pytest.fixture
async def client():
    """Async HTTP client for Automation Miner API"""
    from src.api.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def test_db():
    """
    Test database with automatic setup and teardown.

    Uses PostgreSQL for test isolation.
    """
    test_url = os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://homeiq:homeiq@localhost:5432/homeiq_test",
    )
    db = MinerTestDatabase(test_url)
    await db.create_tables()
    yield db
    await db.drop_tables()
    await db.close()


@pytest.fixture
async def test_repository(test_db):
    """Test repository with database session"""
    from src.miner.repository import CorpusRepository

    async with test_db.get_session() as session:
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
