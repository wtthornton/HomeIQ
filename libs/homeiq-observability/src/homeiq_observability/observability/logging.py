"""
Structured Logging Configuration with Trace Context Integration

Enhances shared/logging_config.py with OpenTelemetry trace context integration.
"""

import logging
import os
from typing import Optional

# Import existing logging config
from ..logging_config import (
    setup_logging as _setup_logging,
    StructuredFormatter,
    get_logger as _get_logger
)

logger = logging.getLogger(__name__)

# OpenTelemetry imports (optional)
try:
    from opentelemetry import trace
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False


class TraceAwareFormatter(StructuredFormatter):
    """
    Enhanced structured formatter that includes OpenTelemetry trace context.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with trace context"""
        # Get base formatted log entry
        log_entry_str = super().format(record)
        
        # Parse JSON (since StructuredFormatter returns JSON string)
        import json
        try:
            log_entry = json.loads(log_entry_str)
        except json.JSONDecodeError:
            # Fallback if not JSON
            return log_entry_str
        
        # Add trace context if OpenTelemetry is available
        if OPENTELEMETRY_AVAILABLE:
            try:
                span = trace.get_current_span()
                if span and span.is_recording():
                    span_context = span.get_span_context()
                    if span_context.is_valid:
                        log_entry["trace_id"] = format(span_context.trace_id, '032x')
                        log_entry["span_id"] = format(span_context.span_id, '016x')
                        log_entry["trace_flags"] = format(span_context.trace_flags, '02x')
            except Exception:
                # Silently fail if trace context unavailable
                pass
        
        return json.dumps(log_entry, default=str)


def setup_structured_logging(service_name: str, log_level: Optional[str] = None, enable_trace_context: bool = True) -> logging.Logger:
    """
    Set up structured logging with optional trace context integration.
    
    Args:
        service_name: Name of the service
        log_level: Logging level (defaults to LOG_LEVEL env var or INFO)
        enable_trace_context: If True, include OpenTelemetry trace context in logs
        
    Returns:
        Configured logger instance
    """
    # Use existing setup_logging but with trace-aware formatter if enabled
    if enable_trace_context and OPENTELEMETRY_AVAILABLE:
        # Create logger manually with trace-aware formatter
        level = log_level or os.getenv('LOG_LEVEL', 'INFO')
        format_type = os.getenv('LOG_FORMAT', 'json')
        output = os.getenv('LOG_OUTPUT', 'stdout')
        
        logger_instance = logging.getLogger(service_name)
        logger_instance.setLevel(getattr(logging, level.upper()))
        logger_instance.handlers.clear()
        
        # Use trace-aware formatter for JSON format
        if format_type.lower() == 'json':
            formatter = TraceAwareFormatter(service_name)
        else:
            formatter = logging.Formatter(
                fmt='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        # Add handlers
        import sys
        if output in ['stdout', 'both']:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            logger_instance.addHandler(console_handler)
        
        logger_instance.propagate = False
        return logger_instance
    else:
        # Use existing setup
        return _setup_logging(service_name, log_level)

