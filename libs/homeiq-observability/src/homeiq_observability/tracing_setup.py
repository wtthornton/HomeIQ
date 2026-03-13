"""OpenTelemetry tracing setup for HomeIQ services.

Configures OTLP export to Jaeger and automatic FastAPI instrumentation.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Service tier and group metadata for span attributes
_SERVICE_TIER: str = ""
_SERVICE_GROUP: str = ""


def setup_tracing(
    service_name: str,
    *,
    group_name: str = "",
    service_tier: str = "",
    otlp_endpoint: str | None = None,
) -> bool:
    """Initialize OpenTelemetry tracing with OTLP export.

    Returns True if tracing was initialized, False if dependencies missing.
    """
    global _SERVICE_TIER, _SERVICE_GROUP
    _SERVICE_TIER = service_tier
    _SERVICE_GROUP = group_name

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
    except ImportError:
        logger.info(
            "OpenTelemetry not installed -- tracing disabled for %s", service_name
        )
        return False

    endpoint = otlp_endpoint or os.getenv(
        "OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger:4318"
    )

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.group": group_name,
            "service.tier": service_tier,
            "deployment.environment": os.getenv("ENVIRONMENT", "production"),
        }
    )

    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces")
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    logger.info(
        "OpenTelemetry tracing initialized: service=%s group=%s tier=%s endpoint=%s",
        service_name,
        group_name,
        service_tier,
        endpoint,
    )
    return True


def instrument_fastapi(app: Any) -> None:
    """Instrument a FastAPI app with OpenTelemetry."""
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        def _server_request_hook(span: Any, scope: dict) -> None:
            if span and span.is_recording():
                if _SERVICE_GROUP:
                    span.set_attribute("service.group", _SERVICE_GROUP)
                if _SERVICE_TIER:
                    span.set_attribute("service.tier", _SERVICE_TIER)

        FastAPIInstrumentor.instrument_app(
            app,
            server_request_hook=_server_request_hook,
        )
    except ImportError:
        pass


def get_tracer(name: str) -> Any:
    """Get an OpenTelemetry tracer (returns no-op if not configured)."""
    try:
        from opentelemetry import trace

        return trace.get_tracer(name)
    except ImportError:
        return None
