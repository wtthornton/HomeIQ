"""OpenVINO Service - Optimized Model Inference.

Phase 1: Containerized AI Models

Provides optimized model inference for:
- BAAI/bge-large-en-v1.5 (1024-dim) - Embeddings [Epic 47]
- bge-reranker-base - Re-ranking
- flan-t5-small - Classification
"""

import json
import logging
import time
from typing import Any

from fastapi import HTTPException, Request
from homeiq_resilience import ServiceLifespan, StandardHealthCheck, create_app
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest

from .config import settings
from .models.openvino_manager import OpenVINOManager
from .models_api import (
    ClassifyRequest,
    ClassifyResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    RerankRequest,
    RerankResponse,
)

# ---------------------------------------------------------------------------
# Structured JSON Logging (ENH-4)
# ---------------------------------------------------------------------------


class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter for log aggregation systems."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "method"):
            log_entry["method"] = record.method
        if hasattr(record, "path"):
            log_entry["path"] = record.path
        if hasattr(record, "status_code"):
            log_entry["status_code"] = record.status_code
        if hasattr(record, "duration_seconds"):
            log_entry["duration_seconds"] = record.duration_seconds
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


# Configure structured logging
_handler = logging.StreamHandler()
_handler.setFormatter(JSONFormatter())
logging.basicConfig(level=logging.INFO, handlers=[_handler])
logger = logging.getLogger(__name__)

# Global model manager
openvino_manager: OpenVINOManager | None = None


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


async def _startup_models() -> None:
    """Initialize OpenVINO model manager."""
    global openvino_manager
    openvino_manager = OpenVINOManager()
    if settings.openvino_preload_models:
        await openvino_manager.initialize()
        logger.info("OpenVINO models preloaded")
    else:
        logger.info("OpenVINO models will lazy-load on first request")


async def _shutdown_models() -> None:
    """Cleanup OpenVINO model manager."""
    global openvino_manager
    if openvino_manager:
        await openvino_manager.cleanup()
    openvino_manager = None


lifespan = ServiceLifespan(settings.service_name)
lifespan.on_startup(_startup_models, name="openvino-models")
lifespan.on_shutdown(_shutdown_models, name="openvino-models")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


async def _check_model_readiness() -> bool:
    """Check if at least one model is loaded."""
    if not openvino_manager:
        return False
    return openvino_manager.is_ready()


health = StandardHealthCheck(
    service_name=settings.service_name,
    version="1.0.0",
)
health.register_check("models", _check_model_readiness)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = create_app(
    title="OpenVINO Service",
    version="1.0.0",
    description="Optimized model inference using OpenVINO INT8 quantization",
    lifespan=lifespan.handler,
    health_check=health,
    cors_origins=settings.get_cors_origins_list(),
)


# ---------------------------------------------------------------------------
# Middleware (MED-4: Request timing / metrics)
# ---------------------------------------------------------------------------


class MetricsMiddleware(BaseHTTPMiddleware):
    """Log request method, path, status code and duration for every request."""

    async def dispatch(self, request: StarletteRequest, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start
        logger.info(
            "request_completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_seconds": round(duration, 4),
            },
        )
        return response


app.add_middleware(MetricsMiddleware)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_manager() -> OpenVINOManager:
    """Return the global manager or raise 503 if the service is not ready."""
    if not openvino_manager:
        raise HTTPException(status_code=503, detail="Service not ready")
    return openvino_manager


async def _verify_api_key(request: Request) -> None:
    """SEC-2: Validate optional API key header."""
    api_key = settings.openvino_api_key
    if api_key and request.headers.get("X-API-Key") != api_key.get_secret_value():
        raise HTTPException(status_code=401, detail="Invalid API key")


def _validate_text_batch(texts: list[str]) -> None:
    """Validate a batch of texts for the /embeddings endpoint."""
    if not texts:
        raise HTTPException(status_code=400, detail="At least one text is required")
    if len(texts) > settings.openvino_max_embedding_texts:
        raise HTTPException(
            status_code=400,
            detail=f"Too many texts (max {settings.openvino_max_embedding_texts})",
        )

    for idx, text in enumerate(texts):
        if not isinstance(text, str):
            raise HTTPException(status_code=400, detail=f"Text at index {idx} must be a string")
        if len(text) > settings.openvino_max_text_length:
            raise HTTPException(
                status_code=400,
                detail=f"Text at index {idx} exceeds {settings.openvino_max_text_length} characters",
            )
        if not text.strip():
            raise HTTPException(status_code=400, detail="Texts cannot be empty strings")


