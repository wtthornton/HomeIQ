"""Shared test fixtures for the electricity-pricing adapter (former electricity-pricing-service)."""

import contextlib
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest


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
async def service_instance(monkeypatch):
    """Create service instance for testing.

    Environment is set through monkeypatch (undone after the test) — the
    adapter reads a fresh ``Settings()`` per instance, not a shared singleton
    (see the adapter's `__init__`), so this is safe even though five other
    adapters' suites share this pytest session.
    """
    from src.adapters.electricity_pricing import ElectricityPricingService

    monkeypatch.setenv("INFLUXDB_TOKEN", "test-token")
    monkeypatch.setenv("INFLUXDB_URL", "http://test-influxdb:8086")
    monkeypatch.setenv("INFLUXDB_ORG", "test-org")
    monkeypatch.setenv("INFLUXDB_BUCKET", "test-bucket")
    monkeypatch.setenv("PRICING_PROVIDER", "awattar")

    service = ElectricityPricingService()

    yield service

    with contextlib.suppress(BaseException):
        await service.shutdown()


@pytest.fixture
def api_client(service_instance, monkeypatch, collectors_client):
    """The shared merged-app TestClient, with the electricity_pricing module's
    `service` singleton swapped for this test's `service_instance`.

    Reuses the session-scoped `collectors_client` rather than spinning up a
    second `TestClient` over the same app — a second lifespan cycle would
    reassign every adapter's module-level service singleton out from under
    the shared client (see tests/test_isolation.py's history with this bug).
    """
    import src.adapters.electricity_pricing as ep_mod

    monkeypatch.setattr(ep_mod, "service", service_instance)
    return collectors_client
