"""AI Core Service - Orchestrator.

Phase 1: Containerized AI Models

Responsibilities:
- Service orchestration
- Request routing
- Circuit breaker patterns
- Fallback mechanisms
- Business logic
"""

import asyncio
import logging
import secrets
import sys
import time
from collections import deque
from typing import Any

from fastapi import Depends, HTTPException, Request, Security
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from homeiq_resilience import ServiceLifespan, StandardHealthCheck, create_app
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse

from .config import settings
from .models import (
    AnalysisRequest,
    AnalysisResponse,
    PatternDetectionRequest,
    PatternDetectionResponse,
    SuggestionRequest,
    SuggestionResponse,
)
from .orchestrator.service_manager import ServiceManager

# Agent Evaluation Framework: SessionTracer wiring (E3.S7)
try:
    from homeiq_patterns.evaluation.session_tracer import PersistentSink, trace_session

    _eval_sink = PersistentSink()  # Persists traces to database (EVAL_STORE_PATH env var)
    _TRACING_AVAILABLE = True
except ImportError:
    _TRACING_AVAILABLE = False


def _trace_decorator():
    """Return the trace_session decorator if available, otherwise a no-op."""
    if _TRACING_AVAILABLE:
        return trace_session(
            agent_name="ai-core-service",
            sink=_eval_sink,
            model="orchestrator",
        )
    return lambda f: f


# Configure structured logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Rate limiter & auth (service-specific)
# ---------------------------------------------------------------------------


class RateLimiter:
    """Simple in-memory sliding window rate limiter with stale entry eviction."""

    def __init__(self, limit: int, window_seconds: int):
        self.limit = max(limit, 1)
        self.window = max(window_seconds, 1)
        self._requests: dict[str, deque[float]] = {}
        self._lock = asyncio.Lock()

    async def check(self, identifier: str) -> None:
        """Check and record a request for the given identifier."""
        async with self._lock:
            now = time.monotonic()
            window_start = now - self.window

            # Periodic cleanup: remove stale identifiers when dict grows large
            if len(self._requests) > 1000:
                stale_keys = [
                    k
                    for k, v in self._requests.items()
                    if not v or v[-1] < window_start
                ]
                for k in stale_keys:
                    del self._requests[k]

            entries = self._requests.setdefault(identifier, deque())

            while entries and entries[0] < window_start:
                entries.popleft()

            if len(entries) >= self.limit:
                raise HTTPException(status_code=429, detail="Rate limit exceeded")

            entries.append(now)


