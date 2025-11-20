# WebSocket Ingestion Service
# This service connects to Home Assistant WebSocket API and ingests events

from __future__ import annotations

from pathlib import Path
from pkgutil import extend_path

# Allow other service `src` packages to resolve through this namespace. This keeps
# legacy `import src.*` statements working across the monorepo.
__path__ = extend_path(__path__, __name__)  # type: ignore[name-defined]

_services_root = Path(__file__).resolve().parents[2]  # .../services/websocket-ingestion
for candidate in _services_root.parent.glob("*/src"):
    candidate_path = str(candidate)
    if candidate_path not in __path__:
        __path__.append(candidate_path)
