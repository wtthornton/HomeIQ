"""
Pytest bootstrap helpers shared across the workspace.

Ensures service `src/` directories are importable regardless of where tests
live (e.g. `services/*/tests`). This avoids the old `tests.*` namespace hacks
that broke once directories with hyphens were introduced.
"""

from __future__ import annotations

import sys
from pathlib import Path


def _insert_unique(path: Path) -> None:
    """Add path to sys.path if absent."""
    resolved = str(path.resolve())
    if resolved not in sys.path:
        sys.path.insert(0, resolved)


# Ignore legacy helper scripts that do not represent real tests.
collect_ignore = ["services/ai-automation-service/scripts/simple_test.py"]

