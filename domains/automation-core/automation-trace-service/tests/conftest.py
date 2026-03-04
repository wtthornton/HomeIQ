"""Pytest configuration for automation-trace-service tests."""

import sys
from pathlib import Path

# Add the service root directory to the Python path
service_root = Path(__file__).resolve().parent.parent
if str(service_root) not in sys.path:
    sys.path.insert(0, str(service_root))
