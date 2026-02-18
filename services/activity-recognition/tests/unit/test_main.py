"""Unit tests for activity-recognition main app."""

async def test_root_endpoint(client) -> None:
    """Root returns service name and version."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "activity-recognition"
    assert data["version"] == "1.0.0"
    assert "docs" in data


async def test_api_health_returns_200_or_503(client) -> None:
    """Health endpoint returns 200 (healthy) or 503 (degraded, no model)."""
    response = await client.get("/api/v1/health")
    assert response.status_code in (200, 503)
    data = response.json()
    assert data["service"] == "activity-recognition"
    assert "model_loaded" in data
