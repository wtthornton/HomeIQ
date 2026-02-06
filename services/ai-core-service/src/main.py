"""
AI Core Service - Orchestrator
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
import os
import secrets
import sys
import time
import uuid
from collections import deque
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field, field_validator
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse

from .orchestrator.service_manager import ServiceManager

# Configure structured logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def _parse_allowed_origins() -> list[str]:
    """Parse comma-delimited allowed origins from environment."""
    raw_origins = os.getenv("AI_CORE_ALLOWED_ORIGINS")
    if raw_origins:
        parsed = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
        if parsed:
            return parsed
    return ["http://localhost:3000", "http://localhost:3001"]


RATE_LIMIT_REQUESTS = int(os.getenv("AI_CORE_RATE_LIMIT", "60"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("AI_CORE_RATE_LIMIT_WINDOW", "60"))
ALLOWED_ORIGINS = _parse_allowed_origins()


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
                    k for k, v in self._requests.items()
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


rate_limiter = RateLimiter(RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW_SECONDS)
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


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize service manager on startup."""
    logger.info("Starting AI Core Service...")
    try:
        api_key = os.getenv("AI_CORE_API_KEY")
        if not api_key:
            raise RuntimeError("AI_CORE_API_KEY environment variable must be set")

        # Get service URLs from environment
        openvino_url = os.getenv("OPENVINO_SERVICE_URL", "http://openvino-service:8019")
        ml_url = os.getenv("ML_SERVICE_URL", "http://ml-service:8020")
        ner_url = os.getenv("NER_SERVICE_URL", "http://ner-service:8031")
        openai_url = os.getenv("OPENAI_SERVICE_URL", "http://openai-service:8020")

        manager = ServiceManager(
            openvino_url=openvino_url,
            ml_url=ml_url,
            ner_url=ner_url,
            openai_url=openai_url,
        )

        await manager.initialize()

        app.state.service_manager = manager
        app.state.api_key_value = api_key

        logger.info("AI Core Service started successfully")
    except Exception as e:
        logger.error("Failed to start AI Core Service: %s", e)
        raise

    yield

    # Cleanup on shutdown
    logger.info("AI Core Service shutting down")
    manager = getattr(app.state, "service_manager", None)
    if manager:
        await manager.aclose()
    app.state.service_manager = None
    app.state.api_key_value = None


# Create FastAPI app with OpenAPI tags
app = FastAPI(
    title="AI Core Service",
    description="Orchestrator for containerized AI models",
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "health", "description": "Health and status endpoints"},
        {"name": "analysis", "description": "Data analysis operations"},
        {"name": "patterns", "description": "Pattern detection operations"},
        {"name": "suggestions", "description": "AI suggestion generation"},
    ],
)


# Request ID tracing middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next: Any) -> Any:
    """Add a unique request ID to every request/response for distributed tracing."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Add request body size limit middleware (2MB)
app.add_middleware(RequestSizeLimitMiddleware, max_content_length=2_097_152)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key", "X-Request-ID"],
)


# Helper to get service_manager from app.state
def _get_service_manager(request: Request) -> ServiceManager:
    """Retrieve service manager from app state, raising 503 if not ready."""
    manager = getattr(request.app.state, "service_manager", None)
    if not manager:
        raise HTTPException(status_code=503, detail="Service not ready")
    return manager


# Pydantic models
class AnalysisRequest(BaseModel):
    data: list[dict[str, Any]] = Field(
        ..., description="Data to analyze", min_length=1, max_length=1000
    )
    analysis_type: str = Field(
        ..., description="Type of analysis to perform", min_length=1, max_length=100
    )
    options: dict[str, Any] = Field(
        default_factory=dict, description="Analysis options", max_length=50
    )

    @field_validator("data")
    @classmethod
    def validate_data_size(cls, v: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Validate data size and content."""
        if not v:
            raise ValueError("Data list cannot be empty")
        if len(v) > 1000:
            raise ValueError("Data list cannot exceed 1000 items")
        # Validate each item is a dict and not too large
        for item in v:
            if not isinstance(item, dict):
                raise ValueError("All data items must be dictionaries")
            # Limit individual item size (prevent DoS)
            if len(str(item)) > 10000:
                raise ValueError("Individual data items cannot exceed 10KB")
        return v

    @field_validator("analysis_type")
    @classmethod
    def validate_analysis_type(cls, v: str) -> str:
        """Validate analysis type."""
        allowed_types = {"pattern_detection", "clustering", "anomaly_detection", "basic"}
        if v not in allowed_types:
            raise ValueError(f"Analysis type must be one of: {', '.join(sorted(allowed_types))}")
        return v


