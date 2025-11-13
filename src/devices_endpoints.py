"""Shim module routing `src.devices_endpoints` to admin API implementation."""

from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parent.parent / "services" / "admin-api" / "src" / "devices_endpoints.py"
)
SPEC = spec_from_file_location(
    "src.devices_endpoints", MODULE_PATH, submodule_search_locations=[str(MODULE_PATH.parent)]
)
MODULE = module_from_spec(SPEC)
MODULE.__package__ = "src"
sys.modules["src.devices_endpoints"] = MODULE

assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)

for name in dir(MODULE):
    if not name.startswith("_"):
        globals()[name] = getattr(MODULE, name)

__all__ = [name for name in globals() if not name.startswith("_")]

