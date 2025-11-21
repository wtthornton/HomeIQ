"""
Shared namespace package for historical tests.

Some legacy suites import modules via the ``tests.*`` namespace (for example
``tests.test_api_keys``). At the same time, many restored tests now live under
service-specific folders such as ``services/admin-api/tests``. This loader bridges
both worlds by lazily resolving missing ``tests.<module>`` imports to the
service-level test files of the same name.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SERVICE_TEST_DIRS = [
    path for path in (_ROOT / "services").glob("*/tests") if path.is_dir()
]

# Allow Python's standard import machinery to discover submodules via these paths.
__path__ = [str(Path(__file__).resolve().parent)] + [
    str(path) for path in _SERVICE_TEST_DIRS
]


def __getattr__(name: str):
    """Handle ``tests.<module>`` lookups for service-local test files."""
    module_name = f"{__name__}.{name}"

    # If another loader already created the module, return it.
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing

    target_file = _find_test_file(name)
    if target_file is None:
        msg = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(msg)

    spec = importlib.util.spec_from_file_location(module_name, target_file)
    if spec is None or spec.loader is None:
        msg = f"unable to load test module {module_name!r}"
        raise AttributeError(msg)

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _find_test_file(name: str) -> Path | None:
    candidate_filename = f"{name}.py"
    for test_dir in _SERVICE_TEST_DIRS:
        candidate = test_dir / candidate_filename
        if candidate.is_file():
            return candidate
    return None
