"""
Shared test configuration for sports-api
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add service root and src/ directory to sys.path for imports
_service_root = str(Path(__file__).resolve().parent.parent)
_service_src = str(Path(__file__).resolve().parent.parent / "src")
if _service_root not in sys.path:
    sys.path.insert(0, _service_root)
if _service_src not in sys.path:
    sys.path.insert(0, _service_src)

# Stub homeiq_observability before any test module imports src.main —
# the real package is not installed in the test environment.
sys.modules['homeiq_observability'] = MagicMock()
sys.modules['homeiq_observability.logging_config'] = MagicMock()
sys.modules['homeiq_observability.logging_config'].setup_logging = MagicMock(return_value=MagicMock())
