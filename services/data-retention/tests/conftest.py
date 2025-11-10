from tests.path_setup import add_service_src

add_service_src(__file__)

import importlib.util

import pytest

if importlib.util.find_spec("influxdb_client_3") is None:
    pytest.skip(
        "influxdb_client_3 dependency not installed; skipping data-retention tests",
        allow_module_level=True,
    )
