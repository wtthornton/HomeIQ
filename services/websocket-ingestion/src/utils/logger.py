"""
Logger utility for websocket-ingestion service.
Exports logger to avoid circular imports.
"""

import sys
from pathlib import Path

# Add shared directory to path for imports
shared_path_override = None
try:
    import os
    shared_path_override = os.getenv('HOMEIQ_SHARED_PATH')
except Exception:
    pass

# Resolve a robust default shared path
try:
    app_root = Path(__file__).resolve().parents[2]  # typically /app
except Exception:
    app_root = Path("/app")

candidate_paths = []
if shared_path_override:
    candidate_paths.append(Path(shared_path_override).expanduser())
candidate_paths.extend([
    app_root / "shared",
    Path("/app/shared"),
    Path.cwd() / "shared",
])

shared_path: Path | None = None
for p in candidate_paths:
    if p.exists():
        shared_path = p.resolve()
        break

if shared_path and str(shared_path) not in sys.path:
    sys.path.append(str(shared_path))
elif not shared_path:
    import logging
    logging.warning("[websocket-ingestion] Warning: could not locate 'shared' directory in expected locations")

from shared.logging_config import setup_logging

# Create and export logger
logger = setup_logging('websocket-ingestion')

