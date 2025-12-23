"""Utility helpers for restoring legacy test import behaviour."""

from __future__ import annotations

import sys
from pathlib import Path
import importlib.util


def add_service_src(conftest_file: str) -> None:
    """
    Insert the adjacent ``src`` directory for a service test suite.

    Parameters
    ----------
    conftest_file:
        ``__file__`` from the caller's conftest module.
    """

    test_dir = Path(conftest_file).resolve().parent
    service_dir = test_dir.parent
    src_dir = service_dir / "src"
    if not src_dir.is_dir():
        return

    resolved = src_dir.resolve()

    _prune_other_service_modules(resolved)
    _prune_other_service_test_modules(test_dir)
    _prune_other_service_paths(resolved)

    resolved_str = str(resolved)
    if resolved_str not in sys.path:
        sys.path.insert(0, resolved_str)

    init_file = src_dir / "__init__.py"
    if not init_file.is_file():
        return

    spec = importlib.util.spec_from_file_location("src", init_file)
    if spec is None or spec.loader is None:
        return

    module = importlib.util.module_from_spec(spec)
    sys.modules["src"] = module
    module.__path__ = [str(resolved)]
    spec.loader.exec_module(module)


def _prune_other_service_paths(current: Path) -> None:
    for existing in sys.path[:]:
        try:
            existing_path = Path(existing).resolve()
            if existing_path == current:
                continue
            if _is_service_src(existing_path) and existing_path != current:
                sys.path.remove(existing)
        except (OSError, ValueError):
            pass


def _prune_other_service_modules(current: Path) -> None:
    to_delete = []
    for name, module in sys.modules.items():
        module_file = getattr(module, "__file__", None)
        if not module_file:
            continue
        try:
            module_path = Path(module_file).resolve()
            if _is_service_src(module_path) and not module_path.is_relative_to(current):
                to_delete.append(name)
        except (OSError, ValueError, AttributeError, TypeError):
            pass

    for name in to_delete:
        sys.modules.pop(name, None)


def _prune_other_service_test_modules(current_tests: Path) -> None:
    to_delete = []
    for name, module in sys.modules.items():
        module_file = getattr(module, "__file__", None)
        if not module_file:
            continue
        try:
            module_path = Path(module_file).resolve()
            if _is_service_test(module_path) and not module_path.is_relative_to(current_tests):
                to_delete.append(name)
        except (OSError, ValueError, AttributeError, TypeError):
            pass

    for name in to_delete:
        sys.modules.pop(name, None)


def _is_service_src(path: Path) -> bool:
    parts = path.parts
    if "services" not in parts:
        return False
    return "src" in parts


def _is_service_test(path: Path) -> bool:
    parts = path.parts
    return "services" in parts and "tests" in parts

