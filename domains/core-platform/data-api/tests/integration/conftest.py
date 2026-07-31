"""Fixtures for data-api integration tests.

`test_db` is requested by every test in this package but was never defined
anywhere, so the whole module errored at setup and never ran.
"""

from __future__ import annotations

import pytest_asyncio


@pytest_asyncio.fixture
async def test_db():
    """Yield an AsyncSession bound to the test database.

    The session is rolled back afterwards so integration tests do not leak
    rows into each other. Schema creation is handled by the autouse `fresh_db`
    fixture in the parent conftest.
    """
    import src.database as database

    if database.AsyncSessionLocal is None:
        import pytest

        pytest.skip("PostgreSQL not available for data-api integration tests")

    async with database.AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()