rate_limiter = RateLimiter(settings.ai_core_rate_limit, settings.ai_core_rate_limit_window)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject request bodies larger than the configured limit."""

    def __init__(self, app: Any, max_content_length: int = 1_048_576):  # 1MB default
        super().__init__(app)
        self.max_content_length = max_content_length

    async def dispatch(
        self, request: StarletteRequest, call_next: Any
    ) -> StarletteResponse:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_content_length:
            return JSONResponse(
                status_code=413,
                content={"detail": "Request body too large"},
            )
        return await call_next(request)


async def verify_api_key(
    request: Request,
    provided_key: str | None = Security(api_key_header),
) -> str:
    """Validate API key from request headers."""
    api_key_value = getattr(request.app.state, "api_key_value", None)

    if api_key_value is None:
        raise HTTPException(status_code=503, detail="Service not ready")

    if not provided_key:
        raise HTTPException(status_code=401, detail="Missing API key")

    if not secrets.compare_digest(provided_key, api_key_value):
        raise HTTPException(status_code=401, detail="Invalid API key")

    return provided_key


async def enforce_rate_limit(
    request: Request,
    api_key: str = Depends(verify_api_key),
) -> None:
    """Enforce per-client + key rate limiting."""
    client_host = request.client.host if request.client else "unknown"
    identifier = f"{client_host}:{api_key}"
    await rate_limiter.check(identifier)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


async def _startup_services() -> None:
    """Initialize service manager and downstream connections."""
    api_key = settings.ai_core_api_key
    if not api_key:
        raise RuntimeError("AI_CORE_API_KEY environment variable must be set")

    manager = ServiceManager(
        openvino_url=settings.openvino_service_url,
        ml_url=settings.ml_service_url,
        ner_url=settings.ner_service_url,
        openai_url=settings.openai_service_url,
    )
    await manager.initialize()

    # Store on module level for access in lifespan/shutdown
    _startup_services._manager = manager
    _startup_services._api_key = api_key.get_secret_value()


async def _shutdown_services() -> None:
    """Shutdown service manager."""
    manager = getattr(_startup_services, "_manager", None)
    if manager:
        await manager.aclose()
    _startup_services._manager = None
    _startup_services._api_key = None


lifespan = ServiceLifespan(settings.service_name, graceful=False)
lifespan.on_startup(_startup_services, name="service-manager")
lifespan.on_shutdown(_shutdown_services, name="service-manager")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


async def _check_downstream_health() -> bool:
    """Check if any downstream service is healthy."""
    manager = getattr(_startup_services, "_manager", None)
    if not manager:
        return False
    service_status = await manager.get_service_status()
    return any(s.get("healthy") for s in service_status.values())


health = StandardHealthCheck(
    service_name=settings.service_name,
    version="1.0.0",
)
health.register_check("downstream-services", _check_downstream_health)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = create_app(
    title="AI Core Service",
    version="1.0.0",
    description="Orchestrator for containerized AI models",
    lifespan=lifespan.handler,
    health_check=health,
    cors_origins=settings.get_cors_origins_list(),
)

# Add request body size limit middleware (2MB)
app.add_middleware(RequestSizeLimitMiddleware, max_content_length=settings.max_content_length)


# Store references on app.state after startup via middleware
@app.middleware("http")
async def _inject_state(request: Request, call_next: Any) -> Any:
    """Inject service manager and api key into app.state for dependency injection."""
    manager = getattr(_startup_services, "_manager", None)
    api_key = getattr(_startup_services, "_api_key", None)
    request.app.state.service_manager = manager
    request.app.state.api_key_value = api_key
    return await call_next(request)


# ---------------------------------------------------------------------------
# Helper to get service_manager from app.state
# ---------------------------------------------------------------------------


def _get_service_manager(request: Request) -> ServiceManager:
    """Retrieve service manager from app state, raising 503 if not ready."""
    manager = getattr(request.app.state, "service_manager", None)
    if not manager:
        raise HTTPException(status_code=503, detail="Service not ready")
    return manager


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------


@app.get("/services/status", tags=["health"])
async def get_service_status(
    request: Request,
    _: None = Depends(enforce_rate_limit),
) -> Any:
    """Get detailed service status."""
    manager = _get_service_manager(request)
    return await manager.get_service_status()


@app.post("/analyze", response_model=AnalysisResponse, tags=["analysis"])
@_trace_decorator()
async def analyze_data(
    request: Request,
    body: AnalysisRequest,
    _: None = Depends(enforce_rate_limit),
) -> AnalysisResponse:
    """Perform comprehensive data analysis."""
    manager = _get_service_manager(request)

    try:
        start_time = time.time()

        results, services_used = await manager.analyze_data(
            data=body.data,
            analysis_type=body.analysis_type,
            options=body.options,
        )

        processing_time = time.time() - start_time

        return AnalysisResponse(
            results=results,
            services_used=services_used,
            processing_time=processing_time,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in data analysis")
        raise HTTPException(status_code=500, detail="Analysis failed") from e


@app.post("/patterns", response_model=PatternDetectionResponse, tags=["patterns"])
@_trace_decorator()
async def detect_patterns(
    request: Request,
    body: PatternDetectionRequest,
    _: None = Depends(enforce_rate_limit),
) -> PatternDetectionResponse:
    """Detect patterns in data."""
    manager = _get_service_manager(request)

    try:
        start_time = time.time()

        patterns, services_used = await manager.detect_patterns(
            patterns=body.patterns,
            detection_type=body.detection_type,
        )

        processing_time = time.time() - start_time

        return PatternDetectionResponse(
            detected_patterns=patterns,
            services_used=services_used,
            processing_time=processing_time,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in pattern detection")
        raise HTTPException(status_code=500, detail="Pattern detection failed") from e


@app.post("/suggestions", response_model=SuggestionResponse, tags=["suggestions"])
async def generate_suggestions(
    request: Request,
    body: SuggestionRequest,
    _: None = Depends(enforce_rate_limit),
) -> SuggestionResponse:
    """Generate AI suggestions."""
    manager = _get_service_manager(request)

    try:
        start_time = time.time()

        suggestions, services_used = await manager.generate_suggestions(
            context=body.context,
            suggestion_type=body.suggestion_type,
        )

        processing_time = time.time() - start_time

        return SuggestionResponse(
            suggestions=suggestions,
            services_used=services_used,
            processing_time=processing_time,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error generating suggestions")
        raise HTTPException(status_code=500, detail="Suggestion generation failed") from e


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=settings.service_port, reload=True)  # noqa: S104
