"""
Shared Observability Module

Provides tracing, logging, and correlation ID utilities for all services.
"""

from .tracing import setup_tracing, trace_function, instrument_fastapi
from .logging import setup_structured_logging
from .correlation import (
    CorrelationMiddleware,
    get_correlation_id_from_request,
    set_correlation_id_in_request
)

# Re-export from logging_config for backward compatibility
from ..logging_config import get_correlation_id, set_correlation_id

__all__ = [
    'setup_tracing',
    'trace_function',
    'instrument_fastapi',
    'setup_structured_logging',
    'CorrelationMiddleware',
    'get_correlation_id',
    'set_correlation_id',
    'get_correlation_id_from_request',
    'set_correlation_id_in_request',
]

