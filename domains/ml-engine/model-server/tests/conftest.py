"""Shared pytest path setup for model-server's merged test suite.

model-server folds three former services' test suites into one flat
``tests/`` directory (openvino-service, ml-service, rag-service — TAP-7276).
Each former suite assumed its own ``src`` package was a sibling of ``tests``;
that is still true here (``model-server/src`` is the sibling), so this
conftest only needs to put the service root, ``src``, and ``tests`` itself
onto ``sys.path`` once, for every test module regardless of which former
service it came from.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

test_dir = Path(__file__).resolve().parent  # model-server/tests
service_dir = test_dir.parent  # model-server
src_dir = service_dir / "src"

for _path in (service_dir, src_dir, test_dir):
    _path_str = str(_path)
    if _path_str not in sys.path:
        sys.path.insert(0, _path_str)

# OpenVINOManager defaults its model cache to /app/models (correct inside the
# production container, where WORKDIR /app is owned by appuser). Outside a
# container that path doesn't exist and isn't writable, so real lifespan
# startup (tests that use `with TestClient(app):`) would fail every time. Set
# this before `src.main` -- and therefore `src.openvino.config` -- is first
# imported, since settings are read from the environment at import time.
os.environ.setdefault("MODEL_CACHE_DIR", str(Path(tempfile.gettempdir()) / "model-server-test-models"))
