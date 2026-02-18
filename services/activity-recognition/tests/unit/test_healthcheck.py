"""Unit tests for healthcheck script."""

import sys
from pathlib import Path

# Ensure service root is on path so "healthcheck" module is found
_service_root = Path(__file__).resolve().parent.parent.parent
if str(_service_root) not in sys.path:
    sys.path.insert(0, str(_service_root))

from healthcheck import _get_port  # noqa: E402


def test_get_port_default() -> None:
    """_get_port returns default when env unset or invalid."""
    assert _get_port() in range(1, 65536)
