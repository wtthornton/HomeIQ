"""
Namespace package shim for legacy `import src.*` paths across services.

We collate every service's `src/` directory so modules can be resolved
regardless of which service initializes the namespace first.
"""

from __future__ import annotations

from pathlib import Path
import importlib
import sys
from pkgutil import extend_path

# Allow sub-packages contributed by service modules to participate.
__path__ = extend_path(__path__, __name__)  # type: ignore[name-defined]

_ROOT = Path(__file__).resolve().parents[1]
_CANDIDATE_DIRS = [
    *(_ROOT / "services").glob("*/src"),
    _ROOT / "shared",
    _ROOT / "tools" / "cli" / "src",
]

for candidate in _CANDIDATE_DIRS:
    if candidate.is_dir():
        candidate_path = str(candidate)
        if candidate_path not in __path__:
            __path__.append(candidate_path)

for _module_name in ("devices_endpoints", "weather_cache", "weather_client"):
    try:
        module = importlib.import_module(f"{__name__}.{_module_name}")
        setattr(sys.modules[__name__], _module_name, module)
    except ModuleNotFoundError:
        continue


def __getattr__(name: str):
    """Lazy import submodules on attribute access."""
    full_name = f"{__name__}.{name}"
    try:
        module = importlib.import_module(full_name)
    except ModuleNotFoundError as exc:
        raise AttributeError(name) from exc

    setattr(sys.modules[__name__], name, module)
    return module

