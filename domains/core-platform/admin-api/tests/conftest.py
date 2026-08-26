from __future__ import annotations

import importlib.util
import os
from pathlib import Path

from homeiq_data.auth import SIGNING_KEY_ENV


# Load path_setup dynamically from repo root
def _load_add_service_src():
    repo_root = Path(__file__).resolve().parents[4]
    path_setup = repo_root / "tests" / "path_setup.py"
    spec = importlib.util.spec_from_file_location("repo_tests.path_setup", path_setup)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load shared test path utilities")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.add_service_src


add_service_src = _load_add_service_src()
add_service_src(__file__)

# Configure the JWT signing key the way compose configures it (TAP-6580).
# ``AuthManager`` refuses to start without ``ADMIN_API_JWT_SECRET`` rather than
# minting a per-process random key, so the suite carries the same obligation a
# deployment does. This runs at conftest import because several test modules
# build ``AdminAPIService`` at module scope, i.e. before any fixture can fire.
os.environ.setdefault(SIGNING_KEY_ENV, "admin-api-test-signing-key")