class AnalysisResponse(BaseModel):
    results: dict[str, Any] = Field(..., description="Analysis results")
    services_used: list[str] = Field(..., description="Services used in analysis")
    processing_time: float = Field(..., description="Total processing time in seconds")


class PatternDetectionRequest(BaseModel):
    patterns: list[dict[str, Any]] = Field(
        ..., description="Patterns to detect", min_length=1, max_length=500
    )
    detection_type: str = Field(
        "full", description="Type of pattern detection", max_length=50
    )

    @field_validator("patterns")
    @classmethod
    def validate_patterns(cls, v: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Validate patterns list."""
        if not v:
            raise ValueError("Patterns list cannot be empty")
        if len(v) > 500:
            raise ValueError("Patterns list cannot exceed 500 items")
        for pattern in v:
            if not isinstance(pattern, dict):
                raise ValueError("All patterns must be dictionaries")
            if len(str(pattern)) > 5000:
                raise ValueError("Individual patterns cannot exceed 5KB")
        return v

    @field_validator("detection_type")
    @classmethod
    def validate_detection_type(cls, v: str) -> str:
        """Validate detection type."""
        allowed_types = {"full", "basic", "quick"}
        if v not in allowed_types:
            raise ValueError(f"Detection type must be one of: {', '.join(sorted(allowed_types))}")
        return v


class PatternDetectionResponse(BaseModel):
    detected_patterns: list[dict[str, Any]] = Field(..., description="Detected patterns")
    services_used: list[str] = Field(..., description="Services used")
    processing_time: float = Field(..., description="Processing time in seconds")


class SuggestionRequest(BaseModel):
    context: dict[str, Any] = Field(..., description="Context for suggestions")
    suggestion_type: str = Field(
        ..., description="Type of suggestions to generate", min_length=1, max_length=100
    )

    @field_validator("context")
    @classmethod
    def validate_context(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate context size."""
        if not v:
            raise ValueError("Context cannot be empty")
        if len(str(v)) > 5000:
            raise ValueError("Context cannot exceed 5KB")
        return v

    @field_validator("suggestion_type")
    @classmethod
    def validate_suggestion_type(cls, v: str) -> str:
        """Validate suggestion type."""
        allowed_types = {
            "automation_improvements",
            "energy_optimization",
            "comfort",
            "security",
            "convenience",
        }
        if v not in allowed_types:
            raise ValueError(f"Suggestion type must be one of: {', '.join(sorted(allowed_types))}")
        return v


class SuggestionResponse(BaseModel):
    suggestions: list[dict[str, Any]] = Field(..., description="Generated suggestions")
    services_used: list[str] = Field(..., description="Services used")
    processing_time: float = Field(..., description="Processing time in seconds")


# API Endpoints
@app.get("/health", tags=["health"])
async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint reflecting downstream service health."""
    manager = getattr(request.app.state, "service_manager", None)
    if not manager:
        raise HTTPException(status_code=503, detail="Service not ready")

    service_status = await manager.get_service_status()
    any_healthy = any(s.get("healthy") for s in service_status.values())

    status = "healthy" if any_healthy else "degraded"
    status_code = 200 if any_healthy else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": status,
            "service": "ai-core-service",
            "services": service_status,
        },
    )


@app.get("/services/status", tags=["health"])
async def get_service_status(
    request: Request,
    _: None = Depends(enforce_rate_limit),
) -> Any:
    """Get detailed service status."""
    manager = _get_service_manager(request)
    return await manager.get_service_status()


@app.post("/analyze", response_model=AnalysisResponse, tags=["analysis"])
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

    uvicorn.run(app, host="0.0.0.0", port=8018)
