"""Pytest hooks for ha-ai-agent-service tests.

`main.py` instantiates Settings at import time and lifespan requires a non-empty
OPENAI_API_KEY. CI and local runs without .env must still load the app for ASGI tests.
"""

from __future__ import annotations

import os

if not os.environ.get("OPENAI_API_KEY", "").strip():
    os.environ["OPENAI_API_KEY"] = "sk-test-not-real-key-for-pytest"


import pytest_asyncio


@pytest_asyncio.fixture(autouse=True)
async def _database():
    """Open a clean database for every test, then close it.

    Nothing else does. ``init_database`` runs only from the service lifespan,
    and ``httpx.ASGITransport`` does not emit lifespan events, so ASGI-driven
    tests reached endpoints in degraded mode while tests calling the services
    directly had no initialization at all. Both answered
    ``RuntimeError: Database not available for ha-ai-agent-service``.

    Function-scoped on purpose. ``DatabaseManager.initialize`` disposes any
    existing engine and builds a new one, and pytest-asyncio gives each test its
    own event loop -- a session-scoped engine stays bound to the loop that
    created it and fails everywhere else with "attached to a different loop".

    Rows are cleared rather than tables dropped: ``initialize`` already ran
    ``create_all``, and leftover rows made tests collide on fixed primary keys
    such as ``conversation_id='test-id-123'``.
    """
    from src.database import Base, close_database, db, init_database

    if await init_database():
        async with db.engine.begin() as conn:
            for table in reversed(Base.metadata.sorted_tables):
                await conn.execute(table.delete())
    yield
    await close_database()
