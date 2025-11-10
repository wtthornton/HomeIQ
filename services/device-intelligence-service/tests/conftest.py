from tests.path_setup import add_service_src

add_service_src(__file__)

import importlib.util

import pytest

if importlib.util.find_spec("src.core") is None:
    pytest.skip(
        "device-intelligence core modules not available; skipping tests in alpha environment",
        allow_module_level=True,
    )
