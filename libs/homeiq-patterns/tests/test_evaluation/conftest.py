"""Conftest for evaluation tests — skip DB-dependent tests when PostgreSQL is unavailable."""

import asyncio

import pytest

_pg_available = None


def _check_pg():
    global _pg_available
    if _pg_available is not None:
        return _pg_available
    try:
        import asyncpg

        async def _try():
            conn = await asyncio.wait_for(
                asyncpg.connect(
                    user="homeiq",
                    password="homeiq",
                    database="homeiq",
                    host="localhost",
                    port=5432,
                ),
                timeout=3,
            )
            await conn.close()

        asyncio.get_event_loop().run_until_complete(_try())
        _pg_available = True
    except Exception:
        _pg_available = False
    return _pg_available


requires_pg = pytest.mark.skipif(
    not _check_pg(),
    reason="PostgreSQL not available at localhost:5432",
)
