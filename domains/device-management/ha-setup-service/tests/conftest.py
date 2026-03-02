from tests.path_setup import add_service_src

add_service_src(__file__)

import os

import pytest

requires_ha_environment = pytest.mark.skipif(
    not os.getenv("HA_SETUP_TESTS"),
    reason="HA_SETUP_TESTS env var not set; skipping tests requiring live HA",
)
