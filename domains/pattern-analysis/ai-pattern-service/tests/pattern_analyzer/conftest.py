"""
Minimal conftest for pattern_analyzer tests.

These tests don't need database or full service dependencies.
"""

import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
