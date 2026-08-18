"""
Make the service root importable so `from src...` resolves.

This file exists because of a difference between the two ways of starting
pytest: `python -m pytest` prepends the current directory to sys.path, and the
`pytest` console script does not. CI runs the console script, so without this
every `from src...` import raised ModuleNotFoundError and the suite failed
wholesale while passing locally under `python -m pytest`.

Matches the idiom already used by the sibling services in this domain.
Deliberately not a pytest.ini: these tests
currently inherit the repo-root [tool.pytest.ini_options], and adding a
service-level ini would move rootdir here and silently drop that config.
"""

import sys
from pathlib import Path

_service_root = Path(__file__).resolve().parent.parent
if str(_service_root) not in sys.path:
    sys.path.insert(0, str(_service_root))
