"""Pytest fixtures for activity-recognition tests."""

import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

# Add src to path so "from src.main import app" works when run from service root
_service_root = Path(__file__).resolve().parent.parent
if str(_service_root) not in sys.path:
    sys.path.insert(0, str(_service_root))


@pytest.fixture
def app():
    """Return the FastAPI app instance."""
    from src.main import app as _app
    return _app


@pytest.fixture
async def client(app):
    """Async HTTP client for testing app endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
