"""Docker routes answer 503 when the socket is unusable — never fabricate.

TAP-5999: mock mode returned 200s with invented logs/stats/containers,
rendering a broken socket as a working fleet. The service now raises
DockerUnavailableError and every route translates it to 503.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent / ".."))

from src.docker_service import DockerService, DockerUnavailableError


def _service_without_client() -> DockerService:
    service = DockerService()
    service.client = None
    return service


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "call",
    [
        lambda s: s.list_containers(),
        lambda s: s.start_container("data-api"),
        lambda s: s.stop_container("data-api"),
        lambda s: s.restart_container("data-api"),
        lambda s: s.get_container_logs("data-api"),
        lambda s: s.get_container_stats("data-api"),
    ],
    ids=["list", "start", "stop", "restart", "logs", "stats"],
)
async def test_every_docker_operation_raises_when_socket_unavailable(call):
    with pytest.raises(DockerUnavailableError):
        await call(_service_without_client())


def test_no_mock_fabrication_remains_in_the_service():
    """The word is gone from behavior: no code path invents container data."""
    import inspect

    from src import docker_service

    src_text = inspect.getsource(docker_service)
    assert "_get_mock_containers" not in src_text
    assert "Mock logs for" not in src_text
    assert "Mock: Container" not in src_text
