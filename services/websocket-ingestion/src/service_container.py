"""
Service Container for WebSocket Ingestion Service

Uses shared service container base class for dependency injection.
"""

import os
import sys
from pathlib import Path

# Add shared directory to path for imports
shared_path_override = os.getenv('HOMEIQ_SHARED_PATH')
try:
    app_root = Path(__file__).resolve().parents[2]  # Go up to project root
except Exception:
    app_root = Path("/app")

candidate_paths = []
if shared_path_override:
    candidate_paths.append(Path(shared_path_override).expanduser())
candidate_paths.extend([
    app_root / "shared",
    Path("/app/shared"),
    Path.cwd() / "shared",
    Path(__file__).parent.parent.parent.parent / "shared",  # Fallback for local dev
])

shared_path = None
for p in candidate_paths:
    if p.exists():
        shared_path = p.resolve()
        break

if shared_path and str(shared_path) not in sys.path:
    sys.path.insert(0, str(shared_path))

import logging

from service_container import BaseServiceContainer

logger = logging.getLogger(__name__)


class WebSocketIngestionServiceContainer(BaseServiceContainer):
    """
    Service container for WebSocket Ingestion service.
    
    Manages dependencies like ConnectionManager, BatchProcessor, etc.
    """

    def __init__(self):
        super().__init__()
        # Services will be registered in main.py during initialization

