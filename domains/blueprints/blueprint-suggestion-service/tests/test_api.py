"""
Epic 90, Story 90.8: Blueprint suggestion service API tests.

Tests HTTP endpoints for blueprint-suggestion-service.
Uses mocked database dependencies to avoid real DB connections.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client():
    """Create a test client with mocked DB and services."""
    # Patch the database dependency before importing the app
    with (
        patch("src.database.init_db", new_callable=AsyncMock, return_value=True),
        patch("src.database.close_db", new_callable=AsyncMock),
        patch("src.database.get_db") as mock_get_db,
        patch("src.api.routes.init_schema_cache", new_callable=AsyncMock),
        patch("src.api.routes.check_schema_version", new_callable=AsyncMock, return_value=True),
    ):
        mock_session = AsyncMock()
        mock_get_db.return_value = mock_session

        from src.main import app

        yield TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        """Health endpoint returns 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_has_status(self, client):
        """Health response contains status field."""
        response = client.get("/health")
        data = response.json()
        assert "status" in data


# ---------------------------------------------------------------------------
# Suggestions endpoint
# ---------------------------------------------------------------------------


class TestSuggestionsEndpoint:
    def test_list_suggestions_endpoint_exists(self, client):
        """GET /api/blueprint-suggestions/suggestions does not 404."""
        response = client.get("/api/blueprint-suggestions/suggestions")
        assert response.status_code != 404

    def test_list_suggestions_with_min_score_filter(self, client):
        """Filter by min_score parameter accepted."""
        response = client.get("/api/blueprint-suggestions/suggestions?min_score=0.8")
        assert response.status_code != 404

    def test_list_suggestions_with_use_case_filter(self, client):
        """Filter by use_case parameter accepted."""
        response = client.get("/api/blueprint-suggestions/suggestions?use_case=energy")
        assert response.status_code != 404

    def test_list_suggestions_with_pagination(self, client):
        """Pagination parameters accepted."""
        response = client.get("/api/blueprint-suggestions/suggestions?limit=5&offset=0")
        assert response.status_code != 404

    def test_list_suggestions_invalid_min_score_rejected(self, client):
        """min_score > 1.0 is rejected as 422."""
        response = client.get("/api/blueprint-suggestions/suggestions?min_score=2.0")
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Stats endpoint
# ---------------------------------------------------------------------------


class TestStatsEndpoint:
    def test_stats_endpoint_exists(self, client):
        """GET /api/blueprint-suggestions/stats does not 404."""
        response = client.get("/api/blueprint-suggestions/stats")
        assert response.status_code != 404


# ---------------------------------------------------------------------------
# Generate endpoint
# ---------------------------------------------------------------------------


class TestGenerateEndpoint:
    def test_generate_endpoint_exists(self, client):
        """POST /api/blueprint-suggestions/generate does not 404/405."""
        response = client.post(
            "/api/blueprint-suggestions/generate",
            json={
                "device_ids": [],
                "complexity": "simple",
                "max_suggestions": 5,
            },
        )
        assert response.status_code not in (404, 405)

    def test_generate_requires_body(self, client):
        """POST without body returns 422."""
        response = client.post("/api/blueprint-suggestions/generate")
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Delete-all endpoint
# ---------------------------------------------------------------------------


class TestDeleteAllEndpoint:
    def test_delete_all_requires_admin_key(self, client):
        """DELETE without X-Admin-Key is rejected (422 for missing header)."""
        response = client.delete("/api/blueprint-suggestions/delete-all")
        assert response.status_code == 422

    def test_delete_all_wrong_key_forbidden(self, client):
        """DELETE with wrong admin key returns 403."""
        with patch("src.api.routes.settings") as mock_settings:
            mock_settings.admin_api_key = "correct-key"
            response = client.delete(
                "/api/blueprint-suggestions/delete-all",
                headers={"X-Admin-Key": "wrong-key"},
            )
            assert response.status_code == 403

    def test_delete_all_endpoint_not_404(self, client):
        """DELETE endpoint exists (not 404)."""
        response = client.delete(
            "/api/blueprint-suggestions/delete-all",
            headers={"X-Admin-Key": "test"},
        )
        assert response.status_code != 404


# ---------------------------------------------------------------------------
# Schema health endpoint
# ---------------------------------------------------------------------------


class TestSchemaHealthEndpoint:
    def test_schema_health_endpoint_exists(self, client):
        """GET /api/blueprint-suggestions/health/schema does not 404."""
        response = client.get("/api/blueprint-suggestions/health/schema")
        assert response.status_code != 404


# ---------------------------------------------------------------------------
# Accept / decline endpoints
# ---------------------------------------------------------------------------


class TestAcceptDeclineEndpoints:
    def test_accept_endpoint_exists(self, client):
        """POST /{suggestion_id}/accept does not 404 for valid UUID."""
        response = client.post(
            "/api/blueprint-suggestions/00000000-0000-0000-0000-000000000001/accept"
        )
        assert response.status_code != 404

    def test_accept_rejects_invalid_uuid(self, client):
        """POST /{suggestion_id}/accept rejects non-UUID path."""
        response = client.post("/api/blueprint-suggestions/not-a-uuid/accept")
        assert response.status_code == 422

    def test_decline_endpoint_exists(self, client):
        """POST /{suggestion_id}/decline does not 404 for valid UUID."""
        response = client.post(
            "/api/blueprint-suggestions/00000000-0000-0000-0000-000000000001/decline"
        )
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_accept_surfaces_blueprint_inputs_from_producer_field(self):
        """blueprint-index's BlueprintResponse serializes inputs under the
        `inputs` field (src/api/schemas.py:57 in blueprint-index), not
        `blueprint_inputs`. accept_suggestion must read that field so
        AcceptSuggestionResponse.blueprint_inputs is populated.

        Calls the route handler directly (bypassing the FastAPI TestClient
        layer) since it exercises the exact buggy line without depending on
        the shared `client` fixture's mocked `get_db`.
        """
        from src.api.routes import accept_suggestion

        mock_suggestion = MagicMock(
            id="00000000-0000-0000-0000-000000000001",
            status="accepted",
            blueprint_id="blueprint-1",
            matched_devices=[{"entity_id": "light.kitchen", "domain": "light"}],
            suggestion_score=0.9,
            conversation_id=None,
        )
        mock_service = MagicMock()
        mock_service.accept_suggestion = AsyncMock(return_value=mock_suggestion)

        mock_blueprint_client = AsyncMock()
        mock_blueprint_client.__aenter__.return_value = mock_blueprint_client
        mock_blueprint_client.get_blueprint = AsyncMock(
            return_value={
                "yaml_content": "blueprint: {}",
                "inputs": {"target_entity": "light.kitchen"},
            }
        )

        with patch(
            "src.clients.blueprint_client.BlueprintClient",
            return_value=mock_blueprint_client,
        ):
            response = await accept_suggestion(
                suggestion_id="00000000-0000-0000-0000-000000000001",
                conversation_id=None,
                db=AsyncMock(),
                service=mock_service,
            )

        assert response.blueprint_inputs == {"target_entity": "light.kitchen"}
