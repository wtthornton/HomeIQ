"""
Logger utility for websocket-ingestion service.
Exports logger to avoid circular imports.
"""

from homeiq_observability.logging_config import setup_logging

# Create and export logger
logger = setup_logging('websocket-ingestion')

