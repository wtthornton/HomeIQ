from tests.path_setup import add_service_src

add_service_src(__file__)

import importlib.util
import os

import pytest

os.environ.setdefault("INFLUXDB_TOKEN", "test-token")

_has_influxdb = importlib.util.find_spec("influxdb_client_3") is not None

requires_influxdb = pytest.mark.skipif(
    not _has_influxdb,
    reason="influxdb_client_3 dependency not installed",
)


@pytest.fixture(scope="session")
def collectors_client():
    """A TestClient over the real merged app, with lifespan started once per session.

    Every adapter's startup hook runs for real against this test environment
    (no live InfluxDB/HA), which is the same degraded-but-running mode the
    live service falls into when a dependency is unreachable — exactly what
    each adapter's own readiness/error-handling code is built to tolerate.
    """
    from fastapi.testclient import TestClient

    from src.main import app

    with TestClient(app) as client:
        yield client