def _validate_rerank_payload(query: str, candidates: list[dict[str, Any]], top_k: int) -> None:
    """Validate the rerank request payload."""
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Query text is required")
    if len(query) > settings.openvino_max_query_length:
        raise HTTPException(
            status_code=400,
            detail=f"Query exceeds {settings.openvino_max_query_length} characters",
        )

    if not candidates:
        raise HTTPException(status_code=400, detail="At least one candidate is required")
    if len(candidates) > settings.openvino_max_rerank_candidates:
        raise HTTPException(
            status_code=400,
            detail=f"Too many candidates (max {settings.openvino_max_rerank_candidates})",
        )

    for idx, candidate in enumerate(candidates):
        description = str(candidate.get("description", ""))
        if len(description) > settings.openvino_max_text_length:
            raise HTTPException(
                status_code=400,
                detail=f"Candidate description at index {idx} exceeds {settings.openvino_max_text_length} characters",
            )

    max_allowed = min(settings.openvino_max_rerank_top_k, len(candidates))
    if top_k < 1 or top_k > max_allowed:
        raise HTTPException(
            status_code=400,
            detail=f"top_k must be between 1 and {max_allowed}",
        )


def _validate_pattern_description(description: str) -> None:
    """Validate the pattern description for classification."""
    if not description or not description.strip():
        raise HTTPException(status_code=400, detail="pattern_description cannot be empty")
    if len(description) > settings.openvino_max_pattern_length:
        raise HTTPException(
            status_code=400,
            detail=f"pattern_description exceeds {settings.openvino_max_pattern_length} characters",
        )


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------


@app.get("/models/status")
async def get_model_status():
    """Get detailed model status."""
    manager = _require_manager()
    return manager.get_model_status()


@app.post("/models/warmup")
async def warmup_models():
    """ENH-2: Pre-load all models (useful for orchestrators)."""
    manager = _require_manager()
    await manager.initialize()
    return {"status": "all_models_loaded", "models": manager.get_model_status()}


@app.post("/embeddings", response_model=EmbeddingResponse)
async def generate_embeddings(request: EmbeddingRequest):
    """Generate embeddings for texts."""
    manager = _require_manager()
    _validate_text_batch(request.texts)  # CRIT-2: single validation call

    try:
        start_time = time.perf_counter()

        embeddings = await manager.generate_embeddings(
            texts=request.texts,
            normalize=request.normalize,
        )

        processing_time = time.perf_counter() - start_time

        return EmbeddingResponse(
            embeddings=embeddings.tolist(),
            model_name="BAAI/bge-large-en-v1.5",
            processing_time=processing_time,
        )

    except TimeoutError as exc:
        timeout = manager.inference_timeout
        logger.warning("Embedding generation timed out after %.2fs", timeout)
        raise HTTPException(
            status_code=504,
            detail=f"Embedding generation timed out after {timeout} seconds",
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error generating embeddings")
        raise HTTPException(status_code=500, detail="Embedding generation failed") from exc


@app.post("/rerank", response_model=RerankResponse)
async def rerank_candidates(request: RerankRequest):
    """Re-rank candidates using bge-reranker."""
    manager = _require_manager()
    _validate_rerank_payload(request.query, request.candidates, request.top_k)

    max_allowed = min(settings.openvino_max_rerank_top_k, len(request.candidates))
    top_k = max(1, min(request.top_k, max_allowed))

    try:
        start_time = time.perf_counter()

        ranked_candidates = await manager.rerank(
            query=request.query,
            candidates=request.candidates,
            top_k=top_k,
        )

        processing_time = time.perf_counter() - start_time

        return RerankResponse(
            ranked_candidates=ranked_candidates,
            model_name="bge-reranker-base",
            processing_time=processing_time,
        )

    except TimeoutError as exc:
        timeout = manager.inference_timeout
        logger.warning("Re-ranking timed out after %.2fs", timeout)
        raise HTTPException(
            status_code=504,
            detail=f"Re-ranking timed out after {timeout} seconds",
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error re-ranking candidates")
        raise HTTPException(status_code=500, detail="Re-ranking failed") from exc


@app.post("/classify", response_model=ClassifyResponse)
async def classify_pattern(request: ClassifyRequest):
    """Classify pattern using flan-t5-small."""
    manager = _require_manager()
    _validate_pattern_description(request.pattern_description)  # CRIT-2: single validation call

    try:
        start_time = time.perf_counter()

        classification = await manager.classify_pattern(
            pattern_description=request.pattern_description,
        )

        processing_time = time.perf_counter() - start_time

        return ClassifyResponse(
            category=classification["category"],
            priority=classification["priority"],
            model_name="flan-t5-small",
            processing_time=processing_time,
        )

    except TimeoutError as exc:
        timeout = manager.inference_timeout
        logger.warning("Pattern classification timed out after %.2fs", timeout)
        raise HTTPException(
            status_code=504,
            detail=f"Classification timed out after {timeout} seconds",
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error classifying pattern")
        raise HTTPException(status_code=500, detail="Classification failed") from exc


# ---------------------------------------------------------------------------
# Entrypoint (LOW-1: configurable port)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=settings.service_port, reload=True)  # noqa: S104
