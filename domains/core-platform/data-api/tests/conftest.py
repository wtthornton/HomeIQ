from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from urllib.parse import quote

import pytest
import pytest_asyncio

_REPO_ROOT = Path(__file__).resolve().parents[4]


def _compose_setting(name: str, default: str) -> str:
    """Read one setting the way compose does: environment first, then ``.env``.

    Only the three PostgreSQL connection keys are read, and nothing is written
    back into ``os.environ`` — the repository ``.env`` leaking into the process
    environment is exactly what made the settings tests answer differently
    depending on where pytest was invoked (TAP-6154).
    """
    if value := os.environ.get(name):
        return value
    env_file = _REPO_ROOT / ".env"
    if not env_file.exists():
        return default
    for line in env_file.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.partition("=")
        if sep and key.strip() == name:
            return value.strip().strip("\"'") or default
    return default


def _test_database_url() -> str:
    """Connection URL for the PostgreSQL these tests run against.

    ``TEST_DATABASE_URL`` wins outright. Otherwise reconstruct the connection
    ``domains/core-platform/compose.yml`` actually publishes: it maps the
    container's 5432 to ``HOMEIQ_POSTGRES_HOST_PORT`` and takes its credentials
    from ``POSTGRES_USER`` / ``POSTGRES_PASSWORD``.

    The previous hardcoded ``homeiq:homeiq@localhost:5432`` matched none of that
    on a machine that remaps the port. Worse than failing to connect, it
    connected to whatever unrelated service happened to hold 5432 and every
    database test died on that stranger's authentication.
    """
    user = _compose_setting("POSTGRES_USER", "homeiq")
    password = _compose_setting("POSTGRES_PASSWORD", "homeiq")
    host = _compose_setting("POSTGRES_HOST", "localhost")
    port = _compose_setting("HOMEIQ_POSTGRES_HOST_PORT", "5432")
    return (
        f"postgresql+asyncpg://{quote(user, safe='')}:{quote(password, safe='')}"
        f"@{host}:{port}/homeiq_test"
    )


# Set test database URL BEFORE any imports
# This ensures the database module uses the test PostgreSQL database
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or _test_database_url()
# Allow data-api to start without DATA_API_API_KEY (for test_main and app imports)
os.environ.setdefault("DATA_API_ALLOW_ANONYMOUS", "true")


# Load path_setup dynamically
def _load_add_service_src():
    repo_root = Path(__file__).resolve().parents[4]
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

from datetime import UTC, datetime
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


@pytest.fixture
def settings_env(monkeypatch, tmp_path):
    """Construct Settings from a known-empty environment (TAP-6154).

    Two things leak into a bare ``Settings()`` and made these tests answer
    differently depending on where pytest was invoked:

    1. ``model_config.env_file = ".env"`` is resolved against the process
       working directory, so running from the repository root loaded the
       repository ``.env`` and re-supplied the very keys a test had just
       deleted. Running from this service directory found no ``.env`` and the
       same test passed.
    2. Several fields carry generic names — ``API_KEY`` above all, which
       env.required documents as the shared service-to-service key — so any
       ambient value in the developer's or runner's shell satisfies them.

    Chdir into an empty tmp_path to close (1) and clear every name the model
    can read to close (2). The name list is derived from the model, so a new
    field cannot silently reintroduce the leak.

    Returns the monkeypatch instance so a test can set what it wants to assert.
    """
    from src.config import Settings

    monkeypatch.chdir(tmp_path)
    for name, field in Settings.model_fields.items():
        for key in {name, field.alias or name}:
            monkeypatch.delenv(key.upper(), raising=False)
    return monkeypatch


# ✅ Context7 Best Practice: Shared mock fixture with cleanup
@pytest.fixture
def mock_influxdb():
    """
    Mock InfluxDB client for testing without database dependency

    Automatically cleaned up after each test.
    """
    with patch("shared.influxdb_query_client.InfluxDBQueryClient") as mock:
        mock.return_value.connect.return_value = True
        mock.return_value.query.return_value = []
        yield mock


# ✅ Context7 Best Practice: Shared database mock fixture
@pytest.fixture
def mock_database():
    """Mock database for testing"""
    with patch("src.database.get_session") as mock:
        yield mock


# Reason the database cannot be used, once that is known. Cached so an absent
# service is diagnosed once rather than re-probed by every test.
_db_unavailable: str | None = None
# Whether a real connection has ever succeeded this session.
_db_probed = False


