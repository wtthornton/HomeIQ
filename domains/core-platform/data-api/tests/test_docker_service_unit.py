"""Unit tests for docker_service.py

Tests DockerService class with mocked Docker client:
ContainerStatus enum, ContainerInfo dataclass, container operations,
log retrieval, stats calculation, name lookups, and mock fallback.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from dataclasses import asdict

from src.docker_service import ContainerInfo, ContainerStatus, DockerService


# ---------------------------------------------------------------------------
# ContainerStatus enum
# ---------------------------------------------------------------------------

class TestContainerStatus:

    @pytest.mark.unit
    def test_running_value(self):
        assert ContainerStatus.RUNNING.value == "running"

    @pytest.mark.unit
    def test_stopped_value(self):
        assert ContainerStatus.STOPPED.value == "stopped"

    @pytest.mark.unit
    def test_starting_value(self):
        assert ContainerStatus.STARTING.value == "starting"

    @pytest.mark.unit
    def test_stopping_value(self):
        assert ContainerStatus.STOPPING.value == "stopping"

    @pytest.mark.unit
    def test_error_value(self):
        assert ContainerStatus.ERROR.value == "error"

    @pytest.mark.unit
    def test_unknown_value(self):
        assert ContainerStatus.UNKNOWN.value == "unknown"

    @pytest.mark.unit
    def test_all_members(self):
        names = {m.name for m in ContainerStatus}
        assert names == {"RUNNING", "STOPPED", "STARTING", "STOPPING", "ERROR", "UNKNOWN"}


# ---------------------------------------------------------------------------
# ContainerInfo dataclass
# ---------------------------------------------------------------------------

class TestContainerInfo:

    @pytest.mark.unit
    def test_creation(self):
        info = ContainerInfo(
            name="homeiq-websocket",
            service_name="websocket-ingestion",
            status=ContainerStatus.RUNNING,
            image="homeiq-websocket:latest",
            created="2024-01-01T00:00:00Z",
            ports={"8001/tcp": "8001"},
            labels={"com.docker.compose.project": "homeiq"},
        )
        assert info.name == "homeiq-websocket"
        assert info.service_name == "websocket-ingestion"
        assert info.status == ContainerStatus.RUNNING
        assert info.is_project_container is True

    @pytest.mark.unit
    def test_default_is_project_container(self):
        info = ContainerInfo(
            name="c", service_name="s", status=ContainerStatus.STOPPED,
            image="img", created="ts", ports={}, labels={},
        )
        assert info.is_project_container is True

    @pytest.mark.unit
    def test_override_is_project_container(self):
        info = ContainerInfo(
            name="c", service_name="s", status=ContainerStatus.STOPPED,
            image="img", created="ts", ports={}, labels={},
            is_project_container=False,
        )
        assert info.is_project_container is False

    @pytest.mark.unit
    def test_asdict(self):
        info = ContainerInfo(
            name="c", service_name="s", status=ContainerStatus.RUNNING,
            image="img", created="ts", ports={"80/tcp": "80"}, labels={"k": "v"},
        )
        d = asdict(info)
        assert d["name"] == "c"
        assert d["ports"] == {"80/tcp": "80"}


# ---------------------------------------------------------------------------
# Helper to build a DockerService with client=None (mock mode)
# ---------------------------------------------------------------------------

def _mock_mode_service() -> DockerService:
    """Create a DockerService that skips Docker init (client=None)."""
    with patch("src.docker_service.docker"):
        svc = DockerService.__new__(DockerService)
        svc.client = None
        svc.container_mapping = {
            "websocket-ingestion": "homeiq-websocket",
            "admin-api": "homeiq-admin",
            "health-dashboard": "homeiq-dashboard",
            "influxdb": "homeiq-influxdb",
            "weather-api": "homeiq-weather",
            "carbon-intensity-service": "homeiq-carbon-intensity",
            "electricity-pricing-service": "homeiq-electricity-pricing",
            "air-quality-service": "homeiq-air-quality",
            "calendar-service": "homeiq-calendar",
            "smart-meter-service": "homeiq-smart-meter",
            "data-retention": "homeiq-data-retention",
        }
        svc.project_label = "com.docker.compose.project=homeiq"
        return svc


def _real_client_service(mock_docker_client: MagicMock) -> DockerService:
    """Create a DockerService with a mocked Docker client."""
    svc = _mock_mode_service()
    svc.client = mock_docker_client
    return svc


def _make_container(
    name: str = "homeiq-websocket",
    status: str = "running",
    labels: dict | None = None,
    image_tags: list[str] | None = None,
    ports: dict | None = None,
    created: str = "2024-01-01T00:00:00Z",
) -> MagicMock:
    """Build a mock Docker container object."""
    container = MagicMock()
    container.name = name
    container.status = status
    container.labels = labels or {"com.docker.compose.project": "homeiq"}
    img = MagicMock()
    img.tags = image_tags if image_tags is not None else [f"{name}:latest"]
    img.short_id = "sha256:abc123"
    container.image = img
    container.attrs = {
        "Created": created,
        "NetworkSettings": {"Ports": ports or {}},
    }
    return container


# ---------------------------------------------------------------------------
# _get_container_name
# ---------------------------------------------------------------------------

class TestGetContainerName:

    def setup_method(self):
        self.svc = _mock_mode_service()

    @pytest.mark.unit
    def test_known_service(self):
        assert self.svc._get_container_name("websocket-ingestion") == "homeiq-websocket"

    @pytest.mark.unit
    def test_unknown_service(self):
        assert self.svc._get_container_name("nonexistent") is None

    @pytest.mark.unit
    def test_influxdb(self):
        assert self.svc._get_container_name("influxdb") == "homeiq-influxdb"


# ---------------------------------------------------------------------------
# _get_service_name_from_container
# ---------------------------------------------------------------------------

class TestGetServiceNameFromContainer:

    def setup_method(self):
        self.svc = _mock_mode_service()

    @pytest.mark.unit
    def test_known_container(self):
        assert self.svc._get_service_name_from_container("homeiq-websocket") == "websocket-ingestion"

    @pytest.mark.unit
    def test_unknown_container_returns_name(self):
        assert self.svc._get_service_name_from_container("random-container") == "random-container"

    @pytest.mark.unit
    def test_admin_container(self):
        assert self.svc._get_service_name_from_container("homeiq-admin") == "admin-api"


# ---------------------------------------------------------------------------
# _get_container_status
# ---------------------------------------------------------------------------

class TestGetContainerStatusMapping:

    def setup_method(self):
        self.svc = _mock_mode_service()

    @pytest.mark.unit
    def test_running(self):
        c = MagicMock()
        c.status = "running"
        assert self.svc._get_container_status(c) == ContainerStatus.RUNNING

    @pytest.mark.unit
    def test_exited(self):
        c = MagicMock()
        c.status = "exited"
        assert self.svc._get_container_status(c) == ContainerStatus.STOPPED

    @pytest.mark.unit
    def test_created(self):
        c = MagicMock()
        c.status = "created"
        assert self.svc._get_container_status(c) == ContainerStatus.STARTING

    @pytest.mark.unit
    def test_restarting(self):
        c = MagicMock()
        c.status = "restarting"
        assert self.svc._get_container_status(c) == ContainerStatus.STARTING

    @pytest.mark.unit
    def test_unknown_status(self):
        c = MagicMock()
        c.status = "paused"
        assert self.svc._get_container_status(c) == ContainerStatus.UNKNOWN

    @pytest.mark.unit
    def test_case_insensitive(self):
        c = MagicMock()
        c.status = "RUNNING"
        assert self.svc._get_container_status(c) == ContainerStatus.RUNNING


# ---------------------------------------------------------------------------
# list_containers
# ---------------------------------------------------------------------------

class TestListContainers:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_mock_mode_returns_containers(self):
        svc = _mock_mode_service()
        result = await svc.list_containers()
        assert isinstance(result, list)
        assert len(result) == len(svc.container_mapping)
        names = {c.name for c in result}
        assert "homeiq-websocket" in names
        assert "homeiq-influxdb" in names

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_mock_containers_have_correct_status(self):
        svc = _mock_mode_service()
        result = await svc.list_containers()
        by_service = {c.service_name: c for c in result}
        assert by_service["influxdb"].status == ContainerStatus.RUNNING
        assert by_service["websocket-ingestion"].status == ContainerStatus.RUNNING
        assert by_service["weather-api"].status == ContainerStatus.STOPPED
        assert by_service["carbon-intensity-service"].status == ContainerStatus.STOPPED

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_mock_containers_have_ports(self):
        svc = _mock_mode_service()
        result = await svc.list_containers()
        by_service = {c.service_name: c for c in result}
        assert by_service["influxdb"].ports == {"8086/tcp": "8086"}
        assert by_service["websocket-ingestion"].ports == {"8001/tcp": "8001"}
        assert by_service["weather-api"].ports == {}

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_with_real_client(self):
        mock_client = MagicMock()
        container = _make_container(
            name="homeiq-websocket",
            status="running",
            ports={"8001/tcp": [{"HostPort": "8001"}]},
        )
        mock_client.containers.list.return_value = [container]
        svc = _real_client_service(mock_client)

        result = await svc.list_containers()
        assert len(result) == 1
        assert result[0].name == "homeiq-websocket"
        assert result[0].status == ContainerStatus.RUNNING
        assert result[0].ports == {"8001/tcp": "8001"}

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_filters_non_project_containers(self):
        mock_client = MagicMock()
        project_container = _make_container(name="homeiq-websocket")
        non_project = _make_container(
            name="other-container",
            labels={"com.docker.compose.project": "other-project"},
        )
        mock_client.containers.list.return_value = [project_container, non_project]
        svc = _real_client_service(mock_client)

        result = await svc.list_containers()
        assert len(result) == 1
        assert result[0].name == "homeiq-websocket"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_image_fallback_to_short_id(self):
        mock_client = MagicMock()
        container = _make_container(name="homeiq-websocket", image_tags=[])
        mock_client.containers.list.return_value = [container]
        svc = _real_client_service(mock_client)

        result = await svc.list_containers()
        assert result[0].image == "sha256:abc123"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_exception_falls_back_to_mock(self):
        mock_client = MagicMock()
        mock_client.containers.list.side_effect = Exception("Docker down")
        svc = _real_client_service(mock_client)

        result = await svc.list_containers()
        # Should fall back to mock containers
        assert len(result) == len(svc.container_mapping)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_empty_labels(self):
        mock_client = MagicMock()
        container = _make_container(name="homeiq-websocket", labels=None)
        # labels=None means no project match
        container.labels = None
        mock_client.containers.list.return_value = [container]
        svc = _real_client_service(mock_client)

        result = await svc.list_containers()
        assert len(result) == 0


# ---------------------------------------------------------------------------
# start_container
# ---------------------------------------------------------------------------

class TestStartContainer:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_mock_mode(self):
        svc = _mock_mode_service()
        ok, msg = await svc.start_container("websocket-ingestion")
        assert ok is True
        assert "Mock" in msg

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_unknown_service(self):
        mock_client = MagicMock()
        svc = _real_client_service(mock_client)
        ok, msg = await svc.start_container("nonexistent")
        assert ok is False
        assert "Unknown service" in msg

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_already_running(self):
        mock_client = MagicMock()
        container = MagicMock()
        container.status = "running"
        mock_client.containers.get.return_value = container
        svc = _real_client_service(mock_client)

        with patch("src.docker_service.asyncio.sleep", new_callable=AsyncMock):
            ok, msg = await svc.start_container("websocket-ingestion")
        assert ok is True
        assert "already running" in msg

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_start_success(self):
        mock_client = MagicMock()
        container = MagicMock()
        container.status = "exited"
        # After reload, status becomes running
        container.reload = MagicMock(side_effect=lambda: setattr(container, "status", "running"))
        mock_client.containers.get.return_value = container
        svc = _real_client_service(mock_client)

        with patch("src.docker_service.asyncio.sleep", new_callable=AsyncMock):
            ok, msg = await svc.start_container("websocket-ingestion")
        assert ok is True
        assert "started successfully" in msg
        container.start.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_start_fails_to_come_up(self):
        mock_client = MagicMock()
        container = MagicMock()
        container.status = "exited"
        # After reload, status stays exited
        container.reload = MagicMock()
        mock_client.containers.get.return_value = container
        svc = _real_client_service(mock_client)

        with patch("src.docker_service.asyncio.sleep", new_callable=AsyncMock):
            ok, msg = await svc.start_container("websocket-ingestion")
        assert ok is False
        assert "failed to start" in msg

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_container_not_found(self):
        import docker as docker_lib

        mock_client = MagicMock()
        mock_client.containers.get.side_effect = docker_lib.errors.NotFound("not found")
        svc = _real_client_service(mock_client)

        ok, msg = await svc.start_container("websocket-ingestion")
        assert ok is False
        assert "not found" in msg.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generic_exception(self):
        mock_client = MagicMock()
        mock_client.containers.get.side_effect = Exception("socket error")
        svc = _real_client_service(mock_client)

        ok, msg = await svc.start_container("websocket-ingestion")
        assert ok is False
        assert "socket error" in msg


# ---------------------------------------------------------------------------
# stop_container
# ---------------------------------------------------------------------------

class TestStopContainer:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_mock_mode(self):
        svc = _mock_mode_service()
        ok, msg = await svc.stop_container("admin-api")
        assert ok is True
        assert "Mock" in msg

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_unknown_service(self):
        mock_client = MagicMock()
        svc = _real_client_service(mock_client)
        ok, msg = await svc.stop_container("nonexistent")
        assert ok is False
        assert "Unknown service" in msg

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_not_running(self):
        mock_client = MagicMock()
        container = MagicMock()
        container.status = "exited"
        mock_client.containers.get.return_value = container
        svc = _real_client_service(mock_client)

        with patch("src.docker_service.asyncio.sleep", new_callable=AsyncMock):
            ok, msg = await svc.stop_container("websocket-ingestion")
        assert ok is True
        assert "not running" in msg

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_stop_success(self):
        mock_client = MagicMock()
        container = MagicMock()
        container.status = "running"
        container.reload = MagicMock(side_effect=lambda: setattr(container, "status", "exited"))
        mock_client.containers.get.return_value = container
        svc = _real_client_service(mock_client)

        with patch("src.docker_service.asyncio.sleep", new_callable=AsyncMock):
            ok, msg = await svc.stop_container("websocket-ingestion")
        assert ok is True
        assert "stopped successfully" in msg
        container.stop.assert_called_once_with(timeout=10)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_stop_fails(self):
        mock_client = MagicMock()
        container = MagicMock()
        container.status = "running"
        # stays running after reload
        container.reload = MagicMock()
        mock_client.containers.get.return_value = container
        svc = _real_client_service(mock_client)

        with patch("src.docker_service.asyncio.sleep", new_callable=AsyncMock):
            ok, msg = await svc.stop_container("websocket-ingestion")
        assert ok is False
        assert "failed to stop" in msg

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_container_not_found(self):
        import docker as docker_lib

        mock_client = MagicMock()
        mock_client.containers.get.side_effect = docker_lib.errors.NotFound("not found")
        svc = _real_client_service(mock_client)

        ok, msg = await svc.stop_container("websocket-ingestion")
        assert ok is False
        assert "not found" in msg.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generic_exception(self):
        mock_client = MagicMock()
        mock_client.containers.get.side_effect = Exception("timeout")
        svc = _real_client_service(mock_client)

        ok, msg = await svc.stop_container("websocket-ingestion")
        assert ok is False
        assert "timeout" in msg


# ---------------------------------------------------------------------------
# restart_container
# ---------------------------------------------------------------------------

class TestRestartContainer:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_mock_mode(self):
        svc = _mock_mode_service()
        ok, msg = await svc.restart_container("influxdb")
        assert ok is True
        assert "Mock" in msg

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_unknown_service(self):
        mock_client = MagicMock()
        svc = _real_client_service(mock_client)
        ok, msg = await svc.restart_container("nonexistent")
        assert ok is False
        assert "Unknown service" in msg

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_restart_success(self):
        mock_client = MagicMock()
        container = MagicMock()
        container.status = "running"
        container.reload = MagicMock()  # stays running after restart
        mock_client.containers.get.return_value = container
        svc = _real_client_service(mock_client)

        with patch("src.docker_service.asyncio.sleep", new_callable=AsyncMock):
            ok, msg = await svc.restart_container("websocket-ingestion")
        assert ok is True
        assert "restarted successfully" in msg
        container.restart.assert_called_once_with(timeout=10)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_restart_fails(self):
        mock_client = MagicMock()
        container = MagicMock()
        container.status = "running"
        container.reload = MagicMock(side_effect=lambda: setattr(container, "status", "exited"))
        mock_client.containers.get.return_value = container
        svc = _real_client_service(mock_client)

        with patch("src.docker_service.asyncio.sleep", new_callable=AsyncMock):
            ok, msg = await svc.restart_container("websocket-ingestion")
        assert ok is False
        assert "failed to restart" in msg

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_container_not_found(self):
        import docker as docker_lib

        mock_client = MagicMock()
        mock_client.containers.get.side_effect = docker_lib.errors.NotFound("not found")
        svc = _real_client_service(mock_client)

        ok, msg = await svc.restart_container("websocket-ingestion")
        assert ok is False
        assert "not found" in msg.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generic_exception(self):
        mock_client = MagicMock()
        mock_client.containers.get.side_effect = Exception("permission denied")
        svc = _real_client_service(mock_client)

        ok, msg = await svc.restart_container("websocket-ingestion")
        assert ok is False
        assert "permission denied" in msg


# ---------------------------------------------------------------------------
# get_container_logs
# ---------------------------------------------------------------------------

class TestGetContainerLogs:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_mock_mode(self):
        svc = _mock_mode_service()
        logs = await svc.get_container_logs("websocket-ingestion")
        assert "Mock logs" in logs
        assert "websocket-ingestion" in logs

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_unknown_service(self):
        mock_client = MagicMock()
        svc = _real_client_service(mock_client)
        logs = await svc.get_container_logs("nonexistent")
        assert "Unknown service" in logs

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_success(self):
        mock_client = MagicMock()
        container = MagicMock()
        container.logs.return_value = b"2024-01-01 INFO: started\n"
        mock_client.containers.get.return_value = container
        svc = _real_client_service(mock_client)

        logs = await svc.get_container_logs("websocket-ingestion", tail=50)
        assert "started" in logs
        container.logs.assert_called_once_with(tail=50, timestamps=True)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_default_tail(self):
        mock_client = MagicMock()
        container = MagicMock()
        container.logs.return_value = b"line\n"
        mock_client.containers.get.return_value = container
        svc = _real_client_service(mock_client)

        await svc.get_container_logs("websocket-ingestion")
        container.logs.assert_called_once_with(tail=100, timestamps=True)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_container_not_found(self):
        import docker as docker_lib

        mock_client = MagicMock()
        mock_client.containers.get.side_effect = docker_lib.errors.NotFound("not found")
        svc = _real_client_service(mock_client)

        logs = await svc.get_container_logs("websocket-ingestion")
        assert "not found" in logs.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generic_exception(self):
        mock_client = MagicMock()
        mock_client.containers.get.side_effect = Exception("boom")
        svc = _real_client_service(mock_client)

        logs = await svc.get_container_logs("websocket-ingestion")
        assert "Error" in logs


# ---------------------------------------------------------------------------
# get_container_stats
# ---------------------------------------------------------------------------

class TestGetContainerStats:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_mock_mode(self):
        svc = _mock_mode_service()
        stats = await svc.get_container_stats("websocket-ingestion")
        assert stats is not None
        assert stats["cpu_percent"] == 15.5
        assert stats["memory_usage"] == 256 * 1024 * 1024
        assert stats["memory_limit"] == 512 * 1024 * 1024
        assert stats["memory_percent"] == 50.0
        assert "timestamp" in stats

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_unknown_service(self):
        mock_client = MagicMock()
        svc = _real_client_service(mock_client)
        stats = await svc.get_container_stats("nonexistent")
        assert stats is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_container_not_running(self):
        mock_client = MagicMock()
        container = MagicMock()
        container.status = "exited"
        mock_client.containers.get.return_value = container
        svc = _real_client_service(mock_client)

        stats = await svc.get_container_stats("websocket-ingestion")
        assert stats is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_stats_calculation(self):
        mock_client = MagicMock()
        container = MagicMock()
        container.status = "running"
        container.stats.return_value = {
            "cpu_stats": {
                "cpu_usage": {"total_usage": 500_000_000, "percpu_usage": [1, 2, 3, 4]},
                "system_cpu_usage": 2_000_000_000,
            },
            "precpu_stats": {
                "cpu_usage": {"total_usage": 400_000_000},
                "system_cpu_usage": 1_000_000_000,
            },
            "memory_stats": {
                "usage": 128 * 1024 * 1024,
                "limit": 512 * 1024 * 1024,
            },
        }
        mock_client.containers.get.return_value = container
        svc = _real_client_service(mock_client)

        stats = await svc.get_container_stats("websocket-ingestion")
        assert stats is not None
        # cpu_delta=100M, system_delta=1B, 4 CPUs => (100M/1B)*4*100 = 40.0
        assert stats["cpu_percent"] == 40.0
        assert stats["memory_usage"] == 128 * 1024 * 1024
        assert stats["memory_limit"] == 512 * 1024 * 1024
        assert stats["memory_percent"] == 25.0
        assert "timestamp" in stats

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_exception_returns_none(self):
        mock_client = MagicMock()
        mock_client.containers.get.side_effect = Exception("fail")
        svc = _real_client_service(mock_client)

        stats = await svc.get_container_stats("websocket-ingestion")
        assert stats is None


# ---------------------------------------------------------------------------
# _get_mock_containers (internal)
# ---------------------------------------------------------------------------

class TestMockContainersFallback:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_all_mapped_services(self):
        svc = _mock_mode_service()
        result = await svc._get_mock_containers()
        assert len(result) == len(svc.container_mapping)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_all_are_project_containers(self):
        svc = _mock_mode_service()
        result = await svc._get_mock_containers()
        assert all(c.is_project_container for c in result)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_all_have_homeiq_label(self):
        svc = _mock_mode_service()
        result = await svc._get_mock_containers()
        for c in result:
            assert c.labels.get("com.docker.compose.project") == "homeiq"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_influxdb_mock_port(self):
        svc = _mock_mode_service()
        result = await svc._get_mock_containers()
        by_service = {c.service_name: c for c in result}
        assert by_service["influxdb"].ports == {"8086/tcp": "8086"}


# ---------------------------------------------------------------------------
# DockerService __init__
# ---------------------------------------------------------------------------

class TestDockerServiceInit:

    @pytest.mark.unit
    def test_init_fallback_to_mock_mode(self):
        """When docker.from_env() fails, client should be None."""
        with patch("src.docker_service.docker") as mock_docker:
            mock_docker.from_env.side_effect = Exception("no docker")
            mock_docker.DockerClient.side_effect = Exception("no docker")
            svc = DockerService()
        assert svc.client is None
        assert "websocket-ingestion" in svc.container_mapping

    @pytest.mark.unit
    def test_init_tcp_success(self):
        """TCP DOCKER_HOST path should connect via DockerClient."""
        with patch("src.docker_service.docker") as mock_docker, \
             patch.dict("os.environ", {"DOCKER_HOST": "tcp://localhost:2375"}):
            mock_client = MagicMock()
            mock_docker.DockerClient.return_value = mock_client
            svc = DockerService()
        assert svc.client is mock_client

    @pytest.mark.unit
    def test_init_tcp_failure(self):
        """TCP DOCKER_HOST failure should fall back to None."""
        with patch("src.docker_service.docker") as mock_docker, \
             patch.dict("os.environ", {"DOCKER_HOST": "tcp://localhost:2375"}):
            mock_docker.DockerClient.side_effect = Exception("refused")
            svc = DockerService()
        assert svc.client is None
