"""
Shared test fixtures for electricity-pricing-service
"""

import contextlib
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

# Add service root and src/ directory to sys.path for imports
_service_root = str(Path(__file__).resolve().parent.parent)
_service_src = str(Path(__file__).resolve().parent.parent / "src")
if _service_root not in sys.path:
    sys.path.insert(0, _service_root)
if _service_src not in sys.path:
    sys.path.insert(0, _service_src)


@pytest.fixture
def mock_influxdb_client():
    """Mock InfluxDB client"""
    client = MagicMock()
    client.write = MagicMock()
    client.close = MagicMock()
    return client


@pytest.fixture
def sample_pricing_data() -> dict:
    """Sample pricing data from provider"""
    now = datetime.now()
    return {
        "current_price": 0.285,
        "currency": "EUR",
        "peak_period": True,
        "cheapest_hours": [2, 3, 4, 5],
        "most_expensive_hours": [18, 19, 20],
        "forecast_24h": [
            {"hour": 0, "price": 0.28, "timestamp": now},
            {"hour": 1, "price": 0.25, "timestamp": now + timedelta(hours=1)},
            {"hour": 2, "price": 0.22, "timestamp": now + timedelta(hours=2)},
            {"hour": 3, "price": 0.21, "timestamp": now + timedelta(hours=3)},
        ],
        "timestamp": now,
        "provider": "awattar",
    }


@pytest.fixture
def sample_cheap_pricing() -> dict:
    """Sample cheap pricing (off-peak)"""
    now = datetime.now()
    return {
        "current_price": 0.18,
        "currency": "EUR",
        "peak_period": False,
        "cheapest_hours": [2, 3, 4, 5],
        "most_expensive_hours": [18, 19, 20],
        "forecast_24h": [],
        "timestamp": now,
        "provider": "awattar",
    }


@pytest.fixture
def sample_expensive_pricing() -> dict:
    """Sample expensive pricing (peak)"""
    now = datetime.now()
    return {
        "current_price": 0.42,
        "currency": "EUR",
        "peak_period": True,
        "cheapest_hours": [2, 3, 4, 5],
        "most_expensive_hours": [18, 19, 20],
        "forecast_24h": [],
        "timestamp": now,
        "provider": "awattar",
    }


@pytest.fixture
async def service_instance(monkeypatch):
    """Create service instance for testing.

    Environment is set through monkeypatch so it is undone after the test;
    a raw os.environ write here leaked INFLUXDB_ORG into test_main's
    default-org assertion.
    """
    from src.main import ElectricityPricingService

    monkeypatch.setenv("INFLUXDB_TOKEN", "test-token")
    monkeypatch.setenv("INFLUXDB_URL", "http://test-influxdb:8086")
    monkeypatch.setenv("INFLUXDB_ORG", "test-org")
    monkeypatch.setenv("INFLUXDB_BUCKET", "test-bucket")
    monkeypatch.setenv("PRICING_PROVIDER", "awattar")

    service = ElectricityPricingService()

    yield service

    # Cleanup
    with contextlib.suppress(BaseException):
        await service.shutdown()


def _asgi_client(app, host: str) -> AsyncClient:
    return AsyncClient(
        transport=ASGITransport(app=app, client=(host, 12345)), base_url="http://test"
    )


@pytest.fixture
async def api_client(service_instance, monkeypatch):
    """ASGI client against the real app with the module-level service swapped in.

    No lifespan runs (startup would open real aiohttp/InfluxDB clients), so
    the fixture's service stands in for the one _startup would create.
    """
    from src import main

    monkeypatch.setattr(main, "service", service_instance)
    async with _asgi_client(main.app, "127.0.0.1") as client:
        yield client


@pytest.fixture
async def external_api_client(service_instance, monkeypatch):
    """Same as api_client, but the request arrives from a non-RFC1918 address."""
    from src import main

    monkeypatch.setattr(main, "service", service_instance)
    async with _asgi_client(main.app, "8.8.8.8") as client:
        yield client
