"""
Service Container for WebSocket Ingestion Service

Uses shared service container base class for dependency injection.
"""

import logging

from homeiq_data.service_container import BaseServiceContainer

logger = logging.getLogger(__name__)


class WebSocketIngestionServiceContainer(BaseServiceContainer):
    """
    Service container for WebSocket Ingestion service.

    Manages dependencies like ConnectionManager, BatchProcessor, etc.
    """

    def __init__(self):
        super().__init__()
        # Services will be registered in main.py during initialization

