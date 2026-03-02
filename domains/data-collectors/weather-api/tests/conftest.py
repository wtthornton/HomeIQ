from tests.path_setup import add_service_src

add_service_src(__file__)

import importlib.util

import pytest

_has_influxdb = importlib.util.find_spec("influxdb_client_3") is not None

requires_influxdb = pytest.mark.skipif(
    not _has_influxdb,
    reason="influxdb_client_3 dependency not installed",
)
