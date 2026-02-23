"""
Unit tests for Automation Service Deployment Router

Epic 39, Story 39.12: Query & Automation Service Testing
"""

from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient


@pytest.fixture
def client_with_mock_deployment_service(client):
    """Client with deployment service mocked so deploy succeeds without HA/Data API."""
    from src.api.dependencies import get_deployment_service
    from src.main import app

    async def mock_deploy_suggestion(suggestion_id: int, **kwargs):
        return {
            "success": True,
            "message": "Automation deployed successfully",
            "data": {
                "suggestion_id": suggestion_id,
                "automation_id": "automation.test_123",
                "status": "deployed",
            },
        }

    mock_svc = AsyncMock()
    mock_svc.deploy_suggestion = mock_deploy_suggestion
    mock_svc.batch_deploy = AsyncMock(
        return_value={"suggestion_ids": [1, 2, 3], "status": "deployed"}
    )
    mock_svc.list_deployed_automations = AsyncMock(return_value=[])
    mock_svc.get_automation_status = AsyncMock(
        return_value={"automation_id": "test-automation-123", "status": "on"}
    )
    mock_svc.enable_automation = AsyncMock(
        return_value={"automation_id": "test-automation-123", "status": "enabled"}
    )
    mock_svc.disable_automation = AsyncMock(
        return_value={"automation_id": "test-automation-123", "status": "disabled"}
    )
    mock_svc.test_connection = AsyncMock(return_value={"status": "ok", "message": "Connected"})
    mock_svc.rollback_automation = AsyncMock(
        return_value={"automation_id": "test-automation-123", "status": "rolled_back"}
    )
    mock_svc.get_automation_versions = AsyncMock(return_value=[])  # router wraps as {versions: [...]}
    app.dependency_overrides[get_deployment_service] = lambda: mock_svc
    yield client
    app.dependency_overrides.pop(get_deployment_service, None)


class TestDeploymentRouter:
    """Test suite for deployment router endpoints."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_deploy_suggestion_endpoint(
        self, client_with_mock_deployment_service: AsyncClient, auth_headers: dict
    ):
        """Test deploy suggestion endpoint (foundation)."""
        response = await client_with_mock_deployment_service.post(
            "/api/deploy/1", json={"skip_validation": False}, headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data.get("data", {}).get("suggestion_id") == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_batch_deploy_endpoint(
        self, client_with_mock_deployment_service: AsyncClient, auth_headers: dict
    ):
        """Test batch deploy endpoint (foundation)."""
        response = await client_with_mock_deployment_service.post(
            "/api/deploy/batch", json=[1, 2, 3], headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "suggestion_ids" in data
        assert "status" in data

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_automations_endpoint(
        self, client_with_mock_deployment_service: AsyncClient, auth_headers: dict
    ):
        """Test list automations endpoint (foundation)."""
        response = await client_with_mock_deployment_service.get(
            "/api/deploy/automations", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "automations" in data
        assert isinstance(data["automations"], list)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_automation_status_endpoint(
        self, client_with_mock_deployment_service: AsyncClient, auth_headers: dict
    ):
        """Test get automation status endpoint (foundation)."""
        response = await client_with_mock_deployment_service.get(
            "/api/deploy/automations/test-automation-123", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "automation_id" in data
        assert data["automation_id"] == "test-automation-123"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_enable_automation_endpoint(
        self, client_with_mock_deployment_service: AsyncClient, auth_headers: dict
    ):
        """Test enable automation endpoint (foundation)."""
        response = await client_with_mock_deployment_service.post(
            "/api/deploy/automations/test-automation-123/enable", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "automation_id" in data
        assert "status" in data

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_disable_automation_endpoint(
        self, client_with_mock_deployment_service: AsyncClient, auth_headers: dict
    ):
        """Test disable automation endpoint (foundation)."""
        response = await client_with_mock_deployment_service.post(
            "/api/deploy/automations/test-automation-123/disable", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "automation_id" in data
        assert "status" in data

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_test_connection_endpoint(
        self, client_with_mock_deployment_service: AsyncClient, auth_headers: dict
    ):
        """Test HA connection endpoint (foundation)."""
        response = await client_with_mock_deployment_service.get(
            "/api/deploy/test-connection", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "message" in data

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rollback_endpoint(
        self, client_with_mock_deployment_service: AsyncClient, auth_headers: dict
    ):
        """Test rollback endpoint (foundation)."""
        response = await client_with_mock_deployment_service.post(
            "/api/deploy/test-automation-123/rollback", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "automation_id" in data
        assert "status" in data

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_versions_endpoint(
        self, client_with_mock_deployment_service: AsyncClient, auth_headers: dict
    ):
        """Test get versions endpoint (foundation)."""
        response = await client_with_mock_deployment_service.get(
            "/api/deploy/test-automation-123/versions", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "automation_id" in data
        assert "versions" in data
        assert isinstance(data["versions"], list)
