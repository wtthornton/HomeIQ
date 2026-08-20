"""
API Endpoint Integration Tests

Epic 49 Story 49.3: Integration Test Suite
Exercises the FastAPI app (/health, /cheapest-hours) through an ASGI client.
"""

from datetime import UTC, datetime

import pytest
from src.main import ElectricityPricingService

CHEAPEST = [
    {"hour": 2, "price": 0.15},
    {"hour": 3, "price": 0.16},
    {"hour": 4, "price": 0.17},
    {"hour": 5, "price": 0.18},
]


@pytest.fixture
def primed(service_instance):
    service_instance.cached_data = {"cheapest_hours": CHEAPEST}
    service_instance.last_fetch_time = datetime.now(UTC)
    return service_instance


@pytest.mark.asyncio
async def test_health_endpoint(api_client):
    """Liveness is served by StandardHealthCheck and is always 200."""
    resp = await api_client.get("/health")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ["healthy", "degraded", "unhealthy"]
    assert data["service"] == "electricity-pricing-service"


@pytest.mark.asyncio
async def test_cheapest_hours_endpoint_default(api_client, primed):
    resp = await api_client.get("/cheapest-hours")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["cheapest_hours"]) == 4
    assert data["provider"] == primed.provider_name
    assert data["timestamp"] == primed.last_fetch_time.isoformat()


@pytest.mark.asyncio
async def test_cheapest_hours_endpoint_with_hours_param(api_client, primed):
    resp = await api_client.get("/cheapest-hours", params={"hours": "2"})

    assert resp.status_code == 200
    assert resp.json()["cheapest_hours"] == CHEAPEST[:2]


@pytest.mark.asyncio
@pytest.mark.parametrize("hours", ["25", "0", "abc"])
async def test_cheapest_hours_endpoint_rejects_bad_hours(api_client, primed, hours):
    resp = await api_client.get("/cheapest-hours", params={"hours": hours})

    assert resp.status_code == 400
    assert "error" in resp.json()


@pytest.mark.asyncio
async def test_cheapest_hours_endpoint_no_data(api_client, service_instance):
    service_instance.cached_data = None

    resp = await api_client.get("/cheapest-hours")

    assert resp.status_code == 503
    assert resp.json() == {"error": "No pricing data available"}


@pytest.mark.asyncio
async def test_cheapest_hours_endpoint_service_not_started(monkeypatch):
    """Without a lifespan the module-level service is None and the route says so."""
    from httpx import ASGITransport, AsyncClient
    from src import main

    monkeypatch.setattr(main, "service", None)
    async with AsyncClient(transport=ASGITransport(app=main.app), base_url="http://test") as client:
        resp = await client.get("/cheapest-hours")

    assert resp.status_code == 503
    assert resp.json() == {"error": "Service not initialized"}


@pytest.mark.asyncio
async def test_cheapest_hours_endpoint_internal_network_required(external_api_client, primed):
    primed.allowed_networks = ["192.168.0.0/16", "172.16.0.0/12", "10.0.0.0/8"]

    resp = await external_api_client.get("/cheapest-hours")

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_service_startup_with_missing_token(monkeypatch):
    """Test service fails fast on missing InfluxDB token"""
    monkeypatch.delenv("INFLUXDB_TOKEN", raising=False)

    with pytest.raises(ValueError) as exc_info:
        ElectricityPricingService()

    assert "INFLUXDB_TOKEN" in str(exc_info.value)


@pytest.mark.asyncio
async def test_service_startup_with_valid_config(monkeypatch):
    """Test service starts successfully with valid configuration"""
    monkeypatch.setenv("INFLUXDB_TOKEN", "test-token")
    monkeypatch.setenv("INFLUXDB_URL", "http://test-influxdb:8086")
    monkeypatch.setenv("INFLUXDB_ORG", "test-org")
    monkeypatch.setenv("INFLUXDB_BUCKET", "test-bucket")

    service = ElectricityPricingService()

    assert service.influxdb_bucket == "test-bucket"
