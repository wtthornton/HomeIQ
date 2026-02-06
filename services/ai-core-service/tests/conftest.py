"""Pytest configuration for ai-core-service tests."""

import sys
from pathlib import Path

# Add the service src directory to the Python path so tests can import modules
service_root = Path(__file__).resolve().parent.parent
if str(service_root) not in sys.path:
    sys.path.insert(0, str(service_root))
