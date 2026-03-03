import importlib.util
import os
import sys

import pytest

# Add service src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

_has_influxdb = importlib.util.find_spec("influxdb_client_3") is not None

requires_influxdb = pytest.mark.skipif(
    not _has_influxdb,
    reason="influxdb_client_3 dependency not installed",
)
