"""
Shared test configuration for ai-code-executor
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
