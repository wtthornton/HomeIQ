"""
OpenTelemetry Tracing Setup

Provides distributed tracing capabilities for all services.
"""

import logging
from typing import Optional, Callable, Any
from functools import wraps
import os

logger = logging.getLogger(__name__)

# OpenTelemetry imports (optional - will fail gracefully if not installed)
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False
    logger.warning("OpenTelemetry not available. Install with: pip install opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-fastapi")


def setup_tracing(service_name: str, otlp_endpoint: Optional[str] = None) -> bool:
    """
    Set up OpenTelemetry tracing for a service.
    
    Args:
        service_name: Name of the service
        otlp_endpoint: Optional OTLP endpoint URL (e.g., "http://jaeger:4317")
        
    Returns:
        True if tracing was set up successfully, False otherwise
    """
    if not OPENTELEMETRY_AVAILABLE:
        logger.warning("OpenTelemetry not available, skipping tracing setup")
        return False
    
    try:
        # Create resource with service name
        resource = Resource.create({
            "service.name": service_name,
            "service.version": os.getenv("SERVICE_VERSION", "1.0.0")
        })
        
        # Create tracer provider
        provider = TracerProvider(resource=resource)
        
        # Add span processor
        if otlp_endpoint:
            # Export to OTLP collector
            otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            logger.info(f"✅ Tracing configured with OTLP endpoint: {otlp_endpoint}")
        else:
            # Console exporter for development
            console_exporter = ConsoleSpanExporter()
            provider.add_span_processor(BatchSpanProcessor(console_exporter))
            logger.info("✅ Tracing configured with console exporter")
        
        # Set global tracer provider
        trace.set_tracer_provider(provider)
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to set up tracing: {e}", exc_info=True)
        return False


def trace_function(operation_name: Optional[str] = None):
    """
    Decorator to trace async functions.
    
    Args:
        operation_name: Optional operation name (defaults to function name)
        
    Example:
        @trace_function("process_event")
        async def process_event(event):
            ...
    """
    def decorator(func: Callable) -> Callable:
        if not OPENTELEMETRY_AVAILABLE:
            # Return function unchanged if OpenTelemetry not available
            return func
        
        op_name = operation_name or func.__name__
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span(op_name) as span:
                try:
                    # Add function arguments as span attributes
                    if args:
                        span.set_attribute("function.args_count", len(args))
                    if kwargs:
                        for key, value in kwargs.items():
                            if isinstance(value, (str, int, float, bool)):
                                span.set_attribute(f"function.{key}", value)
                    
                    result = await func(*args, **kwargs)
                    span.set_status(trace.Status(trace.StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span(op_name) as span:
                try:
                    # Add function arguments as span attributes
                    if args:
                        span.set_attribute("function.args_count", len(args))
                    if kwargs:
                        for key, value in kwargs.items():
                            if isinstance(value, (str, int, float, bool)):
                                span.set_attribute(f"function.{key}", value)
                    
                    result = func(*args, **kwargs)
                    span.set_status(trace.Status(trace.StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
        
        # Return appropriate wrapper based on whether function is async
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def instrument_fastapi(app, service_name: str):
    """
    Instrument FastAPI app with OpenTelemetry.
    
    Args:
        app: FastAPI application instance
        service_name: Name of the service
    """
    if not OPENTELEMETRY_AVAILABLE:
        logger.warning("OpenTelemetry not available, skipping FastAPI instrumentation")
        return False
    
    try:
        FastAPIInstrumentor.instrument_app(app)
        logger.info(f"✅ FastAPI app instrumented for tracing: {service_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to instrument FastAPI app: {e}", exc_info=True)
        return False

