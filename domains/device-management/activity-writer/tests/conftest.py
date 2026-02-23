"""Pytest fixtures for activity-writer tests."""

import sys
from pathlib import Path

# Add src to path so imports work when run from service root
_service_root = Path(__file__).resolve().parent.parent
if str(_service_root) not in sys.path:
    sys.path.insert(0, str(_service_root))

