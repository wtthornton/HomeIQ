from tests.path_setup import add_service_src

add_service_src(__file__)

import os

import pytest

if not os.getenv("HA_SETUP_TESTS"):
    pytest.skip(
        "ha-setup tests require full Home Assistant environment; skipping in alpha environment",
        allow_module_level=True,
    )
