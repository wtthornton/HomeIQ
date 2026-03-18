"""Unit tests for docker_endpoints.py

Tests DockerEndpoints routes with mocked DockerService and APIKeyService.
All Docker/external dependencies are mocked so tests pass without Docker.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from src.docker_service import ContainerInfo, ContainerStatus
from src.docker_endpoints import (
    ContainerOperationResponse,
    ContainerResponse,
    ContainerStatsResponse,
    DockerEndpoints,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_container_info(
    name: str = "homeiq-websocket",
    service_name: str = "websocket-ingestion",
    status: ContainerStatus = ContainerStatus.RUNNING,
    image: str = "homeiq-websocket:latest",
    created: str = "2024-01-01T00:00:00Z",
    ports: dict | None = None,
    labels: dict | None = None,
) -> ContainerInfo:
    return ContainerInfo(
        name=name,
        service_name=service_name,
        status=status,
        image=image,
        created=created,
        ports=ports or {},
        labels=labels or {"com.docker.compose.project": "homeiq"},
    )


@pytest_asyncio.fixture
async def mock_app_client():
    """
    Build a FastAPI app with DockerEndpoints, mocking DockerService and APIKeyService.
    Returns (client, mock_docker_service, mock_api_key_service).
    """
    with patch("src.docker_endpoints.DockerService") as MockDockerSvc, \
         patch("src.docker_endpoints.APIKeyService") as MockAPIKeySvc:
        mock_ds = MockDockerSvc.return_value
        mock_aks = MockAPIKeySvc.return_value

        app = FastAPI()
        endpoints = DockerEndpoints()
        app.include_router(endpoints.router)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac, mock_ds, mock_aks


# ---------------------------------------------------------------------------
# Response model serialization
# ---------------------------------------------------------------------------

class TestResponseModels:

    @pytest.mark.unit
    def test_container_response_model(self):
        resp = ContainerResponse(
            name="homeiq-websocket",
            service_name="websocket-ingestion",
            status="running",
            image="homeiq-websocket:latest",
            created="2024-01-01T00:00:00Z",
            ports={"8001/tcp": "8001"},
            is_project_container=True,
        )
        assert resp.name == "homeiq-websocket"
        assert resp.status == "running"
        d = resp.model_dump()
        assert d["ports"] == {"8001/tcp": "8001"}

    @pytest.mark.unit
    def test_container_operation_response(self):
        resp = ContainerOperationResponse(
            success=True,
            message="started",
            timestamp="2024-01-01T00:00:00",
        )
        assert resp.success is True

    @pytest.mark.unit
    def test_container_stats_response_defaults(self):
        resp = ContainerStatsResponse(timestamp="2024-01-01T00:00:00")
        assert resp.cpu_percent is None
        assert resp.memory_usage is None

    @pytest.mark.unit
    def test_container_stats_response_full(self):
        resp = ContainerStatsResponse(
            cpu_percent=12.5,
            memory_usage=256_000_000,
            memory_limit=512_000_000,
            memory_percent=50.0,
            timestamp="2024-01-01T00:00:00",
        )
        assert resp.cpu_percent == 12.5
        assert resp.memory_percent == 50.0


# ---------------------------------------------------------------------------
# GET /api/v1/docker/containers
# ---------------------------------------------------------------------------

class TestListContainersEndpoint:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_list(self, mock_app_client):
        client, mock_ds, _ = mock_app_client
        mock_ds.list_containers = AsyncMock(return_value=[
            _make_container_info(),
            _make_container_info(
                name="homeiq-influxdb",
                service_name="influxdb",
                ports={"8086/tcp": "8086"},
            ),
        ])

        resp = await client.get("/api/v1/docker/containers")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["name"] == "homeiq-websocket"
        assert data[0]["status"] == "running"
        assert data[1]["service_name"] == "influxdb"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_empty_list(self, mock_app_client):
        client, mock_ds, _ = mock_app_client
        mock_ds.list_containers = AsyncMock(return_value=[])

        resp = await client.get("/api/v1/docker/containers")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_error_500(self, mock_app_client):
        client, mock_ds, _ = mock_app_client
        mock_ds.list_containers = AsyncMock(side_effect=Exception("Docker down"))

        resp = await client.get("/api/v1/docker/containers")
        assert resp.status_code == 500
        assert "Failed to list containers" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# POST /api/v1/docker/containers/{service_name}/start
# ---------------------------------------------------------------------------

class TestStartContainerEndpoint:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_start_success(self, mock_app_client):
        client, mock_ds, _ = mock_app_client
        mock_ds.start_container = AsyncMock(return_value=(True, "Container started"))

        resp = await client.post("/api/v1/docker/containers/websocket-ingestion/start")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["message"] == "Container started"
        assert "timestamp" in data

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_start_failure(self, mock_app_client):
        client, mock_ds, _ = mock_app_client
        mock_ds.start_container = AsyncMock(return_value=(False, "Unknown service"))

        resp = await client.post("/api/v1/docker/containers/bad-service/start")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_start_error_500(self, mock_app_client):
        client, mock_ds, _ = mock_app_client
        mock_ds.start_container = AsyncMock(side_effect=Exception("socket error"))

        resp = await client.post("/api/v1/docker/containers/websocket-ingestion/start")
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# POST /api/v1/docker/containers/{service_name}/stop
# ---------------------------------------------------------------------------

class TestStopContainerEndpoint:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_stop_success(self, mock_app_client):
        client, mock_ds, _ = mock_app_client
        mock_ds.stop_container = AsyncMock(return_value=(True, "Container stopped"))

        resp = await client.post("/api/v1/docker/containers/websocket-ingestion/stop")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["message"] == "Container stopped"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_stop_failure(self, mock_app_client):
        client, mock_ds, _ = mock_app_client
        mock_ds.stop_container = AsyncMock(return_value=(False, "not found"))

        resp = await client.post("/api/v1/docker/containers/bad/stop")
        assert resp.status_code == 200
        assert resp.json()["success"] is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_stop_error_500(self, mock_app_client):
        client, mock_ds, _ = mock_app_client
        mock_ds.stop_container = AsyncMock(side_effect=Exception("fail"))

        resp = await client.post("/api/v1/docker/containers/websocket-ingestion/stop")
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# POST /api/v1/docker/containers/{service_name}/restart
# ---------------------------------------------------------------------------

class TestRestartContainerEndpoint:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_restart_success(self, mock_app_client):
        client, mock_ds, _ = mock_app_client
        mock_ds.restart_container = AsyncMock(return_value=(True, "Container restarted"))

        resp = await client.post("/api/v1/docker/containers/websocket-ingestion/restart")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["message"] == "Container restarted"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_restart_failure(self, mock_app_client):
        client, mock_ds, _ = mock_app_client
        mock_ds.restart_container = AsyncMock(return_value=(False, "failed"))

        resp = await client.post("/api/v1/docker/containers/bad/restart")
        assert resp.status_code == 200
        assert resp.json()["success"] is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_restart_error_500(self, mock_app_client):
        client, mock_ds, _ = mock_app_client
        mock_ds.restart_container = AsyncMock(side_effect=Exception("crash"))

        resp = await client.post("/api/v1/docker/containers/websocket-ingestion/restart")
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# GET /api/v1/docker/containers/{service_name}/logs
# ---------------------------------------------------------------------------

class TestGetContainerLogsEndpoint:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_logs_success(self, mock_app_client):
        client, mock_ds, _ = mock_app_client
        mock_ds.get_container_logs = AsyncMock(return_value="2024-01-01 INFO: ok\n")

        resp = await client.get("/api/v1/docker/containers/websocket-ingestion/logs")
        assert resp.status_code == 200
        data = resp.json()
        assert "logs" in data
        assert "INFO: ok" in data["logs"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_logs_with_tail_param(self, mock_app_client):
        client, mock_ds, _ = mock_app_client
        mock_ds.get_container_logs = AsyncMock(return_value="line\n")

        resp = await client.get("/api/v1/docker/containers/websocket-ingestion/logs?tail=50")
        assert resp.status_code == 200
        mock_ds.get_container_logs.assert_called_once_with("websocket-ingestion", 50)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_logs_default_tail(self, mock_app_client):
        client, mock_ds, _ = mock_app_client
        mock_ds.get_container_logs = AsyncMock(return_value="line\n")

        resp = await client.get("/api/v1/docker/containers/websocket-ingestion/logs")
        assert resp.status_code == 200
        mock_ds.get_container_logs.assert_called_once_with("websocket-ingestion", 100)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_logs_error_500(self, mock_app_client):
        client, mock_ds, _ = mock_app_client
        mock_ds.get_container_logs = AsyncMock(side_effect=Exception("boom"))

        resp = await client.get("/api/v1/docker/containers/websocket-ingestion/logs")
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# GET /api/v1/docker/containers/{service_name}/stats
# ---------------------------------------------------------------------------

class TestGetContainerStatsEndpoint:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_stats_success(self, mock_app_client):
        client, mock_ds, _ = mock_app_client
        mock_ds.get_container_stats = AsyncMock(return_value={
            "cpu_percent": 12.5,
            "memory_usage": 256_000_000,
            "memory_limit": 512_000_000,
            "memory_percent": 50.0,
            "timestamp": "2024-01-01T00:00:00",
        })

        resp = await client.get("/api/v1/docker/containers/websocket-ingestion/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["cpu_percent"] == 12.5
        assert data["memory_percent"] == 50.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_stats_not_found_404(self, mock_app_client):
        client, mock_ds, _ = mock_app_client
        mock_ds.get_container_stats = AsyncMock(return_value=None)

        resp = await client.get("/api/v1/docker/containers/websocket-ingestion/stats")
        assert resp.status_code == 404
        assert "not found or not running" in resp.json()["detail"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_stats_error_500(self, mock_app_client):
        client, mock_ds, _ = mock_app_client
        mock_ds.get_container_stats = AsyncMock(side_effect=Exception("fail"))

        resp = await client.get("/api/v1/docker/containers/websocket-ingestion/stats")
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# GET /api/v1/docker/api-keys
# ---------------------------------------------------------------------------

class TestGetApiKeysEndpoint:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_api_keys_success(self, mock_app_client):
        from src.api_key_service import APIKeyInfo, APIKeyStatus

        client, _, mock_aks = mock_app_client
        mock_aks.get_api_keys = AsyncMock(return_value=[
            APIKeyInfo(
                service="weather",
                key_name="WEATHER_API_KEY",
                status=APIKeyStatus.CONFIGURED,
                masked_key="abc1...xyz9",
                is_required=True,
                description="Weather API key",
            ),
        ])

        resp = await client.get("/api/v1/docker/api-keys")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["service"] == "weather"
        assert data[0]["status"] == "configured"
        assert data[0]["is_required"] is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_api_keys_empty(self, mock_app_client):
        client, _, mock_aks = mock_app_client
        mock_aks.get_api_keys = AsyncMock(return_value=[])

        resp = await client.get("/api/v1/docker/api-keys")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_api_keys_error_500(self, mock_app_client):
        client, _, mock_aks = mock_app_client
        mock_aks.get_api_keys = AsyncMock(side_effect=Exception("db error"))

        resp = await client.get("/api/v1/docker/api-keys")
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# PUT /api/v1/docker/api-keys/{service}
# ---------------------------------------------------------------------------

class TestUpdateApiKeyEndpoint:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_success(self, mock_app_client):
        client, _, mock_aks = mock_app_client
        mock_aks.update_api_key = AsyncMock(return_value=(True, "Key updated"))

        resp = await client.put(
            "/api/v1/docker/api-keys/weather",
            json={"api_key": "new-key-12345"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["message"] == "Key updated"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_error_500(self, mock_app_client):
        client, _, mock_aks = mock_app_client
        mock_aks.update_api_key = AsyncMock(side_effect=Exception("fail"))

        resp = await client.put(
            "/api/v1/docker/api-keys/weather",
            json={"api_key": "key"},
        )
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# POST /api/v1/docker/api-keys/{service}/test
# ---------------------------------------------------------------------------

class TestTestApiKeyEndpoint:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_test_key_success(self, mock_app_client):
        client, _, mock_aks = mock_app_client
        mock_aks.test_api_key = AsyncMock(return_value=(True, "Key valid"))

        resp = await client.post(
            "/api/v1/docker/api-keys/weather/test",
            json={"api_key": "test-key-12345"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["message"] == "Key valid"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_test_key_failure(self, mock_app_client):
        client, _, mock_aks = mock_app_client
        mock_aks.test_api_key = AsyncMock(return_value=(False, "Invalid key"))

        resp = await client.post(
            "/api/v1/docker/api-keys/weather/test",
            json={"api_key": "bad-key"},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_test_key_error_500(self, mock_app_client):
        client, _, mock_aks = mock_app_client
        mock_aks.test_api_key = AsyncMock(side_effect=Exception("network"))

        resp = await client.post(
            "/api/v1/docker/api-keys/weather/test",
            json={"api_key": "key"},
        )
        assert resp.status_code == 500
