"""
Tests for Main Application
Epic 31, Story 31.1
"""

import pytest

pytest.importorskip("influxdb_client_3", reason="influxdb_client_3 required by src.main")

from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient
from src.main import SERVICE_NAME, SERVICE_VERSION, app

client = TestClient(app)


def test_root_endpoint():
    """The root is create_app()'s: the service's own `/` handler was dead code,
    registered after (and shadowed by) the factory's (TAP-6183)."""
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Weather API Service"
    assert data["version"] == SERVICE_VERSION
    assert data["status"] == "running"


def test_health_endpoint():
    """Test health endpoint returns health status.

    weather_service is stubbed rather than lifespan-started: startup needs a
    real INFLUXDB_TOKEN and kicks off network fetches, which unit tests must
    not do. The recent_fetch readiness check reads the stub (TAP-6183).
    """
    import src.main as main_module

    stub = SimpleNamespace(last_successful_fetch=datetime.now(UTC))
    original = main_module.weather_service
    main_module.weather_service = stub
    try:
        response = client.get("/health")
    finally:
        main_module.weather_service = original

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == SERVICE_NAME
    assert "uptime_seconds" in data


def test_metrics_endpoint():
    """Metrics is create_app()'s Prometheus text endpoint; the JSON handler
    the service defined after it was unreachable (TAP-6183)."""
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "# HELP" in response.text


def test_cors_headers():
    """Test CORS headers are present"""
    response = client.get("/", headers={"Origin": "http://localhost:3000"})

    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers


def test_openapi_docs_available():
    """Test that OpenAPI documentation is accessible"""
    response = client.get("/docs")

    assert response.status_code == 200


def test_openapi_json():
    """Test that OpenAPI JSON schema is available"""
    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Weather API Service"
    assert schema["info"]["version"] == SERVICE_VERSION
