from tests.path_setup import add_service_src

add_service_src(__file__)

import os

# TAP-6035: TestClient requests carry Host "testserver" — a DNS name, which
# the rebinding guard refuses unless configured. Set before src.config's
# cached Settings is first built.
os.environ.setdefault("EXPECTED_HOSTS", "testserver")

import pytest

requires_ha_environment = pytest.mark.skipif(
    not os.getenv("HA_SETUP_TESTS"),
    reason="HA_SETUP_TESTS env var not set; skipping tests requiring live HA",
)
