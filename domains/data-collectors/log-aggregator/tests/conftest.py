"""
Shared test configuration for log-aggregator
"""

import sys
from pathlib import Path

# Add service root and src/ directory to sys.path for imports
_service_root = str(Path(__file__).resolve().parent.parent)
_service_src = str(Path(__file__).resolve().parent.parent / "src")
if _service_root not in sys.path:
    sys.path.insert(0, _service_root)
if _service_src not in sys.path:
    sys.path.insert(0, _service_src)


import pytest


@pytest.fixture(autouse=True)
def _isolated_log_directory(tmp_path, monkeypatch):
    """Point the aggregator's log directory at a temp dir.

    The default is /app/logs (the in-container path); constructing a
    LogAggregator outside a container would otherwise try to mkdir under /.
    """
    from config import settings

    monkeypatch.setattr(settings, "log_directory", str(tmp_path / "logs"))
    return tmp_path / "logs"
