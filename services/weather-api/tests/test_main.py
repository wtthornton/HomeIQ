"""
Tests for Main Application
Epic 31, Story 31.1
"""

from fastapi.testclient import TestClient
from src.main import SERVICE_NAME, SERVICE_VERSION, app


client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint returns service information"""
    response = client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == SERVICE_NAME
    assert data["version"] == SERVICE_VERSION
    assert data["status"] == "running"
    assert "endpoints" in data


def test_health_endpoint():
    """Test health endpoint returns health status"""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == SERVICE_NAME
    assert "uptime" in data


def test_metrics_endpoint():
    """Test metrics endpoint returns monitoring data"""
    response = client.get("/metrics")
    
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == SERVICE_NAME
    assert "uptime_seconds" in data
    assert data["status"] == "healthy"


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

