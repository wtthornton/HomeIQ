"""
Tests for health endpoints.
"""

from fastapi.testclient import TestClient

from src.main import app


def test_health():
    """Test health endpoint.

    `with` is required for TestClient to run app lifespan at all -- real
    startup constructs the shared OpenVINO manager and the ml managers, so
    this exercises the actual merged-process readiness path (TAP-7276)
    rather than a stub.
    """
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "model-server"


def test_root():
    """Test root endpoint returns service info."""
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert data["service"] == "model-server"