async def _database_ready() -> tuple[bool, str]:
    """Return whether the test PostgreSQL is usable, and why not when it isn't.

    ``init_db`` assigns ``database.async_engine = db.engine`` before it knows
    whether initialisation worked, so a database that refuses every connection
    still leaves a non-None engine behind. A guard of ``if async_engine is
    None`` therefore only ever fired for the first database test: that one
    skipped honestly and the remaining 105 walked straight into
    ``engine.begin()`` and raised out of the fixture. One absent service read as
    106 broken tests, which is precisely the noise that hides a real failure.

    So connect for real before trusting the engine, and carry the connection
    error into the skip message — a wrong port and a stopped container need
    different fixes, and the old message named neither.

    The engine is still re-established when it is missing: tests that exercise
    the degraded path clear ``async_engine``, and every test after them needs it
    back.
    """
    global _db_unavailable, _db_probed

    import src.database as database
    import src.models  # noqa: F401  (register models with Base before create_all)
    from sqlalchemy import text
    from src.database import init_db

    if _db_unavailable is not None:
        return False, _db_unavailable

    if database.async_engine is None and (not await init_db() or database.async_engine is None):
        _db_unavailable = "init_db() reported the database as unavailable"
        return False, _db_unavailable

    if not _db_probed:
        try:
            async with database.async_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception as err:
            _db_unavailable = f"{type(err).__name__}: {err}"
            return False, _db_unavailable
        _db_probed = True

    return True, ""


# ✅ Context7 Best Practice: Fresh database for each test
@pytest_asyncio.fixture(autouse=True)
async def fresh_db(request):
    """
    Create a fresh PostgreSQL database for each test.
    Ensures tests don't interfere with each other and use latest schema.

    Skipped for tests in *_unit.py files (pure unit tests without DB).
    """
    # Skip DB setup for pure unit test files (no external services needed)
    test_file = request.fspath.basename if hasattr(request, "fspath") else ""
    if test_file.endswith("_unit.py"):
        yield
        return

    # Register all models with Base before create_all (else entities, devices, etc. missing)
    import src.database as database
    from src.database import Base

    ready, reason = await _database_ready()
    if not ready:
        pytest.skip(f"PostgreSQL not available for data-api tests: {reason}")

    engine = database.async_engine

    # Drop all tables first, then create fresh schema
    async with engine.begin() as conn:
        # Drop all tables (if they exist)
        await conn.run_sync(Base.metadata.drop_all)
        # Create all tables with latest schema
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Cleanup: Delete all data but keep table structure
    async with engine.begin() as conn:
        # Delete all rows from all tables
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())

    # Each test runs on its own event loop, but the engine is created once and
    # its pool caches asyncpg connections bound to the loop that opened them.
    # Dispose so the next test opens fresh connections on its own loop
    # ("attached to a different loop" / "Event loop is closed" otherwise).
    # Re-read from the module: a test may have called init_db() and swapped it.
    current_engine = database.async_engine or engine
    await current_engine.dispose()
    if current_engine is not engine:
        await engine.dispose()


# ✅ Context7 Best Practice: Shared test data fixtures
@pytest.fixture
async def sample_event_data():
    """Sample Home Assistant event data for testing"""
    return {
        "entity_id": "light.living_room",
        "state": "on",
        "timestamp": datetime.now(UTC),
        "attributes": {"brightness": 255, "color_temp": 370},
    }


@pytest.fixture
async def sample_device_data():
    """Sample device data for testing"""
    return {
        "id": "test-device-1",
        "name": "Test Light",
        "model": "Smart Bulb v2",
        "manufacturer": "Test Co",
        "sw_version": "1.0.0",
    }


@pytest.fixture
async def sample_stats_data():
    """Sample statistics data for testing"""
    return {
        "total_events": 12345,
        "events_per_minute": 42,
        "error_rate": 0.01,
        "uptime_seconds": 86400,
    }


# ✅ Context7 Best Practice: Pytest markers for test organization
def pytest_configure(config):
    """Register custom pytest markers"""
    config.addinivalue_line("markers", "unit: Unit tests for isolated components")
    config.addinivalue_line("markers", "integration: Integration tests with dependencies")
    config.addinivalue_line("markers", "slow: Slow-running tests (>1s)")
    config.addinivalue_line("markers", "database: Tests requiring database access")
    config.addinivalue_line("markers", "api: API endpoint tests")


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Clear the shared rate-limiter buckets between tests.

    The limiter is a singleton on the module-level DataAPIService, so token
    consumption accumulates across the whole session and later tests start
    getting 429s purely because earlier ones used up the budget.
    """
    from src.main import data_api_service

    data_api_service.rate_limiter._buckets.clear()
    yield
    data_api_service.rate_limiter._buckets.clear()
