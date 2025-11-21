"""
Shared Observability Module

Provides tracing, logging, and correlation ID utilities for all services.
"""

# Re-export from logging_config for backward compatibility
from ..logging_config import get_correlation_id, set_correlation_id
from .correlation import CorrelationMiddleware, get_correlation_id_from_request, set_correlation_id_in_request
from .logging import setup_structured_logging
from .tracing import instrument_fastapi, setup_tracing, trace_function

__all__ = [
    "CorrelationMiddleware",
    "get_correlation_id",
    "get_correlation_id_from_request",
    "instrument_fastapi",
    "set_correlation_id",
    "set_correlation_id_in_request",
    "setup_structured_logging",
    "setup_tracing",
    "trace_function",
]

