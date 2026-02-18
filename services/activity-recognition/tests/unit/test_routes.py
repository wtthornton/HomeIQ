"""Unit tests for activity-recognition API routes."""

async def test_list_activities(client) -> None:
    """GET /activities returns activity id -> name map."""
    response = await client.get("/api/v1/activities")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert data.get("0") == "sleeping"
    assert data.get("9") == "other"


async def test_model_info_without_model(client) -> None:
    """GET /model/info returns loaded=False when no model loaded."""
    response = await client.get("/api/v1/model/info")
    assert response.status_code == 200
    data = response.json()
    assert "loaded" in data
    assert "model_path" in data
