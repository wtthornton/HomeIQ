from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
if str(TEST_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_DIR))


def _load_add_service_src():
    repo_root = Path(__file__).resolve().parents[3]
    path_setup = repo_root / "tests" / "path_setup.py"
    spec = importlib.util.spec_from_file_location("repo_tests.path_setup", path_setup)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load shared test path utilities")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.add_service_src


add_service_src = _load_add_service_src()
add_service_src(__file__)

import pytest

if importlib.util.find_spec("src.core") is None:
    pytest.skip(
        "device-intelligence core modules not available; skipping tests in alpha environment",
        allow_module_level=True,
    )
