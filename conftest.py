from __future__ import annotations

"""
Pytest bootstrap helpers shared across the workspace.

Ensures service `src/` directories are importable regardless of where tests
live (e.g. `services/*/tests`). This avoids the old `tests.*` namespace hacks
that broke once directories with hyphens were introduced.
"""

import sys
from importlib import import_module
from pathlib import Path


def _insert_unique(path: Path) -> None:
    """Add path to sys.path if absent."""
    resolved = str(path.resolve())
    if resolved not in sys.path:
        sys.path.insert(0, resolved)


# Ignore legacy helper scripts that do not represent real tests.
collect_ignore = ["services/ai-automation-service/scripts/simple_test.py"]


def pytest_sessionstart(session):  # pragma: no cover - test harness hook
    """Ensure unified `src` namespace is loaded before any tests import it."""
    project_root = Path(__file__).resolve().parent
    _insert_unique(project_root)

    print("[conftest] Initialising unified src namespace")

    sys.modules.pop("src", None)
    module = import_module("src")
    sys.modules["src"] = module

    for name in ("devices_endpoints", "weather_cache", "weather_client"):
        try:
            submodule = import_module(f"src.{name}")
            setattr(module, name, submodule)
        except ModuleNotFoundError:
            print(f"[conftest] Submodule {name} not found during bootstrap")
            continue
